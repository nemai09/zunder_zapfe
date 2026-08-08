"""Manage the Raspberry Pi system clock backed by a DS3231 RTC."""

from __future__ import annotations

import argparse
import os
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

DEFAULT_RTC_DEVICE = Path("/dev/rtc0")
DEFAULT_INITIALIZED_MARKER = Path("/var/lib/zunder-zapfe/rtc-initialized")

CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def run_command(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        check=True,
        capture_output=True,
        text=True,
    )


def require_rtc_device(device: Path) -> None:
    if not device.exists():
        raise FileNotFoundError(
            f"RTC-Gerät {device} fehlt. DS3231, I²C und Device-Tree-Overlay prüfen."
        )


def load_from_rtc(
    *,
    device: Path = DEFAULT_RTC_DEVICE,
    runner: CommandRunner = run_command,
) -> None:
    """Load the system clock from a DS3231 that stores UTC."""

    require_rtc_device(device)
    runner(["hwclock", "--hctosys", "--utc", "--rtc", str(device)])


def set_from_system_time(
    *,
    device: Path = DEFAULT_RTC_DEVICE,
    initialized_marker: Path = DEFAULT_INITIALIZED_MARKER,
    runner: CommandRunner = run_command,
) -> None:
    """Copy the current system clock to the RTC without changing system time or NTP."""

    require_rtc_device(device)
    runner(["hwclock", "--systohc", "--utc", "--rtc", str(device)])
    initialized_marker.parent.mkdir(parents=True, exist_ok=True)
    initialized_marker.write_text("DS3231 initialized from system clock\n", encoding="utf-8")
    initialized_marker.chmod(0o644)


def read_status(
    *,
    device: Path = DEFAULT_RTC_DEVICE,
    runner: CommandRunner = run_command,
) -> tuple[str, str]:
    require_rtc_device(device)
    system_time = runner(["date", "--iso-8601=seconds"]).stdout.strip()
    rtc_time = runner(["hwclock", "--show", "--utc", "--rtc", str(device)]).stdout.strip()
    return system_time, rtc_time


def require_root() -> None:
    get_effective_user_id = getattr(os, "geteuid", None)
    if get_effective_user_id is None or get_effective_user_id() != 0:
        raise PermissionError("Dieses Kommando muss mit sudo ausgeführt werden.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Systemzeit und DS3231-Echtzeituhr für Zunder Zapfe verwalten."
    )
    parser.add_argument(
        "--device",
        type=Path,
        default=DEFAULT_RTC_DEVICE,
        help="RTC-Gerät (Standard: /dev/rtc0)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("load", help="Systemzeit beim Start aus der RTC laden")
    subparsers.add_parser("status", help="System- und RTC-Zeit anzeigen")

    set_parser = subparsers.add_parser(
        "set",
        help="Aktuelle Systemzeit in die RTC schreiben; NTP bleibt unverändert",
    )
    set_parser.add_argument(
        "--yes",
        action="store_true",
        help="Bestätigung überspringen",
    )
    subparsers.add_parser(
        "set-from-system",
        help="Alias für nicht-interaktive Übernahme der Systemzeit in die RTC",
    )
    return parser


def run() -> None:
    arguments = build_parser().parse_args()
    try:
        require_root()
        if arguments.command == "load":
            load_from_rtc(device=arguments.device)
            system_time, rtc_time = read_status(device=arguments.device)
            print(f"Systemzeit aus {arguments.device} geladen: {system_time}")
            print(f"RTC (UTC): {rtc_time}")
            return

        if arguments.command == "status":
            system_time, rtc_time = read_status(device=arguments.device)
            print(f"Systemzeit: {system_time}")
            print(f"RTC (UTC):  {rtc_time}")
            return

        if arguments.command == "set-from-system":
            set_from_system_time(device=arguments.device)
            system_time, rtc_time = read_status(device=arguments.device)
            print(f"Systemzeit in {arguments.device} übernommen: {system_time}")
            print(f"RTC (UTC): {rtc_time}")
            print("NTP-Konfiguration wurde nicht verändert.")
            return

        system_time = run_command(["date", "--iso-8601=seconds"]).stdout.strip()
        print(f"Aktuelle Systemzeit: {system_time}")
        if not arguments.yes:
            confirmation = input("Aktuelle Systemzeit in die DS3231 schreiben? [j/N]: ")
            if confirmation.strip().lower() not in {"j", "ja"}:
                raise SystemExit("Abgebrochen; Zeit wurde nicht verändert.")
        set_from_system_time(device=arguments.device)
        system_time, rtc_time = read_status(device=arguments.device)
        print(f"Systemzeit unverändert: {system_time}")
        print(f"RTC (UTC):        {rtc_time}")
        print("NTP-Konfiguration wurde nicht verändert.")
    except (FileNotFoundError, PermissionError) as error:
        raise SystemExit(str(error)) from error
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or str(error)).strip()
        raise SystemExit(f"RTC-Kommando fehlgeschlagen: {detail}") from error


if __name__ == "__main__":
    run()
