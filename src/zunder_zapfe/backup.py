"""Create consistent local backups and privacy-reduced billing exports."""

from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
import zipfile
from collections.abc import Callable
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.engine import make_url

from zunder_zapfe.persistence.database import database_url

DEFAULT_BACKUP_DIRECTORY = "data/backups"
DEFAULT_BACKUP_RETENTION = 400
OVERDUE_AFTER = timedelta(minutes=75)
STATUS_FILENAME = "status.json"


class BackupError(RuntimeError):
    """Raised when a backup cannot be created or accessed."""


@dataclass(frozen=True)
class BackupStatus:
    state: str
    last_attempt_at: str | None = None
    last_success_at: str | None = None
    booking_count: int | None = None
    database_file: str | None = None
    csv_archive_file: str | None = None
    detail: str | None = None

    def as_dict(self) -> dict[str, str | int | None]:
        return asdict(self)


class BackupService:
    """Back up one file-based SQLite database without stopping the web service."""

    def __init__(
        self,
        *,
        source_url: str | None = None,
        backup_directory: str | Path | None = None,
        retention: int = DEFAULT_BACKUP_RETENTION,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        parsed_url = make_url(source_url or database_url())
        if parsed_url.get_backend_name() != "sqlite" or parsed_url.database in {
            None,
            "",
            ":memory:",
        }:
            raise BackupError("Datensicherung benötigt eine dateibasierte SQLite-Datenbank")
        if retention < 1:
            raise ValueError("Backup retention must be positive")
        self._source = Path(parsed_url.database).expanduser().resolve()
        configured_directory = backup_directory or os.environ.get(
            "ZUNDER_ZAPFE_BACKUP_DIR", DEFAULT_BACKUP_DIRECTORY
        )
        self._directory = Path(configured_directory).expanduser().resolve()
        self._retention = retention
        self._now = now or (lambda: datetime.now(UTC))

    def create(self) -> BackupStatus:
        """Create and verify one database snapshot and its CSV export package."""
        attempt_at = self._now().astimezone(UTC)
        try:
            status = self._create_snapshot(attempt_at)
        except Exception as error:
            detail = str(error) or error.__class__.__name__
            self._record_failure(attempt_at, detail)
            if isinstance(error, BackupError):
                raise
            raise BackupError(detail) from error
        return status

    def status(self) -> BackupStatus:
        stored = self._read_status()
        if stored is None:
            return BackupStatus(state="missing", detail="Noch keine Sicherung vorhanden")
        if stored.state == "ok" and stored.last_success_at is not None:
            last_success = _parse_timestamp(stored.last_success_at)
            if self._now().astimezone(UTC) - last_success > OVERDUE_AFTER:
                return BackupStatus(
                    **{
                        **stored.as_dict(),
                        "state": "overdue",
                        "detail": "Die letzte erfolgreiche Sicherung ist überfällig",
                    }
                )
        return stored

    def latest_csv_archive(self) -> Path:
        status = self.status()
        if status.csv_archive_file is None:
            raise BackupError("Noch kein CSV-Sicherungspaket vorhanden")
        archive = (self._directory / status.csv_archive_file).resolve()
        try:
            archive.relative_to(self._directory)
        except ValueError as error:
            raise BackupError("Ungültiger Sicherungspfad") from error
        if not archive.is_file():
            raise BackupError("Das letzte CSV-Sicherungspaket fehlt")
        return archive

    def _create_snapshot(self, attempt_at: datetime) -> BackupStatus:
        if not self._source.is_file():
            raise BackupError(f"SQLite-Datenbank nicht gefunden: {self._source}")
        self._prepare_directory()
        stamp = attempt_at.strftime("%Y%m%dT%H%M%SZ")
        database_name = f"zunder-zapfe-{stamp}.db"
        raw_csv_name = f"zunder-zapfe-buchungen-{stamp}.csv"
        billing_csv_name = f"zunder-zapfe-abrechnung-{stamp}.csv"
        archive_name = f"zunder-zapfe-csv-sicherung-{stamp}.zip"
        temp_database = self._directory / f".{database_name}.tmp"
        temp_raw_csv = self._directory / f".{raw_csv_name}.tmp"
        temp_billing_csv = self._directory / f".{billing_csv_name}.tmp"
        temp_archive = self._directory / f".{archive_name}.tmp"
        temporary_files = [temp_database, temp_raw_csv, temp_billing_csv, temp_archive]
        try:
            self._copy_database(temp_database)
            booking_count = self._verify_database(temp_database)
            self._write_raw_csv(temp_database, temp_raw_csv)
            self._write_billing_csv(temp_database, temp_billing_csv)
            self._write_csv_archive(
                temp_archive,
                temp_raw_csv,
                temp_billing_csv,
                attempt_at=attempt_at,
                booking_count=booking_count,
            )
            published = {
                temp_database: self._directory / database_name,
                temp_raw_csv: self._directory / raw_csv_name,
                temp_billing_csv: self._directory / billing_csv_name,
                temp_archive: self._directory / archive_name,
            }
            for temporary, final in published.items():
                os.replace(temporary, final)
                final.chmod(0o600)
            status = BackupStatus(
                state="ok",
                last_attempt_at=_format_timestamp(attempt_at),
                last_success_at=_format_timestamp(attempt_at),
                booking_count=booking_count,
                database_file=database_name,
                csv_archive_file=archive_name,
            )
            self._write_status(status)
            self._prune_old_files()
            return status
        finally:
            for path in temporary_files:
                path.unlink(missing_ok=True)

    def _copy_database(self, destination: Path) -> None:
        source_uri = f"file:{self._source.as_posix()}?mode=ro"
        try:
            with closing(sqlite3.connect(source_uri, uri=True, timeout=10)) as source:
                with closing(sqlite3.connect(destination, timeout=10)) as target:
                    source.backup(target)
        except sqlite3.Error as error:
            raise BackupError(f"SQLite-Sicherung fehlgeschlagen: {error}") from error

    @staticmethod
    def _verify_database(database: Path) -> int:
        try:
            with closing(sqlite3.connect(database)) as connection:
                result = connection.execute("PRAGMA integrity_check").fetchone()
                if result is None or result[0] != "ok":
                    raise BackupError("Integritätsprüfung der Sicherung fehlgeschlagen")
                row = connection.execute("SELECT COUNT(*) FROM tap_bookings").fetchone()
        except sqlite3.Error as error:
            raise BackupError(f"Sicherungsprüfung fehlgeschlagen: {error}") from error
        return int(row[0]) if row is not None else 0

    @staticmethod
    def _write_raw_csv(database: Path, destination: Path) -> None:
        headers = [
            "Buchung-ID",
            "Login-Sitzung",
            "Zeitpunkt",
            "Benutzer-ID",
            "Anzeigename",
            "Vorname",
            "Nachname",
            "Veranstaltung-ID",
            "Veranstaltung",
            "Jahr",
            "Getränk-ID",
            "Getränk",
            "Fass-ID",
            "Zielmenge (ml)",
            "Istmenge (ml)",
            "Impulse",
            "Preis (Cent/L)",
            "Betrag (Cent)",
            "Art",
            "Abschluss",
            "Kostenpflichtig",
        ]
        query = """
            SELECT b.id, b.login_session_id, b.occurred_at,
                   u.id, u.display_name, u.first_name, u.last_name,
                   e.id, e.name, e.year,
                   v.id, v.name, b.keg_id,
                   b.target_volume_ml, b.measured_volume_ml, b.measured_pulses,
                   b.price_per_liter_cents, b.amount_cents,
                   b.kind, b.completion, b.chargeable
            FROM tap_bookings AS b
            JOIN users AS u ON u.id = b.user_id
            JOIN events AS e ON e.id = b.event_id
            JOIN beverages AS v ON v.id = b.beverage_id
            ORDER BY b.id
        """
        BackupService._write_query_csv(database, destination, headers, query)

    @staticmethod
    def _write_billing_csv(database: Path, destination: Path) -> None:
        headers = [
            "Veranstaltung-ID",
            "Veranstaltung",
            "Jahr",
            "Benutzer-ID",
            "Vorname",
            "Nachname",
            "Anzeigename",
            "Getränk-ID",
            "Getränk",
            "Buchungen",
            "Menge (ml)",
            "Betrag (Cent)",
        ]
        query = """
            SELECT e.id, e.name, e.year,
                   u.id, u.first_name, u.last_name, u.display_name,
                   v.id, v.name,
                   COUNT(DISTINCT b.login_session_id),
                   SUM(b.measured_volume_ml), SUM(b.amount_cents)
            FROM tap_bookings AS b
            JOIN users AS u ON u.id = b.user_id
            JOIN events AS e ON e.id = b.event_id
            JOIN beverages AS v ON v.id = b.beverage_id
            WHERE b.chargeable = 1
            GROUP BY e.id, u.id, v.id
            ORDER BY e.year, e.name, u.display_name, v.name, u.id, v.id
        """
        BackupService._write_query_csv(database, destination, headers, query)

    @staticmethod
    def _write_query_csv(
        database: Path,
        destination: Path,
        headers: list[str],
        query: str,
    ) -> None:
        try:
            with closing(sqlite3.connect(database)) as connection:
                rows = connection.execute(query)
                with destination.open("w", encoding="utf-8-sig", newline="") as output:
                    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
                    writer.writerow(headers)
                    writer.writerows(rows)
        except (OSError, sqlite3.Error) as error:
            raise BackupError(f"CSV-Sicherung fehlgeschlagen: {error}") from error

    @staticmethod
    def _write_csv_archive(
        destination: Path,
        raw_csv: Path,
        billing_csv: Path,
        *,
        attempt_at: datetime,
        booking_count: int,
    ) -> None:
        info = io.StringIO()
        info.write("Zunder Zapfe CSV-Sicherung\n")
        info.write(f"Erstellt (UTC): {_format_timestamp(attempt_at)}\n")
        info.write(f"Gesicherte Rohbuchungen: {booking_count}\n")
        info.write("Enthält keine NFC-IDs und keine Passwortdaten.\n")
        try:
            with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(raw_csv, "buchungen.csv")
                archive.write(billing_csv, "abrechnung.csv")
                archive.writestr("sicherungsinfo.txt", info.getvalue())
        except (OSError, zipfile.BadZipFile) as error:
            raise BackupError(f"CSV-Paket konnte nicht erstellt werden: {error}") from error

    def _prepare_directory(self) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        self._directory.chmod(0o700)

    def _record_failure(self, attempt_at: datetime, detail: str) -> None:
        self._prepare_directory()
        previous = self._read_status()
        failed = BackupStatus(
            state="error",
            last_attempt_at=_format_timestamp(attempt_at),
            last_success_at=previous.last_success_at if previous else None,
            booking_count=previous.booking_count if previous else None,
            database_file=previous.database_file if previous else None,
            csv_archive_file=previous.csv_archive_file if previous else None,
            detail=detail,
        )
        self._write_status(failed)

    def _read_status(self) -> BackupStatus | None:
        path = self._directory / STATUS_FILENAME
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return BackupStatus(**payload)
        except FileNotFoundError:
            return None
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            return BackupStatus(state="error", detail=f"Sicherungsstatus unlesbar: {error}")

    def _write_status(self, status: BackupStatus) -> None:
        temporary = self._directory / f".{STATUS_FILENAME}.tmp"
        temporary.write_text(
            json.dumps(status.as_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.chmod(0o600)
        os.replace(temporary, self._directory / STATUS_FILENAME)

    def _prune_old_files(self) -> None:
        patterns = (
            "zunder-zapfe-*.db",
            "zunder-zapfe-buchungen-*.csv",
            "zunder-zapfe-abrechnung-*.csv",
            "zunder-zapfe-csv-sicherung-*.zip",
        )
        for pattern in patterns:
            files = sorted(self._directory.glob(pattern), reverse=True)
            for old_file in files[self._retention :]:
                old_file.unlink(missing_ok=True)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def run() -> None:
    """Create one backup for the systemd timer."""
    try:
        status = BackupService().create()
    except BackupError as error:
        raise SystemExit(f"Datensicherung fehlgeschlagen: {error}") from error
    print(f"Datensicherung erfolgreich: {status.booking_count} Buchungen, {status.database_file}")


if __name__ == "__main__":
    run()
