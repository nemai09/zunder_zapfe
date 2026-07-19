from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import URL, Engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from zunder_zapfe.backend.tap_controller import TapLimits, TapState
from zunder_zapfe.backend.tap_service import FlowCalibration, TapService, TapUnavailable
from zunder_zapfe.configuration import KioskSettings
from zunder_zapfe.demo import DemoSeedRefused, seed_demo_data
from zunder_zapfe.hardware.layer import HardwareLayer
from zunder_zapfe.hardware.simulators import (
    SimulatedEmergencyStop,
    SimulatedFlowMeter,
    SimulatedNfcReader,
    SimulatedValve,
)
from zunder_zapfe.main import create_app
from zunder_zapfe.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from zunder_zapfe.persistence.models import (
    Beverage,
    BookingCompletion,
    BookingKind,
    NfcCard,
    TapBooking,
    TechnicalEvent,
    User,
    UserRole,
)
from zunder_zapfe.persistence.repository import Repository
from zunder_zapfe.smoke_test import run_smoke_test

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = datetime(2026, 7, 19, 20, 0, tzinfo=UTC)
TEST_KIOSK_SETTINGS = KioskSettings(
    standard_portions_ml=(20, 300),
    session_timeout_seconds=60,
)


class ManualClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


@pytest.fixture
def database(tmp_path: Path) -> Iterator[tuple[Engine, sessionmaker[Session]]]:
    database_path = tmp_path / "integrated.db"
    url = URL.create("sqlite", database=str(database_path)).render_as_string(hide_password=False)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = create_database_engine(url)
    try:
        yield engine, create_session_factory(engine)
    finally:
        engine.dispose()


def simulated_hardware(
    clock: ManualClock | None = None,
) -> tuple[HardwareLayer, SimulatedNfcReader, SimulatedFlowMeter]:
    nfc = SimulatedNfcReader()
    flow_meter = SimulatedFlowMeter(clock=clock or ManualClock())
    return (
        HardwareLayer(
            nfc=nfc,
            valve=SimulatedValve(),
            flow_meter=flow_meter,
            emergency_stop=SimulatedEmergencyStop(),
        ),
        nfc,
        flow_meter,
    )


def limits() -> TapLimits:
    return TapLimits(
        first_pulse_timeout_seconds=2,
        between_pulses_timeout_seconds=1,
        maximum_pour_seconds=10,
        watchdog_timeout_seconds=2,
        top_up_window_seconds=5,
        top_up_maximum_seconds=2,
        top_up_maximum_pulses=20,
    )


def seed_data(sessions: sessionmaker[Session]) -> dict[str, int]:
    with sessions.begin() as session:
        repository = Repository(session)
        event = repository.create_event("Zunder 2026", 2026, active=True)
        user = repository.create_user("Chris")
        repository.add_nfc_card(user.id, "04AABBCC")
        admin = repository.create_user("Admin", role=UserRole.ADMIN)
        repository.add_nfc_card(admin.id, "04DDEEFF")
        beverage = repository.create_beverage(
            "Testbier", default_keg_size_ml=50_000, price_per_liter_cents=450
        )
        keg = repository.activate_new_keg(
            event_id=event.id,
            beverage_id=beverage.id,
            initial_volume_ml=50_000,
        )
        return {
            "event_id": event.id,
            "user_id": user.id,
            "admin_id": admin.id,
            "beverage_id": beverage.id,
            "keg_id": keg.id,
        }


def start_service(
    sessions: sessionmaker[Session],
    clock: ManualClock | None = None,
) -> tuple[TapService, HardwareLayer, SimulatedNfcReader, SimulatedFlowMeter]:
    actual_clock = clock or ManualClock()
    hardware, nfc, flow_meter = simulated_hardware(actual_clock)
    hardware.start()
    service = TapService(
        hardware,
        sessions,
        limits(),
        standard_portions_ml=(2, 20),
        calibration=FlowCalibration(pulses_per_liter=500),
        monotonic_clock=actual_clock,
        timestamp_clock=lambda: FIXED_TIME,
        run_background=False,
    )
    service.start()
    return service, hardware, nfc, flow_meter


def stop_service(service: TapService, hardware: HardwareLayer) -> None:
    service.shutdown()
    hardware.stop()


def test_zz_aut_002_007_008_nfc_resolves_only_active_known_cards(
    database: tuple[Engine, sessionmaker[Session]],
) -> None:
    _engine, sessions = database
    ids = seed_data(sessions)
    service, hardware, _nfc, _flow_meter = start_service(sessions)
    try:
        assert service.authenticate_card("11223344") is False
        assert service.status_dict()["state"] is TapState.IDLE
        assert service.authenticate_card("04-aa-bb-cc") is True
        assert service.status_dict()["user_id"] == str(ids["user_id"])
        service.logout()

        with sessions.begin() as session:
            card = session.scalar(select(NfcCard).where(NfcCard.user_id == ids["user_id"]))
            assert card is not None
            card.active = False

        assert service.authenticate_card("04AABBCC") is False
        assert hardware.valve.snapshot().is_open is False
    finally:
        stop_service(service, hardware)


def test_zz_aut_002_background_supervisor_authenticates_presented_card(
    database: tuple[Engine, sessionmaker[Session]],
) -> None:
    _engine, sessions = database
    ids = seed_data(sessions)
    hardware, nfc, _flow_meter = simulated_hardware()
    hardware.start()
    service = TapService(
        hardware,
        sessions,
        limits(),
        run_background=True,
        background_interval_seconds=0.01,
    )
    service.start()
    try:
        nfc.present_card("04AABBCC")
        deadline = time.monotonic() + 1
        while service.status_dict()["user_id"] is None:
            if time.monotonic() >= deadline:
                pytest.fail("Background supervisor did not authenticate the NFC card")
            time.sleep(0.01)

        assert service.status_dict()["user_id"] == str(ids["user_id"])
    finally:
        stop_service(service, hardware)


def test_zz_dat_001_002_and_keg_004_portion_is_persisted_and_survives_restart(
    database: tuple[Engine, sessionmaker[Session]],
) -> None:
    _engine, sessions = database
    ids = seed_data(sessions)
    service, hardware, _nfc, flow_meter = start_service(sessions)
    try:
        assert service.authenticate_card("04AABBCC") is True
        service.start_portion(20)
        flow_meter.add_pulses(10)
        service.heartbeat()
        status = service.poll()

        assert status["state"] is TapState.TOP_UP_AVAILABLE
        assert status["last_booking"]["measured_volume_ml"] == 20
        assert status["last_booking"]["amount_cents"] == 9
        assert service.current_consumption() == {
            "event_id": ids["event_id"],
            "user_id": ids["user_id"],
            "booking_count": 1,
            "measured_volume_ml": 20,
            "amount_cents": 9,
        }
        assert service.current_keg()["remaining_volume_ml"] == 49_980
    finally:
        stop_service(service, hardware)

    restarted, restarted_hardware, _nfc, _flow_meter = start_service(sessions)
    try:
        assert restarted.authenticate_card("04AABBCC") is True
        assert restarted.current_consumption()["amount_cents"] == 9
        assert restarted.current_keg()["remaining_volume_ml"] == 49_980
    finally:
        stop_service(restarted, restarted_hardware)


def test_zz_tap_008_price_and_target_are_snapshotted_at_pour_start(
    database: tuple[Engine, sessionmaker[Session]],
) -> None:
    _engine, sessions = database
    ids = seed_data(sessions)
    service, hardware, _nfc, flow_meter = start_service(sessions)
    try:
        service.authenticate_card("04AABBCC")
        service.start_portion(20)
        with sessions.begin() as session:
            beverage = session.get(Beverage, ids["beverage_id"])
            assert beverage is not None
            beverage.price_per_liter_cents = 900

        flow_meter.add_pulses(6)
        booking_record = service.abort_portion()

        assert booking_record.measured_pulses == 6
        with sessions() as session:
            booking = session.scalar(select(TapBooking))
            assert booking is not None
            assert booking.target_volume_ml == 20
            assert booking.measured_volume_ml == 12
            assert booking.price_per_liter_cents == 450
            assert booking.amount_cents == 5
            assert booking.completion is BookingCompletion.USER_ABORT
    finally:
        stop_service(service, hardware)


def test_zz_tap_009_top_up_creates_a_second_booking(
    database: tuple[Engine, sessionmaker[Session]],
) -> None:
    _engine, sessions = database
    seed_data(sessions)
    service, hardware, _nfc, flow_meter = start_service(sessions)
    try:
        service.authenticate_card("04AABBCC")
        service.start_portion(2)
        flow_meter.add_pulses(1)
        service.heartbeat()
        service.poll()
        service.start_top_up()
        flow_meter.add_pulses(3)
        service.stop_top_up()

        with sessions() as session:
            bookings = list(session.scalars(select(TapBooking).order_by(TapBooking.id)))
            assert [booking.kind for booking in bookings] == [
                BookingKind.PORTION,
                BookingKind.TOP_UP,
            ]
            assert [booking.measured_volume_ml for booking in bookings] == [2, 6]
    finally:
        stop_service(service, hardware)


def test_zz_mnt_002_maintenance_consumes_stock_without_charge(
    database: tuple[Engine, sessionmaker[Session]],
) -> None:
    _engine, sessions = database
    seed_data(sessions)
    service, hardware, _nfc, flow_meter = start_service(sessions)
    try:
        service.authenticate_card("04DDEEFF")
        service.enter_maintenance()
        service.start_maintenance_pour()
        flow_meter.add_pulses(5)
        service.stop_maintenance_pour()

        with sessions() as session:
            booking = session.scalar(select(TapBooking))
            assert booking is not None
            assert booking.kind is BookingKind.MAINTENANCE
            assert booking.measured_volume_ml == 10
            assert booking.chargeable is False
            assert booking.amount_cents == 0
        assert service.current_keg()["remaining_volume_ml"] == 49_990
    finally:
        stop_service(service, hardware)


def test_zz_saf_004_and_dat_004_fault_is_booked_and_logged(
    database: tuple[Engine, sessionmaker[Session]],
) -> None:
    _engine, sessions = database
    seed_data(sessions)
    clock = ManualClock()
    service, hardware, _nfc, _flow_meter = start_service(sessions, clock)
    try:
        service.authenticate_card("04AABBCC")
        service.start_portion(20)
        clock.advance(2)
        service.heartbeat()
        status = service.poll()

        assert status["state"] is TapState.FAULT_LOCKED
        assert hardware.valve.snapshot().is_open is False
        with sessions() as session:
            booking = session.scalar(select(TapBooking))
            events = list(session.scalars(select(TechnicalEvent)))
            assert booking is not None
            assert booking.completion is BookingCompletion.FAULT
            assert any(event.event_type == "tap.fault_locked" for event in events)
    finally:
        stop_service(service, hardware)


def test_zz_saf_003_007_and_dat_004_admin_card_resets_and_logs_latched_fault(
    database: tuple[Engine, sessionmaker[Session]],
) -> None:
    _engine, sessions = database
    seed_data(sessions)
    clock = ManualClock()
    service, hardware, nfc, _flow_meter = start_service(sessions, clock)
    try:
        service.authenticate_card("04AABBCC")
        service.start_portion(20)
        clock.advance(2)
        service.heartbeat()
        assert service.poll()["state"] is TapState.FAULT_LOCKED

        nfc.present_card("04AABBCC")
        with pytest.raises(TapUnavailable, match="active admin card"):
            service.reset_safety_lock()

        nfc.present_card("04DDEEFF")
        status = service.reset_safety_lock()

        assert status["state"] is TapState.IDLE
        assert status["user_id"] is None
        assert hardware.valve.snapshot().is_open is False
        with sessions() as session:
            events = list(session.scalars(select(TechnicalEvent)))
            assert any(event.event_type == "tap.safety_reset" for event in events)
    finally:
        stop_service(service, hardware)


def test_zz_dat_001_persistence_failure_safely_locks_the_tap(
    database: tuple[Engine, sessionmaker[Session]],
) -> None:
    _engine, sessions = database
    seed_data(sessions)
    service, hardware, _nfc, flow_meter = start_service(sessions)

    def fail_booking_insert(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated storage failure")

    event.listen(TapBooking, "before_insert", fail_booking_insert)
    try:
        service.authenticate_card("04AABBCC")
        service.start_portion(20)
        flow_meter.add_pulses(10)
        service.heartbeat()
        status = service.poll()

        assert status["state"] is TapState.FAULT_LOCKED
        assert status["safety_reason"] == "Zapfbuchung konnte nicht gespeichert werden"
        assert "simulated storage failure" in status["persistence_error"]
        assert hardware.valve.snapshot().is_open is False
        with sessions() as session:
            assert session.scalar(select(TapBooking)) is None
    finally:
        event.remove(TapBooking, "before_insert", fail_booking_insert)
        stop_service(service, hardware)


def test_zz_aut_009_second_nfc_card_does_not_replace_pouring_user(
    database: tuple[Engine, sessionmaker[Session]],
) -> None:
    _engine, sessions = database
    ids = seed_data(sessions)
    service, hardware, nfc, _flow_meter = start_service(sessions)
    try:
        nfc.present_card("04AABBCC")
        assert service.process_nfc_snapshot() is True
        service.start_portion(20)
        nfc.remove_card()
        service.process_nfc_snapshot()
        nfc.present_card("04DDEEFF")

        assert service.process_nfc_snapshot() is False
        assert service.status_dict()["user_id"] == str(ids["user_id"])
        assert hardware.valve.snapshot().is_open is True
    finally:
        stop_service(service, hardware)


def test_zz_nfr_003_simulator_api_exercises_integrated_flow(
    database: tuple[Engine, sessionmaker[Session]],
) -> None:
    _engine, sessions = database
    ids = seed_data(sessions)
    hardware, _nfc, _flow_meter = simulated_hardware()

    with TestClient(
        create_app(
            hardware,
            sessions,
            enable_simulator_api=True,
            run_background=False,
            kiosk_settings=TEST_KIOSK_SETTINGS,
        )
    ) as client:
        authenticated = client.post("/api/simulator/nfc/present", json={"uid": "04AABBCC"})
        rejected = client.post("/api/tap/portion", json={"target_volume_ml": 21})
        started = client.post("/api/tap/portion", json={"target_volume_ml": 20})
        completed = client.post("/api/simulator/flow/pulses", json={"count": 10})
        consumption = client.get("/api/consumption/current")

        assert authenticated.status_code == 200
        assert authenticated.json()["user_id"] == str(ids["user_id"])
        assert rejected.status_code == 409
        assert started.status_code == 200
        assert started.json()["target_volume_ml"] == 20
        assert started.json()["measured_volume_ml"] == 0
        assert completed.json()["state"] == "top_up_available"
        assert consumption.json()["measured_volume_ml"] == 20


def test_zz_tap_002_user_special_portion_is_exposed_and_enforced(
    database: tuple[Engine, sessionmaker[Session]],
) -> None:
    _engine, sessions = database
    ids = seed_data(sessions)
    with sessions.begin() as session:
        user = session.get(User, ids["user_id"])
        assert user is not None
        user.special_portion_ml = 420
    hardware, _nfc, _flow_meter = simulated_hardware()

    with TestClient(
        create_app(
            hardware,
            sessions,
            enable_simulator_api=True,
            run_background=False,
        )
    ) as client:
        client.post("/api/simulator/nfc/present", json={"uid": "04AABBCC"})

        options = client.get("/api/tap/options")
        started = client.post("/api/tap/portion", json={"target_volume_ml": 420})

        assert options.json()["standard_portions_ml"] == [300, 500]
        assert options.json()["special_portion_ml"] == 420
        assert started.status_code == 200
        assert started.json()["target_volume_ml"] == 420


def test_smoke_test_command_exercises_and_verifies_public_api(
    database: tuple[Engine, sessionmaker[Session]],
) -> None:
    _engine, sessions = database
    seed_data(sessions)
    hardware, _nfc, _flow_meter = simulated_hardware()

    with TestClient(
        create_app(
            hardware,
            sessions,
            enable_simulator_api=True,
            run_background=False,
            kiosk_settings=TEST_KIOSK_SETTINGS,
        )
    ) as client:
        client.post("/api/simulator/nfc/present", json={"uid": "04AABBCC"})

        class TestClientAdapter:
            @staticmethod
            def request_json(
                method: str, path: str, payload: dict[str, object] | None = None
            ) -> dict[str, object]:
                response = client.request(method, path, json=payload)
                assert response.status_code < 400, response.text
                return response.json()

        result = run_smoke_test(TestClientAdapter(), target_volume_ml=20, pulses_per_liter=500)

        assert result.measured_volume_ml == 20
        assert result.amount_cents == 9
        assert result.remaining_volume_ml == 49_980


def test_safety_reset_api_accepts_presented_admin_card(
    database: tuple[Engine, sessionmaker[Session]],
) -> None:
    _engine, sessions = database
    seed_data(sessions)
    hardware, _nfc, _flow_meter = simulated_hardware()
    emergency_stop = hardware.emergency_stop
    assert isinstance(emergency_stop, SimulatedEmergencyStop)

    with TestClient(
        create_app(
            hardware,
            sessions,
            enable_simulator_api=True,
            run_background=False,
        )
    ) as client:
        client.post("/api/simulator/nfc/present", json={"uid": "04DDEEFF"})
        emergency_stop.trigger()
        assert client.post("/api/tap/poll").json()["state"] == "emergency_stop"
        emergency_stop.release()

        reset = client.post("/api/tap/safety/reset")

        assert reset.status_code == 200
        assert reset.json()["state"] == "idle"
        assert reset.json()["user_id"] is None


def test_zz_sys_004_pour_requires_matching_active_event_and_keg(
    database: tuple[Engine, sessionmaker[Session]],
) -> None:
    _engine, sessions = database
    seed_data(sessions)
    service, hardware, _nfc, _flow_meter = start_service(sessions)
    try:
        service.authenticate_card("04AABBCC")
        with sessions.begin() as session:
            Repository(session).create_event("Zunder 2027", 2027, active=True)

        with pytest.raises(TapUnavailable, match="No matching active"):
            service.start_portion(20)
        assert hardware.valve.snapshot().is_open is False
    finally:
        stop_service(service, hardware)


def test_alpha_demo_seed_only_populates_an_empty_database(
    database: tuple[Engine, sessionmaker[Session]],
) -> None:
    _engine, sessions = database
    with sessions.begin() as session:
        result = seed_demo_data(session, year=2026)

    assert result["user_card_uid"] == "D00DCAFE"
    with sessions.begin() as session:
        with pytest.raises(DemoSeedRefused, match="requires an empty database"):
            seed_demo_data(session, year=2026)
