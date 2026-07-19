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


def test_pi_verification_isolates_tests_from_production_database() -> None:
    verification = (PROJECT_ROOT / "scripts" / "pi-verify.sh").read_text(encoding="utf-8")

    pytest_position = verification.index('python" -m pytest')
    environment_position = verification.index("source /etc/zunder-zapfe/web.env")

    assert "env -u ZUNDER_ZAPFE_DATABASE_URL" in verification
    assert pytest_position < environment_position
