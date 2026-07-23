from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from zunder_zapfe.backend.superadmin_identity import (
    SuperadminConfigurationError,
    configured_superadmin_credential_path,
    load_superadmin_identity,
    provision_superadmin_identity,
)
from zunder_zapfe.hardware.simulators import SimulatedNfcReader
from zunder_zapfe.superadmin_card import capture_superadmin_uid

SUPERADMIN_UID = "D00DCAFE"


def test_zz_aut_013_external_identity_matches_canonical_card_without_raw_uid(
    tmp_path: Path,
) -> None:
    credential_path = tmp_path / "superadmin.credential"

    provision_superadmin_identity(SUPERADMIN_UID, credential_path)
    identity = load_superadmin_identity(
        {"ZUNDER_ZAPFE_SUPERADMIN_CREDENTIAL_PATH": str(credential_path)}
    )

    assert identity is not None
    assert identity.matches("d0-0d:ca fe") is True
    assert identity.matches("DEADBEEF") is False
    assert SUPERADMIN_UID not in credential_path.read_text(encoding="utf-8")
    assert set(json.loads(credential_path.read_text(encoding="utf-8"))) == {
        "format",
        "uid_hash",
    }


def test_zz_aut_013_missing_external_identity_is_disabled_during_rollout(
    tmp_path: Path,
) -> None:
    identity = load_superadmin_identity(
        {"ZUNDER_ZAPFE_SUPERADMIN_CREDENTIAL_PATH": str(tmp_path / "missing.credential")}
    )

    assert identity is None


def test_zz_aut_013_existing_identity_cannot_be_replaced(tmp_path: Path) -> None:
    credential_path = tmp_path / "superadmin.credential"
    provision_superadmin_identity(SUPERADMIN_UID, credential_path)
    original = credential_path.read_bytes()

    with pytest.raises(SuperadminConfigurationError, match="cannot be replaced"):
        provision_superadmin_identity("DEADBEEF", credential_path)

    assert credential_path.read_bytes() == original


def test_zz_aut_013_malformed_credential_fails_closed(tmp_path: Path) -> None:
    credential_path = tmp_path / "superadmin.credential"
    credential_path.write_text('{"format": 1, "uid_hash": "plaintext"}', encoding="utf-8")
    if os.name != "nt":
        credential_path.chmod(0o600)

    with pytest.raises(SuperadminConfigurationError, match="invalid format"):
        load_superadmin_identity({"ZUNDER_ZAPFE_SUPERADMIN_CREDENTIAL_PATH": str(credential_path)})


def test_zz_aut_013_credential_path_is_configurable_without_storing_a_uid() -> None:
    configured = configured_superadmin_credential_path(
        {"ZUNDER_ZAPFE_SUPERADMIN_CREDENTIAL_PATH": "data/local-superadmin.credential"}
    )

    assert configured == Path("data/local-superadmin.credential")


def test_zz_aut_013_provisioning_reads_presented_card_from_hardware() -> None:
    reader = SimulatedNfcReader()
    reader.present_card(SUPERADMIN_UID)

    captured = capture_superadmin_uid(reader, timeout_seconds=1)

    assert captured == SUPERADMIN_UID
