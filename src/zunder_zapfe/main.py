"""Minimal web application used to verify the Raspberry Pi kiosk toolchain."""

from __future__ import annotations

import os
import subprocess
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from zunder_zapfe import __version__
from zunder_zapfe.backend.tap_controller import InvalidTransition, development_limits
from zunder_zapfe.backend.tap_service import FlowCalibration, TapService, TapUnavailable
from zunder_zapfe.hardware import HardwareLayer, create_default_hardware
from zunder_zapfe.hardware.models import status_dict
from zunder_zapfe.hardware.simulators import SimulatedFlowMeter, SimulatedNfcReader
from zunder_zapfe.persistence import create_database_engine, create_session_factory

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


class PortionRequest(BaseModel):
    target_volume_ml: int = Field(gt=0)


class SimulatedCardRequest(BaseModel):
    uid: str = Field(min_length=4, max_length=80)


class SimulatedPulsesRequest(BaseModel):
    count: int = Field(gt=0)


def create_app(
    hardware: HardwareLayer | None = None,
    sessions: sessionmaker[Session] | None = None,
    *,
    enable_simulator_api: bool | None = None,
    run_background: bool = True,
) -> FastAPI:
    """Create the HTTP application with replaceable hardware dependencies."""
    hardware_layer = hardware or create_default_hardware(
        simulate_nfc=os.environ.get("ZUNDER_ZAPFE_SIMULATE_NFC") == "1"
    )
    owned_engine = None
    if sessions is None:
        owned_engine = create_database_engine()
        sessions = create_session_factory(owned_engine)
    simulator_api_enabled = (
        os.environ.get("ZUNDER_ZAPFE_ENABLE_SIMULATOR_API") == "1"
        if enable_simulator_api is None
        else enable_simulator_api
    )
    tap_service = TapService(
        hardware_layer,
        sessions,
        development_limits(),
        calibration=FlowCalibration(
            pulses_per_liter=int(os.environ.get("ZUNDER_ZAPFE_PULSES_PER_LITER", "500"))
        ),
        run_background=run_background,
    )

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        hardware_layer.start()
        try:
            tap_service.start()
            yield
        finally:
            tap_service.shutdown()
            hardware_layer.stop()
            if owned_engine is not None:
                owned_engine.dispose()

    application = FastAPI(
        title="Zunder Zapfe",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")

    @application.exception_handler(TapUnavailable)
    @application.exception_handler(InvalidTransition)
    async def domain_conflict(_request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(error)})

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
        return tap_service.status_dict()

    @application.get("/api/session/status")
    async def session_status() -> dict[str, object]:
        status = tap_service.status_dict()
        return {
            "user_id": status["user_id"],
            "user_display_name": status["user_display_name"],
            "is_admin": status["is_admin"],
            "special_portion_ml": status["special_portion_ml"],
        }

    @application.post("/api/session/logout", status_code=204)
    async def logout() -> Response:
        tap_service.logout()
        return Response(status_code=204)

    @application.post("/api/tap/portion")
    async def start_portion(request: PortionRequest) -> dict[str, Any]:
        return tap_service.start_portion(request.target_volume_ml)

    @application.post("/api/tap/portion/abort")
    async def abort_portion() -> dict[str, Any]:
        return asdict(tap_service.abort_portion())

    @application.post("/api/tap/top-up/start")
    async def start_top_up() -> dict[str, Any]:
        return tap_service.start_top_up()

    @application.post("/api/tap/top-up/stop")
    async def stop_top_up() -> dict[str, Any]:
        return asdict(tap_service.stop_top_up())

    @application.post("/api/tap/maintenance/enter", status_code=204)
    async def enter_maintenance() -> Response:
        tap_service.enter_maintenance()
        return Response(status_code=204)

    @application.post("/api/tap/maintenance/start")
    async def start_maintenance_pour() -> dict[str, Any]:
        return tap_service.start_maintenance_pour()

    @application.post("/api/tap/maintenance/stop")
    async def stop_maintenance_pour() -> dict[str, Any]:
        return asdict(tap_service.stop_maintenance_pour())

    @application.post("/api/tap/maintenance/exit", status_code=204)
    async def exit_maintenance() -> Response:
        tap_service.exit_maintenance()
        return Response(status_code=204)

    @application.post("/api/tap/heartbeat", status_code=204)
    async def heartbeat() -> Response:
        tap_service.heartbeat()
        return Response(status_code=204)

    @application.post("/api/tap/poll")
    async def poll_tap() -> dict[str, Any]:
        return tap_service.poll()

    @application.get("/api/consumption/current")
    async def current_consumption() -> dict[str, int]:
        return tap_service.current_consumption()

    @application.get("/api/keg/current")
    async def current_keg() -> dict[str, Any]:
        return tap_service.current_keg()

    if simulator_api_enabled:

        @application.post("/api/simulator/nfc/present")
        async def simulate_card(request: SimulatedCardRequest) -> dict[str, object]:
            if not isinstance(hardware_layer.nfc, SimulatedNfcReader):
                return JSONResponse(
                    status_code=409, content={"detail": "NFC reader is not simulated"}
                )
            hardware_layer.nfc.present_card(request.uid)
            tap_service.process_nfc_snapshot()
            return await session_status()

        @application.post("/api/simulator/nfc/remove", status_code=204)
        async def remove_simulated_card() -> Response:
            if not isinstance(hardware_layer.nfc, SimulatedNfcReader):
                return JSONResponse(
                    status_code=409, content={"detail": "NFC reader is not simulated"}
                )
            hardware_layer.nfc.remove_card()
            tap_service.process_nfc_snapshot()
            return Response(status_code=204)

        @application.post("/api/simulator/flow/pulses")
        async def simulate_flow(request: SimulatedPulsesRequest) -> dict[str, Any]:
            if not isinstance(hardware_layer.flow_meter, SimulatedFlowMeter):
                return JSONResponse(
                    status_code=409, content={"detail": "Flow meter is not simulated"}
                )
            hardware_layer.flow_meter.add_pulses(request.count)
            tap_service.heartbeat()
            return tap_service.poll()

    return application


app = create_app()


def run() -> None:
    """Run the local-only web server used by the kiosk browser."""
    host = os.environ.get("ZUNDER_ZAPFE_HOST", "127.0.0.1")
    port = int(os.environ.get("ZUNDER_ZAPFE_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, access_log=True)


if __name__ == "__main__":
    run()
