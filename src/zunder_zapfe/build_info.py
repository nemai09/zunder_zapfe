"""Human-readable build identification for deployed checkouts."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from zunder_zapfe import __version__


@dataclass(frozen=True)
class BuildInfo:
    revision: str
    commit_number: int | None
    display_version: str


def current_build_info(repository_root: Path) -> BuildInfo:
    revision = _git_value(repository_root, "rev-parse", "--short", "HEAD")
    raw_commit_number = _git_value(repository_root, "rev-list", "--count", "HEAD")
    try:
        commit_number = int(raw_commit_number)
    except (TypeError, ValueError):
        commit_number = None

    release = __version__.replace("-", "_")
    count = str(commit_number) if commit_number is not None else "unknown"
    git_revision = revision or "unknown"
    return BuildInfo(
        revision=git_revision,
        commit_number=commit_number,
        display_version=f"zzapfe_v{release}_{count}_g{git_revision}",
    )


def _git_value(repository_root: Path, *arguments: str) -> str | None:
    try:
        value = subprocess.run(
            ["git", *arguments],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return value or None
