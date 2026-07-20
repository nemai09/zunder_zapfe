"""Safety-oriented state machine for authenticated and maintenance pours."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import StrEnum
from math import ceil
from typing import Any

from zunder_zapfe.hardware import HardwareLayer


class TapState(StrEnum):
    STARTING = "starting"
    IDLE = "idle"
    AUTHENTICATED = "authenticated"
    MANUAL_POURING = "manual_pouring"
    PORTION_POURING = "portion_pouring"
    TOP_UP_AVAILABLE = "top_up_available"
    TOP_UP_POURING = "top_up_pouring"
    MAINTENANCE = "maintenance"
    MAINTENANCE_POURING = "maintenance_pouring"
    FAULT_LOCKED = "fault_locked"
    EMERGENCY_STOP = "emergency_stop"
    STOPPED = "stopped"


class PourKind(StrEnum):
    MANUAL = "manual"
    PORTION = "portion"
    TOP_UP = "top_up"
    MAINTENANCE = "maintenance"


class PourCompletion(StrEnum):
    TARGET_REACHED = "target_reached"
    USER_ABORT = "user_abort"
    RELEASED = "released"
    LIMIT_REACHED = "limit_reached"
    FAULT = "fault"
    SHUTDOWN = "shutdown"


class InvalidTransition(RuntimeError):
    """Raised when an action is not permitted in the current tap state."""


@dataclass(frozen=True)
class TapLimits:
    first_pulse_timeout_seconds: float
    between_pulses_timeout_seconds: float
    maximum_pour_seconds: float
    watchdog_timeout_seconds: float
    top_up_window_seconds: float
    top_up_maximum_seconds: float
    top_up_maximum_pulses: int
    manual_maximum_seconds: float = 30.0
    session_timeout_seconds: float = 15.0
    flow_watchdog_enabled: bool = True

    def __post_init__(self) -> None:
        numeric_limits = (
            self.first_pulse_timeout_seconds,
            self.between_pulses_timeout_seconds,
            self.maximum_pour_seconds,
            self.watchdog_timeout_seconds,
            self.top_up_window_seconds,
            self.top_up_maximum_seconds,
            self.manual_maximum_seconds,
            self.session_timeout_seconds,
        )
        if any(value <= 0 for value in numeric_limits):
            raise ValueError("All time limits must be greater than zero")
        if self.top_up_maximum_pulses <= 0:
            raise ValueError("Top-up pulse limit must be greater than zero")


@dataclass(frozen=True)
class UserSession:
    user_id: str
    is_admin: bool


@dataclass(frozen=True)
class PourRecord:
    sequence: int
    kind: PourKind
    user_id: str
    measured_pulses: int
    target_pulses: int | None
    completion: PourCompletion
    chargeable: bool


@dataclass(frozen=True)
class TapStatus:
    state: TapState
    user_id: str | None
    is_admin: bool
    valve_open: bool
    measured_pulses: int
    target_pulses: int | None
    top_up_remaining_ms: int | None
    session_remaining_ms: int | None
    safety_reason: str | None


@dataclass
class _ActivePour:
    kind: PourKind
    target_pulses: int | None
    started_at: float
    last_seen_pulses: int = 0


ACTIVE_POUR_STATES = {
    TapState.MANUAL_POURING,
    TapState.PORTION_POURING,
    TapState.TOP_UP_POURING,
    TapState.MAINTENANCE_POURING,
}


class TapController:
    """Coordinate tap hardware through explicit, testable state transitions."""

    def __init__(
        self,
        hardware: HardwareLayer,
        limits: TapLimits,
        clock: Callable[[], float] = time.monotonic,
        *,
        record_sink: Callable[[PourRecord], None] | None = None,
        supervise: bool = True,
        supervisor_interval_seconds: float = 0.05,
    ) -> None:
        if supervisor_interval_seconds <= 0:
            raise ValueError("Supervisor interval must be greater than zero")
        self._hardware = hardware
        self._limits = limits
        self._clock = clock
        self._record_sink = record_sink
        self._supervise = supervise
        self._supervisor_interval_seconds = supervisor_interval_seconds
        self._mutex = threading.RLock()
        self._supervisor_stop = threading.Event()
        self._supervisor_thread: threading.Thread | None = None
        self._state = TapState.STARTING
        self._session: UserSession | None = None
        self._active_pour: _ActivePour | None = None
        self._top_up_deadline: float | None = None
        self._session_last_active_at: float | None = None
        self._last_heartbeat: float | None = None
        self._safety_reason: str | None = None
        self._records: list[PourRecord] = []

    def start(self) -> None:
        with self._mutex:
            self._hardware.valve.close()
            if self._hardware.emergency_stop.snapshot().active:
                self._state = TapState.EMERGENCY_STOP
                self._safety_reason = "Not-Aus ist beim Start aktiv"
            else:
                self._state = TapState.IDLE
                self._safety_reason = None
            self._supervisor_stop.clear()
            if self._supervise and not (
                self._supervisor_thread and self._supervisor_thread.is_alive()
            ):
                self._supervisor_thread = threading.Thread(
                    target=self._supervisor_loop,
                    name="tap-safety-supervisor",
                    daemon=True,
                )
                self._supervisor_thread.start()

    def shutdown(self) -> None:
        self._supervisor_stop.set()
        if self._supervisor_thread and self._supervisor_thread is not threading.current_thread():
            self._supervisor_thread.join(timeout=2)
        with self._mutex:
            if self._state in ACTIVE_POUR_STATES:
                self._finish_active_pour(PourCompletion.SHUTDOWN, TapState.STOPPED)
            else:
                self._hardware.valve.close()
            self._session = None
            self._session_last_active_at = None
            self._state = TapState.STOPPED

    def present_authenticated_card(self, user_id: str, *, is_admin: bool = False) -> bool:
        """Start a session; callers must resolve and validate the NFC card first."""
        if not user_id:
            raise ValueError("User ID must not be empty")
        with self._mutex:
            self._synchronize_emergency_stop()
            if self._state in ACTIVE_POUR_STATES:
                return False
            if self._state is not TapState.IDLE:
                return False
            self._session = UserSession(user_id=user_id, is_admin=is_admin)
            self._session_last_active_at = self._clock()
            self._state = TapState.AUTHENTICATED
            return True

    def logout(self) -> None:
        with self._mutex:
            self._require_state(TapState.AUTHENTICATED, TapState.TOP_UP_AVAILABLE)
            self._session = None
            self._session_last_active_at = None
            self._top_up_deadline = None
            self._state = TapState.IDLE

    def start_portion(self, target_pulses: int) -> None:
        if target_pulses <= 0:
            raise ValueError("Target pulse count must be greater than zero")
        with self._mutex:
            self._require_state(TapState.AUTHENTICATED)
            self._begin_pour(PourKind.PORTION, target_pulses, TapState.PORTION_POURING)

    def start_manual_pour(self) -> None:
        with self._mutex:
            self._require_state(TapState.AUTHENTICATED)
            self._begin_pour(PourKind.MANUAL, None, TapState.MANUAL_POURING)

    def stop_manual_pour(self) -> PourRecord:
        with self._mutex:
            self._require_state(TapState.MANUAL_POURING)
            return self._finish_active_pour(PourCompletion.RELEASED, TapState.AUTHENTICATED)

    def abort_portion(self) -> PourRecord:
        with self._mutex:
            self._require_state(TapState.PORTION_POURING)
            return self._finish_active_pour(PourCompletion.USER_ABORT, TapState.AUTHENTICATED)

    def start_top_up(self) -> None:
        with self._mutex:
            self._require_state(TapState.TOP_UP_AVAILABLE)
            now = self._clock()
            if self._top_up_deadline is None or now >= self._top_up_deadline:
                self._top_up_deadline = None
                self._state = TapState.AUTHENTICATED
                raise InvalidTransition("Top-up window has expired")
            self._begin_pour(PourKind.TOP_UP, None, TapState.TOP_UP_POURING)

    def stop_top_up(self) -> PourRecord:
        with self._mutex:
            self._require_state(TapState.TOP_UP_POURING)
            return self._finish_active_pour(PourCompletion.RELEASED, TapState.AUTHENTICATED)

    def enter_maintenance(self) -> None:
        with self._mutex:
            self._require_state(TapState.AUTHENTICATED)
            if self._session is None or not self._session.is_admin:
                raise InvalidTransition("Maintenance mode requires an admin session")
            self._session_last_active_at = self._clock()
            self._state = TapState.MAINTENANCE

    def start_maintenance_pour(self) -> None:
        with self._mutex:
            self._require_state(TapState.MAINTENANCE)
            self._begin_pour(PourKind.MAINTENANCE, None, TapState.MAINTENANCE_POURING)

    def stop_maintenance_pour(self) -> PourRecord:
        with self._mutex:
            self._require_state(TapState.MAINTENANCE_POURING)
            return self._finish_active_pour(PourCompletion.RELEASED, TapState.MAINTENANCE)

    def exit_maintenance(self) -> None:
        with self._mutex:
            self._require_state(TapState.MAINTENANCE)
            self._session_last_active_at = self._clock()
            self._state = TapState.AUTHENTICATED

    def heartbeat(self) -> None:
        with self._mutex:
            if self._state in ACTIVE_POUR_STATES:
                self._last_heartbeat = self._clock()

    def register_activity(self) -> None:
        """Refresh the authenticated session after an intentional UI interaction."""
        with self._mutex:
            self._require_state(TapState.AUTHENTICATED, TapState.MANUAL_POURING)
            self._session_last_active_at = self._clock()

    def poll(self) -> TapStatus:
        """Apply sensor, target, timeout and watchdog transitions."""
        with self._mutex:
            self._synchronize_emergency_stop()
            now = self._clock()

            if self._state is TapState.TOP_UP_AVAILABLE:
                if self._top_up_deadline is not None and now >= self._top_up_deadline:
                    self._top_up_deadline = None
                    self._session_last_active_at = now
                    self._state = TapState.AUTHENTICATED

            if (
                self._state is TapState.AUTHENTICATED
                and self._session_last_active_at is not None
                and now - self._session_last_active_at >= self._limits.session_timeout_seconds
            ):
                self._session = None
                self._session_last_active_at = None
                self._state = TapState.IDLE

            if self._state in ACTIVE_POUR_STATES:
                self._poll_active_pour(now)

            return self._status_unlocked()

    def lock_for_fault(self, reason: str) -> None:
        if not reason:
            raise ValueError("Fault reason must not be empty")
        with self._mutex:
            self._lock_safely(TapState.FAULT_LOCKED, reason)

    def reset_safety_lock(self, *, is_admin: bool) -> None:
        with self._mutex:
            self._require_state(TapState.FAULT_LOCKED, TapState.EMERGENCY_STOP)
            if not is_admin:
                raise InvalidTransition("Safety reset requires an admin")
            if self._hardware.emergency_stop.snapshot().active:
                raise InvalidTransition("Emergency stop is still active")
            self._hardware.valve.close()
            self._session = None
            self._session_last_active_at = None
            self._safety_reason = None
            self._state = TapState.IDLE

    def snapshot(self) -> TapStatus:
        with self._mutex:
            return self._status_unlocked()

    def snapshot_dict(self) -> dict[str, Any]:
        return asdict(self.snapshot())

    @property
    def records(self) -> tuple[PourRecord, ...]:
        with self._mutex:
            return tuple(self._records)

    def _begin_pour(self, kind: PourKind, target_pulses: int | None, next_state: TapState) -> None:
        self._synchronize_emergency_stop()
        if self._state in {TapState.EMERGENCY_STOP, TapState.FAULT_LOCKED}:
            raise InvalidTransition("Tap is safety-locked")
        now = self._clock()
        self._hardware.flow_meter.begin_measurement()
        self._active_pour = _ActivePour(
            kind=kind,
            target_pulses=target_pulses,
            started_at=now,
        )
        self._last_heartbeat = now
        self._top_up_deadline = None
        try:
            self._hardware.valve.open()
        except Exception as error:
            self._hardware.valve.close()
            self._hardware.flow_meter.end_measurement()
            self._active_pour = None
            self._lock_safely(TapState.FAULT_LOCKED, f"Ventil konnte nicht oeffnen: {error}")
            raise
        self._state = next_state

    def _poll_active_pour(self, now: float) -> None:
        active = self._active_pour
        if active is None:
            self._lock_safely(TapState.FAULT_LOCKED, "Aktiver Zapfkontext fehlt")
            return

        reading = self._hardware.flow_meter.snapshot()
        if reading.pulse_count > active.last_seen_pulses:
            active.last_seen_pulses = reading.pulse_count

        if active.kind is PourKind.PORTION and reading.pulse_count >= (active.target_pulses or 0):
            self._finish_active_pour(PourCompletion.TARGET_REACHED, TapState.TOP_UP_AVAILABLE)
            self._top_up_deadline = now + self._limits.top_up_window_seconds
            return

        if active.kind is PourKind.TOP_UP:
            if reading.pulse_count >= self._limits.top_up_maximum_pulses:
                self._finish_active_pour(PourCompletion.LIMIT_REACHED, TapState.AUTHENTICATED)
                return
            if now - active.started_at >= self._limits.top_up_maximum_seconds:
                self._finish_active_pour(PourCompletion.LIMIT_REACHED, TapState.AUTHENTICATED)
                return

        if self._last_heartbeat is None or (
            now - self._last_heartbeat >= self._limits.watchdog_timeout_seconds
        ):
            self._lock_safely(TapState.FAULT_LOCKED, "Steuerungs-Watchdog abgelaufen")
            return

        if self._limits.flow_watchdog_enabled:
            if reading.pulse_count == 0:
                if now - active.started_at >= self._limits.first_pulse_timeout_seconds:
                    self._lock_safely(TapState.FAULT_LOCKED, "Kein Durchfluss erkannt")
                return

            if reading.last_pulse_at is not None and (
                now - reading.last_pulse_at >= self._limits.between_pulses_timeout_seconds
            ):
                self._lock_safely(TapState.FAULT_LOCKED, "Durchflussimpulse ausgeblieben")
                return

        if active.kind is PourKind.MANUAL:
            if now - active.started_at >= self._limits.manual_maximum_seconds:
                self._finish_active_pour(PourCompletion.LIMIT_REACHED, TapState.AUTHENTICATED)
            return

        if now - active.started_at >= self._limits.maximum_pour_seconds:
            self._lock_safely(TapState.FAULT_LOCKED, "Maximale Zapfdauer ueberschritten")

    def _synchronize_emergency_stop(self) -> None:
        if self._hardware.emergency_stop.snapshot().active:
            self._lock_safely(TapState.EMERGENCY_STOP, "Not-Aus aktiv")

    def _lock_safely(self, state: TapState, reason: str) -> None:
        if self._state in ACTIVE_POUR_STATES and self._active_pour is not None:
            self._finish_active_pour(PourCompletion.FAULT, state)
        else:
            self._hardware.valve.close()
            self._state = state
        self._session = None
        self._session_last_active_at = None
        self._top_up_deadline = None
        self._safety_reason = reason

    def _finish_active_pour(self, completion: PourCompletion, next_state: TapState) -> PourRecord:
        active = self._active_pour
        session = self._session
        if active is None or session is None:
            self._hardware.valve.close()
            raise RuntimeError("Cannot finish pour without active context and session")

        # Closing the valve always precedes measurement finalization and state changes.
        self._hardware.valve.close()
        reading = self._hardware.flow_meter.end_measurement()
        record = PourRecord(
            sequence=len(self._records) + 1,
            kind=active.kind,
            user_id=session.user_id,
            measured_pulses=reading.pulse_count,
            target_pulses=active.target_pulses,
            completion=completion,
            chargeable=active.kind is not PourKind.MAINTENANCE,
        )
        self._records.append(record)
        self._active_pour = None
        self._last_heartbeat = None
        self._state = next_state
        if next_state in {TapState.AUTHENTICATED, TapState.MAINTENANCE}:
            self._session_last_active_at = self._clock()
        if self._record_sink is not None:
            self._record_sink(record)
        return record

    def _status_unlocked(self) -> TapStatus:
        reading = self._hardware.flow_meter.snapshot()
        valve = self._hardware.valve.snapshot()
        top_up_remaining_ms = None
        if self._state is TapState.TOP_UP_AVAILABLE and self._top_up_deadline is not None:
            top_up_remaining_ms = max(0, ceil((self._top_up_deadline - self._clock()) * 1000))
        session_remaining_ms = None
        if self._session is not None and self._session_last_active_at is not None:
            if self._state in ACTIVE_POUR_STATES:
                session_remaining_ms = ceil(self._limits.session_timeout_seconds * 1000)
            else:
                remaining_seconds = self._limits.session_timeout_seconds - (
                    self._clock() - self._session_last_active_at
                )
                session_remaining_ms = max(0, ceil(remaining_seconds * 1000))
        return TapStatus(
            state=self._state,
            user_id=self._session.user_id if self._session else None,
            is_admin=self._session.is_admin if self._session else False,
            valve_open=valve.is_open,
            measured_pulses=reading.pulse_count if self._active_pour else 0,
            target_pulses=self._active_pour.target_pulses if self._active_pour else None,
            top_up_remaining_ms=top_up_remaining_ms,
            session_remaining_ms=session_remaining_ms,
            safety_reason=self._safety_reason,
        )

    def _require_state(self, *allowed: TapState) -> None:
        self._synchronize_emergency_stop()
        if self._state not in allowed:
            expected = ", ".join(state.value for state in allowed)
            raise InvalidTransition(
                f"Action requires state {expected}; current state is {self._state.value}"
            )

    def _supervisor_loop(self) -> None:
        while not self._supervisor_stop.wait(self._supervisor_interval_seconds):
            try:
                self.poll()
            except Exception as error:
                with self._mutex:
                    self._lock_safely(
                        TapState.FAULT_LOCKED,
                        f"Interner Fehler der Sicherheitsueberwachung: {error}",
                    )


def development_limits(
    *,
    session_timeout_seconds: float = 15.0,
    manual_maximum_seconds: float = 30.0,
    flow_watchdog_enabled: bool = True,
) -> TapLimits:
    """Non-production limits used while only simulated tap hardware is present."""
    return TapLimits(
        first_pulse_timeout_seconds=2.0,
        between_pulses_timeout_seconds=1.0,
        maximum_pour_seconds=30.0,
        watchdog_timeout_seconds=2.0,
        top_up_window_seconds=8.0,
        top_up_maximum_seconds=3.0,
        top_up_maximum_pulses=100,
        manual_maximum_seconds=manual_maximum_seconds,
        session_timeout_seconds=session_timeout_seconds,
        flow_watchdog_enabled=flow_watchdog_enabled,
    )
