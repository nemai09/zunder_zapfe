"""Offline password authentication and revocable sessions for web admins."""

from __future__ import annotations

import hashlib
import secrets
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pwdlib import PasswordHash
from sqlalchemy.orm import Session, sessionmaker

from zunder_zapfe.persistence.models import User, UserRole, WebAdminSession
from zunder_zapfe.persistence.repository import Repository

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128
DEFAULT_IDLE_TIMEOUT = timedelta(minutes=30)
DEFAULT_ABSOLUTE_TIMEOUT = timedelta(hours=12)
MAX_LOGIN_FAILURES = 5
LOGIN_FAILURE_WINDOW = timedelta(minutes=1)


class WebAuthenticationError(RuntimeError):
    """Raised when web credentials or a web session are invalid."""


class WebAuthorizationError(RuntimeError):
    """Raised when an authenticated user is not allowed to administer."""


class WebCsrfError(RuntimeError):
    """Raised when a state-changing web request lacks its CSRF proof."""


class WebLoginRateLimited(RuntimeError):
    """Raised after repeated failed web logins."""


@dataclass(frozen=True)
class WebAdminIdentity:
    user_id: int
    display_name: str
    session_id: int
    idle_expires_at: datetime
    absolute_expires_at: datetime


@dataclass(frozen=True)
class IssuedWebSession:
    token: str
    csrf_token: str
    identity: WebAdminIdentity
    idle_expires_at: datetime
    absolute_expires_at: datetime


class WebAuthService:
    """Hash passwords and manage personal, server-side web admin sessions."""

    def __init__(
        self,
        sessions: sessionmaker[Session],
        *,
        idle_timeout: timedelta = DEFAULT_IDLE_TIMEOUT,
        absolute_timeout: timedelta = DEFAULT_ABSOLUTE_TIMEOUT,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if idle_timeout <= timedelta(0) or absolute_timeout <= idle_timeout:
            raise ValueError("Web session timeouts are invalid")
        self._sessions = sessions
        self._idle_timeout = idle_timeout
        self._absolute_timeout = absolute_timeout
        self._now = now or (lambda: datetime.now(UTC))
        self._password_hash = PasswordHash.recommended()
        self._dummy_hash = self._password_hash.hash(secrets.token_urlsafe(32))
        self._login_failures: dict[int, list[datetime]] = {}
        self._failure_mutex = threading.Lock()

    def list_login_admins(self) -> list[dict[str, object]]:
        with self._sessions() as session:
            return [
                {"id": user.id, "display_name": user.display_name}
                for user in Repository(session).list_web_admins()
            ]

    def login(self, *, user_id: int, password: str) -> IssuedWebSession:
        now = self._utc_now()
        self._ensure_login_allowed(user_id, now)
        issued: IssuedWebSession | None = None
        with self._sessions.begin() as session:
            user = session.get(User, user_id)
            stored_hash = (
                user.password_hash
                if user is not None
                and user.active
                and user.role is UserRole.ADMIN
                and user.password_hash
                else self._dummy_hash
            )
            password_matches = self._password_hash.verify(password, stored_hash)
            authenticated = stored_hash != self._dummy_hash and password_matches
            if not authenticated:
                Repository(session).record_technical_event(
                    severity="warning",
                    event_type="web_admin.login_failed",
                    message="Fehlgeschlagene Admin-Webanmeldung",
                    details={"user_id": user_id},
                )
            else:
                self._clear_login_failures(user_id)
                token = secrets.token_urlsafe(32)
                csrf_token = secrets.token_urlsafe(32)
                idle_expires_at = now + self._idle_timeout
                absolute_expires_at = now + self._absolute_timeout
                web_session = WebAdminSession(
                    token_hash=_token_hash(token),
                    csrf_token_hash=_token_hash(csrf_token),
                    user_id=user.id,
                    created_at=now,
                    last_activity_at=now,
                    idle_expires_at=idle_expires_at,
                    absolute_expires_at=absolute_expires_at,
                )
                session.add(web_session)
                session.flush()
                Repository(session).record_technical_event(
                    severity="info",
                    event_type="web_admin.login_succeeded",
                    message="Admin-Webanmeldung erfolgreich",
                    details={"user_id": user.id, "session_id": web_session.id},
                )
                identity = WebAdminIdentity(
                    user_id=user.id,
                    display_name=user.display_name,
                    session_id=web_session.id,
                    idle_expires_at=idle_expires_at,
                    absolute_expires_at=absolute_expires_at,
                )
                issued = IssuedWebSession(
                    token=token,
                    csrf_token=csrf_token,
                    identity=identity,
                    idle_expires_at=idle_expires_at,
                    absolute_expires_at=absolute_expires_at,
                )
        if issued is None:
            self._record_login_failure(user_id, now)
            raise WebAuthenticationError("Admin oder Passwort ist ungültig")
        return issued

    def authenticate(
        self,
        token: str | None,
        *,
        csrf_token: str | None = None,
        require_csrf: bool = False,
    ) -> WebAdminIdentity:
        if not token:
            raise WebAuthenticationError("Keine Admin-Websitzung vorhanden")
        now = self._utc_now()
        error: RuntimeError | None = None
        identity: WebAdminIdentity | None = None
        with self._sessions.begin() as session:
            repository = Repository(session)
            web_session = repository.find_web_admin_session(_token_hash(token))
            if web_session is None or web_session.revoked_at is not None:
                raise WebAuthenticationError("Admin-Websitzung ist ungültig")
            if now >= _as_utc(web_session.idle_expires_at) or now >= _as_utc(
                web_session.absolute_expires_at
            ):
                web_session.revoked_at = now
                error = WebAuthenticationError("Admin-Websitzung ist abgelaufen")
            else:
                user = session.get(User, web_session.user_id)
                if (
                    user is None
                    or not user.active
                    or user.role is not UserRole.ADMIN
                    or not user.password_hash
                ):
                    web_session.revoked_at = now
                    error = WebAuthorizationError("Aktiver Adminzugang erforderlich")
                elif require_csrf and (
                    not csrf_token
                    or not secrets.compare_digest(
                        web_session.csrf_token_hash,
                        _token_hash(csrf_token),
                    )
                ):
                    raise WebCsrfError("CSRF-Prüfung fehlgeschlagen")
                else:
                    web_session.last_activity_at = now
                    web_session.idle_expires_at = min(
                        now + self._idle_timeout,
                        _as_utc(web_session.absolute_expires_at),
                    )
                    identity = WebAdminIdentity(
                        user_id=user.id,
                        display_name=user.display_name,
                        session_id=web_session.id,
                        idle_expires_at=_as_utc(web_session.idle_expires_at),
                        absolute_expires_at=_as_utc(web_session.absolute_expires_at),
                    )
        if error is not None:
            raise error
        if identity is None:
            raise WebAuthenticationError("Admin-Websitzung ist ungültig")
        return identity

    def logout(self, token: str | None, *, csrf_token: str | None) -> None:
        identity = self.authenticate(token, csrf_token=csrf_token, require_csrf=True)
        now = self._utc_now()
        with self._sessions.begin() as session:
            web_session = session.get(WebAdminSession, identity.session_id)
            if web_session is not None:
                web_session.revoked_at = now
            Repository(session).record_technical_event(
                severity="info",
                event_type="web_admin.logout",
                message="Admin-Websitzung beendet",
                details={"user_id": identity.user_id, "session_id": identity.session_id},
            )

    def change_own_password(
        self,
        token: str | None,
        *,
        csrf_token: str | None,
        current_password: str,
        new_password: str,
    ) -> None:
        identity = self.authenticate(token, csrf_token=csrf_token, require_csrf=True)
        normalized_password = _validate_password(new_password)
        now = self._utc_now()
        with self._sessions.begin() as session:
            repository = Repository(session)
            user = repository.get_user(identity.user_id)
            if not user.password_hash or not self._password_hash.verify(
                current_password, user.password_hash
            ):
                raise WebAuthenticationError("Das bisherige Passwort ist ungültig")
            user.password_hash = self._password_hash.hash(normalized_password)
            repository.revoke_web_admin_sessions(user.id, revoked_at=now)
            repository.record_admin_action(
                admin_user_id=user.id,
                action="admin.password_changed",
                entity_type="user",
                entity_id=str(user.id),
                new_values={"web_password_configured": True},
            )

    def reset_password(
        self,
        *,
        actor_user_id: int,
        target_user_id: int,
        new_password: str,
    ) -> None:
        if actor_user_id == target_user_id:
            raise WebAuthorizationError(
                "Das eigene Passwort muss mit dem bisherigen Passwort geändert werden"
            )
        normalized_password = _validate_password(new_password)
        now = self._utc_now()
        with self._sessions.begin() as session:
            repository = Repository(session)
            actor = repository.get_user(actor_user_id)
            target = repository.get_user(target_user_id)
            if not actor.active or actor.role is not UserRole.ADMIN:
                raise WebAuthorizationError("Aktiver Adminzugang erforderlich")
            if not target.active or target.role is not UserRole.ADMIN:
                raise ValueError("Nur ein aktiver Admin kann ein Webpasswort erhalten")
            target.password_hash = self._password_hash.hash(normalized_password)
            repository.revoke_web_admin_sessions(target.id, revoked_at=now)
            repository.record_admin_action(
                admin_user_id=actor.id,
                action="admin.password_reset",
                entity_type="user",
                entity_id=str(target.id),
                new_values={"web_password_configured": True},
            )

    def set_initial_password(self, *, user_id: int, password: str) -> None:
        normalized_password = _validate_password(password)
        now = self._utc_now()
        with self._sessions.begin() as session:
            repository = Repository(session)
            user = repository.get_user(user_id)
            if not user.active or user.role is not UserRole.ADMIN:
                raise ValueError(
                    "Das Initialpasswort kann nur für einen aktiven Admin gesetzt werden"
                )
            action = (
                "admin.password_initialized"
                if user.password_hash is None
                else "admin.password_reset_local"
            )
            user.password_hash = self._password_hash.hash(normalized_password)
            repository.revoke_web_admin_sessions(user.id, revoked_at=now)
            repository.record_admin_action(
                admin_user_id=user.id,
                action=action,
                entity_type="user",
                entity_id=str(user.id),
                new_values={"web_password_configured": True},
            )

    def _ensure_login_allowed(self, user_id: int, now: datetime) -> None:
        with self._failure_mutex:
            failures = [
                occurred_at
                for occurred_at in self._login_failures.get(user_id, [])
                if now - occurred_at < LOGIN_FAILURE_WINDOW
            ]
            self._login_failures[user_id] = failures
            if len(failures) >= MAX_LOGIN_FAILURES:
                raise WebLoginRateLimited("Zu viele Fehlversuche; bitte kurz warten")

    def _record_login_failure(self, user_id: int, now: datetime) -> None:
        with self._failure_mutex:
            self._login_failures.setdefault(user_id, []).append(now)

    def _clear_login_failures(self, user_id: int) -> None:
        with self._failure_mutex:
            self._login_failures.pop(user_id, None)

    def _utc_now(self) -> datetime:
        return _as_utc(self._now())


def _validate_password(password: str) -> str:
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ValueError(
            f"Passwort muss zwischen {MIN_PASSWORD_LENGTH} und "
            f"{MAX_PASSWORD_LENGTH} Zeichen lang sein"
        )
    if not password.strip():
        raise ValueError("Passwort darf nicht nur aus Leerzeichen bestehen")
    return password


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
