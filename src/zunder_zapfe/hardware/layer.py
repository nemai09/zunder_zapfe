"""Composition root for all hardware used by the application."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from zunder_zapfe.hardware.adapters import Acr122uNfcReader, GpioFlowMeter, GpioValve
from zunder_zapfe.hardware.interfaces import EmergencyStop, FlowMeter, NfcReader, Valve
from zunder_zapfe.hardware.models import status_dict
from zunder_zapfe.hardware.simulators import (
    SimulatedEmergencyStop,
    SimulatedFlowMeter,
    SimulatedNfcReader,
    SimulatedValve,
)


@dataclass
class HardwareLayer:
    """Hardware dependencies consumed by backend application services."""

    nfc: NfcReader
    valve: Valve
    flow_meter: FlowMeter
    emergency_stop: EmergencyStop

    def start(self) -> None:
        # Safety-related components are initialized before input devices.
        self.valve.start()
        self.flow_meter.start()
        self.emergency_stop.start()
        self.nfc.start()

    def stop(self) -> None:
        # Closing the valve is the first shutdown action, even in simulation.
        self.valve.stop()
        self.flow_meter.stop()
        self.emergency_stop.stop()
        self.nfc.stop()

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {
            "nfc": status_dict(self.nfc.snapshot()),
            "valve": status_dict(self.valve.snapshot()),
            "flow_meter": status_dict(self.flow_meter.snapshot()),
            "emergency_stop": status_dict(self.emergency_stop.snapshot()),
        }


def create_default_hardware(
    *,
    simulate_nfc: bool = False,
    simulate_tap_hardware: bool = False,
    environment: Mapping[str, str] | None = None,
) -> HardwareLayer:
    """Build target hardware; simulators require an explicit development flag."""
    values = environment if environment is not None else os.environ
    if simulate_tap_hardware:
        valve: Valve = SimulatedValve()
        flow_meter: FlowMeter = SimulatedFlowMeter()
    else:
        valve_pin = _gpio_number(values, "ZUNDER_ZAPFE_VALVE_GPIO", 17)
        flow_pin = _gpio_number(values, "ZUNDER_ZAPFE_FLOW_GPIO", 27)
        if valve_pin == flow_pin:
            raise ValueError("Valve and flow GPIO must be different")
        valve = GpioValve(valve_pin)
        flow_meter = GpioFlowMeter(flow_pin)

    return HardwareLayer(
        nfc=SimulatedNfcReader() if simulate_nfc else Acr122uNfcReader(),
        valve=valve,
        flow_meter=flow_meter,
        emergency_stop=SimulatedEmergencyStop(),
    )


def _gpio_number(values: Mapping[str, str], name: str, default: int) -> int:
    try:
        pin = int(values.get(name, str(default)))
    except ValueError as error:
        raise ValueError(f"{name} must be an integer BCM GPIO number") from error
    if not 0 <= pin <= 27:
        raise ValueError(f"{name} must be between BCM GPIO 0 and 27")
    return pin
