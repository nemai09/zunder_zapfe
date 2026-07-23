"""Protected administration workflows shared by kiosk and smartphone sessions."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from zunder_zapfe.backend.tap_service import TapService
from zunder_zapfe.hardware import HardwareLayer
from zunder_zapfe.persistence.models import Beverage, Event, Keg, NfcCard, User, UserRole
from zunder_zapfe.persistence.repository import Repository, canonicalize_nfc_uid

ADMIN_TIMEOUT_SETTING = "session.admin_timeout_seconds"
MIN_ADMIN_TIMEOUT_SECONDS = 10
MAX_ADMIN_TIMEOUT_SECONDS = 3600
REMOTE_NFC_CAPTURE_TIMEOUT_SECONDS = 45


class AdminConflict(RuntimeError):
    """Raised when an otherwise authorized admin action conflicts with domain state."""


@dataclass
class _NfcCapture:
    sequence: int
    admin_user_id: int
    target_user_id: int
    observed_empty_reader: bool
    remote: bool


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
        self._capture_sequence = 0
        self._capture_timer: threading.Timer | None = None
        self._expired_capture: tuple[int, int] | None = None
        self._mutex = threading.RLock()

    def enter(self) -> dict[str, Any]:
        timeout_seconds = self._configured_timeout()
        return self._tap_service.enter_admin_mode(timeout_seconds)

    def exit(self) -> dict[str, Any]:
        self._cancel_capture()
        return self._tap_service.exit_admin_mode()

    def settings(self, *, admin_user_id: int | None = None) -> dict[str, int]:
        self._require_admin_id(admin_user_id)
        return {"admin_session_timeout_seconds": self._configured_timeout()}

    def update_settings(
        self,
        *,
        admin_session_timeout_seconds: int,
        admin_user_id: int | None = None,
    ) -> dict[str, int]:
        admin_id = self._require_admin_id(admin_user_id)
        timeout_seconds = self._validate_timeout(admin_session_timeout_seconds)
        with self._sessions.begin() as session:
            Repository(session).set_setting(
                ADMIN_TIMEOUT_SETTING,
                timeout_seconds,
                admin_user_id=admin_id,
            )
        self._tap_service.apply_admin_session_timeout(timeout_seconds)
        return {"admin_session_timeout_seconds": timeout_seconds}

    def list_users(self, *, admin_user_id: int | None = None) -> list[dict[str, Any]]:
        self._require_admin_id(admin_user_id)
        with self._sessions() as session:
            repository = Repository(session)
            return [self._user_snapshot(repository, user) for user in repository.list_users()]

    def list_events(self, *, admin_user_id: int | None = None) -> list[dict[str, Any]]:
        self._require_admin_id(admin_user_id)
        with self._sessions() as session:
            return [self._event_snapshot(event) for event in Repository(session).list_events()]

    def create_event(
        self,
        *,
        name: str,
        year: int,
        starts_at: datetime | None,
        ends_at: datetime | None,
        active: bool,
        admin_user_id: int | None = None,
    ) -> dict[str, Any]:
        admin_id = self._require_admin_id(admin_user_id)
        starts_at = _as_utc(starts_at)
        ends_at = _as_utc(ends_at)
        if starts_at is not None and ends_at is not None and ends_at < starts_at:
            raise ValueError("Event end must not be before its start")
        with self._sessions.begin() as session:
            repository = Repository(session)
            if active and session.scalar(select(Keg.id).where(Keg.active.is_(True))) is not None:
                raise AdminConflict("An event with an active keg can only change via keg switch")
            event = repository.create_event(name, year, active=active)
            event.starts_at = starts_at
            event.ends_at = ends_at
            snapshot = self._event_snapshot(event)
            repository.record_admin_action(
                admin_user_id=admin_id,
                action="event.created",
                entity_type="event",
                entity_id=str(event.id),
                new_values=snapshot,
            )
            return snapshot

    def update_event(
        self,
        event_id: int,
        *,
        name: str,
        year: int,
        starts_at: datetime | None,
        ends_at: datetime | None,
        active: bool,
        admin_user_id: int | None = None,
    ) -> dict[str, Any]:
        admin_id = self._require_admin_id(admin_user_id)
        starts_at = _as_utc(starts_at)
        ends_at = _as_utc(ends_at)
        with self._sessions.begin() as session:
            repository = Repository(session)
            event = repository.get_event(event_id)
            active_keg = session.scalar(select(Keg).where(Keg.active.is_(True)))
            if active_keg is not None and (
                (not active and active_keg.event_id == event_id)
                or (active and active_keg.event_id != event_id)
            ):
                raise AdminConflict("The active keg and event must remain assigned to each other")
            old_values = self._event_snapshot(event)
            event = repository.update_event(
                event_id,
                name=name,
                year=year,
                starts_at=starts_at,
                ends_at=ends_at,
                active=active,
            )
            snapshot = self._event_snapshot(event)
            repository.record_admin_action(
                admin_user_id=admin_id,
                action="event.updated",
                entity_type="event",
                entity_id=str(event.id),
                old_values=old_values,
                new_values=snapshot,
            )
            return snapshot

    def list_beverages(self, *, admin_user_id: int | None = None) -> list[dict[str, Any]]:
        self._require_admin_id(admin_user_id)
        with self._sessions() as session:
            return [
                self._beverage_snapshot(beverage)
                for beverage in Repository(session).list_beverages()
            ]

    def create_beverage(
        self,
        *,
        name: str,
        default_keg_size_ml: int,
        price_per_liter_cents: int,
        admin_user_id: int | None = None,
    ) -> dict[str, Any]:
        admin_id = self._require_admin_id(admin_user_id)
        with self._sessions.begin() as session:
            repository = Repository(session)
            beverage = repository.create_beverage(
                name,
                default_keg_size_ml=default_keg_size_ml,
                price_per_liter_cents=price_per_liter_cents,
            )
            snapshot = self._beverage_snapshot(beverage)
            repository.record_admin_action(
                admin_user_id=admin_id,
                action="beverage.created",
                entity_type="beverage",
                entity_id=str(beverage.id),
                new_values=snapshot,
            )
            return snapshot

    def update_beverage(
        self,
        beverage_id: int,
        *,
        name: str,
        default_keg_size_ml: int,
        price_per_liter_cents: int,
        active: bool,
        admin_user_id: int | None = None,
    ) -> dict[str, Any]:
        admin_id = self._require_admin_id(admin_user_id)
        with self._sessions.begin() as session:
            repository = Repository(session)
            beverage = repository.get_beverage(beverage_id)
            if not active:
                active_keg = session.scalar(
                    select(Keg).where(
                        Keg.active.is_(True),
                        Keg.beverage_id == beverage_id,
                    )
                )
                if active_keg is not None:
                    raise AdminConflict("The beverage of the active keg cannot be disabled")
            old_values = self._beverage_snapshot(beverage)
            beverage = repository.update_beverage(
                beverage_id,
                name=name,
                default_keg_size_ml=default_keg_size_ml,
                price_per_liter_cents=price_per_liter_cents,
                active=active,
            )
            snapshot = self._beverage_snapshot(beverage)
            repository.record_admin_action(
                admin_user_id=admin_id,
                action="beverage.updated",
                entity_type="beverage",
                entity_id=str(beverage.id),
                old_values=old_values,
                new_values=snapshot,
            )
            return snapshot

    def list_kegs(self, *, admin_user_id: int | None = None) -> list[dict[str, Any]]:
        self._require_admin_id(admin_user_id)
        with self._sessions() as session:
            repository = Repository(session)
            return [self._keg_snapshot(repository, keg) for keg in repository.list_kegs()]

    def switch_keg(
        self,
        *,
        event_id: int,
        beverage_id: int,
        initial_volume_ml: int,
        admin_user_id: int | None = None,
    ) -> dict[str, Any]:
        admin_id = self._require_admin_id(admin_user_id)
        with self._sessions.begin() as session:
            repository = Repository(session)
            event = repository.get_event(event_id)
            beverage = repository.get_beverage(beverage_id)
            if not beverage.active:
                raise AdminConflict("Only an active beverage can be assigned to a new keg")
            old_keg = session.scalar(select(Keg).where(Keg.active.is_(True)))
            old_values = self._keg_snapshot(repository, old_keg) if old_keg is not None else None
            repository.activate_event(event.id)
            keg = repository.activate_new_keg(
                event_id=event.id,
                beverage_id=beverage.id,
                initial_volume_ml=initial_volume_ml,
            )
            snapshot = self._keg_snapshot(repository, keg)
            repository.record_admin_action(
                admin_user_id=admin_id,
                action="keg.switched",
                entity_type="keg",
                entity_id=str(keg.id),
                old_values=old_values,
                new_values=snapshot,
            )
            return snapshot

    def create_user(
        self,
        *,
        first_name: str,
        last_name: str | None,
        note: str | None,
        is_admin: bool,
        admin_user_id: int | None = None,
    ) -> dict[str, Any]:
        admin_id = self._require_admin_id(admin_user_id)
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
        admin_user_id: int | None = None,
    ) -> dict[str, Any]:
        admin_id = self._require_admin_id(admin_user_id)
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
            if not active or next_role is not UserRole.ADMIN:
                user.password_hash = None
                repository.revoke_web_admin_sessions(
                    user.id,
                    revoked_at=datetime.now(UTC),
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

    def delete_user(
        self,
        user_id: int,
        *,
        admin_user_id: int | None = None,
    ) -> None:
        admin_id = self._require_admin_id(admin_user_id)
        with self._sessions.begin() as session:
            repository = Repository(session)
            user = repository.get_user(user_id)
            if user.id == admin_id:
                raise AdminConflict("The active admin cannot delete itself")
            if user.role is UserRole.ADMIN and user.active:
                active_admins = session.scalar(
                    select(func.count(User.id)).where(
                        User.role == UserRole.ADMIN,
                        User.active.is_(True),
                        User.deleted_at.is_(None),
                    )
                )
                if int(active_admins or 0) <= 1:
                    raise AdminConflict("The last active admin cannot be deleted")
            old_values = self._audited_user_values(user)
            _user, removed_card_count = repository.soft_delete_user(
                user_id,
                deleted_at=datetime.now(UTC),
            )
            repository.record_admin_action(
                admin_user_id=admin_id,
                action="user.deleted",
                entity_type="user",
                entity_id=str(user.id),
                old_values=old_values,
                new_values={
                    "active": False,
                    "deleted": True,
                    "removed_nfc_card_count": removed_card_count,
                    "web_password_configured": False,
                },
            )
        with self._mutex:
            if self._capture is not None and self._capture.target_user_id == user_id:
                self._cancel_capture_unlocked()

    def list_nfc_cards(
        self,
        user_id: int,
        *,
        admin_user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        self._require_admin_id(admin_user_id)
        with self._sessions() as session:
            repository = Repository(session)
            return [self._card_snapshot(card) for card in repository.list_nfc_cards(user_id)]

    def capture_nfc_card(
        self,
        user_id: int,
        *,
        admin_user_id: int | None = None,
        remote: bool = False,
    ) -> dict[str, Any]:
        """Capture only a UID observed by the local reader after an empty-reader phase."""
        admin_id = self._require_admin_id(admin_user_id)
        with self._sessions() as session:
            Repository(session).get_user(user_id)

        with self._mutex:
            capture_key = (admin_id, user_id)
            if remote and self._expired_capture == capture_key:
                self._expired_capture = None
                return {"state": "timed_out", "card": None}
            capture = self._capture
            if (
                capture is None
                or capture.admin_user_id != admin_id
                or capture.target_user_id != user_id
                or capture.remote != remote
            ):
                self._cancel_capture_unlocked()
                if remote:
                    self._tap_service.begin_remote_nfc_capture()
                nfc = self._hardware.nfc.snapshot()
                self._capture_sequence += 1
                capture = _NfcCapture(
                    sequence=self._capture_sequence,
                    admin_user_id=admin_id,
                    target_user_id=user_id,
                    observed_empty_reader=nfc.state != "card",
                    remote=remote,
                )
                self._capture = capture
                if remote:
                    self._start_capture_timer(capture)
            else:
                nfc = self._hardware.nfc.snapshot()

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
                self._cancel_capture_unlocked()
                raise AdminConflict("The reader returned an invalid NFC UID") from error

            with self._sessions.begin() as session:
                repository = Repository(session)
                existing = repository.find_nfc_card(uid)
                if existing is not None and existing.user_id != user_id:
                    self._cancel_capture_unlocked()
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
            self._cancel_capture_unlocked()
            return {"state": "assigned", "card": snapshot}

    def cancel_nfc_capture(self, *, admin_user_id: int | None = None) -> None:
        self._require_admin_id(admin_user_id)
        self._cancel_capture()

    def set_nfc_card_active(
        self,
        card_id: int,
        *,
        active: bool,
        admin_user_id: int | None = None,
    ) -> dict[str, Any]:
        admin_id = self._require_admin_id(admin_user_id)
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

    def remove_nfc_card(self, card_id: int, *, admin_user_id: int | None = None) -> None:
        admin_id = self._require_admin_id(admin_user_id)
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

    def _require_admin_id(self, admin_user_id: int | None = None) -> int:
        admin_id = (
            self._tap_service.require_admin_user_id() if admin_user_id is None else admin_user_id
        )
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
    def _event_snapshot(event: Event) -> dict[str, Any]:
        return {
            "id": event.id,
            "name": event.name,
            "year": event.year,
            "starts_at": event.starts_at.isoformat() if event.starts_at else None,
            "ends_at": event.ends_at.isoformat() if event.ends_at else None,
            "active": event.active,
        }

    @staticmethod
    def _beverage_snapshot(beverage: Beverage) -> dict[str, Any]:
        return {
            "id": beverage.id,
            "name": beverage.name,
            "default_keg_size_ml": beverage.default_keg_size_ml,
            "price_per_liter_cents": beverage.price_per_liter_cents,
            "active": beverage.active,
        }

    @staticmethod
    def _keg_snapshot(repository: Repository, keg: Keg) -> dict[str, Any]:
        event = repository.get_event(keg.event_id)
        beverage = repository.get_beverage(keg.beverage_id)
        return {
            "id": keg.id,
            "event_id": event.id,
            "event_name": event.name,
            "beverage_id": beverage.id,
            "beverage_name": beverage.name,
            "initial_volume_ml": keg.initial_volume_ml,
            "remaining_volume_ml": repository.remaining_keg_volume_ml(keg.id),
            "active": keg.active,
            "opened_at": keg.opened_at.isoformat(),
            "closed_at": keg.closed_at.isoformat() if keg.closed_at else None,
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
            "has_password": user.password_hash is not None,
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
            self._expired_capture = None
            self._cancel_capture_unlocked()

    def _cancel_capture_unlocked(self) -> None:
        capture = self._capture
        self._capture = None
        if self._capture_timer is not None:
            self._capture_timer.cancel()
            self._capture_timer = None
        if capture is not None and capture.remote:
            self._tap_service.end_remote_nfc_capture()

    def _start_capture_timer(self, capture: _NfcCapture) -> None:
        timer = threading.Timer(
            REMOTE_NFC_CAPTURE_TIMEOUT_SECONDS,
            self._expire_capture,
            args=(capture.sequence,),
        )
        timer.daemon = True
        self._capture_timer = timer
        timer.start()

    def _expire_capture(self, sequence: int) -> None:
        with self._mutex:
            capture = self._capture
            if capture is None or capture.sequence != sequence:
                return
            self._expired_capture = (capture.admin_user_id, capture.target_user_id)
            self._cancel_capture_unlocked()


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
