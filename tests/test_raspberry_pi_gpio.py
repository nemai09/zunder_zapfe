from collections.abc import Callable

import pytest

from zunder_zapfe.backend.tap_controller import PourKind, TapController, TapLimits
from zunder_zapfe.hardware.adapters.raspberry_pi import GpioFlowMeter, GpioValve
from zunder_zapfe.hardware.layer import HardwareLayer, create_default_hardware
from zunder_zapfe.hardware.simulators import (
    SimulatedEmergencyStop,
    SimulatedFlowMeter,
    SimulatedNfcReader,
    SimulatedValve,
)


class FakeOutput:
    def __init__(self) -> None:
        self.value = False
        self.closed = False

    def on(self) -> None:
        self.value = True

    def off(self) -> None:
        self.value = False

    def close(self) -> None:
        self.closed = True


class FakePulseInput:
    def __init__(self) -> None:
        self.when_activated: Callable[[], None] | None = None
        self.closed = False

    def pulse(self) -> None:
        if self.when_activated is not None:
            self.when_activated()

    def close(self) -> None:
        self.closed = True


class ManualClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


def test_gpio_valve_is_low_on_start_and_stop_and_high_while_open() -> None:
    output = FakeOutput()
    valve = GpioValve(17, output_factory=lambda _pin: output)

    valve.start()
    assert output.value is False
    assert valve.snapshot().is_open is False
    assert valve.snapshot().simulated is False

    valve.open()
    assert output.value is True
    assert valve.snapshot().is_open is True

    valve.stop()
    assert output.value is False
    assert output.closed is True
    assert valve.snapshot().is_open is False


def test_gpio_flow_meter_counts_falling_edges_only_during_measurement() -> None:
    pulse_input = FakePulseInput()
    clock_values = iter([10.0, 10.1])
    meter = GpioFlowMeter(
        27,
        input_factory=lambda _pin: pulse_input,
        clock=lambda: next(clock_values),
    )
    meter.start()

    pulse_input.pulse()
    assert meter.snapshot().pulse_count == 0

    meter.begin_measurement()
    pulse_input.pulse()
    pulse_input.pulse()
    reading = meter.end_measurement()

    assert reading.pulse_count == 2
    assert reading.last_pulse_at == 10.1
    assert reading.measuring is False
    assert reading.simulated is False

    pulse_input.pulse()
    assert meter.snapshot().pulse_count == 2

    meter.stop()
    assert pulse_input.when_activated is None
    assert pulse_input.closed is True


def test_gpio_path_completes_a_manual_pour() -> None:
    output = FakeOutput()
    pulse_input = FakePulseInput()
    clock = ManualClock()
    valve = GpioValve(17, output_factory=lambda _pin: output)
    flow_meter = GpioFlowMeter(
        27,
        input_factory=lambda _pin: pulse_input,
        clock=clock,
    )
    hardware = HardwareLayer(
        nfc=SimulatedNfcReader(),
        valve=valve,
        flow_meter=flow_meter,
        emergency_stop=SimulatedEmergencyStop(),
    )
    limits = TapLimits(
        first_pulse_timeout_seconds=2,
        between_pulses_timeout_seconds=1,
        maximum_pour_seconds=10,
        watchdog_timeout_seconds=2,
        top_up_window_seconds=5,
        top_up_maximum_seconds=2,
        top_up_maximum_pulses=100,
    )
    hardware.start()
    controller = TapController(hardware, limits, clock=clock, supervise=False)
    controller.start()
    controller.present_authenticated_card("gpio-user")

    controller.start_manual_pour()
    assert output.value is True
    for _ in range(10):
        pulse_input.pulse()
    record = controller.stop_manual_pour()

    assert output.value is False
    assert record.kind is PourKind.MANUAL
    assert record.measured_pulses == 10
    hardware.stop()


def test_default_hardware_uses_gpio_and_simulators_require_explicit_flag() -> None:
    target = create_default_hardware(
        simulate_nfc=True,
        environment={
            "ZUNDER_ZAPFE_VALVE_GPIO": "17",
            "ZUNDER_ZAPFE_FLOW_GPIO": "27",
        },
    )
    simulated = create_default_hardware(
        simulate_nfc=True,
        simulate_tap_hardware=True,
        environment={},
    )

    assert isinstance(target.valve, GpioValve)
    assert isinstance(target.flow_meter, GpioFlowMeter)
    assert target.valve.pin == 17
    assert target.flow_meter.pin == 27
    assert isinstance(simulated.valve, SimulatedValve)
    assert isinstance(simulated.flow_meter, SimulatedFlowMeter)


@pytest.mark.parametrize(
    "environment",
    [
        {"ZUNDER_ZAPFE_VALVE_GPIO": "not-a-number"},
        {
            "ZUNDER_ZAPFE_VALVE_GPIO": "17",
            "ZUNDER_ZAPFE_FLOW_GPIO": "17",
        },
        {"ZUNDER_ZAPFE_FLOW_GPIO": "28"},
    ],
)
def test_invalid_gpio_configuration_is_rejected(environment: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        create_default_hardware(simulate_nfc=True, environment=environment)
