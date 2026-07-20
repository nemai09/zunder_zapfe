"""Minimal web application used to verify the Raspberry Pi kiosk toolchain."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from ipaddress import ip_address
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, sessionmaker

from zunder_zapfe import __version__
from zunder_zapfe.api_models import (
    AdminNfcCaptureResponse,
    AdminNfcCardResponse,
    AdminNfcCardStatusRequest,
    AdminSettingsResponse,
    AdminSettingsUpdateRequest,
    AdminUserCreateRequest,
    AdminUserResponse,
    AdminUserUpdateRequest,
    ConsumptionResponse,
    ErrorResponse,
    HardwareStatusResponse,
    HealthResponse,
    KegStatusResponse,
    NfcStatusResponse,
    PortionRequest,
    PourRecordResponse,
    SessionStatusResponse,
    SimulatedCardRequest,
    SimulatedPulsesRequest,
    TapOptionsResponse,
    TapStatusResponse,
)
from zunder_zapfe.backend.admin_service import AdminConflict, AdminService
from zunder_zapfe.backend.tap_controller import InvalidTransition, development_limits
from zunder_zapfe.backend.tap_service import FlowCalibration, TapService, TapUnavailable
from zunder_zapfe.build_info import current_build_info
from zunder_zapfe.configuration import KioskSettings, load_kiosk_settings
from zunder_zapfe.hardware import HardwareLayer, create_default_hardware
from zunder_zapfe.hardware.models import status_dict
from zunder_zapfe.hardware.simulators import SimulatedFlowMeter, SimulatedNfcReader
from zunder_zapfe.persistence import create_database_engine, create_session_factory

WEB_ROOT = Path(__file__).resolve().parent / "web"


BUILD_INFO = current_build_info(WEB_ROOT.parents[2])


def create_app(
    hardware: HardwareLayer | None = None,
    sessions: sessionmaker[Session] | None = None,
    *,
    enable_simulator_api: bool | None = None,
    run_background: bool = True,
    kiosk_settings: KioskSettings | None = None,
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
    resolved_kiosk_settings = kiosk_settings or load_kiosk_settings()
    tap_service = TapService(
        hardware_layer,
        sessions,
        development_limits(
            session_timeout_seconds=resolved_kiosk_settings.session_timeout_seconds,
            admin_session_timeout_seconds=(resolved_kiosk_settings.admin_session_timeout_seconds),
            manual_maximum_seconds=resolved_kiosk_settings.manual_maximum_pour_seconds,
            flow_watchdog_enabled=(not resolved_kiosk_settings.debug_disable_flow_watchdog),
        ),
        calibration=FlowCalibration(
            pulses_per_liter=int(os.environ.get("ZUNDER_ZAPFE_PULSES_PER_LITER", "500"))
        ),
        standard_portions_ml=resolved_kiosk_settings.standard_portions_ml,
        run_background=run_background,
    )
    admin_service = AdminService(
        hardware_layer,
        sessions,
        tap_service,
        default_timeout_seconds=resolved_kiosk_settings.admin_session_timeout_seconds,
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
        description=(
            "Local alpha API for NFC authentication, safe tap control and SQLite bookings."
        ),
        version=__version__,
        license_info={
            "name": "GNU General Public License v3.0 or later",
            "identifier": "GPL-3.0-or-later",
        },
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")

    @application.middleware("http")
    async def prevent_kiosk_asset_cache(request: Request, call_next: Any) -> Response:
        if request.url.path.startswith("/api/admin/") and not _is_loopback_request(request):
            return JSONResponse(
                status_code=403,
                content={"detail": "Local admin API is only available over loopback"},
            )
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(TapUnavailable)
    @application.exception_handler(InvalidTransition)
    @application.exception_handler(AdminConflict)
    async def domain_conflict(_request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @application.exception_handler(PermissionError)
    async def admin_forbidden(_request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(error)})

    @application.exception_handler(LookupError)
    async def entity_not_found(_request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @application.exception_handler(ValueError)
    async def invalid_domain_value(_request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @application.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(WEB_ROOT / "index.html")

    conflict_response = {409: {"model": ErrorResponse, "description": "Domain conflict"}}

    @application.get("/api/health", response_model=HealthResponse)
    async def health() -> dict[str, str]:
        return {
            "application": "zunder-zapfe",
            "status": "ready",
            "version": __version__,
            "build": BUILD_INFO.display_version,
            "revision": BUILD_INFO.revision,
            "server_time": datetime.now(UTC).isoformat(),
        }

    @application.get("/api/nfc/status", response_model=NfcStatusResponse)
    async def nfc_status() -> dict[str, object]:
        return status_dict(hardware_layer.nfc.snapshot())

    @application.get("/api/hardware/status", response_model=HardwareStatusResponse)
    async def hardware_status() -> dict[str, dict[str, object]]:
        return hardware_layer.snapshot()

    @application.get("/api/tap/status", response_model=TapStatusResponse)
    async def tap_status() -> dict[str, object]:
        return tap_service.status_dict()

    @application.get("/api/session/status", response_model=SessionStatusResponse)
    async def session_status() -> dict[str, object]:
        status = tap_service.status_dict()
        return {
            "user_id": status["user_id"],
            "user_display_name": status["user_display_name"],
            "is_admin": status["is_admin"],
            "special_portion_ml": status["special_portion_ml"],
        }

    @application.get("/api/tap/options", response_model=TapOptionsResponse)
    async def tap_options() -> dict[str, Any]:
        return {
            **tap_service.portion_options(),
            "session_timeout_seconds": resolved_kiosk_settings.session_timeout_seconds,
            "manual_press_debounce_ms": resolved_kiosk_settings.manual_press_debounce_ms,
            "manual_maximum_pour_seconds": (resolved_kiosk_settings.manual_maximum_pour_seconds),
            "debug_flow_watchdog_disabled": (resolved_kiosk_settings.debug_disable_flow_watchdog),
            "admin_session_timeout_seconds": (
                resolved_kiosk_settings.admin_session_timeout_seconds
            ),
        }

    admin_responses = {
        403: {"model": ErrorResponse, "description": "Active admin mode required"},
        409: {"model": ErrorResponse, "description": "Domain conflict"},
        422: {"model": ErrorResponse, "description": "Invalid value"},
    }

    @application.post(
        "/api/admin/session/enter",
        response_model=TapStatusResponse,
        responses=admin_responses,
    )
    async def enter_admin_session() -> dict[str, Any]:
        return admin_service.enter()

    @application.post(
        "/api/admin/session/exit",
        response_model=TapStatusResponse,
        responses=admin_responses,
    )
    async def exit_admin_session() -> dict[str, Any]:
        return admin_service.exit()

    @application.get(
        "/api/admin/settings",
        response_model=AdminSettingsResponse,
        responses=admin_responses,
    )
    async def admin_settings() -> dict[str, int]:
        return admin_service.settings()

    @application.patch(
        "/api/admin/settings",
        response_model=AdminSettingsResponse,
        responses=admin_responses,
    )
    async def update_admin_settings(request: AdminSettingsUpdateRequest) -> dict[str, int]:
        return admin_service.update_settings(
            admin_session_timeout_seconds=request.admin_session_timeout_seconds
        )

    @application.get(
        "/api/admin/users",
        response_model=list[AdminUserResponse],
        responses=admin_responses,
    )
    async def list_admin_users() -> list[dict[str, Any]]:
        return admin_service.list_users()

    @application.post(
        "/api/admin/users",
        response_model=AdminUserResponse,
        status_code=201,
        responses=admin_responses,
    )
    async def create_admin_user(request: AdminUserCreateRequest) -> dict[str, Any]:
        return admin_service.create_user(**request.model_dump())

    @application.patch(
        "/api/admin/users/{user_id}",
        response_model=AdminUserResponse,
        responses=admin_responses,
    )
    async def update_admin_user(
        user_id: int,
        request: AdminUserUpdateRequest,
    ) -> dict[str, Any]:
        return admin_service.update_user(user_id, **request.model_dump())

    @application.get(
        "/api/admin/users/{user_id}/nfc-cards",
        response_model=list[AdminNfcCardResponse],
        responses=admin_responses,
    )
    async def list_admin_user_nfc_cards(user_id: int) -> list[dict[str, Any]]:
        return admin_service.list_nfc_cards(user_id)

    @application.post(
        "/api/admin/users/{user_id}/nfc-cards/capture",
        response_model=AdminNfcCaptureResponse,
        responses=admin_responses,
    )
    async def capture_admin_user_nfc_card(user_id: int) -> dict[str, Any]:
        return admin_service.capture_nfc_card(user_id)

    @application.delete(
        "/api/admin/nfc-capture",
        status_code=204,
        responses=admin_responses,
    )
    async def cancel_admin_nfc_capture() -> Response:
        admin_service.cancel_nfc_capture()
        return Response(status_code=204)

    @application.patch(
        "/api/admin/nfc-cards/{card_id}",
        response_model=AdminNfcCardResponse,
        responses=admin_responses,
    )
    async def update_admin_nfc_card(
        card_id: int,
        request: AdminNfcCardStatusRequest,
    ) -> dict[str, Any]:
        return admin_service.set_nfc_card_active(card_id, active=request.active)

    @application.post("/api/session/logout", status_code=204, responses=conflict_response)
    async def logout() -> Response:
        tap_service.logout()
        return Response(status_code=204)

    @application.post("/api/session/activity", status_code=204, responses=conflict_response)
    async def register_session_activity() -> Response:
        tap_service.register_activity()
        return Response(status_code=204)

    @application.post(
        "/api/tap/portion", response_model=TapStatusResponse, responses=conflict_response
    )
    async def start_portion(request: PortionRequest) -> dict[str, Any]:
        return tap_service.start_portion(request.target_volume_ml)

    @application.post(
        "/api/tap/portion/abort",
        response_model=PourRecordResponse,
        responses=conflict_response,
    )
    async def abort_portion() -> dict[str, Any]:
        return asdict(tap_service.abort_portion())

    @application.post(
        "/api/tap/manual/start", response_model=TapStatusResponse, responses=conflict_response
    )
    async def start_manual_pour() -> dict[str, Any]:
        return tap_service.start_manual_pour()

    @application.post(
        "/api/tap/manual/stop",
        response_model=PourRecordResponse,
        responses=conflict_response,
    )
    async def stop_manual_pour() -> dict[str, Any]:
        return asdict(tap_service.stop_manual_pour())

    @application.post(
        "/api/tap/top-up/start", response_model=TapStatusResponse, responses=conflict_response
    )
    async def start_top_up() -> dict[str, Any]:
        return tap_service.start_top_up()

    @application.post(
        "/api/tap/top-up/stop",
        response_model=PourRecordResponse,
        responses=conflict_response,
    )
    async def stop_top_up() -> dict[str, Any]:
        return asdict(tap_service.stop_top_up())

    @application.post("/api/tap/maintenance/enter", status_code=204, responses=conflict_response)
    async def enter_maintenance() -> Response:
        tap_service.enter_maintenance()
        return Response(status_code=204)

    @application.post(
        "/api/tap/maintenance/start",
        response_model=TapStatusResponse,
        responses=conflict_response,
    )
    async def start_maintenance_pour() -> dict[str, Any]:
        return tap_service.start_maintenance_pour()

    @application.post(
        "/api/tap/maintenance/stop",
        response_model=PourRecordResponse,
        responses=conflict_response,
    )
    async def stop_maintenance_pour() -> dict[str, Any]:
        return asdict(tap_service.stop_maintenance_pour())

    @application.post("/api/tap/maintenance/exit", status_code=204, responses=conflict_response)
    async def exit_maintenance() -> Response:
        tap_service.exit_maintenance()
        return Response(status_code=204)

    @application.post("/api/tap/heartbeat", status_code=204)
    async def heartbeat() -> Response:
        tap_service.heartbeat()
        return Response(status_code=204)

    @application.post("/api/tap/poll", response_model=TapStatusResponse)
    async def poll_tap() -> dict[str, Any]:
        return tap_service.poll()

    @application.post(
        "/api/tap/safety/reset",
        response_model=TapStatusResponse,
        responses=conflict_response,
    )
    async def reset_safety_lock() -> dict[str, Any]:
        return tap_service.reset_safety_lock()

    @application.get(
        "/api/consumption/current",
        response_model=ConsumptionResponse,
        responses=conflict_response,
    )
    async def current_consumption() -> dict[str, int]:
        return tap_service.current_consumption()

    @application.get(
        "/api/keg/current", response_model=KegStatusResponse, responses=conflict_response
    )
    async def current_keg() -> dict[str, Any]:
        return tap_service.current_keg()

    if simulator_api_enabled:

        @application.post(
            "/api/simulator/nfc/present",
            response_model=SessionStatusResponse,
            responses=conflict_response,
        )
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

        @application.post(
            "/api/simulator/flow/pulses",
            response_model=TapStatusResponse,
            responses=conflict_response,
        )
        async def simulate_flow(request: SimulatedPulsesRequest) -> dict[str, Any]:
            if not isinstance(hardware_layer.flow_meter, SimulatedFlowMeter):
                return JSONResponse(
                    status_code=409, content={"detail": "Flow meter is not simulated"}
                )
            hardware_layer.flow_meter.add_pulses(request.count)
            tap_service.heartbeat()
            return tap_service.poll()

    return application


def _is_loopback_request(request: Request) -> bool:
    if request.client is None:
        return False
    try:
        return ip_address(request.client.host).is_loopback
    except ValueError:
        return False


app = create_app()


def run() -> None:
    """Run the local-only web server used by the kiosk browser."""
    host = os.environ.get("ZUNDER_ZAPFE_HOST", "127.0.0.1")
    port = int(os.environ.get("ZUNDER_ZAPFE_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, access_log=True)


if __name__ == "__main__":
    run()
