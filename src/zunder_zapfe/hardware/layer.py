"""Composition root for all hardware used by the application."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zunder_zapfe.hardware.adapters import Acr122uNfcReader
from zunder_zapfe.hardware.interfaces import EmergencyStop, FlowMeter, NfcReader, Valve
from zunder_zapfe.hardware.models import status_dict
from zunder_zapfe.hardware.simulators import (
    SimulatedEmergencyStop,
    SimulatedFlowMeter,
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


def create_default_hardware() -> HardwareLayer:
    """Build the current hybrid setup: real NFC plus simulated tap hardware."""
    return HardwareLayer(
        nfc=Acr122uNfcReader(),
        valve=SimulatedValve(),
        flow_meter=SimulatedFlowMeter(),
        emergency_stop=SimulatedEmergencyStop(),
    )
