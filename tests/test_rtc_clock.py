from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from zunder_zapfe.rtc_clock import (
    load_from_rtc,
    read_status,
    require_rtc_device,
    set_from_system_time,
)


class RecordingRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        recorded = list(command)
        self.commands.append(recorded)
        if recorded[0] == "date":
            output = "2026-08-08T14:30:00+02:00\n"
        elif "--show" in recorded:
            output = "2026-08-08 12:30:00.000000+00:00\n"
        else:
            output = ""
        return subprocess.CompletedProcess(recorded, 0, stdout=output, stderr="")


def test_zz_tim_001_loads_system_clock_from_utc_rtc(tmp_path: Path) -> None:
    device = tmp_path / "rtc0"
    device.touch()
    runner = RecordingRunner()

    load_from_rtc(device=device, runner=runner)

    assert runner.commands == [["hwclock", "--hctosys", "--utc", "--rtc", str(device)]]


def test_zz_tim_001_set_writes_system_time_without_changing_ntp(tmp_path: Path) -> None:
    device = tmp_path / "rtc0"
    marker = tmp_path / "state" / "rtc-initialized"
    device.touch()
    runner = RecordingRunner()

    set_from_system_time(
        device=device,
        initialized_marker=marker,
        runner=runner,
    )

    assert runner.commands == [["hwclock", "--systohc", "--utc", "--rtc", str(device)]]
    assert marker.read_text(encoding="utf-8") == "DS3231 initialized from system clock\n"


def test_zz_tim_001_status_exposes_system_and_rtc_time(tmp_path: Path) -> None:
    device = tmp_path / "rtc0"
    device.touch()
    runner = RecordingRunner()

    system_time, rtc_time = read_status(device=device, runner=runner)

    assert system_time == "2026-08-08T14:30:00+02:00"
    assert rtc_time == "2026-08-08 12:30:00.000000+00:00"


def test_rtc_operation_fails_clearly_when_device_is_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="RTC-Gerät"):
        require_rtc_device(tmp_path / "rtc0")
