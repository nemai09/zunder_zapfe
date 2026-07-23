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
from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, sessionmaker

from zunder_zapfe import __version__
from zunder_zapfe.api_models import (
    AdminAuditEntryResponse,
    AdminBeverageCreateRequest,
    AdminBeverageResponse,
    AdminBeverageUpdateRequest,
    AdminBookingResponse,
    AdminBookingSessionResponse,
    AdminEventCreateRequest,
    AdminEventResponse,
    AdminEventStatisticsResponse,
    AdminEventUpdateRequest,
    AdminKegResponse,
    AdminKegSwitchRequest,
    AdminNfcCaptureResponse,
    AdminNfcCardResponse,
    AdminNfcCardStatusRequest,
    AdminSettingsResponse,
    AdminSettingsUpdateRequest,
    AdminTechnicalEventResponse,
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
    SuperadminDiagnosticsResponse,
    SuperadminProvisioningRequest,
    SuperadminProvisioningResponse,
    TapOptionsResponse,
    TapStatusResponse,
    WebAdminLoginOptionResponse,
    WebAdminLoginRequest,
    WebAdminPasswordChangeRequest,
    WebAdminPasswordResetRequest,
    WebAdminSessionResponse,
    WifiModeRequest,
    WifiStatusResponse,
)
from zunder_zapfe.backend.admin_service import AdminConflict, AdminService
from zunder_zapfe.backend.superadmin_identity import (
    SuperadminIdentity,
    load_superadmin_identity,
)
from zunder_zapfe.backend.superadmin_service import SuperadminService
from zunder_zapfe.backend.tap_controller import InvalidTransition, development_limits
from zunder_zapfe.backend.tap_service import FlowCalibration, TapService, TapUnavailable
from zunder_zapfe.backend.web_auth_service import (
    WebAdminIdentity,
    WebAuthenticationError,
    WebAuthorizationError,
    WebAuthService,
    WebCsrfError,
    WebLoginRateLimited,
)
from zunder_zapfe.backend.wifi_mode_service import WifiModeError, WifiModeService
from zunder_zapfe.build_info import current_build_info
from zunder_zapfe.configuration import KioskSettings, load_kiosk_settings
from zunder_zapfe.hardware import HardwareLayer, create_default_hardware
from zunder_zapfe.hardware.models import status_dict
from zunder_zapfe.hardware.simulators import SimulatedFlowMeter, SimulatedNfcReader
from zunder_zapfe.persistence import create_database_engine, create_session_factory

WEB_ROOT = Path(__file__).resolve().parent / "web"
WEB_ADMIN_SESSION_COOKIE = "zz_admin_session"
WEB_ADMIN_CSRF_COOKIE = "zz_admin_csrf"
WEB_ADMIN_CSRF_HEADER = "X-CSRF-Token"


BUILD_INFO = current_build_info(WEB_ROOT.parents[2])


def create_app(
    hardware: HardwareLayer | None = None,
    sessions: sessionmaker[Session] | None = None,
    *,
    enable_simulator_api: bool | None = None,
    run_background: bool = True,
    kiosk_settings: KioskSettings | None = None,
    wifi_mode_service: WifiModeService | None = None,
    superadmin_identity: SuperadminIdentity | None = None,
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
    resolved_wifi_mode_service = wifi_mode_service or WifiModeService()
    resolved_superadmin_identity = superadmin_identity or load_superadmin_identity()
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
        superadmin_identity=resolved_superadmin_identity,
    )
    admin_service = AdminService(
        hardware_layer,
        sessions,
        tap_service,
        default_timeout_seconds=resolved_kiosk_settings.admin_session_timeout_seconds,
        wifi_mode_service=resolved_wifi_mode_service,
        superadmin_identity=resolved_superadmin_identity,
    )
    web_auth_service = WebAuthService(sessions)
    superadmin_service = SuperadminService(
        hardware_layer,
        sessions,
        tap_service,
        wifi_mode_service=resolved_wifi_mode_service,
        identity=resolved_superadmin_identity,
    )

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        hardware_layer.start()
        try:
            tap_service.start()
            yield
        finally:
            superadmin_service.shutdown()
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
        local_only = (
            request.url.path == "/system"
            or request.url.path.startswith("/api/admin/")
            or request.url.path.startswith("/api/system/")
        )
        if local_only and not _is_loopback_request(request):
            return JSONResponse(
                status_code=403,
                content={"detail": "Local admin API is only available over loopback"},
            )
        response = await call_next(request)
        if request.url.path in {"/", "/admin", "/system"} or request.url.path.startswith(
            "/static/"
        ):
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

    @application.exception_handler(WebAuthenticationError)
    async def web_authentication_failed(_request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(error)})

    @application.exception_handler(WebAuthorizationError)
    @application.exception_handler(WebCsrfError)
    async def web_authorization_failed(_request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(error)})

    @application.exception_handler(WebLoginRateLimited)
    async def web_login_rate_limited(_request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": str(error)},
            headers={"Retry-After": "60"},
        )

    @application.exception_handler(LookupError)
    async def entity_not_found(_request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @application.exception_handler(ValueError)
    async def invalid_domain_value(_request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @application.exception_handler(WifiModeError)
    async def wifi_mode_failed(_request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(error)})

    @application.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(WEB_ROOT / "index.html")

    @application.get("/admin", include_in_schema=False)
    async def smartphone_admin() -> FileResponse:
        return FileResponse(WEB_ROOT / "admin.html")

    @application.get("/system", include_in_schema=False)
    async def local_system_admin() -> FileResponse:
        tap_service.require_system_page_access()
        return FileResponse(WEB_ROOT / "system.html")

    conflict_response = {409: {"model": ErrorResponse, "description": "Domain conflict"}}

    def require_web_admin(
        request: Request,
        *,
        write: bool = False,
        allow_password_change: bool = False,
    ) -> WebAdminIdentity:
        identity = web_auth_service.authenticate(
            request.cookies.get(WEB_ADMIN_SESSION_COOKIE),
            csrf_token=request.headers.get(WEB_ADMIN_CSRF_HEADER),
            require_csrf=write,
        )
        if identity.password_change_required and not allow_password_change:
            raise WebAuthorizationError(
                "Vor der Verwaltung muss das Einmalpasswort geändert werden"
            )
        return identity

    def web_session_response(identity: WebAdminIdentity) -> dict[str, object]:
        return {
            "user_id": identity.user_id,
            "display_name": identity.display_name,
            "idle_expires_at": identity.idle_expires_at,
            "absolute_expires_at": identity.absolute_expires_at,
            "password_change_required": identity.password_change_required,
        }

    def clear_web_admin_cookies(response: Response) -> None:
        response.delete_cookie(WEB_ADMIN_SESSION_COOKIE, path="/")
        response.delete_cookie(WEB_ADMIN_CSRF_COOKIE, path="/")

    @application.get(
        "/api/web-auth/admins",
        response_model=list[WebAdminLoginOptionResponse],
    )
    async def web_login_admins() -> list[dict[str, object]]:
        return web_auth_service.list_login_admins()

    @application.post(
        "/api/web-auth/login",
        response_model=WebAdminSessionResponse,
        responses={
            401: {"model": ErrorResponse, "description": "Invalid credentials"},
            429: {"model": ErrorResponse, "description": "Too many attempts"},
        },
    )
    async def web_admin_login(
        request: WebAdminLoginRequest,
        response: Response,
    ) -> dict[str, object]:
        issued = web_auth_service.login(user_id=request.user_id, password=request.password)
        max_age = max(
            1,
            int((issued.absolute_expires_at - datetime.now(UTC)).total_seconds()),
        )
        response.set_cookie(
            WEB_ADMIN_SESSION_COOKIE,
            issued.token,
            max_age=max_age,
            httponly=True,
            secure=False,
            samesite="strict",
            path="/",
        )
        response.set_cookie(
            WEB_ADMIN_CSRF_COOKIE,
            issued.csrf_token,
            max_age=max_age,
            httponly=False,
            secure=False,
            samesite="strict",
            path="/",
        )
        return web_session_response(issued.identity)

    @application.get(
        "/api/web-auth/session",
        response_model=WebAdminSessionResponse,
        responses={401: {"model": ErrorResponse, "description": "No valid session"}},
    )
    async def web_admin_session(request: Request) -> dict[str, object]:
        return web_session_response(require_web_admin(request, allow_password_change=True))

    @application.post(
        "/api/web-auth/logout",
        status_code=204,
        responses={401: {"model": ErrorResponse, "description": "No valid session"}},
    )
    async def web_admin_logout(request: Request) -> Response:
        web_auth_service.logout(
            request.cookies.get(WEB_ADMIN_SESSION_COOKIE),
            csrf_token=request.headers.get(WEB_ADMIN_CSRF_HEADER),
        )
        response = Response(status_code=204)
        clear_web_admin_cookies(response)
        return response

    @application.post(
        "/api/web-auth/password",
        status_code=204,
        responses={401: {"model": ErrorResponse, "description": "Invalid password"}},
    )
    async def change_web_admin_password(
        request_body: WebAdminPasswordChangeRequest,
        request: Request,
    ) -> Response:
        web_auth_service.change_own_password(
            request.cookies.get(WEB_ADMIN_SESSION_COOKIE),
            csrf_token=request.headers.get(WEB_ADMIN_CSRF_HEADER),
            current_password=request_body.current_password,
            new_password=request_body.new_password,
        )
        response = Response(status_code=204)
        clear_web_admin_cookies(response)
        return response

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

    @application.get("/api/wifi/status", response_model=WifiStatusResponse)
    def wifi_status() -> dict[str, str | bool | None]:
        return resolved_wifi_mode_service.status().as_dict()

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

    @application.delete(
        "/api/admin/users/{user_id}",
        status_code=204,
        responses=admin_responses,
    )
    async def delete_admin_user(user_id: int) -> Response:
        admin_service.delete_user(user_id)
        return Response(status_code=204)

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

    @application.delete(
        "/api/admin/nfc-cards/{card_id}",
        status_code=204,
        responses=admin_responses,
    )
    async def remove_admin_nfc_card(card_id: int) -> Response:
        admin_service.remove_nfc_card(card_id)
        return Response(status_code=204)

    web_admin_responses = {
        401: {"model": ErrorResponse, "description": "Valid web admin session required"},
        403: {"model": ErrorResponse, "description": "Admin authorization failed"},
        409: {"model": ErrorResponse, "description": "Domain conflict"},
        422: {"model": ErrorResponse, "description": "Invalid value"},
    }

    @application.get(
        "/api/web-admin/settings",
        response_model=AdminSettingsResponse,
        responses=web_admin_responses,
    )
    async def web_admin_settings(request: Request) -> dict[str, int]:
        identity = require_web_admin(request)
        return admin_service.settings(admin_user_id=identity.user_id)

    @application.patch(
        "/api/web-admin/settings",
        response_model=AdminSettingsResponse,
        responses=web_admin_responses,
    )
    async def update_web_admin_settings(
        request_body: AdminSettingsUpdateRequest,
        request: Request,
    ) -> dict[str, int]:
        identity = require_web_admin(request, write=True)
        return admin_service.update_settings(
            admin_session_timeout_seconds=request_body.admin_session_timeout_seconds,
            admin_user_id=identity.user_id,
        )

    @application.get(
        "/api/web-admin/events",
        response_model=list[AdminEventResponse],
        responses=web_admin_responses,
    )
    async def list_web_admin_events(request: Request) -> list[dict[str, Any]]:
        identity = require_web_admin(request)
        return admin_service.list_events(admin_user_id=identity.user_id)

    @application.post(
        "/api/web-admin/events",
        response_model=AdminEventResponse,
        status_code=201,
        responses=web_admin_responses,
    )
    async def create_web_admin_event(
        request_body: AdminEventCreateRequest,
        request: Request,
    ) -> dict[str, Any]:
        identity = require_web_admin(request, write=True)
        return admin_service.create_event(
            **request_body.model_dump(),
            admin_user_id=identity.user_id,
        )

    @application.patch(
        "/api/web-admin/events/{event_id}",
        response_model=AdminEventResponse,
        responses=web_admin_responses,
    )
    async def update_web_admin_event(
        event_id: int,
        request_body: AdminEventUpdateRequest,
        request: Request,
    ) -> dict[str, Any]:
        identity = require_web_admin(request, write=True)
        return admin_service.update_event(
            event_id,
            **request_body.model_dump(),
            admin_user_id=identity.user_id,
        )

    @application.get(
        "/api/web-admin/beverages",
        response_model=list[AdminBeverageResponse],
        responses=web_admin_responses,
    )
    async def list_web_admin_beverages(request: Request) -> list[dict[str, Any]]:
        identity = require_web_admin(request)
        return admin_service.list_beverages(admin_user_id=identity.user_id)

    @application.post(
        "/api/web-admin/beverages",
        response_model=AdminBeverageResponse,
        status_code=201,
        responses=web_admin_responses,
    )
    async def create_web_admin_beverage(
        request_body: AdminBeverageCreateRequest,
        request: Request,
    ) -> dict[str, Any]:
        identity = require_web_admin(request, write=True)
        return admin_service.create_beverage(
            **request_body.model_dump(),
            admin_user_id=identity.user_id,
        )

    @application.patch(
        "/api/web-admin/beverages/{beverage_id}",
        response_model=AdminBeverageResponse,
        responses=web_admin_responses,
    )
    async def update_web_admin_beverage(
        beverage_id: int,
        request_body: AdminBeverageUpdateRequest,
        request: Request,
    ) -> dict[str, Any]:
        identity = require_web_admin(request, write=True)
        return admin_service.update_beverage(
            beverage_id,
            **request_body.model_dump(),
            admin_user_id=identity.user_id,
        )

    @application.get(
        "/api/web-admin/kegs",
        response_model=list[AdminKegResponse],
        responses=web_admin_responses,
    )
    async def list_web_admin_kegs(request: Request) -> list[dict[str, Any]]:
        identity = require_web_admin(request)
        return admin_service.list_kegs(admin_user_id=identity.user_id)

    @application.post(
        "/api/web-admin/kegs/switch",
        response_model=AdminKegResponse,
        status_code=201,
        responses=web_admin_responses,
    )
    async def switch_web_admin_keg(
        request_body: AdminKegSwitchRequest,
        request: Request,
    ) -> dict[str, Any]:
        identity = require_web_admin(request, write=True)
        return admin_service.switch_keg(
            **request_body.model_dump(),
            admin_user_id=identity.user_id,
        )

    @application.post(
        "/api/web-admin/kegs/detach",
        response_model=AdminKegResponse,
        responses=web_admin_responses,
    )
    async def detach_web_admin_keg(request: Request) -> dict[str, Any]:
        identity = require_web_admin(request, write=True)
        return admin_service.detach_keg(admin_user_id=identity.user_id)

    @application.get(
        "/api/web-admin/bookings",
        response_model=list[AdminBookingResponse],
        responses=web_admin_responses,
    )
    async def list_web_admin_bookings(
        request: Request,
        event_id: int | None = Query(default=None, gt=0),
        user_id: int | None = Query(default=None, gt=0),
        keg_id: int | None = Query(default=None, gt=0),
        kind: str | None = None,
        completion: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        identity = require_web_admin(request)
        return admin_service.list_bookings(
            event_id=event_id,
            user_id=user_id,
            keg_id=keg_id,
            kind=kind,
            completion=completion,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            limit=limit,
            admin_user_id=identity.user_id,
        )

    @application.get(
        "/api/web-admin/booking-sessions",
        response_model=list[AdminBookingSessionResponse],
        responses=web_admin_responses,
    )
    async def list_web_admin_booking_sessions(
        request: Request,
        event_id: int | None = Query(default=None, gt=0),
        user_id: int | None = Query(default=None, gt=0),
        keg_id: int | None = Query(default=None, gt=0),
        kind: str | None = None,
        completion: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        identity = require_web_admin(request)
        return admin_service.list_booking_sessions(
            event_id=event_id,
            user_id=user_id,
            keg_id=keg_id,
            kind=kind,
            completion=completion,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            limit=limit,
            admin_user_id=identity.user_id,
        )

    @application.get(
        "/api/web-admin/statistics",
        response_model=AdminEventStatisticsResponse,
        responses=web_admin_responses,
    )
    async def web_admin_statistics(
        request: Request,
        event_id: int = Query(gt=0),
    ) -> dict[str, Any]:
        identity = require_web_admin(request)
        return admin_service.event_statistics(
            event_id,
            admin_user_id=identity.user_id,
        )

    @application.get(
        "/api/web-admin/audit",
        response_model=list[AdminAuditEntryResponse],
        responses=web_admin_responses,
    )
    async def list_web_admin_audit(
        request: Request,
        entity_type: str | None = None,
        action: str | None = None,
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        identity = require_web_admin(request)
        return admin_service.list_audit_entries(
            entity_type=entity_type,
            action=action,
            limit=limit,
            admin_user_id=identity.user_id,
        )

    @application.get(
        "/api/web-admin/technical-events",
        response_model=list[AdminTechnicalEventResponse],
        responses=web_admin_responses,
    )
    async def list_web_admin_technical_events(
        request: Request,
        severity: str | None = None,
        event_type: str | None = None,
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        identity = require_web_admin(request)
        return admin_service.list_technical_events(
            severity=severity,
            event_type=event_type,
            limit=limit,
            admin_user_id=identity.user_id,
        )

    @application.get(
        "/api/web-admin/users",
        response_model=list[AdminUserResponse],
        responses=web_admin_responses,
    )
    async def list_web_admin_users(request: Request) -> list[dict[str, Any]]:
        identity = require_web_admin(request)
        return admin_service.list_users(admin_user_id=identity.user_id)

    @application.post(
        "/api/web-admin/users",
        response_model=AdminUserResponse,
        status_code=201,
        responses=web_admin_responses,
    )
    async def create_web_admin_user(
        request_body: AdminUserCreateRequest,
        request: Request,
    ) -> dict[str, Any]:
        identity = require_web_admin(request, write=True)
        return admin_service.create_user(
            **request_body.model_dump(),
            admin_user_id=identity.user_id,
        )

    @application.patch(
        "/api/web-admin/users/{user_id}",
        response_model=AdminUserResponse,
        responses=web_admin_responses,
    )
    async def update_web_admin_user(
        user_id: int,
        request_body: AdminUserUpdateRequest,
        request: Request,
    ) -> dict[str, Any]:
        identity = require_web_admin(request, write=True)
        return admin_service.update_user(
            user_id,
            **request_body.model_dump(),
            admin_user_id=identity.user_id,
        )

    @application.delete(
        "/api/web-admin/users/{user_id}",
        status_code=204,
        responses=web_admin_responses,
    )
    async def delete_web_admin_user(user_id: int, request: Request) -> Response:
        identity = require_web_admin(request, write=True)
        admin_service.delete_user(user_id, admin_user_id=identity.user_id)
        return Response(status_code=204)

    @application.put(
        "/api/web-admin/users/{user_id}/password",
        status_code=204,
        responses=web_admin_responses,
    )
    async def reset_web_admin_password(
        user_id: int,
        request_body: WebAdminPasswordResetRequest,
        request: Request,
    ) -> Response:
        identity = require_web_admin(request, write=True)
        web_auth_service.reset_password(
            actor_user_id=identity.user_id,
            target_user_id=user_id,
            new_password=request_body.new_password,
        )
        return Response(status_code=204)

    @application.get(
        "/api/web-admin/users/{user_id}/nfc-cards",
        response_model=list[AdminNfcCardResponse],
        responses=web_admin_responses,
    )
    async def list_web_admin_user_nfc_cards(
        user_id: int,
        request: Request,
    ) -> list[dict[str, Any]]:
        identity = require_web_admin(request)
        return admin_service.list_nfc_cards(user_id, admin_user_id=identity.user_id)

    @application.post(
        "/api/web-admin/users/{user_id}/nfc-cards/capture",
        response_model=AdminNfcCaptureResponse,
        responses=web_admin_responses,
    )
    async def capture_web_admin_user_nfc_card(
        user_id: int,
        request: Request,
    ) -> dict[str, Any]:
        identity = require_web_admin(request, write=True)
        return admin_service.capture_nfc_card(
            user_id,
            admin_user_id=identity.user_id,
            remote=True,
        )

    @application.delete(
        "/api/web-admin/nfc-capture",
        status_code=204,
        responses=web_admin_responses,
    )
    async def cancel_web_admin_nfc_capture(request: Request) -> Response:
        identity = require_web_admin(request, write=True)
        admin_service.cancel_nfc_capture(admin_user_id=identity.user_id)
        return Response(status_code=204)

    @application.patch(
        "/api/web-admin/nfc-cards/{card_id}",
        response_model=AdminNfcCardResponse,
        responses=web_admin_responses,
    )
    async def update_web_admin_nfc_card(
        card_id: int,
        request_body: AdminNfcCardStatusRequest,
        request: Request,
    ) -> dict[str, Any]:
        identity = require_web_admin(request, write=True)
        return admin_service.set_nfc_card_active(
            card_id,
            active=request_body.active,
            admin_user_id=identity.user_id,
        )

    @application.delete(
        "/api/web-admin/nfc-cards/{card_id}",
        status_code=204,
        responses=web_admin_responses,
    )
    async def remove_web_admin_nfc_card(card_id: int, request: Request) -> Response:
        identity = require_web_admin(request, write=True)
        admin_service.remove_nfc_card(card_id, admin_user_id=identity.user_id)
        return Response(status_code=204)

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

    @application.post(
        "/api/system/maintenance/start",
        response_model=TapStatusResponse,
        responses=conflict_response,
    )
    async def start_superadmin_maintenance_pour() -> dict[str, Any]:
        return tap_service.start_superadmin_maintenance_pour()

    @application.post(
        "/api/system/maintenance/stop",
        response_model=PourRecordResponse,
        responses=conflict_response,
    )
    async def stop_superadmin_maintenance_pour() -> dict[str, Any]:
        return asdict(tap_service.stop_superadmin_maintenance_pour())

    @application.post(
        "/api/system/maintenance/heartbeat",
        status_code=204,
        responses=conflict_response,
    )
    async def superadmin_maintenance_heartbeat() -> Response:
        tap_service.superadmin_heartbeat()
        return Response(status_code=204)

    @application.post(
        "/api/system/wifi/mode",
        response_model=WifiStatusResponse,
        responses={
            403: {"model": ErrorResponse, "description": "Superadmin card required"},
            503: {"model": ErrorResponse, "description": "Wi-Fi control unavailable"},
        },
    )
    def switch_system_wifi_mode(
        request: WifiModeRequest,
    ) -> dict[str, str | bool | None]:
        return superadmin_service.switch_wifi_mode(request.mode)

    @application.get(
        "/api/system/diagnostics",
        response_model=SuperadminDiagnosticsResponse,
        responses={403: {"model": ErrorResponse, "description": "Superadmin card required"}},
    )
    def superadmin_diagnostics() -> dict[str, Any]:
        tap_service.require_superadmin_presence()
        hardware_status = hardware_layer.snapshot()
        hardware_status["nfc"].pop("uid", None)
        try:
            keg = tap_service.current_keg()
        except TapUnavailable:
            keg = None
        return {
            "application": {
                "version": __version__,
                "build": BUILD_INFO.display_version,
                "revision": BUILD_INFO.revision,
            },
            "tap": tap_service.status_dict(),
            "nfc": hardware_status["nfc"],
            "valve": hardware_status["valve"],
            "flow_meter": hardware_status["flow_meter"],
            "emergency_stop": hardware_status["emergency_stop"],
            "wifi": resolved_wifi_mode_service.status().as_dict(),
            "keg": keg,
        }

    @application.post(
        "/api/system/provisioning/start",
        response_model=SuperadminProvisioningResponse,
        responses={403: {"model": ErrorResponse, "description": "Superadmin card required"}},
    )
    def start_superadmin_provisioning(
        request: SuperadminProvisioningRequest,
    ) -> dict[str, str | None]:
        return superadmin_service.start_provisioning(request.role)

    @application.post(
        "/api/system/provisioning/poll",
        response_model=SuperadminProvisioningResponse,
    )
    def poll_superadmin_provisioning() -> dict[str, str | None]:
        return superadmin_service.poll_provisioning()

    @application.delete(
        "/api/system/provisioning",
        response_model=SuperadminProvisioningResponse,
    )
    def cancel_superadmin_provisioning() -> dict[str, str | None]:
        return superadmin_service.cancel_provisioning()

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
    access_log = os.environ.get("ZUNDER_ZAPFE_ACCESS_LOG", "0") == "1"
    uvicorn.run(app, host=host, port=port, access_log=access_log)


if __name__ == "__main__":
    run()
