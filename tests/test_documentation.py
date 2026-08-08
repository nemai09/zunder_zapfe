from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"!?\[[^]]*]\(([^)]+)\)")
REQUIREMENT_ID = re.compile(r"\bZZ-[A-Z]+-\d{3}\b")


def documentation_files() -> list[Path]:
    roots = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "AGENTS.md",
        PROJECT_ROOT / "CONTRIBUTING.md",
        PROJECT_ROOT / "SECURITY.md",
        PROJECT_ROOT / "CODE_OF_CONDUCT.md",
    ]
    return roots + sorted((PROJECT_ROOT / "docs").rglob("*.md"))


def test_required_community_and_contract_files_exist() -> None:
    required = [
        "LICENSE",
        "README.md",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        ".github/pull_request_template.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/workflows/ci.yml",
        "docs/interfaces/openapi.json",
    ]

    missing = [relative for relative in required if not (PROJECT_ROOT / relative).is_file()]

    assert not missing, f"Missing project files: {missing}"


def test_gpl_license_is_consistent_across_project_metadata() -> None:
    license_text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "GNU GENERAL PUBLIC LICENSE" in license_text
    assert "Version 3, 29 June 2007" in license_text
    assert project["project"]["license"] == "GPL-3.0-or-later"
    assert "GPL-3.0-or-later" in readme


def test_internal_markdown_links_resolve() -> None:
    broken: list[str] = []
    for document in documentation_files():
        content = document.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(content):
            target = raw_target.strip().strip("<>").split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            linked_path = (document.parent / unquote(target)).resolve()
            if not linked_path.exists():
                broken.append(f"{document.relative_to(PROJECT_ROOT)} -> {target}")

    assert not broken, "Broken documentation links:\n" + "\n".join(broken)


def test_documented_requirement_ids_exist() -> None:
    catalog = (PROJECT_ROOT / "requirements" / "anforderungskatalog.txt").read_text(
        encoding="utf-8"
    )
    known = set(REQUIREMENT_ID.findall(catalog))
    unknown: list[str] = []
    for document in documentation_files():
        referenced = set(REQUIREMENT_ID.findall(document.read_text(encoding="utf-8")))
        for requirement_id in sorted(referenced - known):
            unknown.append(f"{document.relative_to(PROJECT_ROOT)}: {requirement_id}")

    assert not unknown, "Unknown requirement IDs:\n" + "\n".join(unknown)


def test_openapi_snapshot_matches_application() -> None:
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "export_openapi.py"), "--check"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_pi_installer_runs_repository_pip_as_service_user() -> None:
    installer = (PROJECT_ROOT / "scripts" / "install-pi.sh").read_text(encoding="utf-8")
    run_as_user = 'runuser -u "${kiosk_user}" --'

    assert installer.count(run_as_user) >= 3
    assert '  "${app_dir}/.venv/bin/python" -m pip install' in installer
    assert '\n"${app_dir}/.venv/bin/python" -m pip install' not in installer


def test_web_service_uses_writable_runtime_directory_for_gpio_notifications() -> None:
    service = (PROJECT_ROOT / "deploy" / "systemd" / "zunder-zapfe-web.service.in").read_text(
        encoding="utf-8"
    )

    assert "RuntimeDirectory=zunder-zapfe" in service
    assert "RuntimeDirectoryMode=0750" in service
    assert "WorkingDirectory=/run/zunder-zapfe" in service
    assert "WorkingDirectory=@@APP_DIR@@" not in service


def test_pi_verification_isolates_tests_from_production_database() -> None:
    verification = (PROJECT_ROOT / "scripts" / "pi-verify.sh").read_text(encoding="utf-8")

    pytest_position = verification.index('python" -m pytest')
    environment_position = verification.index("source /etc/zunder-zapfe/web.env")

    assert "env -u ZUNDER_ZAPFE_DATABASE_URL" in verification
    assert pytest_position < environment_position


def test_rtc_service_runs_before_web_and_is_verified_on_target() -> None:
    rtc_service = (PROJECT_ROOT / "deploy" / "systemd" / "zunder-zapfe-rtc.service.in").read_text(
        encoding="utf-8"
    )
    web_service = (PROJECT_ROOT / "deploy" / "systemd" / "zunder-zapfe-web.service.in").read_text(
        encoding="utf-8"
    )
    installer = (PROJECT_ROOT / "scripts" / "install-pi.sh").read_text(encoding="utf-8")
    verification = (PROJECT_ROOT / "scripts" / "pi-verify.sh").read_text(encoding="utf-8")

    assert "ExecStart=@@APP_DIR@@/.venv/bin/zunder-zapfe-rtc load" in rtc_service
    assert "Before=zunder-zapfe-web.service" in rtc_service
    assert "ConditionPathExists=/var/lib/zunder-zapfe/rtc-initialized" in rtc_service
    assert "CapabilityBoundingSet=CAP_SYS_TIME CAP_DAC_READ_SEARCH" in rtc_service
    assert "DeviceAllow=/dev/rtc0 rw" in rtc_service
    assert "Wants=zunder-zapfe-rtc.service" in web_service
    assert "After=local-fs.target zunder-zapfe-rtc.service" in web_service
    assert "dtoverlay=i2c-rtc,ds3231" in installer
    assert "util-linux-extra" in installer
    assert "systemctl enable zunder-zapfe-rtc.service" in installer
    assert "/usr/local/sbin/zunder-zapfe-rtc" in installer
    assert "systemctl is-active --quiet zunder-zapfe-rtc.service" in verification
    assert "rtc-ds1307" in verification
    assert "0068" in verification


def test_kiosk_does_not_open_the_desktop_keyring_during_autologin() -> None:
    launcher = (PROJECT_ROOT / "deploy" / "kiosk" / "zunder-zapfe-kiosk").read_text(
        encoding="utf-8"
    )

    assert "--password-store=basic" in launcher
    assert "while true; do" in launcher
    assert "sleep 2" in launcher


def test_backup_timer_is_installed_and_verified_without_blocking_the_web_service() -> None:
    timer = (PROJECT_ROOT / "deploy" / "systemd" / "zunder-zapfe-backup.timer").read_text(
        encoding="utf-8"
    )
    service = (PROJECT_ROOT / "deploy" / "systemd" / "zunder-zapfe-backup.service.in").read_text(
        encoding="utf-8"
    )
    installer = (PROJECT_ROOT / "scripts" / "install-pi.sh").read_text(encoding="utf-8")
    verification = (PROJECT_ROOT / "scripts" / "pi-verify.sh").read_text(encoding="utf-8")

    assert "OnUnitActiveSec=30min" in timer
    assert "Persistent=true" in timer
    assert "ExecStart=@@APP_DIR@@/.venv/bin/zunder-zapfe-backup" in service
    assert "ReadWritePaths=/var/lib/zunder-zapfe" in service
    assert "ProtectHome=read-only" in service
    assert "ProtectHome=true" not in service
    assert "systemctl enable --now zunder-zapfe-backup.timer" in installer
    assert "if ! systemctl start zunder-zapfe-backup.service" in installer
    assert "systemctl is-active --quiet zunder-zapfe-backup.timer" in verification
