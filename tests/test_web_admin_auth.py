from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import URL, Engine, select
from sqlalchemy.orm import Session, sessionmaker

from zunder_zapfe.backend import admin_service as admin_service_module
from zunder_zapfe.backend.superadmin_identity import (
    load_superadmin_identity,
    provision_superadmin_identity,
)
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
    BookingCompletion,
    BookingKind,
    NfcCard,
    TapBooking,
    TechnicalEvent,
    User,
    UserRole,
    WebAdminSession,
)
from zunder_zapfe.persistence.repository import NewTapBooking, Repository

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADMIN_PASSWORD = "Alpha-Admin-2026"
NEW_ADMIN_PASSWORD = "Neues-Admin-2026"
SUPERADMIN_UID = "D00DCAFE"


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
        superadmin_identity=superadmin_identity,
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


def test_emergency_admin_must_change_initial_password_before_management(
    web_admin_api: tuple[object, ...],
) -> None:
    client, sessions, ids = web_admin_api
    with sessions.begin() as session:
        admin = session.get(User, ids["admin_id"])
        assert admin is not None
        admin.password_change_required = True

    login_response = client.post(
        "/api/web-auth/login",
        json={"user_id": ids["admin_id"], "password": ADMIN_PASSWORD},
    )
    assert login_response.status_code == 200
    assert login_response.json()["password_change_required"] is True
    csrf_token = client.cookies.get("zz_admin_csrf")
    assert csrf_token
    assert client.get("/api/web-auth/session").json()["password_change_required"] is True
    assert client.get("/api/web-admin/users").status_code == 403

    changed = client.post(
        "/api/web-auth/password",
        json={
            "current_password": ADMIN_PASSWORD,
            "new_password": NEW_ADMIN_PASSWORD,
        },
        headers=csrf_headers(csrf_token),
    )
    assert changed.status_code == 204

    new_session = client.post(
        "/api/web-auth/login",
        json={"user_id": ids["admin_id"], "password": NEW_ADMIN_PASSWORD},
    )
    assert new_session.status_code == 200
    assert new_session.json()["password_change_required"] is False
    assert client.get("/api/web-admin/users").status_code == 200
    with sessions() as session:
        admin = session.get(User, ids["admin_id"])
        assert admin is not None
        assert admin.password_change_required is False


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


def test_web_admin_can_assign_wristband_while_tap_is_safely_locked(
    web_admin_api: tuple[object, ...],
) -> None:
    client, _sessions, ids = web_admin_api
    csrf_token = login(client, ids["admin_id"])
    headers = csrf_headers(csrf_token)
    path = f"/api/web-admin/users/{ids['user_id']}/nfc-cards/capture"

    started = client.post(path, headers=headers)
    assert started.status_code == 200
    assert started.json()["state"] == "waiting"
    tap_status = client.get("/api/tap/status").json()
    assert tap_status["state"] == "nfc_capture"
    assert tap_status["user_id"] is None
    assert tap_status["valve_open"] is False

    client.post("/api/simulator/nfc/present", json={"uid": "A1B2C3D4"})
    assigned = client.post(path, headers=headers)

    assert assigned.status_code == 200
    assert assigned.json()["state"] == "assigned"
    assert assigned.json()["card"]["uid_hint"] == "…C3D4"
    tap_status = client.get("/api/tap/status").json()
    assert tap_status["state"] == "idle"
    assert tap_status["registration_welcome"] == "Uli User"
    assert client.get("/api/tap/status").json()["state"] == "idle"
    cards = client.get(f"/api/web-admin/users/{ids['user_id']}/nfc-cards").json()
    assert len(cards) == 1
    assert cards[0]["uid_hint"] == "…C3D4"


def test_zz_aut_013_remote_capture_rejects_superadmin_card(
    web_admin_api: tuple[object, ...],
) -> None:
    client, sessions, ids = web_admin_api
    csrf_token = login(client, ids["admin_id"])
    headers = csrf_headers(csrf_token)
    path = f"/api/web-admin/users/{ids['user_id']}/nfc-cards/capture"

    assert client.post(path, headers=headers).json()["state"] == "waiting"
    client.post("/api/simulator/nfc/present", json={"uid": SUPERADMIN_UID})
    response = client.post(path, headers=headers)

    assert response.status_code == 409
    assert "Superadmin-Karte" in response.json()["detail"]
    assert client.get("/api/tap/status").json()["state"] == "idle"
    with sessions() as session:
        assert Repository(session).find_nfc_card(SUPERADMIN_UID) is None


def test_zz_aut_004_assigned_wristband_must_be_removed_before_it_can_log_in(
    web_admin_api: tuple[object, ...],
) -> None:
    client, _sessions, ids = web_admin_api
    csrf_token = login(client, ids["admin_id"])
    headers = csrf_headers(csrf_token)
    path = f"/api/web-admin/users/{ids['user_id']}/nfc-cards/capture"

    assert client.post(path, headers=headers).json()["state"] == "waiting"
    client.post("/api/simulator/nfc/present", json={"uid": "A1B2C3D4"})
    assert client.post(path, headers=headers).json()["state"] == "assigned"

    still_present = client.post(
        "/api/simulator/nfc/present",
        json={"uid": "A1B2C3D4"},
    )
    assert still_present.json()["user_id"] is None
    assert client.get("/api/tap/status").json()["state"] == "idle"

    assert client.post("/api/simulator/nfc/remove").status_code == 204
    presented_again = client.post(
        "/api/simulator/nfc/present",
        json={"uid": "A1B2C3D4"},
    )
    assert presented_again.json()["user_id"] == str(ids["user_id"])


def test_zz_aut_004_conflicting_remote_wristband_does_not_start_a_tap_session(
    web_admin_api: tuple[object, ...],
) -> None:
    client, sessions, ids = web_admin_api
    csrf_token = login(client, ids["admin_id"])
    headers = csrf_headers(csrf_token)
    with sessions.begin() as session:
        repository = Repository(session)
        repository.add_nfc_card(ids["user_id"], "A1B2C3D4")
        other = repository.create_user("Nora", last_name="Neu")

    path = f"/api/web-admin/users/{other.id}/nfc-cards/capture"
    assert client.post(path, headers=headers).json()["state"] == "waiting"
    client.post("/api/simulator/nfc/present", json={"uid": "A1B2C3D4"})

    conflict = client.post(path, headers=headers)

    assert conflict.status_code == 409
    assert "already assigned" in conflict.json()["detail"]
    still_present = client.post(
        "/api/simulator/nfc/present",
        json={"uid": "A1B2C3D4"},
    )
    assert still_present.json()["user_id"] is None
    assert client.get("/api/tap/status").json()["state"] == "idle"

    assert client.post("/api/simulator/nfc/remove").status_code == 204
    presented_again = client.post(
        "/api/simulator/nfc/present",
        json={"uid": "A1B2C3D4"},
    )
    assert presented_again.json()["user_id"] == str(ids["user_id"])


def test_web_admin_can_cancel_remote_wristband_capture(
    web_admin_api: tuple[object, ...],
) -> None:
    client, _sessions, ids = web_admin_api
    csrf_token = login(client, ids["admin_id"])
    headers = csrf_headers(csrf_token)
    path = f"/api/web-admin/users/{ids['user_id']}/nfc-cards/capture"

    assert client.post(path, headers=headers).status_code == 200
    assert client.get("/api/tap/status").json()["state"] == "nfc_capture"
    assert client.delete("/api/web-admin/nfc-capture").status_code == 403
    assert client.delete("/api/web-admin/nfc-capture", headers=headers).status_code == 204
    assert client.get("/api/tap/status").json()["state"] == "idle"


def test_web_admin_can_update_existing_admin_timeout(
    web_admin_api: tuple[object, ...],
) -> None:
    client, _sessions, ids = web_admin_api
    csrf_token = login(client, ids["admin_id"])

    response = client.patch(
        "/api/web-admin/settings",
        json={"admin_session_timeout_seconds": 45},
        headers=csrf_headers(csrf_token),
    )

    assert response.status_code == 200
    assert response.json() == {"admin_session_timeout_seconds": 45}
    assert client.get("/api/web-admin/settings").json() == {"admin_session_timeout_seconds": 45}


def test_remote_wristband_capture_times_out_and_releases_tap(
    web_admin_api: tuple[object, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _sessions, ids = web_admin_api
    monkeypatch.setattr(
        admin_service_module,
        "REMOTE_NFC_CAPTURE_TIMEOUT_SECONDS",
        0.02,
    )
    csrf_token = login(client, ids["admin_id"])
    headers = csrf_headers(csrf_token)
    path = f"/api/web-admin/users/{ids['user_id']}/nfc-cards/capture"

    assert client.post(path, headers=headers).json()["state"] == "waiting"
    deadline = time.monotonic() + 1
    while client.get("/api/tap/status").json()["state"] == "nfc_capture":
        assert time.monotonic() < deadline
        time.sleep(0.01)

    assert client.get("/api/tap/status").json()["state"] == "idle"
    assert client.post(path, headers=headers).json()["state"] == "timed_out"


def test_zz_aut_004_user_delete_preserves_bookings_and_never_reuses_id(
    web_admin_api: tuple[object, ...],
) -> None:
    client, sessions, ids = web_admin_api
    csrf_token = login(client, ids["admin_id"])
    headers = csrf_headers(csrf_token)
    with sessions.begin() as session:
        repository = Repository(session)
        target = repository.get_user(ids["user_id"])
        target.role = UserRole.ADMIN
        repository.add_nfc_card(ids["user_id"], "A1B2C3D4")
        event = repository.create_event("Zunder 2026", 2026, active=True)
        beverage = repository.create_beverage(
            "Testbier",
            default_keg_size_ml=50_000,
            price_per_liter_cents=400,
        )
        keg = repository.activate_new_keg(
            event_id=event.id,
            beverage_id=beverage.id,
            initial_volume_ml=50_000,
        )
        booking = repository.add_tap_booking(
            NewTapBooking(
                event_id=event.id,
                user_id=ids["user_id"],
                beverage_id=beverage.id,
                keg_id=keg.id,
                occurred_at=datetime(2026, 7, 23, 12, 0, tzinfo=UTC),
                target_volume_ml=None,
                measured_volume_ml=400,
                measured_pulses=200,
                price_per_liter_cents=400,
                kind=BookingKind.MANUAL,
                completion=BookingCompletion.RELEASED,
                chargeable=True,
            )
        )
        booking_id = booking.id
    target_auth = WebAuthService(sessions)
    target_auth.set_initial_password(
        user_id=ids["user_id"],
        password=NEW_ADMIN_PASSWORD,
    )
    target_web_session_id = target_auth.login(
        user_id=ids["user_id"],
        password=NEW_ADMIN_PASSWORD,
    ).identity.session_id

    assert (
        client.delete(
            f"/api/web-admin/users/{ids['admin_id']}",
            headers=headers,
        ).status_code
        == 409
    )
    capture_path = f"/api/web-admin/users/{ids['user_id']}/nfc-cards/capture"
    assert client.post(capture_path, headers=headers).json()["state"] == "waiting"
    assert client.get("/api/tap/status").json()["state"] == "nfc_capture"
    deleted = client.delete(
        f"/api/web-admin/users/{ids['user_id']}",
        headers=headers,
    )
    assert deleted.status_code == 204
    assert client.get("/api/tap/status").json()["state"] == "idle"
    assert {user["id"] for user in client.get("/api/web-admin/users").json()} == {ids["admin_id"]}

    with sessions() as session:
        stored_user = session.get(User, ids["user_id"])
        stored_booking = session.get(TapBooking, booking_id)
        assert stored_user is not None
        assert stored_user.deleted_at is not None
        assert stored_user.active is False
        assert stored_user.password_hash is None
        assert stored_booking is not None
        assert stored_booking.user_id == ids["user_id"]
        assert session.scalar(select(NfcCard).where(NfcCard.user_id == ids["user_id"])) is None
        target_web_session = session.get(WebAdminSession, target_web_session_id)
        assert target_web_session is not None
        assert target_web_session.revoked_at is not None
        actions = list(session.scalars(select(AdminAuditEntry.action)))
        assert "user.deleted" in actions

    created = client.post(
        "/api/web-admin/users",
        json={
            "first_name": "Später",
            "last_name": None,
            "note": None,
            "is_admin": False,
        },
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["id"] > ids["user_id"]
