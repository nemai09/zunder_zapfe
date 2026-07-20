"""Application service connecting NFC, tap control and persistent bookings."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from zunder_zapfe.backend.tap_controller import (
    PourRecord,
    TapController,
    TapLimits,
    TapState,
)
from zunder_zapfe.hardware import HardwareLayer
from zunder_zapfe.persistence.models import BookingCompletion, BookingKind, UserRole
from zunder_zapfe.persistence.repository import (
    ActiveTapContext,
    NewTapBooking,
    Repository,
    canonicalize_nfc_uid,
)


class TapUnavailable(RuntimeError):
    """Raised when the persistent tap context does not permit a pour."""


@dataclass(frozen=True)
class FlowCalibration:
    """Integer-only conversion between sensor pulses and milliliters."""

    pulses_per_liter: int = 500

    def __post_init__(self) -> None:
        if self.pulses_per_liter <= 0:
            raise ValueError("Pulses per liter must be greater than zero")

    def target_pulses(self, volume_ml: int) -> int:
        if volume_ml <= 0:
            raise ValueError("Target volume must be greater than zero")
        return max(1, (volume_ml * self.pulses_per_liter + 999) // 1000)

    def measured_volume_ml(self, pulse_count: int) -> int:
        if pulse_count < 0:
            raise ValueError("Pulse count must not be negative")
        return (pulse_count * 1000 + self.pulses_per_liter // 2) // self.pulses_per_liter


@dataclass(frozen=True)
class AuthenticatedUser:
    id: int
    display_name: str
    is_admin: bool
    special_portion_ml: int | None


@dataclass(frozen=True)
class _PendingBooking:
    event_id: int
    user_id: int
    beverage_id: int
    keg_id: int
    target_volume_ml: int | None
    price_per_liter_cents: int


class TapService:
    """Own the integrated runtime flow from NFC authentication to booking."""

    def __init__(
        self,
        hardware: HardwareLayer,
        sessions: sessionmaker[Session],
        limits: TapLimits,
        *,
        calibration: FlowCalibration | None = None,
        standard_portions_ml: tuple[int, ...] = (300, 500),
        monotonic_clock: Callable[[], float] = time.monotonic,
        timestamp_clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        run_background: bool = True,
        background_interval_seconds: float = 0.05,
    ) -> None:
        if background_interval_seconds <= 0:
            raise ValueError("Background interval must be greater than zero")
        self._hardware = hardware
        self._sessions = sessions
        self._calibration = calibration or FlowCalibration()
        normalized_portions = tuple(dict.fromkeys(standard_portions_ml))
        if len(normalized_portions) < 2 or any(value <= 0 for value in normalized_portions):
            raise ValueError("At least two positive standard portions are required")
        self._standard_portions_ml = normalized_portions
        self._timestamp_clock = timestamp_clock
        self._run_background = run_background
        self._background_interval_seconds = background_interval_seconds
        self._mutex = threading.RLock()
        self._background_stop = threading.Event()
        self._background_thread: threading.Thread | None = None
        self._authenticated_user: AuthenticatedUser | None = None
        self._pending_booking: _PendingBooking | None = None
        self._last_presented_uid: str | None = None
        self._last_state = TapState.STARTING
        self._last_background_error: str | None = None
        self._persistence_error: str | None = None
        self._last_booking: dict[str, Any] | None = None
        self._controller = TapController(
            hardware,
            limits,
            clock=monotonic_clock,
            record_sink=self._persist_record,
            supervise=False,
        )

    @property
    def controller(self) -> TapController:
        return self._controller

    def start(self) -> None:
        with self._mutex:
            self._controller.start()
            self._last_state = self._controller.snapshot().state
            self._background_stop.clear()
            if self._run_background and not (
                self._background_thread and self._background_thread.is_alive()
            ):
                self._background_thread = threading.Thread(
                    target=self._background_loop,
                    name="tap-application-supervisor",
                    daemon=True,
                )
                self._background_thread.start()

    def shutdown(self) -> None:
        self._background_stop.set()
        if self._background_thread and self._background_thread is not threading.current_thread():
            self._background_thread.join(timeout=2)
        with self._mutex:
            self._controller.shutdown()
            self._authenticated_user = None
            self._pending_booking = None

    def authenticate_card(self, uid: str) -> bool:
        canonical_uid = canonicalize_nfc_uid(uid)
        with self._sessions() as session:
            user = Repository(session).find_active_user_by_card(canonical_uid)
            if user is None:
                return False
            authenticated = AuthenticatedUser(
                id=user.id,
                display_name=user.display_name,
                is_admin=user.role is UserRole.ADMIN,
                special_portion_ml=user.special_portion_ml,
            )

        accepted = self._controller.present_authenticated_card(
            str(authenticated.id), is_admin=authenticated.is_admin
        )
        with self._mutex:
            if accepted:
                self._authenticated_user = authenticated
                self._persistence_error = None
            return accepted

    def process_nfc_snapshot(self) -> bool:
        nfc = self._hardware.nfc.snapshot()
        if nfc.state != "card" or not nfc.uid:
            with self._mutex:
                self._last_presented_uid = None
            return False

        try:
            uid = canonicalize_nfc_uid(nfc.uid)
        except ValueError as error:
            self._record_technical_event(
                severity="warning",
                event_type="nfc.invalid_uid",
                message=str(error),
                details={"uid": nfc.uid},
            )
            return False

        with self._mutex:
            if uid == self._last_presented_uid:
                return False
            self._last_presented_uid = uid
        return self.authenticate_card(uid)

    def logout(self) -> None:
        self._controller.logout()
        with self._mutex:
            self._authenticated_user = None

    def start_portion(self, target_volume_ml: int) -> dict[str, Any]:
        if target_volume_ml <= 0:
            raise ValueError("Target volume must be greater than zero")
        user = self._require_authenticated_user()
        allowed = set(self._standard_portions_ml)
        if user.special_portion_ml is not None:
            allowed.add(user.special_portion_ml)
        if target_volume_ml not in allowed:
            raise TapUnavailable("Selected portion is not available for this user")
        self._prepare_booking(target_volume_ml)
        try:
            self._controller.start_portion(self._calibration.target_pulses(target_volume_ml))
        except Exception:
            with self._mutex:
                self._pending_booking = None
            raise
        return self.status_dict()

    def abort_portion(self) -> PourRecord:
        return self._controller.abort_portion()

    def start_manual_pour(self) -> dict[str, Any]:
        self._prepare_booking(None)
        try:
            self._controller.start_manual_pour()
        except Exception:
            with self._mutex:
                self._pending_booking = None
            raise
        return self.status_dict()

    def stop_manual_pour(self) -> PourRecord:
        return self._controller.stop_manual_pour()

    def start_top_up(self) -> dict[str, Any]:
        self._prepare_booking(None)
        try:
            self._controller.start_top_up()
        except Exception:
            with self._mutex:
                self._pending_booking = None
            raise
        return self.status_dict()

    def stop_top_up(self) -> PourRecord:
        return self._controller.stop_top_up()

    def enter_maintenance(self) -> None:
        self._controller.enter_maintenance()

    def start_maintenance_pour(self) -> dict[str, Any]:
        self._prepare_booking(None)
        try:
            self._controller.start_maintenance_pour()
        except Exception:
            with self._mutex:
                self._pending_booking = None
            raise
        return self.status_dict()

    def stop_maintenance_pour(self) -> PourRecord:
        return self._controller.stop_maintenance_pour()

    def exit_maintenance(self) -> None:
        self._controller.exit_maintenance()

    def heartbeat(self) -> None:
        self._controller.heartbeat()

    def register_activity(self) -> None:
        self._controller.register_activity()

    def reset_safety_lock(self) -> dict[str, Any]:
        """Reset a latched safety state while an active admin card is present."""
        nfc = self._hardware.nfc.snapshot()
        if nfc.state != "card" or not nfc.uid:
            raise TapUnavailable("Safety reset requires a presented admin card")

        try:
            canonical_uid = canonicalize_nfc_uid(nfc.uid)
        except ValueError as error:
            raise TapUnavailable("Safety reset requires a valid admin card") from error

        with self._sessions() as session:
            user = Repository(session).find_active_user_by_card(canonical_uid)
            if user is None or user.role is not UserRole.ADMIN:
                raise TapUnavailable("Safety reset requires an active admin card")

        previous = self._controller.snapshot()
        self._controller.reset_safety_lock(is_admin=True)
        with self._mutex:
            self._authenticated_user = None
            self._pending_booking = None
            self._persistence_error = None
            self._last_presented_uid = canonical_uid
            self._last_state = TapState.IDLE
        self._record_technical_event(
            severity="info",
            event_type="tap.safety_reset",
            message="Sicherheitssperre durch Admin-Karte zurueckgesetzt",
            details={
                "previous_state": previous.state.value,
                "admin_user_id": user.id,
            },
        )
        return self.status_dict()

    def poll(self) -> dict[str, Any]:
        status = self._controller.poll()
        self._observe_state(status.state, status.safety_reason)
        self._reconcile_authenticated_user(status.user_id)
        return self.status_dict()

    def status_dict(self) -> dict[str, Any]:
        status = self._controller.snapshot_dict()
        with self._mutex:
            user = self._authenticated_user
            pending = self._pending_booking
            status.update(
                {
                    "user_display_name": user.display_name if user else None,
                    "special_portion_ml": user.special_portion_ml if user else None,
                    "persistence_error": self._persistence_error,
                    "last_booking": self._last_booking,
                    "measured_volume_ml": self._calibration.measured_volume_ml(
                        int(status["measured_pulses"])
                    ),
                    "target_volume_ml": pending.target_volume_ml if pending else None,
                }
            )
        return status

    def portion_options(self) -> dict[str, Any]:
        status = self._controller.snapshot()
        with self._mutex:
            user = self._authenticated_user
            special = (
                user.special_portion_ml
                if user is not None and status.user_id == str(user.id)
                else None
            )
        return {
            "standard_portions_ml": list(self._standard_portions_ml),
            "special_portion_ml": special,
        }

    def current_consumption(self) -> dict[str, int]:
        user = self._require_authenticated_user()
        with self._sessions() as session:
            repository = Repository(session)
            context = self._require_active_context(repository)
            summary = repository.user_consumption(event_id=context.event_id, user_id=user.id)
            return asdict(summary)

    def current_keg(self) -> dict[str, Any]:
        with self._sessions() as session:
            repository = Repository(session)
            context = self._require_active_context(repository)
            return {
                **asdict(context),
                "remaining_volume_ml": repository.remaining_keg_volume_ml(context.keg_id),
            }

    def _prepare_booking(self, target_volume_ml: int | None) -> _PendingBooking:
        status = self._controller.snapshot()
        with self._mutex:
            if self._pending_booking is not None:
                raise TapUnavailable("A booking is already pending")
            user = self._authenticated_user
            if user is None or status.user_id != str(user.id):
                self._authenticated_user = None
                raise TapUnavailable("No active authenticated user")
            with self._sessions() as session:
                repository = Repository(session)
                context = self._require_active_context(repository)
                remaining_volume_ml = repository.remaining_keg_volume_ml(context.keg_id)
                if remaining_volume_ml <= 0:
                    raise TapUnavailable("The active keg has no calculated remaining volume")
                if target_volume_ml is not None and target_volume_ml > remaining_volume_ml:
                    raise TapUnavailable("Target volume exceeds calculated keg stock")
            pending = _PendingBooking(
                event_id=context.event_id,
                user_id=user.id,
                beverage_id=context.beverage_id,
                keg_id=context.keg_id,
                target_volume_ml=target_volume_ml,
                price_per_liter_cents=context.price_per_liter_cents,
            )
            self._pending_booking = pending
            return pending

    def _persist_record(self, record: PourRecord) -> None:
        with self._mutex:
            pending = self._pending_booking
            if pending is None or record.user_id != str(pending.user_id):
                self._persistence_error = "Persistent booking context is missing or inconsistent"
                self._controller.lock_for_fault("Zapfbuchung konnte nicht zugeordnet werden")
                return

            measured_volume_ml = self._calibration.measured_volume_ml(record.measured_pulses)
            try:
                with self._sessions.begin() as session:
                    booking = Repository(session).add_tap_booking(
                        NewTapBooking(
                            event_id=pending.event_id,
                            user_id=pending.user_id,
                            beverage_id=pending.beverage_id,
                            keg_id=pending.keg_id,
                            occurred_at=self._timestamp_clock(),
                            target_volume_ml=pending.target_volume_ml,
                            measured_volume_ml=measured_volume_ml,
                            measured_pulses=record.measured_pulses,
                            price_per_liter_cents=pending.price_per_liter_cents,
                            kind=BookingKind(record.kind.value),
                            completion=BookingCompletion(record.completion.value),
                            chargeable=record.chargeable,
                        )
                    )
                    booking_snapshot = {
                        "id": booking.id,
                        "measured_volume_ml": booking.measured_volume_ml,
                        "amount_cents": booking.amount_cents,
                        "kind": booking.kind.value,
                        "completion": booking.completion.value,
                    }
            except Exception as error:
                self._persistence_error = f"{type(error).__name__}: {error}"
                self._pending_booking = None
                self._controller.lock_for_fault("Zapfbuchung konnte nicht gespeichert werden")
                self._record_technical_event(
                    severity="error",
                    event_type="booking.persistence_failed",
                    message="Zapfbuchung konnte nicht gespeichert werden",
                    details={"error": self._persistence_error},
                )
                return

            self._last_booking = booking_snapshot
            self._persistence_error = None
            self._pending_booking = None

    def _require_authenticated_user(self) -> AuthenticatedUser:
        status = self._controller.snapshot()
        with self._mutex:
            user = self._authenticated_user
            if user is None or status.user_id != str(user.id):
                self._authenticated_user = None
                raise TapUnavailable("No active authenticated user")
            return user

    @staticmethod
    def _require_active_context(repository: Repository) -> ActiveTapContext:
        context = repository.active_tap_context()
        if context is None:
            raise TapUnavailable("No matching active event, keg and beverage")
        return context

    def _reconcile_authenticated_user(self, controller_user_id: str | None) -> None:
        with self._mutex:
            if controller_user_id is None:
                self._authenticated_user = None

    def _observe_state(self, state: TapState, reason: str | None) -> None:
        with self._mutex:
            previous = self._last_state
            self._last_state = state
        if state == previous or state not in {TapState.FAULT_LOCKED, TapState.EMERGENCY_STOP}:
            return
        self._record_technical_event(
            severity="error",
            event_type=f"tap.{state.value}",
            message=reason or state.value,
            details={"previous_state": previous.value, "state": state.value},
        )

    def _record_technical_event(
        self, *, severity: str, event_type: str, message: str, details: Any = None
    ) -> None:
        try:
            with self._sessions.begin() as session:
                Repository(session).record_technical_event(
                    severity=severity,
                    event_type=event_type,
                    message=message,
                    details=details,
                )
        except Exception:
            # Hardware safety must never depend on diagnostic logging succeeding.
            return

    def _background_loop(self) -> None:
        while not self._background_stop.wait(self._background_interval_seconds):
            try:
                self.poll()
                self.process_nfc_snapshot()
                self._last_background_error = None
            except Exception as error:
                error_text = f"{type(error).__name__}: {error}"
                if error_text != self._last_background_error:
                    self._record_technical_event(
                        severity="error",
                        event_type="backend.supervisor_error",
                        message="Fehler in der Backend-Ueberwachung",
                        details={"error": error_text},
                    )
                    self._last_background_error = error_text
