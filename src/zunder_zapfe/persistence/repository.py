"""Transaction-scoped persistence operations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zunder_zapfe.persistence.models import (
    AdminAuditEntry,
    Beverage,
    BookingCompletion,
    BookingKind,
    Event,
    Keg,
    NfcCard,
    Setting,
    TapBooking,
    TechnicalEvent,
    User,
    UserRole,
)


def canonicalize_nfc_uid(uid: str) -> str:
    canonical = re.sub(r"[\s:-]", "", uid).upper()
    if len(canonical) < 4 or len(canonical) % 2 or not re.fullmatch(r"[0-9A-F]+", canonical):
        raise ValueError("NFC UID must contain an even number of hexadecimal digits")
    return canonical


@dataclass(frozen=True)
class NewTapBooking:
    event_id: int
    user_id: int
    beverage_id: int
    keg_id: int
    occurred_at: datetime
    target_volume_ml: int | None
    measured_volume_ml: int
    measured_pulses: int
    price_per_liter_cents: int
    kind: BookingKind
    completion: BookingCompletion
    chargeable: bool


@dataclass(frozen=True)
class ActiveTapContext:
    event_id: int
    event_name: str
    beverage_id: int
    beverage_name: str
    keg_id: int
    initial_volume_ml: int
    price_per_liter_cents: int


@dataclass(frozen=True)
class ConsumptionSummary:
    event_id: int
    user_id: int
    booking_count: int
    measured_volume_ml: int
    amount_cents: int


class Repository:
    """Persist domain objects using the transaction owned by the caller."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_event(self, name: str, year: int, *, active: bool = False) -> Event:
        event = Event(name=_required_text(name, "Event name"), year=year, active=False)
        self.session.add(event)
        self.session.flush()
        if active:
            self.activate_event(event.id)
        return event

    def activate_event(self, event_id: int) -> Event:
        event = self.session.get(Event, event_id)
        if event is None:
            raise LookupError(f"Event {event_id} does not exist")
        for current_event in self.session.scalars(select(Event).where(Event.active.is_(True))):
            current_event.active = False
        event.active = True
        self.session.flush()
        return event

    def create_user(
        self,
        first_name: str,
        *,
        last_name: str | None = None,
        note: str | None = None,
        role: UserRole = UserRole.USER,
        active: bool = True,
    ) -> User:
        normalized_first_name = _required_text(first_name, "First name")
        normalized_last_name = _optional_text(last_name)
        user = User(
            display_name=_display_name(normalized_first_name, normalized_last_name),
            first_name=normalized_first_name,
            last_name=normalized_last_name,
            note=_optional_text(note),
            role=role,
            active=active,
        )
        self.session.add(user)
        self.session.flush()
        return user

    def get_user(self, user_id: int) -> User:
        user = self.session.get(User, user_id)
        if user is None:
            raise LookupError(f"User {user_id} does not exist")
        return user

    def list_users(self) -> list[User]:
        return list(self.session.scalars(select(User).order_by(User.first_name, User.last_name)))

    def update_user(
        self,
        user_id: int,
        *,
        first_name: str,
        last_name: str | None,
        note: str | None,
        role: UserRole,
        active: bool,
    ) -> User:
        user = self.get_user(user_id)
        user.first_name = _required_text(first_name, "First name")
        user.last_name = _optional_text(last_name)
        user.note = _optional_text(note)
        user.display_name = _display_name(user.first_name, user.last_name)
        user.role = role
        user.active = active
        self.session.flush()
        return user

    def add_nfc_card(self, user_id: int, uid: str) -> NfcCard:
        self.get_user(user_id)
        card = NfcCard(user_id=user_id, uid=canonicalize_nfc_uid(uid), active=True)
        self.session.add(card)
        self.session.flush()
        return card

    def get_nfc_card(self, card_id: int) -> NfcCard:
        card = self.session.get(NfcCard, card_id)
        if card is None:
            raise LookupError(f"NFC card {card_id} does not exist")
        return card

    def find_nfc_card(self, uid: str) -> NfcCard | None:
        return self.session.scalar(select(NfcCard).where(NfcCard.uid == canonicalize_nfc_uid(uid)))

    def list_nfc_cards(self, user_id: int) -> list[NfcCard]:
        self.get_user(user_id)
        return list(
            self.session.scalars(
                select(NfcCard).where(NfcCard.user_id == user_id).order_by(NfcCard.id)
            )
        )

    def set_nfc_card_active(self, card_id: int, *, active: bool) -> NfcCard:
        card = self.get_nfc_card(card_id)
        card.active = active
        self.session.flush()
        return card

    def delete_nfc_card(self, card_id: int) -> None:
        card = self.get_nfc_card(card_id)
        self.session.delete(card)
        self.session.flush()

    def find_active_user_by_card(self, uid: str) -> User | None:
        statement = (
            select(User)
            .join(NfcCard, NfcCard.user_id == User.id)
            .where(
                NfcCard.uid == canonicalize_nfc_uid(uid),
                NfcCard.active.is_(True),
                User.active.is_(True),
            )
        )
        return self.session.scalar(statement)

    def create_beverage(
        self, name: str, *, default_keg_size_ml: int, price_per_liter_cents: int
    ) -> Beverage:
        beverage = Beverage(
            name=_required_text(name, "Beverage name"),
            default_keg_size_ml=default_keg_size_ml,
            price_per_liter_cents=price_per_liter_cents,
            active=True,
        )
        self.session.add(beverage)
        self.session.flush()
        return beverage

    def active_tap_context(self) -> ActiveTapContext | None:
        statement = (
            select(Event, Keg, Beverage)
            .join(Keg, Keg.event_id == Event.id)
            .join(Beverage, Beverage.id == Keg.beverage_id)
            .where(
                Event.active.is_(True),
                Keg.active.is_(True),
                Beverage.active.is_(True),
            )
        )
        row = self.session.execute(statement).one_or_none()
        if row is None:
            return None
        event, keg, beverage = row
        return ActiveTapContext(
            event_id=event.id,
            event_name=event.name,
            beverage_id=beverage.id,
            beverage_name=beverage.name,
            keg_id=keg.id,
            initial_volume_ml=keg.initial_volume_ml,
            price_per_liter_cents=beverage.price_per_liter_cents,
        )

    def activate_new_keg(
        self,
        *,
        event_id: int,
        beverage_id: int,
        initial_volume_ml: int,
        opened_at: datetime | None = None,
    ) -> Keg:
        timestamp = opened_at or datetime.now(UTC)
        for current_keg in self.session.scalars(select(Keg).where(Keg.active.is_(True))):
            current_keg.active = False
            current_keg.closed_at = timestamp
        keg = Keg(
            event_id=event_id,
            beverage_id=beverage_id,
            initial_volume_ml=initial_volume_ml,
            active=True,
            opened_at=timestamp,
        )
        self.session.add(keg)
        self.session.flush()
        return keg

    def add_tap_booking(self, values: NewTapBooking) -> TapBooking:
        keg = self.session.get(Keg, values.keg_id)
        if keg is None:
            raise LookupError(f"Keg {values.keg_id} does not exist")
        if keg.event_id != values.event_id or keg.beverage_id != values.beverage_id:
            raise ValueError("Booking event and beverage must match the selected keg")
        if self.session.get(User, values.user_id) is None:
            raise LookupError(f"User {values.user_id} does not exist")
        amount_cents = (
            calculate_amount_cents(values.measured_volume_ml, values.price_per_liter_cents)
            if values.chargeable
            else 0
        )
        booking = TapBooking(**values.__dict__, amount_cents=amount_cents)
        self.session.add(booking)
        self.session.flush()
        return booking

    def list_user_bookings(self, *, event_id: int, user_id: int) -> list[TapBooking]:
        statement = (
            select(TapBooking)
            .where(TapBooking.event_id == event_id, TapBooking.user_id == user_id)
            .order_by(TapBooking.occurred_at, TapBooking.id)
        )
        return list(self.session.scalars(statement))

    def user_consumption(self, *, event_id: int, user_id: int) -> ConsumptionSummary:
        if self.session.get(Event, event_id) is None:
            raise LookupError(f"Event {event_id} does not exist")
        if self.session.get(User, user_id) is None:
            raise LookupError(f"User {user_id} does not exist")
        booking_count, measured_volume_ml, amount_cents = self.session.execute(
            select(
                func.count(TapBooking.id),
                func.coalesce(func.sum(TapBooking.measured_volume_ml), 0),
                func.coalesce(func.sum(TapBooking.amount_cents), 0),
            ).where(
                TapBooking.event_id == event_id,
                TapBooking.user_id == user_id,
                TapBooking.chargeable.is_(True),
            )
        ).one()
        return ConsumptionSummary(
            event_id=event_id,
            user_id=user_id,
            booking_count=int(booking_count),
            measured_volume_ml=int(measured_volume_ml),
            amount_cents=int(amount_cents),
        )

    def remaining_keg_volume_ml(self, keg_id: int) -> int:
        keg = self.session.get(Keg, keg_id)
        if keg is None:
            raise LookupError(f"Keg {keg_id} does not exist")
        consumed = self.session.scalar(
            select(func.coalesce(func.sum(TapBooking.measured_volume_ml), 0)).where(
                TapBooking.keg_id == keg_id
            )
        )
        return keg.initial_volume_ml - int(consumed or 0)

    def set_setting(
        self,
        key: str,
        value: Any,
        *,
        admin_user_id: int,
    ) -> Setting:
        admin = self.session.get(User, admin_user_id)
        if admin is None or not admin.active or admin.role is not UserRole.ADMIN:
            raise PermissionError("An active admin is required to change settings")

        setting = self.session.get(Setting, key)
        old_value = json.loads(setting.value_json) if setting is not None else None
        value_json = _json(value)
        if setting is None:
            setting = Setting(
                key=key,
                value_json=value_json,
                updated_by_user_id=admin_user_id,
            )
            self.session.add(setting)
        else:
            setting.value_json = value_json
            setting.updated_by_user_id = admin_user_id

        self.record_admin_action(
            admin_user_id=admin_user_id,
            action="setting.changed",
            entity_type="setting",
            entity_id=key,
            old_values=old_value,
            new_values=value,
        )
        self.session.flush()
        return setting

    def get_setting(self, key: str, default: Any = None) -> Any:
        setting = self.session.get(Setting, key)
        return default if setting is None else json.loads(setting.value_json)

    def record_admin_action(
        self,
        *,
        admin_user_id: int,
        action: str,
        entity_type: str,
        entity_id: str | None,
        old_values: Any = None,
        new_values: Any = None,
    ) -> AdminAuditEntry:
        self._require_active_admin(admin_user_id)
        entry = AdminAuditEntry(
            admin_user_id=admin_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values_json=_json(old_values) if old_values is not None else None,
            new_values_json=_json(new_values) if new_values is not None else None,
        )
        self.session.add(entry)
        return entry

    def record_technical_event(
        self,
        *,
        severity: str,
        event_type: str,
        message: str,
        details: Any = None,
    ) -> TechnicalEvent:
        entry = TechnicalEvent(
            severity=severity,
            event_type=event_type,
            message=message,
            details_json=_json(details) if details is not None else None,
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def _require_active_admin(self, user_id: int) -> User:
        user = self.session.get(User, user_id)
        if user is None or not user.active or user.role is not UserRole.ADMIN:
            raise PermissionError("An active admin is required")
        return user


def calculate_amount_cents(measured_volume_ml: int, price_per_liter_cents: int) -> int:
    """Round a measured volume to the nearest cent without floating point."""
    if measured_volume_ml < 0 or price_per_liter_cents < 0:
        raise ValueError("Measured volume and price must not be negative")
    return (measured_volume_ml * price_per_liter_cents + 500) // 1000


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _required_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} must not be empty")
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _display_name(first_name: str, last_name: str | None) -> str:
    display_name = first_name if last_name is None else f"{first_name} {last_name}"
    if len(display_name) > 120:
        raise ValueError("Combined first and last name must not exceed 120 characters")
    return display_name
