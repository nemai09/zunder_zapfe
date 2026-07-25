"""GPIO adapters used by the Raspberry Pi target application."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Protocol

from zunder_zapfe.hardware.interfaces import HardwareError
from zunder_zapfe.hardware.models import FlowReading, ValveStatus


class DigitalOutput(Protocol):
    def on(self) -> None: ...

    def off(self) -> None: ...

    def close(self) -> None: ...


class PulseInput(Protocol):
    when_activated: Callable[[], None] | None

    def close(self) -> None: ...


OutputFactory = Callable[[int], DigitalOutput]
InputFactory = Callable[[int], PulseInput]


def _gpiozero_output(pin: int) -> DigitalOutput:
    from gpiozero import DigitalOutputDevice

    return DigitalOutputDevice(pin, active_high=True, initial_value=False)


def _gpiozero_pulse_input(pin: int) -> PulseInput:
    from gpiozero import DigitalInputDevice

    # Bei pull_up=True ist LOW aktiv. when_activated entspricht damit der
    # fallenden Flanke eines Open-Collector-Durchflusssensors.
    return DigitalInputDevice(pin, pull_up=True)


class GpioValve:
    """Normally-closed valve controlled by an active-high driver input."""

    def __init__(self, pin: int, *, output_factory: OutputFactory = _gpiozero_output) -> None:
        self.pin = pin
        self._output_factory = output_factory
        self._device: DigitalOutput | None = None
        self._is_open = False
        self._available = False
        self._detail = "GPIO noch nicht gestartet"
        self._lock = threading.RLock()

    def start(self) -> None:
        with self._lock:
            if self._device is not None:
                self.stop()
            try:
                device = self._output_factory(self.pin)
                device.off()
            except Exception as error:
                self._available = False
                self._is_open = False
                self._detail = f"Ventilausgang BCM {self.pin} nicht verfügbar: {error}"
                raise HardwareError(self._detail) from error
            self._device = device
            self._is_open = False
            self._available = True
            self._detail = f"Ventilausgang BCM {self.pin}, aktiv HIGH"

    def stop(self) -> None:
        with self._lock:
            device = self._device
            self._device = None
            self._is_open = False
            self._available = False
            if device is None:
                return
            try:
                device.off()
            finally:
                device.close()
            self._detail = f"Ventilausgang BCM {self.pin} gestoppt"

    def open(self) -> None:
        with self._lock:
            device = self._require_device()
            try:
                device.on()
            except Exception as error:
                self._is_open = False
                self._available = False
                self._detail = f"Ventilausgang BCM {self.pin} fehlgeschlagen: {error}"
                try:
                    device.off()
                finally:
                    raise HardwareError(self._detail) from error
            self._is_open = True

    def close(self) -> None:
        with self._lock:
            self._is_open = False
            if self._device is None:
                return
            try:
                self._device.off()
            except Exception as error:
                self._available = False
                self._detail = f"Ventilausgang BCM {self.pin} konnte nicht schließen: {error}"
                raise HardwareError(self._detail) from error

    def snapshot(self) -> ValveStatus:
        with self._lock:
            return ValveStatus(
                is_open=self._is_open,
                available=self._available,
                simulated=False,
                detail=self._detail,
            )

    def _require_device(self) -> DigitalOutput:
        if self._device is None or not self._available:
            raise HardwareError(f"Ventilausgang BCM {self.pin} ist nicht verfügbar")
        return self._device


class GpioFlowMeter:
    """Counts falling edges from an open-collector flow sensor."""

    def __init__(
        self,
        pin: int,
        *,
        input_factory: InputFactory = _gpiozero_pulse_input,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.pin = pin
        self._input_factory = input_factory
        self._clock = clock
        self._device: PulseInput | None = None
        self._pulse_count = 0
        self._measuring = False
        self._last_pulse_at: float | None = None
        self._available = False
        self._detail = "GPIO noch nicht gestartet"
        self._lock = threading.Lock()

    def start(self) -> None:
        device: PulseInput | None = None
        try:
            device = self._input_factory(self.pin)
            device.when_activated = self._record_falling_edge
        except Exception as error:
            if device is not None:
                device.close()
            with self._lock:
                self._available = False
                self._detail = f"Durchflusseingang BCM {self.pin} nicht verfügbar: {error}"
            raise HardwareError(self._detail) from error
        with self._lock:
            self._device = device
            self._pulse_count = 0
            self._measuring = False
            self._last_pulse_at = None
            self._available = True
            self._detail = f"Durchflusseingang BCM {self.pin}, fallende Flanke"

    def stop(self) -> None:
        with self._lock:
            device = self._device
            self._device = None
            self._measuring = False
            self._available = False
            self._detail = f"Durchflusseingang BCM {self.pin} gestoppt"
        if device is not None:
            device.when_activated = None
            device.close()

    def begin_measurement(self) -> None:
        with self._lock:
            self._require_device()
            self._pulse_count = 0
            self._last_pulse_at = None
            self._measuring = True

    def end_measurement(self) -> FlowReading:
        with self._lock:
            self._measuring = False
            return self._snapshot_unlocked()

    def snapshot(self) -> FlowReading:
        with self._lock:
            return self._snapshot_unlocked()

    def _record_falling_edge(self) -> None:
        with self._lock:
            if not self._measuring:
                return
            self._pulse_count += 1
            self._last_pulse_at = self._clock()

    def _require_device(self) -> PulseInput:
        if self._device is None or not self._available:
            raise HardwareError(f"Durchflusseingang BCM {self.pin} ist nicht verfügbar")
        return self._device

    def _snapshot_unlocked(self) -> FlowReading:
        return FlowReading(
            pulse_count=self._pulse_count,
            measuring=self._measuring,
            last_pulse_at=self._last_pulse_at,
            available=self._available,
            simulated=False,
            detail=self._detail,
        )
