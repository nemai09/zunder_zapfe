"""Provision the immutable local superadmin identity from the ACR122U reader."""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from pathlib import Path

from zunder_zapfe.backend.superadmin_identity import (
    SuperadminConfigurationError,
    configured_superadmin_credential_path,
    provision_superadmin_identity,
)
from zunder_zapfe.hardware.adapters import Acr122uNfcReader
from zunder_zapfe.hardware.interfaces import NfcReader
from zunder_zapfe.nfc_identity import canonicalize_nfc_uid


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
    try:
        uid = capture_superadmin_uid(
            Acr122uNfcReader(),
            timeout_seconds=arguments.timeout,
        )
        provision_superadmin_identity(uid, arguments.credential_path)
    except (SuperadminConfigurationError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print("Superadmin-Karte wurde lokal eingerichtet; die UID wurde nicht ausgegeben.")


if __name__ == "__main__":
    run()
