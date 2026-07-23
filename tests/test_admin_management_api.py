from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import URL, Engine, select
from sqlalchemy.orm import Session, sessionmaker

from zunder_zapfe.backend.web_auth_service import WebAuthService
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
from zunder_zapfe.persistence.models import AdminAuditEntry, Event, Keg, UserRole
from zunder_zapfe.persistence.repository import Repository

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADMIN_PASSWORD = "Alpha-Admin-2026"


@pytest.fixture
def management_api(
    tmp_path: Path,
) -> Iterator[tuple[TestClient, sessionmaker[Session], int]]:
    database_path = tmp_path / "admin-management.db"
    url = URL.create("sqlite", database=str(database_path)).render_as_string(hide_password=False)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine: Engine = create_database_engine(url)
    sessions = create_session_factory(engine)
    with sessions.begin() as session:
        admin = Repository(session).create_user(
            "Ada",
            last_name="Admin",
            role=UserRole.ADMIN,
        )
        admin_id = admin.id
    WebAuthService(sessions).set_initial_password(
        user_id=admin_id,
        password=ADMIN_PASSWORD,
    )
    application = create_app(
        HardwareLayer(
            nfc=SimulatedNfcReader(),
            valve=SimulatedValve(),
            flow_meter=SimulatedFlowMeter(),
            emergency_stop=SimulatedEmergencyStop(),
        ),
        sessions,
        enable_simulator_api=False,
        run_background=False,
        kiosk_settings=KioskSettings(admin_session_timeout_seconds=30),
    )
    try:
        with TestClient(application, client=("10.42.0.2", 50000)) as client:
            yield client, sessions, admin_id
    finally:
        engine.dispose()


def login(client: TestClient, admin_id: int) -> dict[str, str]:
    response = client.post(
        "/api/web-auth/login",
        json={"user_id": admin_id, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    token = client.cookies.get("zz_admin_csrf")
    assert token
    return {"X-CSRF-Token": token}


def test_zz_keg_001_002_admin_manages_events_beverages_and_keg_switch(
    management_api: tuple[TestClient, sessionmaker[Session], int],
) -> None:
    client, sessions, admin_id = management_api
    assert client.get("/api/web-admin/events").status_code == 401
    headers = login(client, admin_id)
    assert (
        client.post(
            "/api/web-admin/events",
            json={"name": "Ohne CSRF", "year": 2026},
        ).status_code
        == 403
    )

    first_event = client.post(
        "/api/web-admin/events",
        json={"name": "Zunder 2026", "year": 2026},
        headers=headers,
    )
    second_event = client.post(
        "/api/web-admin/events",
        json={"name": "Zunder 2027", "year": 2027},
        headers=headers,
    )
    assert first_event.status_code == 201
    assert second_event.status_code == 201
    first_beverage = client.post(
        "/api/web-admin/beverages",
        json={
            "name": "Pils",
            "default_keg_size_ml": 50_000,
            "price_per_liter_cents": 450,
        },
        headers=headers,
    )
    second_beverage = client.post(
        "/api/web-admin/beverages",
        json={
            "name": "Radler",
            "default_keg_size_ml": 30_000,
            "price_per_liter_cents": 400,
        },
        headers=headers,
    )
    assert first_beverage.status_code == 201
    assert second_beverage.status_code == 201

    first_keg = client.post(
        "/api/web-admin/kegs/switch",
        json={
            "event_id": first_event.json()["id"],
            "beverage_id": first_beverage.json()["id"],
            "initial_volume_ml": 50_000,
        },
        headers=headers,
    )
    second_keg = client.post(
        "/api/web-admin/kegs/switch",
        json={
            "event_id": second_event.json()["id"],
            "beverage_id": second_beverage.json()["id"],
            "initial_volume_ml": 30_000,
        },
        headers=headers,
    )
    assert first_keg.status_code == 201
    assert second_keg.status_code == 201
    assert second_keg.json()["active"] is True
    assert second_keg.json()["event_name"] == "Zunder 2027"
    assert second_keg.json()["remaining_volume_ml"] == 30_000

    kegs = client.get("/api/web-admin/kegs").json()
    assert [keg["id"] for keg in kegs] == [
        second_keg.json()["id"],
        first_keg.json()["id"],
    ]
    assert kegs[1]["active"] is False
    assert kegs[1]["closed_at"] is not None
    events = client.get("/api/web-admin/events").json()
    assert next(event for event in events if event["id"] == second_event.json()["id"])["active"]

    disable_active_beverage = client.patch(
        f"/api/web-admin/beverages/{second_beverage.json()['id']}",
        json={
            **second_beverage.json(),
            "active": False,
        },
        headers=headers,
    )
    assert disable_active_beverage.status_code == 409

    with sessions() as session:
        assert (
            session.scalar(select(Event).where(Event.active.is_(True))).id
            == second_event.json()["id"]
        )
        assert session.scalar(select(Keg).where(Keg.active.is_(True))).id == second_keg.json()["id"]
        actions = list(session.scalars(select(AdminAuditEntry.action).order_by(AdminAuditEntry.id)))
    assert actions[-6:] == [
        "event.created",
        "event.created",
        "beverage.created",
        "beverage.created",
        "keg.switched",
        "keg.switched",
    ]


def test_zz_sys_004_conflicting_master_data_is_rejected(
    management_api: tuple[TestClient, sessionmaker[Session], int],
) -> None:
    client, _sessions, admin_id = management_api
    headers = login(client, admin_id)
    payload = {"name": "Zunder", "year": 2026}
    assert client.post("/api/web-admin/events", json=payload, headers=headers).status_code == 201
    assert client.post("/api/web-admin/events", json=payload, headers=headers).status_code == 422

    beverage = {
        "name": "Pils",
        "default_keg_size_ml": 50_000,
        "price_per_liter_cents": 450,
    }
    assert (
        client.post("/api/web-admin/beverages", json=beverage, headers=headers).status_code == 201
    )
    assert (
        client.post("/api/web-admin/beverages", json=beverage, headers=headers).status_code == 422
    )
