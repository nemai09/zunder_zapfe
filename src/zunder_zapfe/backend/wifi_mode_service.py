"""Read and switch the Raspberry Pi NetworkManager operating mode."""

from __future__ import annotations

import subprocess
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

WIFI_HELPER_PATH = Path("/usr/local/sbin/zunder-zapfe-wifi-mode")
WIFI_MODES = frozenset({"ap", "client", "disconnected", "unavailable", "unknown"})


class WifiModeError(RuntimeError):
    """Raised when the installed NetworkManager helper cannot switch modes."""


@dataclass(frozen=True)
class WifiStatus:
    mode: str
    active_connection: str | None
    ssid: str | None
    ip_address: str | None
    client_profile_available: bool
    detail: str | None = None

    def as_dict(self) -> dict[str, str | bool | None]:
        return asdict(self)


CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


class WifiModeService:
    """Use a narrowly scoped installed helper without handling Wi-Fi secrets."""

    def __init__(
        self,
        helper_path: Path = WIFI_HELPER_PATH,
        *,
        command_runner: CommandRunner | None = None,
        cache_seconds: float = 2.0,
    ) -> None:
        self._helper_path = helper_path
        self._command_runner = command_runner or self._run_command
        self._cache_seconds = cache_seconds
        self._cached_status: WifiStatus | None = None
        self._cached_at = 0.0
        self._command_mutex = threading.Lock()

    def status(self, *, force: bool = False) -> WifiStatus:
        now = time.monotonic()
        if (
            not force
            and self._cached_status is not None
            and now - self._cached_at < self._cache_seconds
        ):
            return self._cached_status
        try:
            result = self._run_helper("status")
            if result.returncode != 0:
                status = self._unavailable(_command_error(result))
            else:
                status = _parse_status(result.stdout)
        except FileNotFoundError:
            status = self._unavailable("WLAN-Modussteuerung ist nicht installiert")
        except subprocess.TimeoutExpired:
            status = self._unavailable("WLAN-Statusabfrage hat das Zeitlimit überschritten")
        except WifiModeError as error:
            status = self._unavailable(str(error))
        except OSError as error:
            status = self._unavailable(f"WLAN-Statusabfrage fehlgeschlagen: {error}")
        self._cached_status = status
        self._cached_at = now
        return status

    def switch(self, mode: str) -> WifiStatus:
        if mode not in {"ap", "client"}:
            raise ValueError("Wi-Fi mode must be 'ap' or 'client'")
        try:
            result = self._run_helper(mode)
        except FileNotFoundError as error:
            raise WifiModeError("WLAN-Modussteuerung ist nicht installiert") from error
        except subprocess.TimeoutExpired as error:
            raise WifiModeError("WLAN-Moduswechsel hat das Zeitlimit überschritten") from error
        except OSError as error:
            raise WifiModeError(f"WLAN-Moduswechsel fehlgeschlagen: {error}") from error
        if result.returncode != 0:
            raise WifiModeError(_command_error(result))
        status = _parse_status(result.stdout)
        if status.mode != mode:
            raise WifiModeError("NetworkManager meldet nach dem Wechsel einen anderen Modus")
        self._cached_status = status
        self._cached_at = time.monotonic()
        return status

    @staticmethod
    def _unavailable(detail: str) -> WifiStatus:
        return WifiStatus(
            mode="unavailable",
            active_connection=None,
            ssid=None,
            ip_address=None,
            client_profile_available=False,
            detail=detail,
        )

    def _run_helper(self, action: str) -> subprocess.CompletedProcess[str]:
        with self._command_mutex:
            return self._command_runner([str(self._helper_path), action])

    @staticmethod
    def _run_command(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=4 if command[-1] == "status" else 25,
        )


def _parse_status(output: str) -> WifiStatus:
    values: dict[str, str] = {}
    for line in output.splitlines():
        key, separator, value = line.partition("=")
        if separator and key in {
            "mode",
            "active_connection",
            "ssid",
            "ip_address",
            "client_profile_available",
            "detail",
        }:
            values[key] = value
    mode = values.get("mode", "unknown")
    if mode not in WIFI_MODES:
        raise WifiModeError("WLAN-Hilfsprogramm lieferte einen ungültigen Modus")
    return WifiStatus(
        mode=mode,
        active_connection=values.get("active_connection") or None,
        ssid=values.get("ssid") or None,
        ip_address=values.get("ip_address") or None,
        client_profile_available=values.get("client_profile_available") == "true",
        detail=values.get("detail") or None,
    )


def _command_error(result: subprocess.CompletedProcess[str]) -> str:
    detail = result.stderr.strip()
    return detail or "NetworkManager konnte den WLAN-Modus nicht umschalten"
