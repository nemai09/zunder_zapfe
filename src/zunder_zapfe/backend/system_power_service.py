"""Narrow Raspberry Pi power-control integration for the local admin UI."""

from __future__ import annotations

import os
import socket
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

SYSTEM_POWER_HELPER_PATH = Path("/usr/local/sbin/zunder-zapfe-system-power")
SYSTEM_POWER_ACTIONS = frozenset({"reboot", "poweroff"})


class SystemPowerError(RuntimeError):
    """Raised when the installed power-control helper cannot perform an action."""


@dataclass(frozen=True)
class SystemStatus:
    hostname: str
    uptime_seconds: int
    power_control_available: bool
    detail: str | None = None

    def as_dict(self) -> dict[str, str | int | bool | None]:
        return asdict(self)


CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


class SystemPowerService:
    """Expose only status, reboot and poweroff through an installed helper."""

    def __init__(
        self,
        helper_path: Path = SYSTEM_POWER_HELPER_PATH,
        *,
        command_runner: CommandRunner | None = None,
    ) -> None:
        self._helper_path = helper_path
        self._command_runner = command_runner or self._run_command

    def status(self) -> SystemStatus:
        available = self._helper_path.is_file() and os.access(self._helper_path, os.X_OK)
        return SystemStatus(
            hostname=socket.gethostname(),
            uptime_seconds=max(0, int(time.monotonic())),
            power_control_available=available,
            detail=None if available else "Systemsteuerung ist nicht installiert",
        )

    def request(self, action: str) -> None:
        if action not in SYSTEM_POWER_ACTIONS:
            raise ValueError("System action must be 'reboot' or 'poweroff'")
        try:
            result = self._command_runner([str(self._helper_path), action])
        except FileNotFoundError as error:
            raise SystemPowerError("Systemsteuerung ist nicht installiert") from error
        except subprocess.TimeoutExpired as error:
            raise SystemPowerError("Systemaktion hat das Zeitlimit überschritten") from error
        except OSError as error:
            raise SystemPowerError(
                f"Systemaktion konnte nicht gestartet werden: {error}"
            ) from error
        if result.returncode != 0:
            detail = result.stderr.strip()
            raise SystemPowerError(detail or "Systemaktion wurde abgelehnt")

    @staticmethod
    def _run_command(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
