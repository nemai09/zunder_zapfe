from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import URL, Engine, select
from sqlalchemy.orm import Session, sessionmaker

from zunder_zapfe.backend.web_auth_service import WebAuthenticationError, WebAuthService
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
from zunder_zapfe.persistence.models import (
    AdminAuditEntry,
    TechnicalEvent,
    User,
    UserRole,
    WebAdminSession,
)
from zunder_zapfe.persistence.repository import Repository

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADMIN_PASSWORD = "Alpha-Admin-2026"
NEW_ADMIN_PASSWORD = "Neues-Admin-2026"


@pytest.fixture
def web_admin_api(
    tmp_path: Path,
) -> Iterator[tuple[TestClient, sessionmaker[Session], dict[str, int]]]:
    database_path = tmp_path / "web-admin-api.db"
    url = URL.create("sqlite", database=str(database_path)).render_as_string(hide_password=False)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine: Engine = create_database_engine(url)
    sessions = create_session_factory(engine)
    with sessions.begin() as session:
        repository = Repository(session)
        admin = repository.create_user("Ada", last_name="Admin", role=UserRole.ADMIN)
        user = repository.create_user("Uli", last_name="User")
        ids = {"admin_id": admin.id, "user_id": user.id}
    WebAuthService(sessions).set_initial_password(
        user_id=ids["admin_id"],
        password=ADMIN_PASSWORD,
    )

    hardware = HardwareLayer(
        nfc=SimulatedNfcReader(),
        valve=SimulatedValve(),
        flow_meter=SimulatedFlowMeter(),
        emergency_stop=SimulatedEmergencyStop(),
    )
    application = create_app(
        hardware,
        sessions,
        enable_simulator_api=True,
        run_background=False,
        kiosk_settings=KioskSettings(admin_session_timeout_seconds=30),
    )
    try:
        with TestClient(application, client=("10.42.0.2", 50000)) as client:
            yield client, sessions, ids
    finally:
        engine.dispose()


def login(
    client: TestClient,
    user_id: int,
    password: str = ADMIN_PASSWORD,
) -> str:
    response = client.post(
        "/api/web-auth/login",
        json={"user_id": user_id, "password": password},
    )
    assert response.status_code == 200
    csrf_token = client.cookies.get("zz_admin_csrf")
    assert csrf_token
    return csrf_token


def csrf_headers(csrf_token: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf_token}


def test_zz_aut_003_only_active_admins_with_password_can_log_in(
    web_admin_api: tuple[object, ...],
) -> None:
    client, sessions, ids = web_admin_api

    options = client.get("/api/web-auth/admins")
    assert options.status_code == 200
    assert options.json() == [{"id": ids["admin_id"], "display_name": "Ada Admin"}]
    assert (
        client.post(
            "/api/web-auth/login",
            json={"user_id": ids["user_id"], "password": ADMIN_PASSWORD},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/web-auth/login",
            json={"user_id": ids["admin_id"], "password": "Falsches-Passwort"},
        ).status_code
        == 401
    )

    login_response = client.post(
        "/api/web-auth/login",
        json={"user_id": ids["admin_id"], "password": ADMIN_PASSWORD},
    )
    assert login_response.status_code == 200
    assert login_response.json()["display_name"] == "Ada Admin"
    assert any(
        "HttpOnly" in value and "SameSite=strict" in value
        for value in login_response.headers.get_list("set-cookie")
    )

    raw_token = client.cookies.get("zz_admin_session")
    assert raw_token
    with sessions() as session:
        admin = session.get(User, ids["admin_id"])
        stored_session = session.scalar(select(WebAdminSession))
        assert admin is not None
        assert admin.password_hash is not None
        assert admin.password_hash.startswith("$argon2")
        assert admin.password_hash != ADMIN_PASSWORD
        assert stored_session is not None
        assert stored_session.token_hash != raw_token


def test_zz_aut_003_web_admin_routes_require_session_and_csrf(
    web_admin_api: tuple[object, ...],
) -> None:
    client, sessions, ids = web_admin_api

    assert client.get("/api/web-admin/users").status_code == 401
    csrf_token = login(client, ids["admin_id"])
    users = client.get("/api/web-admin/users")
    assert users.status_code == 200
    assert users.json()[0]["has_password"] is True

    payload = {
        "first_name": "Chris",
        "last_name": "Beispiel",
        "note": None,
        "is_admin": False,
    }
    assert client.post("/api/web-admin/users", json=payload).status_code == 403
    created = client.post(
        "/api/web-admin/users",
        json=payload,
        headers=csrf_headers(csrf_token),
    )
    assert created.status_code == 201

    with sessions() as session:
        actions = list(session.scalars(select(AdminAuditEntry.action)))
        assert "user.created" in actions


def test_zz_aut_012_password_change_revokes_session_and_never_logs_password(
    web_admin_api: tuple[object, ...],
) -> None:
    client, sessions, ids = web_admin_api
    csrf_token = login(client, ids["admin_id"])

    wrong = client.post(
        "/api/web-auth/password",
        json={
            "current_password": "Falsches-Passwort",
            "new_password": NEW_ADMIN_PASSWORD,
        },
        headers=csrf_headers(csrf_token),
    )
    assert wrong.status_code == 401

    changed = client.post(
        "/api/web-auth/password",
        json={
            "current_password": ADMIN_PASSWORD,
            "new_password": NEW_ADMIN_PASSWORD,
        },
        headers=csrf_headers(csrf_token),
    )
    assert changed.status_code == 204
    assert client.get("/api/web-auth/session").status_code == 401
    assert (
        client.post(
            "/api/web-auth/login",
            json={"user_id": ids["admin_id"], "password": ADMIN_PASSWORD},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/web-auth/login",
            json={"user_id": ids["admin_id"], "password": NEW_ADMIN_PASSWORD},
        ).status_code
        == 200
    )

    with sessions() as session:
        audit_text = "\n".join(
            filter(
                None,
                session.scalars(select(AdminAuditEntry.new_values_json)).all(),
            )
        )
        event_text = "\n".join(
            event.details_json or "" for event in session.scalars(select(TechnicalEvent))
        )
        assert ADMIN_PASSWORD not in audit_text + event_text
        assert NEW_ADMIN_PASSWORD not in audit_text + event_text


def test_zz_aut_012_admin_can_set_another_admin_password(
    web_admin_api: tuple[object, ...],
) -> None:
    client, _sessions, ids = web_admin_api
    csrf_token = login(client, ids["admin_id"])
    created = client.post(
        "/api/web-admin/users",
        json={
            "first_name": "Berta",
            "last_name": "Bier",
            "note": None,
            "is_admin": True,
        },
        headers=csrf_headers(csrf_token),
    )
    assert created.status_code == 201
    new_admin = created.json()
    assert new_admin["has_password"] is False

    reset = client.put(
        f"/api/web-admin/users/{new_admin['id']}/password",
        json={"new_password": NEW_ADMIN_PASSWORD},
        headers=csrf_headers(csrf_token),
    )
    assert reset.status_code == 204

    options = client.get("/api/web-auth/admins").json()
    assert {option["id"] for option in options} == {ids["admin_id"], new_admin["id"]}
    assert (
        client.post(
            "/api/web-auth/login",
            json={"user_id": new_admin["id"], "password": NEW_ADMIN_PASSWORD},
        ).status_code
        == 200
    )


def test_zz_aut_003_repeated_failed_logins_are_rate_limited(
    web_admin_api: tuple[object, ...],
) -> None:
    client, _sessions, ids = web_admin_api
    payload = {"user_id": ids["admin_id"], "password": "Falsches-Passwort"}

    assert [client.post("/api/web-auth/login", json=payload).status_code for _ in range(5)] == [
        401,
        401,
        401,
        401,
        401,
    ]
    response = client.post("/api/web-auth/login", json=payload)
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"


def test_zz_aut_003_expired_web_session_is_persistently_revoked(
    web_admin_api: tuple[object, ...],
) -> None:
    _client, sessions, ids = web_admin_api
    current_time = [datetime(2026, 7, 23, 12, 0, tzinfo=UTC)]
    auth = WebAuthService(
        sessions,
        idle_timeout=timedelta(minutes=30),
        absolute_timeout=timedelta(hours=12),
        now=lambda: current_time[0],
    )
    issued = auth.login(user_id=ids["admin_id"], password=ADMIN_PASSWORD)
    current_time[0] += timedelta(minutes=31)

    with pytest.raises(WebAuthenticationError, match="abgelaufen"):
        auth.authenticate(issued.token)

    with sessions() as session:
        stored = session.get(WebAdminSession, issued.identity.session_id)
        assert stored is not None
        assert stored.revoked_at is not None
