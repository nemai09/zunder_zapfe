import time

import pytest

from zunder_zapfe.backend.tap_controller import (
    InvalidTransition,
    PourCompletion,
    PourKind,
    TapController,
    TapLimits,
    TapState,
)
from zunder_zapfe.hardware.layer import HardwareLayer
from zunder_zapfe.hardware.simulators import (
    SimulatedEmergencyStop,
    SimulatedFlowMeter,
    SimulatedNfcReader,
    SimulatedValve,
)


class ManualClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def tap_setup(
    *, flow_watchdog_enabled: bool = True
) -> tuple[
    TapController,
    HardwareLayer,
    ManualClock,
    SimulatedFlowMeter,
    SimulatedEmergencyStop,
]:
    clock = ManualClock()
    flow_meter = SimulatedFlowMeter(clock=clock)
    emergency_stop = SimulatedEmergencyStop()
    hardware = HardwareLayer(
        nfc=SimulatedNfcReader(),
        valve=SimulatedValve(),
        flow_meter=flow_meter,
        emergency_stop=emergency_stop,
    )
    limits = TapLimits(
        first_pulse_timeout_seconds=2,
        between_pulses_timeout_seconds=1,
        maximum_pour_seconds=10,
        watchdog_timeout_seconds=2,
        top_up_window_seconds=5,
        top_up_maximum_seconds=2,
        top_up_maximum_pulses=3,
        flow_watchdog_enabled=flow_watchdog_enabled,
    )
    hardware.start()
    controller = TapController(hardware, limits, clock=clock, supervise=False)
    controller.start()
    return controller, hardware, clock, flow_meter, emergency_stop


def test_complete_simulated_portion_and_top_up() -> None:
    controller, hardware, clock, flow_meter, _emergency_stop = tap_setup()

    assert controller.present_authenticated_card("user-1") is True
    controller.start_portion(target_pulses=10)
    assert hardware.valve.snapshot().is_open is True

    flow_meter.add_pulses(6)
    controller.heartbeat()
    assert controller.poll().state is TapState.PORTION_POURING

    clock.advance(0.1)
    flow_meter.add_pulses(4)
    controller.heartbeat()
    assert controller.poll().state is TapState.TOP_UP_AVAILABLE
    assert hardware.valve.snapshot().is_open is False

    controller.start_top_up()
    flow_meter.add_pulses(2)
    top_up = controller.stop_top_up()

    assert controller.snapshot().state is TapState.AUTHENTICATED
    assert [(record.kind, record.measured_pulses) for record in controller.records] == [
        (PourKind.PORTION, 10),
        (PourKind.TOP_UP, 2),
    ]
    assert top_up.completion is PourCompletion.RELEASED
    assert all(record.chargeable for record in controller.records)


def test_manual_abort_records_only_measured_pulses() -> None:
    controller, hardware, _clock, flow_meter, _emergency_stop = tap_setup()
    controller.present_authenticated_card("user-1")
    controller.start_portion(target_pulses=10)
    flow_meter.add_pulses(4)

    record = controller.abort_portion()

    assert record.measured_pulses == 4
    assert record.target_pulses == 10
    assert record.completion is PourCompletion.USER_ABORT
    assert hardware.valve.snapshot().is_open is False
    assert controller.snapshot().state is TapState.AUTHENTICATED


def test_zz_tap_013_manual_pour_stops_on_release_and_records_actual_pulses() -> None:
    controller, hardware, _clock, flow_meter, _emergency_stop = tap_setup()
    controller.present_authenticated_card("user-1")

    controller.start_manual_pour()
    flow_meter.add_pulses(7)
    record = controller.stop_manual_pour()

    assert record.kind is PourKind.MANUAL
    assert record.measured_pulses == 7
    assert record.target_pulses is None
    assert record.completion is PourCompletion.RELEASED
    assert record.chargeable is True
    assert hardware.valve.snapshot().is_open is False
    assert controller.snapshot().state is TapState.AUTHENTICATED

    with pytest.raises(InvalidTransition):
        controller.stop_manual_pour()
    assert len(controller.records) == 1


def test_zz_tap_014_manual_pour_stops_at_configured_time_limit() -> None:
    controller, hardware, clock, flow_meter, _emergency_stop = tap_setup()
    controller.present_authenticated_card("user-1")
    controller.start_manual_pour()
    flow_meter.add_pulses(3)
    clock.advance(29.5)
    flow_meter.add_pulses(1)
    clock.advance(0.5)
    controller.heartbeat()
    status = controller.poll()

    assert status.state is TapState.AUTHENTICATED
    assert hardware.valve.snapshot().is_open is False
    assert controller.records[-1].kind is PourKind.MANUAL
    assert controller.records[-1].completion is PourCompletion.LIMIT_REACHED
    assert controller.records[-1].measured_pulses == 4


def test_second_card_is_ignored_while_pouring() -> None:
    controller, _hardware, _clock, _flow_meter, _emergency_stop = tap_setup()
    controller.present_authenticated_card("user-1")
    controller.start_portion(target_pulses=10)

    assert controller.present_authenticated_card("user-2", is_admin=True) is False
    assert controller.snapshot().user_id == "user-1"
    assert controller.snapshot().state is TapState.PORTION_POURING


def test_emergency_stop_closes_and_latches_until_admin_reset() -> None:
    controller, hardware, _clock, flow_meter, emergency_stop = tap_setup()
    controller.present_authenticated_card("user-1")
    controller.start_portion(target_pulses=10)
    flow_meter.add_pulses(2)

    emergency_stop.trigger()
    status = controller.poll()

    assert status.state is TapState.EMERGENCY_STOP
    assert status.user_id is None
    assert hardware.valve.snapshot().is_open is False
    assert controller.records[-1].completion is PourCompletion.FAULT

    emergency_stop.release()
    assert controller.poll().state is TapState.EMERGENCY_STOP
    with pytest.raises(InvalidTransition):
        controller.reset_safety_lock(is_admin=False)

    controller.reset_safety_lock(is_admin=True)
    assert controller.snapshot().state is TapState.IDLE


def test_missing_first_pulse_locks_tap() -> None:
    controller, hardware, clock, _flow_meter, _emergency_stop = tap_setup()
    controller.present_authenticated_card("user-1")
    controller.start_portion(target_pulses=10)

    clock.advance(2)
    controller.heartbeat()
    status = controller.poll()

    assert status.state is TapState.FAULT_LOCKED
    assert status.safety_reason == "Kein Durchfluss erkannt"
    assert hardware.valve.snapshot().is_open is False


def test_debug_mode_disables_only_flow_watchdog() -> None:
    controller, hardware, clock, _flow_meter, _emergency_stop = tap_setup(
        flow_watchdog_enabled=False
    )
    controller.present_authenticated_card("user-1")
    controller.start_manual_pour()

    clock.advance(3)
    controller.heartbeat()
    status = controller.poll()

    assert status.state is TapState.MANUAL_POURING
    assert hardware.valve.snapshot().is_open is True
    record = controller.stop_manual_pour()
    assert record.measured_pulses == 0
    assert hardware.valve.snapshot().is_open is False


def test_debug_flow_mode_keeps_control_watchdog_active() -> None:
    controller, hardware, clock, _flow_meter, _emergency_stop = tap_setup(
        flow_watchdog_enabled=False
    )
    controller.present_authenticated_card("user-1")
    controller.start_manual_pour()

    clock.advance(2)
    status = controller.poll()

    assert status.state is TapState.FAULT_LOCKED
    assert status.safety_reason == "Steuerungs-Watchdog abgelaufen"
    assert hardware.valve.snapshot().is_open is False


def test_watchdog_closes_tap_without_heartbeat() -> None:
    controller, hardware, clock, flow_meter, _emergency_stop = tap_setup()
    controller.present_authenticated_card("user-1")
    controller.start_portion(target_pulses=10)
    flow_meter.add_pulses(1)

    clock.advance(2)
    status = controller.poll()

    assert status.state is TapState.FAULT_LOCKED
    assert status.safety_reason == "Steuerungs-Watchdog abgelaufen"
    assert hardware.valve.snapshot().is_open is False


def test_top_up_stops_at_configured_pulse_limit() -> None:
    controller, hardware, _clock, flow_meter, _emergency_stop = tap_setup()
    controller.present_authenticated_card("user-1")
    controller.start_portion(target_pulses=1)
    flow_meter.add_pulses(1)
    controller.poll()
    controller.start_top_up()

    flow_meter.add_pulses(3)
    status = controller.poll()

    assert status.state is TapState.AUTHENTICATED
    assert hardware.valve.snapshot().is_open is False
    assert controller.records[-1].completion is PourCompletion.LIMIT_REACHED
    assert controller.records[-1].measured_pulses == 3


def test_top_up_stops_at_configured_time_limit() -> None:
    controller, hardware, clock, flow_meter, _emergency_stop = tap_setup()
    controller.present_authenticated_card("user-1")
    controller.start_portion(target_pulses=1)
    flow_meter.add_pulses(1)
    controller.poll()
    controller.start_top_up()
    flow_meter.add_pulses(1)
    clock.advance(2)
    flow_meter.add_pulses(1)
    controller.heartbeat()

    status = controller.poll()

    assert status.state is TapState.AUTHENTICATED
    assert hardware.valve.snapshot().is_open is False
    assert controller.records[-1].completion is PourCompletion.LIMIT_REACHED
    assert controller.records[-1].measured_pulses == 2


def test_top_up_window_expires_without_opening_valve() -> None:
    controller, hardware, clock, flow_meter, _emergency_stop = tap_setup()
    controller.present_authenticated_card("user-1")
    controller.start_portion(target_pulses=1)
    flow_meter.add_pulses(1)
    controller.poll()

    clock.advance(5)
    assert controller.poll().state is TapState.AUTHENTICATED
    assert hardware.valve.snapshot().is_open is False
    with pytest.raises(InvalidTransition):
        controller.start_top_up()


def test_zz_tap_009_status_reports_remaining_top_up_window() -> None:
    controller, _hardware, clock, flow_meter, _emergency_stop = tap_setup()
    controller.present_authenticated_card("user-1")
    controller.start_portion(target_pulses=1)
    flow_meter.add_pulses(1)

    status = controller.poll()
    assert status.top_up_remaining_ms == 5000

    clock.advance(1.25)
    assert controller.snapshot().top_up_remaining_ms == 3750


def test_zz_aut_010_inactive_session_logs_out_automatically() -> None:
    controller, hardware, clock, _flow_meter, _emergency_stop = tap_setup()
    controller.present_authenticated_card("user-1")

    clock.advance(14)
    assert controller.poll().state is TapState.AUTHENTICATED
    clock.advance(1)
    status = controller.poll()

    assert status.state is TapState.IDLE
    assert status.user_id is None
    assert hardware.valve.snapshot().is_open is False


def test_zz_aut_010_ui_activity_resets_session_timeout() -> None:
    controller, _hardware, clock, _flow_meter, _emergency_stop = tap_setup()
    controller.present_authenticated_card("user-1")

    assert controller.snapshot().session_remaining_ms == 15_000
    clock.advance(5)
    assert controller.snapshot().session_remaining_ms == 10_000

    controller.register_activity()
    assert controller.snapshot().session_remaining_ms == 15_000
    clock.advance(14)
    assert controller.poll().state is TapState.AUTHENTICATED


def test_missing_followup_pulses_lock_tap() -> None:
    controller, hardware, clock, flow_meter, _emergency_stop = tap_setup()
    controller.present_authenticated_card("user-1")
    controller.start_portion(target_pulses=10)
    flow_meter.add_pulses(1)
    controller.poll()

    clock.advance(1)
    controller.heartbeat()
    status = controller.poll()

    assert status.state is TapState.FAULT_LOCKED
    assert status.safety_reason == "Durchflussimpulse ausgeblieben"
    assert hardware.valve.snapshot().is_open is False


def test_maintenance_pour_is_not_chargeable() -> None:
    controller, _hardware, _clock, flow_meter, _emergency_stop = tap_setup()
    controller.present_authenticated_card("admin-1", is_admin=True)
    controller.enter_maintenance()
    controller.start_maintenance_pour()
    flow_meter.add_pulses(7)

    record = controller.stop_maintenance_pour()

    assert record.kind is PourKind.MAINTENANCE
    assert record.measured_pulses == 7
    assert record.chargeable is False
    assert controller.snapshot().state is TapState.MAINTENANCE


def test_non_admin_cannot_enter_maintenance() -> None:
    controller, _hardware, _clock, _flow_meter, _emergency_stop = tap_setup()
    controller.present_authenticated_card("user-1")

    with pytest.raises(InvalidTransition):
        controller.enter_maintenance()

    assert controller.snapshot().state is TapState.AUTHENTICATED


def test_background_supervisor_enforces_watchdog() -> None:
    flow_meter = SimulatedFlowMeter()
    hardware = HardwareLayer(
        nfc=SimulatedNfcReader(),
        valve=SimulatedValve(),
        flow_meter=flow_meter,
        emergency_stop=SimulatedEmergencyStop(),
    )
    limits = TapLimits(
        first_pulse_timeout_seconds=1,
        between_pulses_timeout_seconds=1,
        maximum_pour_seconds=2,
        watchdog_timeout_seconds=0.05,
        top_up_window_seconds=1,
        top_up_maximum_seconds=1,
        top_up_maximum_pulses=3,
    )
    hardware.start()
    controller = TapController(hardware, limits, supervisor_interval_seconds=0.01)
    controller.start()
    controller.present_authenticated_card("user-1")
    controller.start_portion(target_pulses=10)
    flow_meter.add_pulses(1)

    deadline = time.monotonic() + 1
    while controller.snapshot().state is TapState.PORTION_POURING:
        if time.monotonic() >= deadline:
            pytest.fail("Background supervisor did not enforce watchdog timeout")
        time.sleep(0.01)

    controller.shutdown()
    hardware.stop()
    assert hardware.valve.snapshot().is_open is False
    assert controller.records[-1].completion is PourCompletion.FAULT
