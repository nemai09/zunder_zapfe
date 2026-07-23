"""Provision the immutable local superadmin identity from the ACR122U reader."""

from __future__ import annotations

import argparse
import os
import time
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from zunder_zapfe.backend.superadmin_identity import (
    SuperadminConfigurationError,
    configured_superadmin_credential_path,
    provision_superadmin_identity,
)
from zunder_zapfe.hardware.adapters import Acr122uNfcReader
from zunder_zapfe.hardware.interfaces import NfcReader
from zunder_zapfe.nfc_identity import canonicalize_nfc_uid
from zunder_zapfe.persistence import create_database_engine, create_session_factory
from zunder_zapfe.persistence.repository import Repository

DEFAULT_SYSTEM_DATABASE_URL = "sqlite:////var/lib/zunder-zapfe/zunder-zapfe.db"


def capture_superadmin_uid(
    reader: NfcReader,
    *,
    timeout_seconds: float = 60,
    monotonic_clock: Callable[[], float] = time.monotonic,
    wait: Callable[[float], None] = time.sleep,
) -> str:
    if timeout_seconds <= 0:
        raise ValueError("Capture timeout must be greater than zero")
    deadline = monotonic_clock() + timeout_seconds
    reader.start()
    try:
        while monotonic_clock() < deadline:
            status = reader.snapshot()
            if status.state == "card" and status.uid:
                return canonicalize_nfc_uid(status.uid)
            wait(min(0.1, max(0.0, deadline - monotonic_clock())))
    finally:
        reader.stop()
    raise SuperadminConfigurationError("Keine NFC-Karte innerhalb des Zeitlimits erkannt")


def ensure_uid_is_not_assigned(
    uid: str,
    sessions: sessionmaker[Session],
) -> None:
    """Fail closed when the selected card still belongs to a database user."""
    canonical_uid = canonicalize_nfc_uid(uid)
    try:
        with sessions() as session:
            existing = Repository(session).find_nfc_card(canonical_uid)
    except Exception as error:
        raise SuperadminConfigurationError(
            "Benutzerdatenbank konnte nicht auf Kartenkonflikte geprüft werden"
        ) from error
    if existing is not None:
        raise SuperadminConfigurationError("Diese Karte ist bereits einem Benutzer zugeordnet")


def configured_system_database_url() -> str:
    database_url = os.environ.get(
        "ZUNDER_ZAPFE_DATABASE_URL",
        DEFAULT_SYSTEM_DATABASE_URL,
    )
    parsed = make_url(database_url)
    if parsed.get_backend_name() != "sqlite" or not parsed.database:
        raise SuperadminConfigurationError(
            "Superadmin-Einrichtung benötigt die lokale SQLite-Datenbank"
        )
    if not Path(parsed.database).is_file():
        raise SuperadminConfigurationError("Produktive Benutzerdatenbank wurde nicht gefunden")
    return database_url


def run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--credential-path",
        type=Path,
        default=configured_superadmin_credential_path(),
        help="lokale Credential-Datei; enthält keine UID im Klartext",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60,
        help="Sekunden zum Auflegen der Superadmin-Karte",
    )
    arguments = parser.parse_args()

    if arguments.credential_path.exists():
        raise SystemExit("Superadmin-Credential existiert bereits und wird nicht überschrieben.")

    print("Superadmin-Karte auf den ACR122U legen.")
    engine = None
    try:
        uid = capture_superadmin_uid(
            Acr122uNfcReader(),
            timeout_seconds=arguments.timeout,
        )
        engine = create_database_engine(configured_system_database_url())
        ensure_uid_is_not_assigned(uid, create_session_factory(engine))
        provision_superadmin_identity(uid, arguments.credential_path)
    except (SuperadminConfigurationError, ValueError) as error:
        raise SystemExit(str(error)) from error
    finally:
        if engine is not None:
            engine.dispose()
    print("Superadmin-Karte wurde lokal eingerichtet; die UID wurde nicht ausgegeben.")


if __name__ == "__main__":
    run()
