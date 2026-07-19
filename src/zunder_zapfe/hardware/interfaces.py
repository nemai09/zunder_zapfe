"""Contracts implemented by real hardware adapters and development simulators."""

from __future__ import annotations

from typing import Protocol

from zunder_zapfe.hardware.models import (
    EmergencyStopStatus,
    FlowReading,
    NfcStatus,
    ValveStatus,
)


class HardwareError(RuntimeError):
    """Base error raised when a hardware operation cannot be completed safely."""


class NfcReader(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def snapshot(self) -> NfcStatus: ...


class Valve(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def open(self) -> None: ...

    def close(self) -> None: ...

    def snapshot(self) -> ValveStatus: ...


class FlowMeter(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def begin_measurement(self) -> None: ...

    def end_measurement(self) -> FlowReading: ...

    def snapshot(self) -> FlowReading: ...


class EmergencyStop(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def snapshot(self) -> EmergencyStopStatus: ...
