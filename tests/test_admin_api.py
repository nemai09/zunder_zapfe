from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import URL, Engine, select
from sqlalchemy.orm import Session, sessionmaker

from zunder_zapfe.backend.superadmin_identity import (
    load_superadmin_identity,
    provision_superadmin_identity,
)
from zunder_zapfe.backend.wifi_mode_service import WifiStatus
from zunder_zapfe.configuration import KioskSettings
from zunder_zapfe.hardware.layer import HardwareLayer
from zunder_zapfe.hardware.simulators import (
    SimulatedEmergencyStop,
    SimulatedFlowMeter,
    SimulatedNfcReader,
    SimulatedValve,
)
from zunder_zapfe.main import create_app
from zunder_zapfe.persistence.database import create_database_engine, create_session_factory
from zunder_zapfe.persistence.models import AdminAuditEntry, NfcCard, UserRole
from zunder_zapfe.persistence.repository import Repository

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADMIN_UID = "04DDEEFF"
USER_UID = "04AABBCC"
NEW_UID = "11223344"
SUPERADMIN_UID = "D00DCAFE"


class FakeWifiModeService:
    def __init__(self) -> None:
        self.current = WifiStatus(
            mode="ap",
            active_connection="zunder-zapfe-ap",
            ssid="ZUNDER_ZAPFE",
            ip_address="10.42.0.1",
            client_profile_available=True,
        )

    def status(self, *, force: bool = False) -> WifiStatus:
        return self.current

    def switch(self, mode: str) -> WifiStatus:
        self.current = WifiStatus(
            mode=mode,
            active_connection="zunder-zapfe-ap" if mode == "ap" else "Werkstatt",
            ssid="ZUNDER_ZAPFE" if mode == "ap" else "Werkstatt",
            ip_address="10.42.0.1" if mode == "ap" else "192.0.2.20",
            client_profile_available=True,
        )
        return self.current


@pytest.fixture
def admin_api(
    tmp_path: Path,
) -> Iterator[tuple[TestClient, sessionmaker[Session], SimulatedNfcReader, dict[str, int]]]:
    database_path = tmp_path / "admin-api.db"
    url = URL.create("sqlite", database=str(database_path)).render_as_string(hide_password=False)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine: Engine = create_database_engine(url)
    sessions = create_session_factory(engine)
    with sessions.begin() as session:
        repository = Repository(session)
        admin = repository.create_user("Ada", last_name="Admin", role=UserRole.ADMIN)
        repository.add_nfc_card(admin.id, ADMIN_UID)
        user = repository.create_user("Uli", last_name="User")
        repository.add_nfc_card(user.id, USER_UID)
        ids = {"admin_id": admin.id, "user_id": user.id}

    nfc = SimulatedNfcReader()
    hardware = HardwareLayer(
        nfc=nfc,
        valve=SimulatedValve(),
        flow_meter=SimulatedFlowMeter(),
        emergency_stop=SimulatedEmergencyStop(),
    )
    credential_path = tmp_path / "superadmin.credential"
    provision_superadmin_identity(SUPERADMIN_UID, credential_path)
    superadmin_identity = load_superadmin_identity(
        {"ZUNDER_ZAPFE_SUPERADMIN_CREDENTIAL_PATH": str(credential_path)}
    )
    assert superadmin_identity is not None
    application = create_app(
        hardware,
        sessions,
        enable_simulator_api=True,
        run_background=False,
        kiosk_settings=KioskSettings(admin_session_timeout_seconds=30),
        wifi_mode_service=FakeWifiModeService(),
        superadmin_identity=superadmin_identity,
    )
    try:
        with TestClient(application, client=("127.0.0.1", 50000)) as client:
            yield client, sessions, nfc, ids
    finally:
        engine.dispose()


def present(client: TestClient, uid: str) -> None:
    response = client.post("/api/simulator/nfc/present", json={"uid": uid})
    assert response.status_code == 200


def remove(client: TestClient) -> None:
    response = client.post("/api/simulator/nfc/remove")
    assert response.status_code == 204


def enter_admin(client: TestClient) -> None:
    present(client, ADMIN_UID)
    response = client.post("/api/admin/session/enter")
    assert response.status_code == 200
    assert response.json()["state"] == "admin"
    assert response.json()["valve_open"] is False


def test_admin_api_requires_an_explicit_admin_mode(admin_api: tuple[object, ...]) -> None:
    client, _sessions, _nfc, _ids = admin_api

    assert client.get("/api/admin/users").status_code == 403
    present(client, USER_UID)
    assert client.post("/api/admin/session/enter").status_code == 403
    assert client.get("/api/admin/users").status_code == 403


def test_admin_user_management_is_audited(admin_api: tuple[object, ...]) -> None:
    client, sessions, _nfc, _ids = admin_api
    enter_admin(client)

    created = client.post(
        "/api/admin/users",
        json={
            "first_name": "  Chris  ",
            "last_name": " Example ",
            "note": "Helferteam",
            "is_admin": False,
        },
    )
    assert created.status_code == 201
    user = created.json()
    assert user["display_name"] == "Chris Example"
    assert user["active_nfc_card_count"] == 0

    updated = client.patch(
        f"/api/admin/users/{user['id']}",
        json={
            "first_name": "Chris",
            "last_name": None,
            "note": "Abendkasse",
            "is_admin": False,
            "active": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Chris"

    with sessions() as session:
        actions = list(session.scalars(select(AdminAuditEntry.action).order_by(AdminAuditEntry.id)))
    assert actions == ["user.created", "user.updated"]


def test_live_nfc_capture_requires_removal_and_never_returns_full_uid(
    admin_api: tuple[object, ...],
) -> None:
    client, sessions, _nfc, ids = admin_api
    enter_admin(client)

    capture_path = f"/api/admin/users/{ids['user_id']}/nfc-cards/capture"
    assert client.post(capture_path).json()["state"] == "remove_card"
    remove(client)
    assert client.post(capture_path).json()["state"] == "waiting"
    present(client, NEW_UID)

    assigned = client.post(capture_path)
    assert assigned.status_code == 200
    assert assigned.json()["state"] == "assigned"
    card = assigned.json()["card"]
    assert card["uid_hint"] == "…3344"
    assert NEW_UID not in assigned.text

    cards = client.get(f"/api/admin/users/{ids['user_id']}/nfc-cards")
    assert cards.status_code == 200
    assert all("uid" not in item for item in cards.json())

    with sessions() as session:
        stored = session.scalar(select(NfcCard).where(NfcCard.uid == NEW_UID))
        assert stored is not None
        assert stored.user_id == ids["user_id"]
        audit = session.scalars(select(AdminAuditEntry).order_by(AdminAuditEntry.id)).all()
        assert audit[-1].action == "nfc_card.assigned"
        assert NEW_UID not in (audit[-1].new_values_json or "")


def test_zz_aut_013_normal_capture_rejects_superadmin_card(
    admin_api: tuple[object, ...],
) -> None:
    client, sessions, _nfc, ids = admin_api
    enter_admin(client)
    capture_path = f"/api/admin/users/{ids['user_id']}/nfc-cards/capture"

    assert client.post(capture_path).json()["state"] == "remove_card"
    remove(client)
    assert client.post(capture_path).json()["state"] == "waiting"
    present(client, SUPERADMIN_UID)

    response = client.post(capture_path)

    assert response.status_code == 409
    assert "Superadmin-Karte" in response.json()["detail"]
    with sessions() as session:
        assert Repository(session).find_nfc_card(SUPERADMIN_UID) is None


def test_nfc_assignment_can_be_removed_audited_and_reused(
    admin_api: tuple[object, ...],
) -> None:
    client, sessions, _nfc, ids = admin_api
    enter_admin(client)
    cards = client.get(f"/api/admin/users/{ids['user_id']}/nfc-cards").json()

    removed = client.delete(f"/api/admin/nfc-cards/{cards[0]['id']}")
    assert removed.status_code == 204
    assert client.get(f"/api/admin/users/{ids['user_id']}/nfc-cards").json() == []

    created = client.post(
        "/api/admin/users",
        json={
            "first_name": "Neu",
            "last_name": None,
            "note": None,
            "is_admin": False,
        },
    ).json()
    remove(client)
    capture_path = f"/api/admin/users/{created['id']}/nfc-cards/capture"
    assert client.post(capture_path).json()["state"] == "waiting"
    present(client, USER_UID)
    assert client.post(capture_path).json()["state"] == "assigned"

    with sessions() as session:
        reused = session.scalar(select(NfcCard).where(NfcCard.uid == USER_UID))
        assert reused is not None
        assert reused.user_id == created["id"]
        actions = list(session.scalars(select(AdminAuditEntry.action)))
        assert "nfc_card.removed" in actions


def test_last_active_admin_wristband_cannot_be_removed(
    admin_api: tuple[object, ...],
) -> None:
    client, _sessions, _nfc, ids = admin_api
    enter_admin(client)
    cards = client.get(f"/api/admin/users/{ids['admin_id']}/nfc-cards").json()

    response = client.delete(f"/api/admin/nfc-cards/{cards[0]['id']}")

    assert response.status_code == 409
    assert "last active wristband" in response.json()["detail"]


def test_admin_timeout_is_configurable_and_self_protected(admin_api: tuple[object, ...]) -> None:
    client, _sessions, _nfc, ids = admin_api
    enter_admin(client)

    response = client.patch(
        "/api/admin/settings",
        json={"admin_session_timeout_seconds": 45},
    )
    assert response.status_code == 200
    assert response.json()["admin_session_timeout_seconds"] == 45
    assert client.get("/api/tap/status").json()["session_remaining_ms"] <= 45_000

    response = client.patch(
        f"/api/admin/users/{ids['admin_id']}",
        json={
            "first_name": "Ada",
            "last_name": "Admin",
            "note": None,
            "is_admin": False,
            "active": True,
        },
    )
    assert response.status_code == 409

    exit_response = client.post("/api/admin/session/exit")
    assert exit_response.status_code == 200
    assert exit_response.json()["state"] == "authenticated"


def test_local_wifi_mode_switch_requires_admin_mode_and_is_audited(
    admin_api: tuple[object, ...],
) -> None:
    client, sessions, _nfc, _ids = admin_api
    assert client.get("/system").status_code == 403
    assert client.get("/api/wifi/status").json()["mode"] == "ap"
    assert client.post("/api/admin/wifi/mode", json={"mode": "client"}).status_code == 403
    enter_admin(client)
    system_page = client.get("/system")
    assert system_page.status_code == 200
    assert "Lokales Low-Level-Menü" in system_page.text

    switched = client.post("/api/admin/wifi/mode", json={"mode": "client"})

    assert switched.status_code == 200
    assert switched.json()["mode"] == "client"
    assert switched.json()["active_connection"] == "Werkstatt"
    with sessions() as session:
        actions = list(session.scalars(select(AdminAuditEntry.action)))
    assert actions == ["wifi.mode_switch_requested", "wifi.mode_switched"]
