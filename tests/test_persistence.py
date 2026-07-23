from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import URL, Engine, inspect, select, text
from sqlalchemy.exc import IntegrityError

from zunder_zapfe.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from zunder_zapfe.persistence.models import (
    AdminAuditEntry,
    BookingCompletion,
    BookingKind,
    Event,
    ImmutableBookingError,
    Keg,
    NfcCard,
    TapBooking,
    TechnicalEvent,
    UserRole,
)
from zunder_zapfe.persistence.repository import NewTapBooking, Repository
from zunder_zapfe.superadmin_card import ensure_uid_is_not_assigned

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sqlite_url(path: Path) -> str:
    return URL.create("sqlite", database=str(path)).render_as_string(hide_password=False)


def alembic_config(url: str) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    return config


@pytest.fixture
def migrated_engine(tmp_path: Path) -> Iterator[Engine]:
    url = sqlite_url(tmp_path / "zunder-zapfe-test.db")
    command.upgrade(alembic_config(url), "head")
    engine = create_database_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()


def seed_booking(engine: Engine) -> tuple[int, int, int, int, int]:
    sessions = create_session_factory(engine)
    with sessions.begin() as session:
        repository = Repository(session)
        event = repository.create_event("Zunder 2026", 2026, active=True)
        user = repository.create_user("Chris")
        beverage = repository.create_beverage(
            "Testbier", default_keg_size_ml=50_000, price_per_liter_cents=400
        )
        keg = repository.activate_new_keg(
            event_id=event.id,
            beverage_id=beverage.id,
            initial_volume_ml=50_000,
        )
        booking = repository.add_tap_booking(
            NewTapBooking(
                event_id=event.id,
                user_id=user.id,
                beverage_id=beverage.id,
                keg_id=keg.id,
                occurred_at=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
                target_volume_ml=500,
                measured_volume_ml=400,
                measured_pulses=200,
                price_per_liter_cents=400,
                kind=BookingKind.PORTION,
                completion=BookingCompletion.USER_ABORT,
                chargeable=True,
            )
        )
        return event.id, user.id, beverage.id, keg.id, booking.id


def test_initial_migration_creates_current_schema(migrated_engine: Engine) -> None:
    tables = set(inspect(migrated_engine).get_table_names())

    assert tables == {
        "admin_audit_entries",
        "alembic_version",
        "beverages",
        "events",
        "kegs",
        "nfc_cards",
        "settings",
        "tap_bookings",
        "technical_events",
        "users",
        "web_admin_sessions",
    }
    user_columns = {column["name"] for column in inspect(migrated_engine).get_columns("users")}
    assert "deleted_at" in user_columns
    assert "password_change_required" in user_columns
    booking_columns = {
        column["name"]: column for column in inspect(migrated_engine).get_columns("tap_bookings")
    }
    assert booking_columns["user_id"]["nullable"] is True
    assert booking_columns["login_session_id"]["nullable"] is True
    audit_columns = {
        column["name"]: column
        for column in inspect(migrated_engine).get_columns("admin_audit_entries")
    }
    assert audit_columns["actor_kind"]["nullable"] is False
    assert audit_columns["admin_user_id"]["nullable"] is True
    command.check(alembic_config(str(migrated_engine.url)))


def test_zz_aut_013_superadmin_provisioning_rejects_existing_user_card(
    migrated_engine: Engine,
) -> None:
    sessions = create_session_factory(migrated_engine)
    with sessions.begin() as session:
        repository = Repository(session)
        user = repository.create_user("Bereits zugeordnet")
        repository.add_nfc_card(user.id, "D00DCAFE")

    with pytest.raises(
        RuntimeError,
        match="bereits einem Benutzer zugeordnet",
    ):
        ensure_uid_is_not_assigned("d0-0d-ca-fe", sessions)

    ensure_uid_is_not_assigned("DEADBEEF", sessions)


def test_initial_migration_creates_missing_database_directory(tmp_path: Path) -> None:
    database_path = tmp_path / "new-data-directory" / "zunder-zapfe-test.db"

    command.upgrade(alembic_config(sqlite_url(database_path)), "head")

    assert database_path.is_file()


def test_manual_booking_migration_preserves_existing_bookings(tmp_path: Path) -> None:
    url = sqlite_url(tmp_path / "upgrade-from-initial.db")
    config = alembic_config(url)
    command.upgrade(config, "665c808f8308")
    engine = create_database_engine(url)
    try:
        timestamp = "2026-07-19 12:00:00"
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO events "
                    "(id, name, year, active, created_at) "
                    "VALUES (1, 'Zunder 2026', 2026, 1, :timestamp)"
                ),
                {"timestamp": timestamp},
            )
            connection.execute(
                text(
                    "INSERT INTO users "
                    "(id, display_name, role, active, created_at, updated_at) "
                    "VALUES (1, 'Chris', 'user', 1, :timestamp, :timestamp)"
                ),
                {"timestamp": timestamp},
            )
            connection.execute(
                text(
                    "INSERT INTO beverages "
                    "(id, name, default_keg_size_ml, price_per_liter_cents, active, "
                    "created_at, updated_at) VALUES "
                    "(1, 'Testbier', 50000, 400, 1, :timestamp, :timestamp)"
                ),
                {"timestamp": timestamp},
            )
            connection.execute(
                text(
                    "INSERT INTO kegs "
                    "(id, event_id, beverage_id, initial_volume_ml, active, opened_at) "
                    "VALUES (1, 1, 1, 50000, 1, :timestamp)"
                ),
                {"timestamp": timestamp},
            )
            connection.execute(
                text(
                    "INSERT INTO tap_bookings "
                    "(id, event_id, user_id, beverage_id, keg_id, occurred_at, "
                    "target_volume_ml, measured_volume_ml, measured_pulses, "
                    "price_per_liter_cents, amount_cents, kind, completion, chargeable) "
                    "VALUES (1, 1, 1, 1, 1, :timestamp, 500, 400, 200, 400, 160, "
                    "'portion', 'user_abort', 1)"
                ),
                {"timestamp": timestamp},
            )
            connection.execute(
                text(
                    "INSERT INTO admin_audit_entries "
                    "(id, occurred_at, admin_user_id, action, entity_type) "
                    "VALUES (1, :timestamp, 1, 'legacy.action', 'legacy')"
                ),
                {"timestamp": timestamp},
            )
        booking_id = 1
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    migrated = create_database_engine(url)
    try:
        sessions = create_session_factory(migrated)
        with sessions() as session:
            booking = session.get(TapBooking, booking_id)
            assert booking is not None
            assert booking.kind is BookingKind.PORTION
            assert booking.login_session_id == "legacy-1"
            audit = session.get(AdminAuditEntry, 1)
            assert audit is not None
            assert audit.actor_kind == "user_admin"
            assert audit.admin_user_id == 1
    finally:
        migrated.dispose()

    command.downgrade(config, "e18c4f45a501")
    downgraded = create_database_engine(url)
    try:
        assert "actor_kind" not in {
            column["name"] for column in inspect(downgraded).get_columns("admin_audit_entries")
        }
        booking_columns = {
            column["name"]: column for column in inspect(downgraded).get_columns("tap_bookings")
        }
        assert booking_columns["user_id"]["nullable"] is False
        assert booking_columns["login_session_id"]["nullable"] is False
    finally:
        downgraded.dispose()


def test_user_profile_migration_backfills_existing_display_name(tmp_path: Path) -> None:
    url = sqlite_url(tmp_path / "upgrade-user-profile.db")
    config = alembic_config(url)
    command.upgrade(config, "830d216e8ba1")
    engine = create_database_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users "
                    "(id, display_name, role, active, created_at, updated_at) "
                    "VALUES (1, 'Legacy Name', 'user', 1, :timestamp, :timestamp)"
                ),
                {"timestamp": "2026-07-19 12:00:00"},
            )
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    migrated = create_database_engine(url)
    try:
        row = (
            migrated.connect()
            .execute(text("SELECT first_name, last_name, note FROM users WHERE id = 1"))
            .one()
        )
        assert row == ("Legacy Name", None, None)
    finally:
        migrated.dispose()


def test_web_admin_session_migration_preserves_existing_admin(tmp_path: Path) -> None:
    url = sqlite_url(tmp_path / "upgrade-web-admin-session.db")
    config = alembic_config(url)
    command.upgrade(config, "a91f5e7c2d10")
    engine = create_database_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users "
                    "(id, display_name, first_name, role, active, password_hash, "
                    "created_at, updated_at) "
                    "VALUES (1, 'Ada Admin', 'Ada', 'admin', 1, 'existing-hash', "
                    ":timestamp, :timestamp)"
                ),
                {"timestamp": "2026-07-23 12:00:00"},
            )
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    migrated = create_database_engine(url)
    try:
        with migrated.connect() as connection:
            password_hash = connection.scalar(text("SELECT password_hash FROM users WHERE id = 1"))
        assert password_hash == "existing-hash"
        assert "web_admin_sessions" in inspect(migrated).get_table_names()
    finally:
        migrated.dispose()


def test_user_ids_are_not_reused_after_a_physical_row_delete(
    migrated_engine: Engine,
) -> None:
    sessions = create_session_factory(migrated_engine)
    with sessions.begin() as session:
        repository = Repository(session)
        repository.create_user("Erster")
        removed = repository.create_user("Zweiter")
        removed_id = removed.id

    with migrated_engine.begin() as connection:
        users_ddl = connection.scalar(
            text("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'")
        )
        connection.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": removed_id})
    assert "AUTOINCREMENT" in str(users_ddl).upper()

    with sessions.begin() as session:
        created = Repository(session).create_user("Dritter")
        assert created.id > removed_id


def test_repository_persists_core_domain_and_calculates_amount(
    migrated_engine: Engine,
) -> None:
    event_id, user_id, _beverage_id, keg_id, booking_id = seed_booking(migrated_engine)
    sessions = create_session_factory(migrated_engine)

    with sessions() as session:
        repository = Repository(session)
        bookings = repository.list_user_bookings(event_id=event_id, user_id=user_id)

        assert [booking.id for booking in bookings] == [booking_id]
        assert bookings[0].measured_volume_ml == 400
        assert bookings[0].amount_cents == 160
        assert repository.remaining_keg_volume_ml(keg_id) == 49_600


def test_superadmin_maintenance_has_no_user_or_login_and_is_audited(
    migrated_engine: Engine,
) -> None:
    event_id, _user_id, beverage_id, keg_id, _booking_id = seed_booking(migrated_engine)
    sessions = create_session_factory(migrated_engine)

    with sessions.begin() as session:
        repository = Repository(session)
        booking = repository.add_tap_booking(
            NewTapBooking(
                event_id=event_id,
                user_id=None,
                beverage_id=beverage_id,
                keg_id=keg_id,
                occurred_at=datetime.now(UTC),
                target_volume_ml=None,
                measured_volume_ml=100,
                measured_pulses=50,
                price_per_liter_cents=400,
                kind=BookingKind.MAINTENANCE,
                completion=BookingCompletion.CARD_REMOVED,
                chargeable=False,
                login_session_id=None,
            )
        )
        audit = repository.record_superadmin_action(
            action="maintenance.poured",
            entity_type="tap_booking",
            entity_id=str(booking.id),
        )
        assert booking.user_id is None
        assert booking.login_session_id is None
        assert booking.amount_cents == 0
        assert audit.actor_kind == "superadmin"
        assert audit.admin_user_id is None


def test_userless_chargeable_booking_is_rejected(migrated_engine: Engine) -> None:
    event_id, _user_id, beverage_id, keg_id, _booking_id = seed_booking(migrated_engine)
    sessions = create_session_factory(migrated_engine)

    with sessions.begin() as session:
        with pytest.raises(ValueError, match="userless booking"):
            Repository(session).add_tap_booking(
                NewTapBooking(
                    event_id=event_id,
                    user_id=None,
                    beverage_id=beverage_id,
                    keg_id=keg_id,
                    occurred_at=datetime.now(UTC),
                    target_volume_ml=None,
                    measured_volume_ml=100,
                    measured_pulses=50,
                    price_per_liter_cents=400,
                    kind=BookingKind.MANUAL,
                    completion=BookingCompletion.RELEASED,
                    chargeable=True,
                    login_session_id=None,
                )
            )


def test_only_one_event_and_keg_remain_active(migrated_engine: Engine) -> None:
    sessions = create_session_factory(migrated_engine)
    with sessions.begin() as session:
        repository = Repository(session)
        first_event = repository.create_event("Zunder 2025", 2025, active=True)
        second_event = repository.create_event("Zunder 2026", 2026, active=True)
        beverage = repository.create_beverage(
            "Testbier", default_keg_size_ml=50_000, price_per_liter_cents=400
        )
        first_keg = repository.activate_new_keg(
            event_id=second_event.id,
            beverage_id=beverage.id,
            initial_volume_ml=50_000,
        )
        second_keg = repository.activate_new_keg(
            event_id=second_event.id,
            beverage_id=beverage.id,
            initial_volume_ml=30_000,
        )

        assert session.get(Event, first_event.id).active is False
        assert session.get(Event, second_event.id).active is True
        assert session.get(Keg, first_keg.id).active is False
        assert session.get(Keg, first_keg.id).closed_at is not None
        assert session.get(Keg, second_keg.id).active is True


def test_nfc_uid_is_canonical_and_blocked_card_does_not_authenticate(
    migrated_engine: Engine,
) -> None:
    sessions = create_session_factory(migrated_engine)
    with sessions.begin() as session:
        repository = Repository(session)
        user = repository.create_user("Admin", role=UserRole.ADMIN)
        card = repository.add_nfc_card(user.id, "04-aa:bb cc")

        assert card.uid == "04AABBCC"
        assert repository.find_active_user_by_card("04 AA BB CC").id == user.id

        card.active = False
        session.flush()
        assert repository.find_active_user_by_card("04AABBCC") is None


def test_booking_is_immutable_in_orm_and_database(migrated_engine: Engine) -> None:
    *_ids, booking_id = seed_booking(migrated_engine)
    sessions = create_session_factory(migrated_engine)

    with sessions() as session:
        booking = session.get(TapBooking, booking_id)
        assert booking is not None
        booking.amount_cents = 1
        with pytest.raises(ImmutableBookingError):
            session.flush()
        session.rollback()

    with pytest.raises(IntegrityError):
        with migrated_engine.begin() as connection:
            connection.execute(
                text("UPDATE tap_bookings SET amount_cents = 1 WHERE id = :booking_id"),
                {"booking_id": booking_id},
            )


def test_booking_must_match_keg_event_and_beverage(migrated_engine: Engine) -> None:
    event_id, user_id, beverage_id, keg_id, _booking_id = seed_booking(migrated_engine)
    sessions = create_session_factory(migrated_engine)
    with sessions.begin() as session:
        repository = Repository(session)
        other_event = repository.create_event("Zunder 2027", 2027)

        with pytest.raises(ValueError, match="must match"):
            repository.add_tap_booking(
                NewTapBooking(
                    event_id=other_event.id,
                    user_id=user_id,
                    beverage_id=beverage_id,
                    keg_id=keg_id,
                    occurred_at=datetime.now(UTC),
                    target_volume_ml=500,
                    measured_volume_ml=500,
                    measured_pulses=250,
                    price_per_liter_cents=400,
                    kind=BookingKind.PORTION,
                    completion=BookingCompletion.TARGET_REACHED,
                    chargeable=True,
                )
            )


def test_sqlite_foreign_keys_are_enforced(migrated_engine: Engine) -> None:
    sessions = create_session_factory(migrated_engine)
    with pytest.raises(IntegrityError):
        with sessions.begin() as session:
            session.add(NfcCard(uid="AABBCCDD", user_id=999, active=True))
            session.flush()


def test_setting_changes_are_admin_only_and_audited(migrated_engine: Engine) -> None:
    sessions = create_session_factory(migrated_engine)
    with sessions.begin() as session:
        repository = Repository(session)
        admin = repository.create_user("Admin", role=UserRole.ADMIN)
        user = repository.create_user("User")

        with pytest.raises(PermissionError):
            repository.set_setting("tap.logout_seconds", 30, admin_user_id=user.id)

        repository.set_setting("tap.logout_seconds", 30, admin_user_id=admin.id)
        repository.set_setting("tap.logout_seconds", 45, admin_user_id=admin.id)

        entries = list(session.scalars(select(AdminAuditEntry).order_by(AdminAuditEntry.id)))
        assert len(entries) == 2
        assert all(entry.actor_kind == "user_admin" for entry in entries)
        assert entries[0].old_values_json is None
        assert entries[0].new_values_json == "30"
        assert entries[1].old_values_json == "30"
        assert entries[1].new_values_json == "45"


def test_technical_events_are_persisted(migrated_engine: Engine) -> None:
    sessions = create_session_factory(migrated_engine)
    with sessions.begin() as session:
        repository = Repository(session)
        event = repository.record_technical_event(
            severity="error",
            event_type="tap.flow_timeout",
            message="Kein Durchfluss erkannt",
            details={"state": "portion_pouring"},
        )

        stored = session.get(TechnicalEvent, event.id)
        assert stored is not None
        assert stored.details_json == '{"state":"portion_pouring"}'
