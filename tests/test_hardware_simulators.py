from zunder_zapfe.hardware.layer import HardwareLayer
from zunder_zapfe.hardware.simulators import (
    SimulatedEmergencyStop,
    SimulatedFlowMeter,
    SimulatedNfcReader,
    SimulatedValve,
)


def test_simulated_nfc_reader_can_present_and_remove_card() -> None:
    reader = SimulatedNfcReader()

    reader.present_card("04AABBCCDD")
    assert reader.snapshot().uid == "04AABBCCDD"
    assert reader.snapshot().state == "card"

    reader.remove_card()
    assert reader.snapshot().uid is None
    assert reader.snapshot().state == "ready"


def test_simulated_flow_meter_only_counts_during_measurement() -> None:
    meter = SimulatedFlowMeter()

    meter.add_pulses(3)
    assert meter.snapshot().pulse_count == 0

    meter.begin_measurement()
    meter.add_pulses(12)
    reading = meter.end_measurement()

    assert reading.pulse_count == 12
    assert reading.measuring is False


def test_simulated_emergency_stop_changes_state() -> None:
    emergency_stop = SimulatedEmergencyStop()

    emergency_stop.trigger()
    assert emergency_stop.snapshot().active is True

    emergency_stop.release()
    assert emergency_stop.snapshot().active is False


def test_hardware_layer_closes_valve_on_start_and_stop() -> None:
    valve = SimulatedValve()
    hardware = HardwareLayer(
        nfc=SimulatedNfcReader(),
        valve=valve,
        flow_meter=SimulatedFlowMeter(),
        emergency_stop=SimulatedEmergencyStop(),
    )
    valve.open()

    hardware.start()
    assert valve.snapshot().is_open is False

    valve.open()
    hardware.stop()
    assert valve.snapshot().is_open is False
