"""Manage the Raspberry Pi system clock backed by a DS3231 RTC."""

from __future__ import annotations

import argparse
import os
import subprocess
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

DEFAULT_RTC_DEVICE = Path("/dev/rtc0")
LOCAL_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

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


def parse_local_time(value: str) -> str:
    try:
        parsed = datetime.strptime(value.strip(), LOCAL_TIME_FORMAT)
    except ValueError as error:
        raise ValueError("Zeit muss das Format JJJJ-MM-TT HH:MM:SS haben.") from error
    return parsed.strftime(LOCAL_TIME_FORMAT)


def set_manual_time(
    local_time: str,
    *,
    device: Path = DEFAULT_RTC_DEVICE,
    runner: CommandRunner = run_command,
) -> str:
    """Set local system time, disable NTP and copy the result to the RTC as UTC."""

    require_rtc_device(device)
    normalized = parse_local_time(local_time)
    runner(["timedatectl", "set-ntp", "false"])
    runner(["date", "--set", normalized])
    runner(["hwclock", "--systohc", "--utc", "--rtc", str(device)])
    return normalized


def set_from_system_time(
    *,
    device: Path = DEFAULT_RTC_DEVICE,
    runner: CommandRunner = run_command,
) -> None:
    """Copy the current system clock to the RTC without changing NTP settings."""

    require_rtc_device(device)
    runner(["hwclock", "--systohc", "--utc", "--rtc", str(device)])


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
        help="Lokale Systemzeit interaktiv stellen und in die RTC schreiben",
    )
    set_parser.add_argument(
        "local_time",
        nargs="?",
        help='Lokale Zeit im Format "JJJJ-MM-TT HH:MM:SS"',
    )
    set_parser.add_argument(
        "--yes",
        action="store_true",
        help="Bestätigung überspringen",
    )
    subparsers.add_parser(
        "set-from-system",
        help="Bereits korrekte Systemzeit in die RTC übernehmen",
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
            return

        requested_time = arguments.local_time
        if requested_time is None:
            requested_time = input("Lokale Zeit (JJJJ-MM-TT HH:MM:SS): ").strip()
        normalized_time = parse_local_time(requested_time)
        if not arguments.yes:
            confirmation = input(
                f"Systemzeit auf {normalized_time} stellen und NTP deaktivieren? [j/N]: "
            )
            if confirmation.strip().lower() not in {"j", "ja"}:
                raise SystemExit("Abgebrochen; Zeit wurde nicht verändert.")
        set_manual_time(normalized_time, device=arguments.device)
        system_time, rtc_time = read_status(device=arguments.device)
        print(f"Systemzeit gesetzt: {system_time}")
        print(f"RTC (UTC):        {rtc_time}")
    except (FileNotFoundError, PermissionError, ValueError) as error:
        raise SystemExit(str(error)) from error
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or str(error)).strip()
        raise SystemExit(f"RTC-Kommando fehlgeschlagen: {detail}") from error


if __name__ == "__main__":
    run()
