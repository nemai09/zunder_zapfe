"""External, immutable NFC identity used for local maintenance access."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from pwdlib import PasswordHash

from zunder_zapfe.nfc_identity import canonicalize_nfc_uid

DEFAULT_SUPERADMIN_CREDENTIAL_PATH: Final = Path("/var/lib/zunder-zapfe/superadmin.credential")
SUPERADMIN_CREDENTIAL_PATH_VARIABLE: Final = "ZUNDER_ZAPFE_SUPERADMIN_CREDENTIAL_PATH"
_CREDENTIAL_FORMAT: Final = 1
_MAX_CREDENTIAL_BYTES: Final = 8192


class SuperadminConfigurationError(RuntimeError):
    """Raised when the external superadmin credential cannot be used safely."""


class SuperadminIdentity:
    """Verify presented cards without retaining or exposing their raw UID."""

    def __init__(self, uid_hash: str) -> None:
        if not uid_hash.startswith("$argon2"):
            raise SuperadminConfigurationError("Superadmin credential has an invalid format")
        self._uid_hash = uid_hash
        self._password_hash = PasswordHash.recommended()

    def matches(self, uid: str) -> bool:
        canonical_uid = canonicalize_nfc_uid(uid)
        try:
            return self._password_hash.verify(canonical_uid, self._uid_hash)
        except Exception as error:
            raise SuperadminConfigurationError(
                "Superadmin credential cannot be verified"
            ) from error

    @classmethod
    def from_file(cls, credential_path: Path) -> SuperadminIdentity:
        _require_private_permissions(credential_path)
        try:
            raw = credential_path.read_bytes()
        except OSError as error:
            raise SuperadminConfigurationError("Superadmin credential cannot be read") from error
        if not raw or len(raw) > _MAX_CREDENTIAL_BYTES:
            raise SuperadminConfigurationError("Superadmin credential has an invalid size")
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SuperadminConfigurationError(
                "Superadmin credential has an invalid format"
            ) from error
        if (
            not isinstance(document, dict)
            or document.get("format") != _CREDENTIAL_FORMAT
            or not isinstance(document.get("uid_hash"), str)
        ):
            raise SuperadminConfigurationError("Superadmin credential has an invalid format")
        return cls(document["uid_hash"])


def configured_superadmin_credential_path(
    environment: Mapping[str, str] | None = None,
) -> Path:
    values = environment if environment is not None else os.environ
    raw_path = values.get(
        SUPERADMIN_CREDENTIAL_PATH_VARIABLE,
        str(DEFAULT_SUPERADMIN_CREDENTIAL_PATH),
    ).strip()
    if not raw_path:
        raise SuperadminConfigurationError("Superadmin credential path must not be empty")
    return Path(raw_path).expanduser()


def load_superadmin_identity(
    environment: Mapping[str, str] | None = None,
) -> SuperadminIdentity | None:
    """Load the optional rollout credential; a malformed existing file is fatal."""
    credential_path = configured_superadmin_credential_path(environment)
    if not credential_path.exists():
        return None
    return SuperadminIdentity.from_file(credential_path)


def provision_superadmin_identity(uid: str, credential_path: Path) -> None:
    """Create the external credential once and refuse in-application replacement."""
    canonical_uid = canonicalize_nfc_uid(uid)
    if not credential_path.parent.is_dir():
        raise SuperadminConfigurationError("Superadmin credential directory does not exist")
    payload = json.dumps(
        {
            "format": _CREDENTIAL_FORMAT,
            "uid_hash": PasswordHash.recommended().hash(canonical_uid),
        },
        sort_keys=True,
    )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor: int | None = None
    try:
        descriptor = os.open(credential_path, flags, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            descriptor = None
            stream.write(payload)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        credential_path.chmod(0o600)
    except FileExistsError as error:
        raise SuperadminConfigurationError(
            "Superadmin credential already exists and cannot be replaced"
        ) from error
    except OSError as error:
        if descriptor is not None:
            os.close(descriptor)
        try:
            credential_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise SuperadminConfigurationError("Superadmin credential could not be created") from error


def _require_private_permissions(credential_path: Path) -> None:
    if os.name == "nt":
        return
    try:
        mode = credential_path.stat().st_mode
    except OSError as error:
        raise SuperadminConfigurationError(
            "Superadmin credential metadata cannot be read"
        ) from error
    if mode & 0o077:
        raise SuperadminConfigurationError(
            "Superadmin credential must not be readable by group or others"
        )
