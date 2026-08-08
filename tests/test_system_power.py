from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from zunder_zapfe.backend.system_power_service import SystemPowerError, SystemPowerService

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RecordingRunner:
    def __init__(self, *, returncode: int = 0, stderr: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        self.commands.append(list(command))
        return subprocess.CompletedProcess(command, self.returncode, stdout="", stderr=self.stderr)


def test_zz_ui_010_system_power_service_allows_only_fixed_actions(tmp_path: Path) -> None:
    helper = tmp_path / "zunder-zapfe-system-power"
    helper.touch()
    helper.chmod(0o755)
    runner = RecordingRunner()
    service = SystemPowerService(helper, command_runner=runner)

    status = service.status()
    assert status.power_control_available is True
    assert status.hostname
    assert status.uptime_seconds >= 0

    service.request("reboot")
    service.request("poweroff")
    with pytest.raises(ValueError, match="reboot.*poweroff"):
        service.request("arbitrary-command")

    assert runner.commands == [
        [str(helper), "reboot"],
        [str(helper), "poweroff"],
    ]


def test_zz_ui_010_system_power_service_reports_helper_failures(tmp_path: Path) -> None:
    missing = SystemPowerService(tmp_path / "missing")
    assert missing.status().power_control_available is False
    with pytest.raises(SystemPowerError, match="nicht installiert"):
        missing.request("reboot")

    helper = tmp_path / "zunder-zapfe-system-power"
    helper.touch()
    helper.chmod(0o755)
    failing = SystemPowerService(
        helper,
        command_runner=RecordingRunner(returncode=1, stderr="Nicht autorisiert"),
    )
    with pytest.raises(SystemPowerError, match="Nicht autorisiert"):
        failing.request("poweroff")


def test_zz_ui_010_pi_installer_grants_only_login1_power_actions() -> None:
    installer = (PROJECT_ROOT / "scripts" / "install-pi.sh").read_text(encoding="utf-8")
    helper = (PROJECT_ROOT / "scripts" / "system-power.sh").read_text(encoding="utf-8")
    policy = (PROJECT_ROOT / "deploy" / "polkit" / "zunder-zapfe-power.rules.in").read_text(
        encoding="utf-8"
    )

    assert "/usr/local/sbin/zunder-zapfe-system-power" in installer
    assert "61-zunder-zapfe-power.rules" in installer
    assert "reboot|poweroff)" in helper
    assert 'systemctl --no-block "${action}"' in helper
    assert "org.freedesktop.login1.reboot" in policy
    assert "org.freedesktop.login1.power-off" in policy
    assert "org.freedesktop.systemd1.manage-units" not in policy
    verification = (PROJECT_ROOT / "scripts" / "pi-verify.sh").read_text(encoding="utf-8")
    assert "zunder-zapfe-system-power" in verification
    assert "61-zunder-zapfe-power.rules" in verification
