from __future__ import annotations

import csv
import io
import json
import sqlite3
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import URL

from zunder_zapfe.backup import BackupError, BackupService
from zunder_zapfe.persistence.database import create_database_engine, create_session_factory
from zunder_zapfe.persistence.models import BookingCompletion, BookingKind, UserRole
from zunder_zapfe.persistence.repository import NewTapBooking, Repository

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_booked_database(path: Path) -> str:
    url = URL.create("sqlite", database=str(path)).render_as_string(hide_password=False)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = create_database_engine(url)
    sessions = create_session_factory(engine)
    with sessions.begin() as session:
        repository = Repository(session)
        event = repository.create_event("Zunder 2026", 2026, active=True)
        user = repository.create_user("Ada", last_name="Admin", role=UserRole.ADMIN)
        user.password_hash = "DARF-NICHT-IN-DIE-CSV"
        card = repository.add_nfc_card(user.id, "DEADBEEF")
        assert card.uid == "DEADBEEF"
        beverage = repository.create_beverage(
            "Pils",
            default_keg_size_ml=50_000,
            price_per_liter_cents=450,
        )
        keg = repository.activate_new_keg(
            event_id=event.id,
            beverage_id=beverage.id,
            initial_volume_ml=50_000,
        )
        for measured_volume_ml in (300, 200):
            repository.add_tap_booking(
                NewTapBooking(
                    event_id=event.id,
                    user_id=user.id,
                    beverage_id=beverage.id,
                    keg_id=keg.id,
                    occurred_at=datetime(2026, 8, 9, 12, 0, tzinfo=UTC),
                    target_volume_ml=None,
                    measured_volume_ml=measured_volume_ml,
                    measured_pulses=measured_volume_ml // 2,
                    price_per_liter_cents=450,
                    kind=BookingKind.MANUAL,
                    completion=BookingCompletion.RELEASED,
                    chargeable=True,
                    login_session_id="login-1",
                )
            )
    engine.dispose()
    return url


def test_backup_is_consistent_and_csv_package_omits_credentials(tmp_path: Path) -> None:
    database_path = tmp_path / "source.db"
    backup_directory = tmp_path / "backups"
    url = create_booked_database(database_path)
    now = datetime(2026, 8, 9, 12, 30, tzinfo=UTC)
    service = BackupService(
        source_url=url,
        backup_directory=backup_directory,
        now=lambda: now,
    )

    status = service.create()

    assert status.state == "ok"
    assert status.booking_count == 2
    assert status.database_file is not None
    backup_database = backup_directory / status.database_file
    with sqlite3.connect(backup_database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("SELECT COUNT(*) FROM tap_bookings").fetchone() == (2,)

    archive_path = service.latest_csv_archive()
    with zipfile.ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == {
            "abrechnung.csv",
            "buchungen.csv",
            "sicherungsinfo.txt",
        }
        raw_csv = archive.read("buchungen.csv").decode("utf-8-sig")
        billing_csv = archive.read("abrechnung.csv").decode("utf-8-sig")
        info = archive.read("sicherungsinfo.txt").decode("utf-8")

    assert "DEADBEEF" not in raw_csv + billing_csv
    assert "DARF-NICHT-IN-DIE-CSV" not in raw_csv + billing_csv
    assert "Ada Admin" in raw_csv
    rows = list(csv.DictReader(io.StringIO(billing_csv), delimiter=";"))
    assert rows == [
        {
            "Veranstaltung-ID": "1",
            "Veranstaltung": "Zunder 2026",
            "Jahr": "2026",
            "Benutzer-ID": "1",
            "Vorname": "Ada",
            "Nachname": "Admin",
            "Anzeigename": "Ada Admin",
            "Getränk-ID": "1",
            "Getränk": "Pils",
            "Buchungen": "1",
            "Menge (ml)": "500",
            "Betrag (Cent)": "225",
        }
    ]
    assert "Gesicherte Rohbuchungen: 2" in info


def test_failed_backup_preserves_last_successful_download(tmp_path: Path) -> None:
    database_path = tmp_path / "source.db"
    backup_directory = tmp_path / "backups"
    url = create_booked_database(database_path)
    current_time = datetime(2026, 8, 9, 12, 30, tzinfo=UTC)
    service = BackupService(
        source_url=url,
        backup_directory=backup_directory,
        now=lambda: current_time,
    )
    successful = service.create()
    successful_archive = service.latest_csv_archive()

    current_time += timedelta(minutes=30)
    missing_url = URL.create("sqlite", database=str(tmp_path / "missing.db")).render_as_string(
        hide_password=False
    )
    service = BackupService(
        source_url=missing_url,
        backup_directory=backup_directory,
        now=lambda: current_time,
    )
    with pytest.raises(BackupError, match="nicht gefunden"):
        service.create()

    failed = service.status()
    assert failed.state == "error"
    assert failed.last_success_at == successful.last_success_at
    assert failed.booking_count == 2
    assert service.latest_csv_archive() == successful_archive


def test_backup_status_becomes_overdue_without_destroying_snapshot(tmp_path: Path) -> None:
    database_path = tmp_path / "source.db"
    backup_directory = tmp_path / "backups"
    url = create_booked_database(database_path)
    current_time = datetime(2026, 8, 9, 12, 30, tzinfo=UTC)
    service = BackupService(
        source_url=url,
        backup_directory=backup_directory,
        now=lambda: current_time,
    )
    service.create()

    current_time += timedelta(minutes=76)

    assert service.status().state == "overdue"
    assert service.latest_csv_archive().is_file()


def test_backup_status_file_contains_no_database_contents(tmp_path: Path) -> None:
    database_path = tmp_path / "source.db"
    backup_directory = tmp_path / "backups"
    url = create_booked_database(database_path)
    BackupService(source_url=url, backup_directory=backup_directory).create()

    status = json.loads((backup_directory / "status.json").read_text(encoding="utf-8"))

    assert status["state"] == "ok"
    assert "DEADBEEF" not in json.dumps(status)
