"""Protected administration workflows for the local kiosk UI."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from zunder_zapfe.backend.tap_service import TapService
from zunder_zapfe.hardware import HardwareLayer
from zunder_zapfe.persistence.models import NfcCard, User, UserRole
from zunder_zapfe.persistence.repository import Repository, canonicalize_nfc_uid

ADMIN_TIMEOUT_SETTING = "session.admin_timeout_seconds"
MIN_ADMIN_TIMEOUT_SECONDS = 10
MAX_ADMIN_TIMEOUT_SECONDS = 3600


class AdminConflict(RuntimeError):
    """Raised when an otherwise authorized admin action conflicts with domain state."""


@dataclass
class _NfcCapture:
    admin_user_id: int
    target_user_id: int
    observed_empty_reader: bool


class AdminService:
    """Apply admin authorization, persistence, auditing and NFC capture rules."""

    def __init__(
        self,
        hardware: HardwareLayer,
        sessions: sessionmaker[Session],
        tap_service: TapService,
        *,
        default_timeout_seconds: int = 30,
    ) -> None:
        self._hardware = hardware
        self._sessions = sessions
        self._tap_service = tap_service
        self._default_timeout_seconds = self._validate_timeout(default_timeout_seconds)
        self._capture: _NfcCapture | None = None
        self._mutex = threading.RLock()

    def enter(self) -> dict[str, Any]:
        timeout_seconds = self._configured_timeout()
        return self._tap_service.enter_admin_mode(timeout_seconds)

    def exit(self) -> dict[str, Any]:
        self._cancel_capture()
        return self._tap_service.exit_admin_mode()

    def settings(self) -> dict[str, int]:
        self._require_admin_id()
        return {"admin_session_timeout_seconds": self._configured_timeout()}

    def update_settings(self, *, admin_session_timeout_seconds: int) -> dict[str, int]:
        admin_id = self._require_admin_id()
        timeout_seconds = self._validate_timeout(admin_session_timeout_seconds)
        with self._sessions.begin() as session:
            Repository(session).set_setting(
                ADMIN_TIMEOUT_SETTING,
                timeout_seconds,
                admin_user_id=admin_id,
            )
        self._tap_service.set_admin_session_timeout(timeout_seconds)
        return {"admin_session_timeout_seconds": timeout_seconds}

    def list_users(self) -> list[dict[str, Any]]:
        self._require_admin_id()
        with self._sessions() as session:
            repository = Repository(session)
            return [self._user_snapshot(repository, user) for user in repository.list_users()]

    def create_user(
        self,
        *,
        first_name: str,
        last_name: str | None,
        note: str | None,
        is_admin: bool,
    ) -> dict[str, Any]:
        admin_id = self._require_admin_id()
        with self._sessions.begin() as session:
            repository = Repository(session)
            user = repository.create_user(
                first_name,
                last_name=last_name,
                note=note,
                role=UserRole.ADMIN if is_admin else UserRole.USER,
            )
            repository.record_admin_action(
                admin_user_id=admin_id,
                action="user.created",
                entity_type="user",
                entity_id=str(user.id),
                new_values=self._audited_user_values(user),
            )
            return self._user_snapshot(repository, user)

    def update_user(
        self,
        user_id: int,
        *,
        first_name: str,
        last_name: str | None,
        note: str | None,
        is_admin: bool,
        active: bool,
    ) -> dict[str, Any]:
        admin_id = self._require_admin_id()
        with self._sessions.begin() as session:
            repository = Repository(session)
            user = repository.get_user(user_id)
            next_role = UserRole.ADMIN if is_admin else UserRole.USER
            if user.id == admin_id and (not active or next_role is not UserRole.ADMIN):
                raise AdminConflict("The active admin cannot deactivate or demote itself")
            if (
                user.role is UserRole.ADMIN
                and user.active
                and (not active or next_role is not UserRole.ADMIN)
            ):
                active_admins = session.scalar(
                    select(func.count(User.id)).where(
                        User.role == UserRole.ADMIN,
                        User.active.is_(True),
                    )
                )
                if int(active_admins or 0) <= 1:
                    raise AdminConflict("The last active admin cannot be deactivated or demoted")
            old_values = self._audited_user_values(user)
            user = repository.update_user(
                user_id,
                first_name=first_name,
                last_name=last_name,
                note=note,
                role=next_role,
                active=active,
            )
            repository.record_admin_action(
                admin_user_id=admin_id,
                action="user.updated",
                entity_type="user",
                entity_id=str(user.id),
                old_values=old_values,
                new_values=self._audited_user_values(user),
            )
            return self._user_snapshot(repository, user)

    def list_nfc_cards(self, user_id: int) -> list[dict[str, Any]]:
        self._require_admin_id()
        with self._sessions() as session:
            repository = Repository(session)
            return [self._card_snapshot(card) for card in repository.list_nfc_cards(user_id)]

    def capture_nfc_card(self, user_id: int) -> dict[str, Any]:
        """Capture only a UID observed by the local reader after an empty-reader phase."""
        admin_id = self._require_admin_id()
        with self._sessions() as session:
            Repository(session).get_user(user_id)

        nfc = self._hardware.nfc.snapshot()
        with self._mutex:
            capture = self._capture
            if (
                capture is None
                or capture.admin_user_id != admin_id
                or capture.target_user_id != user_id
            ):
                capture = _NfcCapture(
                    admin_user_id=admin_id,
                    target_user_id=user_id,
                    observed_empty_reader=nfc.state != "card",
                )
                self._capture = capture

            if not capture.observed_empty_reader:
                if nfc.state == "card":
                    return {"state": "remove_card", "card": None}
                capture.observed_empty_reader = True
                return {"state": "waiting", "card": None}

            if nfc.state in {"starting", "unavailable", "disconnected", "error"}:
                return {"state": "reader_unavailable", "card": None}
            if nfc.state != "card" or not nfc.uid:
                return {"state": "waiting", "card": None}

            try:
                uid = canonicalize_nfc_uid(nfc.uid)
            except ValueError as error:
                raise AdminConflict("The reader returned an invalid NFC UID") from error

            with self._sessions.begin() as session:
                repository = Repository(session)
                existing = repository.find_nfc_card(uid)
                if existing is not None and existing.user_id != user_id:
                    self._capture = None
                    raise AdminConflict("This wristband is already assigned to another user")
                if existing is None:
                    card = repository.add_nfc_card(user_id, uid)
                    action = "nfc_card.assigned"
                else:
                    card = repository.set_nfc_card_active(existing.id, active=True)
                    action = "nfc_card.reactivated"
                repository.record_admin_action(
                    admin_user_id=admin_id,
                    action=action,
                    entity_type="nfc_card",
                    entity_id=str(card.id),
                    new_values={"user_id": user_id, "active": True},
                )
                snapshot = self._card_snapshot(card)
            self._capture = None
            return {"state": "assigned", "card": snapshot}

    def cancel_nfc_capture(self) -> None:
        self._require_admin_id()
        self._cancel_capture()

    def set_nfc_card_active(self, card_id: int, *, active: bool) -> dict[str, Any]:
        admin_id = self._require_admin_id()
        with self._sessions.begin() as session:
            repository = Repository(session)
            card = repository.get_nfc_card(card_id)
            if not active and card.user_id == admin_id:
                active_cards = session.scalar(
                    select(func.count(NfcCard.id)).where(
                        NfcCard.user_id == admin_id,
                        NfcCard.active.is_(True),
                    )
                )
                if int(active_cards or 0) <= 1:
                    raise AdminConflict("The active admin's last wristband cannot be disabled")
            old_active = card.active
            card = repository.set_nfc_card_active(card_id, active=active)
            repository.record_admin_action(
                admin_user_id=admin_id,
                action="nfc_card.status_changed",
                entity_type="nfc_card",
                entity_id=str(card.id),
                old_values={"active": old_active, "user_id": card.user_id},
                new_values={"active": card.active, "user_id": card.user_id},
            )
            return self._card_snapshot(card)

    def remove_nfc_card(self, card_id: int) -> None:
        admin_id = self._require_admin_id()
        with self._sessions.begin() as session:
            repository = Repository(session)
            card = repository.get_nfc_card(card_id)
            user = repository.get_user(card.user_id)
            if card.active and user.active and user.role is UserRole.ADMIN:
                active_cards = session.scalar(
                    select(func.count(NfcCard.id)).where(
                        NfcCard.user_id == user.id,
                        NfcCard.active.is_(True),
                    )
                )
                if int(active_cards or 0) <= 1:
                    raise AdminConflict(
                        "The last active wristband of an active admin cannot be removed"
                    )
            user_id = card.user_id
            repository.record_admin_action(
                admin_user_id=admin_id,
                action="nfc_card.removed",
                entity_type="nfc_card",
                entity_id=str(card.id),
                old_values={"user_id": user_id, "active": card.active},
            )
            repository.delete_nfc_card(card_id)

    def _require_admin_id(self) -> int:
        admin_id = self._tap_service.require_admin_user_id()
        with self._sessions() as session:
            user = session.get(User, admin_id)
            if user is None or not user.active or user.role is not UserRole.ADMIN:
                raise PermissionError("An active admin account is required")
        return admin_id

    def _configured_timeout(self) -> int:
        with self._sessions() as session:
            value = Repository(session).get_setting(
                ADMIN_TIMEOUT_SETTING,
                self._default_timeout_seconds,
            )
        try:
            return self._validate_timeout(int(value))
        except (TypeError, ValueError) as error:
            raise AdminConflict("The stored admin timeout is invalid") from error

    @staticmethod
    def _validate_timeout(value: int) -> int:
        if not MIN_ADMIN_TIMEOUT_SECONDS <= value <= MAX_ADMIN_TIMEOUT_SECONDS:
            raise ValueError(
                f"Admin timeout must be between {MIN_ADMIN_TIMEOUT_SECONDS} and "
                f"{MAX_ADMIN_TIMEOUT_SECONDS} seconds"
            )
        return value

    @staticmethod
    def _audited_user_values(user: User) -> dict[str, Any]:
        return {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "note": user.note,
            "role": user.role.value,
            "active": user.active,
        }

    @staticmethod
    def _user_snapshot(repository: Repository, user: User) -> dict[str, Any]:
        cards = repository.list_nfc_cards(user.id)
        return {
            "id": user.id,
            "display_name": user.display_name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "note": user.note,
            "is_admin": user.role is UserRole.ADMIN,
            "active": user.active,
            "nfc_card_count": len(cards),
            "active_nfc_card_count": sum(card.active for card in cards),
        }

    @staticmethod
    def _card_snapshot(card: NfcCard) -> dict[str, Any]:
        return {
            "id": card.id,
            "user_id": card.user_id,
            "uid_hint": f"…{card.uid[-4:]}",
            "active": card.active,
        }

    def _cancel_capture(self) -> None:
        with self._mutex:
            self._capture = None
