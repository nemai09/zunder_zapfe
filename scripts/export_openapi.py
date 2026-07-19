"""Export or verify the committed OpenAPI contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
OPENAPI_PATH = PROJECT_ROOT / "docs" / "interfaces" / "openapi.json"
sys.path.insert(0, str(SOURCE_ROOT))

from zunder_zapfe.main import create_app  # noqa: E402


def rendered_openapi() -> str:
    """Return the deterministic production API contract."""
    application = create_app(enable_simulator_api=False, run_background=False)
    return json.dumps(application.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail instead of writing when the committed contract is stale",
    )
    arguments = parser.parse_args()
    rendered = rendered_openapi()

    if arguments.check:
        current = OPENAPI_PATH.read_text(encoding="utf-8") if OPENAPI_PATH.exists() else ""
        if current != rendered:
            print(
                "OpenAPI snapshot is stale; run: python scripts/export_openapi.py",
                file=sys.stderr,
            )
            raise SystemExit(1)
        print(f"OpenAPI snapshot is current: {OPENAPI_PATH.relative_to(PROJECT_ROOT)}")
        return

    OPENAPI_PATH.parent.mkdir(parents=True, exist_ok=True)
    OPENAPI_PATH.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"Wrote {OPENAPI_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    run()
