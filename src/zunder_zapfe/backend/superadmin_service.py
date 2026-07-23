"""Presence-bound local Superadmin workflows."""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass

from pwdlib import PasswordHash
from sqlalchemy.orm import Session, sessionmaker

from zunder_zapfe.backend.superadmin_identity import SuperadminIdentity
from zunder_zapfe.backend.tap_service import TapService
from zunder_zapfe.backend.wifi_mode_service import WifiModeError, WifiModeService
from zunder_zapfe.hardware import HardwareLayer
from zunder_zapfe.nfc_identity import canonicalize_nfc_uid
from zunder_zapfe.persistence.models import UserRole
from zunder_zapfe.persistence.repository import Repository

PROVISIONING_TIMEOUT_SECONDS = 15


@dataclass
class _ProvisioningCapture:
    sequence: int
    role: UserRole
    observed_empty_reader: bool = False


class SuperadminService:
    """Coordinate bounded local maintenance actions without a user account."""

    def __init__(
        self,
        hardware: HardwareLayer,
        sessions: sessionmaker[Session],
        tap_service: TapService,
        *,
        wifi_mode_service: WifiModeService,
        identity: SuperadminIdentity | None,
    ) -> None:
        self._hardware = hardware
        self._sessions = sessions
        self._tap_service = tap_service
        self._wifi_mode_service = wifi_mode_service
        self._identity = identity
        self._password_hash = PasswordHash.recommended()
        self._capture: _ProvisioningCapture | None = None
        self._capture_sequence = 0
        self._capture_timer: threading.Timer | None = None
        self._terminal_state = "inactive"
        self._mutex = threading.RLock()

    def shutdown(self) -> None:
        with self._mutex:
            self._cancel_timer()
            self._capture = None

    def switch_wifi_mode(self, mode: str) -> dict[str, str | bool | None]:
        self._tap_service.require_superadmin_presence()
        old_status = self._wifi_mode_service.status(force=True).as_dict()
        with self._sessions.begin() as session:
            Repository(session).record_superadmin_action(
                action="wifi.mode_switch_requested",
                entity_type="wifi",
                entity_id="wlan0",
                old_values=old_status,
                new_values={"requested_mode": mode},
            )
        try:
            new_status = self._wifi_mode_service.switch(mode)
        except WifiModeError:
            with self._sessions.begin() as session:
                Repository(session).record_technical_event(
                    severity="error",
                    event_type="wifi.mode_switch_failed",
                    message="WLAN-Moduswechsel durch Superadmin fehlgeschlagen",
                    details={"requested_mode": mode, "actor_kind": "superadmin"},
                )
            raise
        with self._sessions.begin() as session:
            Repository(session).record_superadmin_action(
                action="wifi.mode_switched",
                entity_type="wifi",
                entity_id="wlan0",
                old_values=old_status,
                new_values=new_status.as_dict(),
            )
        return new_status.as_dict()

    def start_provisioning(self, role: str) -> dict[str, str | None]:
        requested_role = UserRole(role)
        with self._mutex:
            if self._capture is not None:
                raise RuntimeError("Eine Notfallanlage läuft bereits")
            self._tap_service.begin_provisioning_handover()
            self._capture_sequence += 1
            capture = _ProvisioningCapture(
                sequence=self._capture_sequence,
                role=requested_role,
            )
            self._capture = capture
            self._terminal_state = "remove_card"
            timer = threading.Timer(
                PROVISIONING_TIMEOUT_SECONDS,
                self._expire_capture,
                args=(capture.sequence,),
            )
            timer.daemon = True
            self._capture_timer = timer
            timer.start()
        return self._result("remove_card")

    def poll_provisioning(self) -> dict[str, str | None]:
        with self._mutex:
            capture = self._capture
            if capture is None:
                return self._result(self._terminal_state)

            nfc = self._hardware.nfc.snapshot()
            if not capture.observed_empty_reader:
                if nfc.state != "card":
                    capture.observed_empty_reader = True
                    self._terminal_state = "waiting"
                    return self._result("waiting")
                return self._result("remove_card")

            if nfc.state in {"starting", "unavailable", "disconnected", "error"}:
                return self._result("reader_unavailable")
            if nfc.state != "card" or not nfc.uid:
                return self._result("waiting")

            try:
                uid = canonicalize_nfc_uid(nfc.uid)
            except ValueError:
                return self._finish_capture("invalid_card")
            if self._identity is not None and self._identity.matches(uid):
                return self._finish_capture("superadmin_card")

            one_time_password = secrets.token_urlsafe(9) if capture.role is UserRole.ADMIN else None
            try:
                with self._sessions.begin() as session:
                    repository = Repository(session)
                    if repository.find_nfc_card(uid) is not None:
                        card_assigned = True
                        display_name = None
                    else:
                        card_assigned = False
                        prefix = (
                            "Notfall-Admin"
                            if capture.role is UserRole.ADMIN
                            else "Notfall-Benutzer"
                        )
                        user = repository.create_user(prefix, role=capture.role)
                        user.first_name = f"{prefix} {user.id}"
                        user.display_name = user.first_name
                        if one_time_password is not None:
                            user.password_hash = self._password_hash.hash(one_time_password)
                            user.password_change_required = True
                        repository.add_nfc_card(user.id, uid)
                        repository.record_superadmin_action(
                            action="user.emergency_created",
                            entity_type="user",
                            entity_id=str(user.id),
                            new_values={
                                "display_name": user.display_name,
                                "role": user.role.value,
                                "password_change_required": user.password_change_required,
                            },
                        )
                        display_name = user.display_name
            except Exception:
                self._finish_capture("failed")
                raise
            if card_assigned:
                return self._finish_capture("card_assigned")
            return self._finish_capture(
                "created",
                display_name=display_name,
                one_time_password=one_time_password,
            )

    def cancel_provisioning(self) -> dict[str, str | None]:
        with self._mutex:
            if self._capture is None:
                return self._result(self._terminal_state)
            return self._finish_capture("cancelled")

    def _expire_capture(self, sequence: int) -> None:
        with self._mutex:
            if self._capture is None or self._capture.sequence != sequence:
                return
            self._finish_capture("timeout")

    def _finish_capture(
        self,
        state: str,
        *,
        display_name: str | None = None,
        one_time_password: str | None = None,
    ) -> dict[str, str | None]:
        self._cancel_timer()
        self._capture = None
        self._terminal_state = state
        self._tap_service.end_provisioning_handover()
        return self._result(
            state,
            display_name=display_name,
            one_time_password=one_time_password,
        )

    def _cancel_timer(self) -> None:
        if self._capture_timer is not None:
            self._capture_timer.cancel()
        self._capture_timer = None

    @staticmethod
    def _result(
        state: str,
        *,
        display_name: str | None = None,
        one_time_password: str | None = None,
    ) -> dict[str, str | None]:
        return {
            "state": state,
            "display_name": display_name,
            "one_time_password": one_time_password,
        }
