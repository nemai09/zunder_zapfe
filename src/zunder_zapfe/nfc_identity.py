"""Hardware- and persistence-neutral NFC UID normalization."""

from __future__ import annotations

import re


def canonicalize_nfc_uid(uid: str) -> str:
    """Return the stable uppercase hexadecimal representation of an NFC UID."""
    canonical = re.sub(r"[\s:-]", "", uid).upper()
    if len(canonical) < 4 or len(canonical) % 2 or not re.fullmatch(r"[0-9A-F]+", canonical):
        raise ValueError("NFC UID must contain an even number of hexadecimal digits")
    return canonical
