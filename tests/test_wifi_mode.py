from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from zunder_zapfe.backend import wifi_mode_service
from zunder_zapfe.backend.wifi_mode_service import WifiModeError, WifiModeService


class RecordingRunner:
    def __init__(self, results: list[subprocess.CompletedProcess[str]]) -> None:
        self.results = results
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        return self.results.pop(0)


def result(
    stdout: str = "",
    *,
    returncode: int = 0,
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_wifi_status_is_parsed_and_cached_without_credentials() -> None:
    runner = RecordingRunner(
        [
            result(
                "mode=ap\n"
                "active_connection=zunder-zapfe-ap\n"
                "ssid=ZUNDER_ZAPFE\n"
                "ip_address=10.42.0.1\n"
                "client_profile_available=true\n"
            )
        ]
    )
    service = WifiModeService(
        Path("/test/wifi-mode"),
        command_runner=runner,
        cache_seconds=10,
    )

    first = service.status()
    second = service.status()

    assert first == second
    assert first.mode == "ap"
    assert first.ssid == "ZUNDER_ZAPFE"
    assert first.client_profile_available is True
    assert runner.commands == [[str(Path("/test/wifi-mode")), "status"]]


def test_wifi_status_uses_thirty_second_default_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner(
        [
            result("mode=ap\nclient_profile_available=true\n"),
            result("mode=client\nclient_profile_available=true\n"),
        ]
    )
    moments = iter([100.0, 129.9, 130.0])
    monkeypatch.setattr(wifi_mode_service.time, "monotonic", lambda: next(moments))
    service = WifiModeService(Path("/test/wifi-mode"), command_runner=runner)

    assert service.status().mode == "ap"
    assert service.status().mode == "ap"
    assert service.status().mode == "client"
    assert runner.commands == [
        [str(Path("/test/wifi-mode")), "status"],
        [str(Path("/test/wifi-mode")), "status"],
    ]


def test_wifi_switch_only_accepts_explicit_modes_and_reports_helper_errors() -> None:
    runner = RecordingRunner(
        [
            result(
                "mode=client\n"
                "active_connection=Werkstatt\n"
                "ssid=Werkstatt\n"
                "ip_address=192.0.2.20\n"
                "client_profile_available=true\n"
            ),
            result(returncode=1, stderr="Das bekannte WLAN war nicht erreichbar."),
        ]
    )
    service = WifiModeService(Path("/test/wifi-mode"), command_runner=runner)

    assert service.switch("client").mode == "client"
    with pytest.raises(WifiModeError, match="nicht erreichbar"):
        service.switch("ap")
    with pytest.raises(ValueError, match="ap.*client"):
        service.switch("automatic")
    assert runner.commands == [
        [str(Path("/test/wifi-mode")), "client"],
        [str(Path("/test/wifi-mode")), "ap"],
    ]


def test_missing_wifi_helper_yields_an_unavailable_read_only_status() -> None:
    def missing(_command: list[str]) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError

    status = WifiModeService(Path("/missing"), command_runner=missing).status()

    assert status.mode == "unavailable"
    assert status.client_profile_available is False
    assert "nicht installiert" in (status.detail or "")
