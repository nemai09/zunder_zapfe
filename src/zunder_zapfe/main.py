"""Minimal web application used to verify the Raspberry Pi kiosk toolchain."""

from __future__ import annotations

import os
import subprocess
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from zunder_zapfe import __version__
from zunder_zapfe.backend.tap_controller import TapController, development_limits
from zunder_zapfe.hardware import HardwareLayer, create_default_hardware
from zunder_zapfe.hardware.models import status_dict

WEB_ROOT = Path(__file__).resolve().parent / "web"


def current_revision() -> str:
    """Return the deployed Git revision when running from a checkout."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=WEB_ROOT.parents[2],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


REVISION = current_revision()


def create_app(hardware: HardwareLayer | None = None) -> FastAPI:
    """Create the HTTP application with replaceable hardware dependencies."""
    hardware_layer = hardware or create_default_hardware()
    tap_controller = TapController(hardware_layer, development_limits())

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        hardware_layer.start()
        tap_controller.start()
        try:
            yield
        finally:
            tap_controller.shutdown()
            hardware_layer.stop()

    application = FastAPI(
        title="Zunder Zapfe",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")

    @application.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(WEB_ROOT / "index.html")

    @application.get("/api/health")
    async def health() -> dict[str, str]:
        return {
            "application": "zunder-zapfe",
            "status": "ready",
            "version": __version__,
            "revision": REVISION,
            "server_time": datetime.now(UTC).isoformat(),
        }

    @application.get("/api/nfc/status")
    async def nfc_status() -> dict[str, object]:
        return status_dict(hardware_layer.nfc.snapshot())

    @application.get("/api/hardware/status")
    async def hardware_status() -> dict[str, dict[str, object]]:
        return hardware_layer.snapshot()

    @application.get("/api/tap/status")
    async def tap_status() -> dict[str, object]:
        return tap_controller.snapshot_dict()

    return application


app = create_app()


def run() -> None:
    """Run the local-only web server used by the kiosk browser."""
    host = os.environ.get("ZUNDER_ZAPFE_HOST", "127.0.0.1")
    port = int(os.environ.get("ZUNDER_ZAPFE_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, access_log=True)


if __name__ == "__main__":
    run()
