"""In-memory hardware implementations for development and automated tests."""

from __future__ import annotations

import threading

from zunder_zapfe.hardware.models import (
    EmergencyStopStatus,
    FlowReading,
    NfcStatus,
    ValveStatus,
)


class SimulatedNfcReader:
    def __init__(self) -> None:
        self._status = NfcStatus(state="ready", reader="Simulated NFC reader", simulated=True)
        self._lock = threading.Lock()

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def snapshot(self) -> NfcStatus:
        with self._lock:
            return self._status

    def present_card(self, uid: str) -> None:
        with self._lock:
            self._status = NfcStatus(
                state="card", reader="Simulated NFC reader", uid=uid, simulated=True
            )

    def remove_card(self) -> None:
        with self._lock:
            self._status = NfcStatus(state="ready", reader="Simulated NFC reader", simulated=True)


class SimulatedValve:
    """Valve simulator whose startup and shutdown state is always closed."""

    def __init__(self) -> None:
        self._is_open = False
        self._lock = threading.Lock()

    def start(self) -> None:
        self.close()

    def stop(self) -> None:
        self.close()

    def open(self) -> None:
        with self._lock:
            self._is_open = True

    def close(self) -> None:
        with self._lock:
            self._is_open = False

    def snapshot(self) -> ValveStatus:
        with self._lock:
            return ValveStatus(is_open=self._is_open, simulated=True)


class SimulatedFlowMeter:
    def __init__(self) -> None:
        self._pulse_count = 0
        self._measuring = False
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            self._pulse_count = 0
            self._measuring = False

    def stop(self) -> None:
        with self._lock:
            self._measuring = False

    def begin_measurement(self) -> None:
        with self._lock:
            self._pulse_count = 0
            self._measuring = True

    def end_measurement(self) -> FlowReading:
        with self._lock:
            self._measuring = False
            return self._snapshot_unlocked()

    def snapshot(self) -> FlowReading:
        with self._lock:
            return self._snapshot_unlocked()

    def add_pulses(self, count: int = 1) -> None:
        if count < 0:
            raise ValueError("Pulse count must not be negative")
        with self._lock:
            if self._measuring:
                self._pulse_count += count

    def _snapshot_unlocked(self) -> FlowReading:
        return FlowReading(
            pulse_count=self._pulse_count,
            measuring=self._measuring,
            simulated=True,
        )


class SimulatedEmergencyStop:
    def __init__(self) -> None:
        self._active = False
        self._lock = threading.Lock()

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def snapshot(self) -> EmergencyStopStatus:
        with self._lock:
            return EmergencyStopStatus(active=self._active, simulated=True)

    def trigger(self) -> None:
        with self._lock:
            self._active = True

    def release(self) -> None:
        with self._lock:
            self._active = False
