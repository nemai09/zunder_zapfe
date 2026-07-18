"""Minimal web application used to verify the Raspberry Pi kiosk toolchain."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from zunder_zapfe import __version__

WEB_ROOT = Path(__file__).resolve().parent / "web"


def create_app() -> FastAPI:
    """Create the HTTP application without accessing Raspberry Pi hardware."""
    application = FastAPI(
        title="Zunder Zapfe",
        version=__version__,
        docs_url=None,
        redoc_url=None,
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
            "server_time": datetime.now(UTC).isoformat(),
        }

    return application


app = create_app()


def run() -> None:
    """Run the local-only web server used by the kiosk browser."""
    host = os.environ.get("ZUNDER_ZAPFE_HOST", "127.0.0.1")
    port = int(os.environ.get("ZUNDER_ZAPFE_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, access_log=True)


if __name__ == "__main__":
    run()
