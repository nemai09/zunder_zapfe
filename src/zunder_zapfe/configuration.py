"""Runtime configuration used by the local kiosk client."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_STANDARD_PORTIONS_ML = (300, 500)
DEFAULT_SESSION_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class KioskSettings:
    standard_portions_ml: tuple[int, ...] = DEFAULT_STANDARD_PORTIONS_ML
    session_timeout_seconds: int = DEFAULT_SESSION_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if len(self.standard_portions_ml) < 2:
            raise ValueError("At least two standard portions are required")
        if any(volume <= 0 for volume in self.standard_portions_ml):
            raise ValueError("Standard portions must be greater than zero")
        if len(set(self.standard_portions_ml)) != len(self.standard_portions_ml):
            raise ValueError("Standard portions must be unique")
        if self.session_timeout_seconds <= 0:
            raise ValueError("Session timeout must be greater than zero")


def load_kiosk_settings(environment: Mapping[str, str] | None = None) -> KioskSettings:
    values = environment if environment is not None else os.environ
    raw_portions = values.get(
        "ZUNDER_ZAPFE_STANDARD_PORTIONS_ML",
        ",".join(str(volume) for volume in DEFAULT_STANDARD_PORTIONS_ML),
    )
    try:
        portions = tuple(int(value.strip()) for value in raw_portions.split(",") if value.strip())
        timeout = int(
            values.get(
                "ZUNDER_ZAPFE_SESSION_TIMEOUT_SECONDS",
                str(DEFAULT_SESSION_TIMEOUT_SECONDS),
            )
        )
    except ValueError as error:
        raise ValueError("Kiosk configuration must contain integer values") from error
    return KioskSettings(
        standard_portions_ml=portions,
        session_timeout_seconds=timeout,
    )
