import time

import pytest
from smartcard.Exceptions import CardRequestTimeoutException

from zunder_zapfe.hardware.adapters.acr122u import UID_COMMAND, Acr122uNfcReader
from zunder_zapfe.hardware.layer import HardwareLayer, create_default_hardware
from zunder_zapfe.hardware.simulators import (
    SimulatedEmergencyStop,
    SimulatedFlowMeter,
    SimulatedNfcReader,
    SimulatedValve,
)

ACR_READER_NAME = "ACS ACR122U PICC Interface 00 00"


class FakeCardConnection:
    def __init__(self, uid: list[int]) -> None:
        self.uid = uid
        self.connect_count = 0
        self.disconnect_count = 0
        self.commands: list[list[int]] = []

    def connect(self) -> None:
        self.connect_count += 1

    def transmit(self, command: list[int]) -> tuple[list[int], int, int]:
        self.commands.append(command)
        return self.uid, 0x90, 0x00

    def disconnect(self) -> None:
        self.disconnect_count += 1


class FakeCard:
    def __init__(self, connection: FakeCardConnection) -> None:
        self.reader = ACR_READER_NAME
        self.atr = [0x3B, 0x00]
        self.connection = connection

    def createConnection(self) -> FakeCardConnection:
        return self.connection


class TimeoutCardRequest:
    def __enter__(self) -> "TimeoutCardRequest":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def waitforcardevent(self) -> list[FakeCard]:
        time.sleep(0.005)
        raise CardRequestTimeoutException()


def test_simulated_nfc_reader_can_present_and_remove_card() -> None:
    reader = SimulatedNfcReader()

    reader.present_card("04AABBCCDD")
    assert reader.snapshot().uid == "04AABBCCDD"
    assert reader.snapshot().state == "card"

    reader.remove_card()
    assert reader.snapshot().uid is None
    assert reader.snapshot().state == "ready"


def test_acr122u_reads_uid_once_per_card_presence() -> None:
    connection = FakeCardConnection([0x04, 0xAA, 0xBB, 0xCC])
    card = FakeCard(connection)
    reader = Acr122uNfcReader(reader_provider=lambda: [ACR_READER_NAME])

    reader._process_card_event([card])
    reader._process_card_event([card])

    assert reader.snapshot().state == "card"
    assert reader.snapshot().uid == "04AABBCC"
    assert connection.connect_count == 1
    assert connection.disconnect_count == 1
    assert connection.commands == [UID_COMMAND]

    reader._process_card_event([])
    reader._process_card_event([card])

    assert connection.connect_count == 2


def test_acr122u_recovers_reader_status_after_usb_hotplug() -> None:
    available_readers: list[object] = []
    reader = Acr122uNfcReader(reader_provider=lambda: available_readers)

    reader._refresh_reader_status()
    assert reader.snapshot().state == "disconnected"

    available_readers.append(ACR_READER_NAME)
    reader._process_card_event([])
    assert reader.snapshot().state == "ready"

    available_readers.clear()
    reader._process_card_event([])
    assert reader.snapshot().state == "disconnected"


def test_acr122u_recreates_event_request_after_pcsc_failure() -> None:
    attempts = 0

    def request_factory(*, timeout: float) -> TimeoutCardRequest:
        nonlocal attempts
        assert timeout == 0.02
        attempts += 1
        if attempts == 1:
            raise RuntimeError("PC/SC service stopped")
        return TimeoutCardRequest()

    reader = Acr122uNfcReader(
        event_wait_timeout_seconds=0.02,
        reconnect_interval_seconds=0.01,
        card_request_factory=request_factory,
        reader_provider=lambda: [ACR_READER_NAME],
    )

    reader.start()
    deadline = time.monotonic() + 1
    while reader.snapshot().state != "ready":
        if time.monotonic() >= deadline:
            pytest.fail("NFC adapter did not recover after PC/SC failure")
        time.sleep(0.005)
    reader.stop()

    assert attempts >= 2
    assert reader._thread is not None
    assert reader._thread.is_alive() is False


@pytest.mark.parametrize(
    "settings",
    [
        {"event_wait_timeout_seconds": 0},
        {"reconnect_interval_seconds": 0},
    ],
)
def test_acr122u_rejects_nonpositive_monitor_intervals(settings: dict[str, float]) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        Acr122uNfcReader(**settings)


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


def test_default_hardware_can_explicitly_simulate_nfc_for_alpha_debugging() -> None:
    hardware = create_default_hardware(simulate_nfc=True)

    assert isinstance(hardware.nfc, SimulatedNfcReader)
    assert hardware.nfc.snapshot().simulated is True
