"""Hardware-neutral status objects shared by adapters and the backend."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class NfcStatus:
    state: str
    reader: str | None = None
    uid: str | None = None
    detail: str | None = None
    simulated: bool = False


@dataclass(frozen=True)
class ValveStatus:
    is_open: bool
    available: bool = True
    simulated: bool = False
    detail: str | None = None


@dataclass(frozen=True)
class FlowReading:
    pulse_count: int
    measuring: bool
    last_pulse_at: float | None = None
    available: bool = True
    simulated: bool = False
    detail: str | None = None


@dataclass(frozen=True)
class EmergencyStopStatus:
    active: bool
    available: bool = True
    simulated: bool = False
    detail: str | None = None


def status_dict(status: object) -> dict[str, Any]:
    """Convert a hardware status dataclass into an API-friendly dictionary."""
    return asdict(status)
