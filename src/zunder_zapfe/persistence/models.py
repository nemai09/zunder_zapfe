"""SQLAlchemy mappings for persistent domain data."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class BookingKind(StrEnum):
    MANUAL = "manual"
    PORTION = "portion"
    TOP_UP = "top_up"
    MAINTENANCE = "maintenance"
    FREE_ADMIN = "free_admin"


class BookingCompletion(StrEnum):
    TARGET_REACHED = "target_reached"
    USER_ABORT = "user_abort"
    RELEASED = "released"
    LIMIT_REACHED = "limit_reached"
    FAULT = "fault"
    SHUTDOWN = "shutdown"


def enum_type(enum_class: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("name", "year", name="uq_events_name_year"),
        Index(
            "uq_events_single_active",
            "active",
            unique=True,
            sqlite_where=text("active = 1"),
        ),
        CheckConstraint("year >= 2000 AND year <= 9999", name="ck_events_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    year: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "special_portion_ml IS NULL OR special_portion_ml > 0",
            name="ck_users_special_portion_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str | None] = mapped_column(String(80))
    note: Mapped[str | None] = mapped_column(Text)
    role: Mapped[UserRole] = mapped_column(enum_type(UserRole, "user_role"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    special_portion_ml: Mapped[int | None] = mapped_column(Integer)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class NfcCard(Base):
    __tablename__ = "nfc_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[str] = mapped_column(String(40), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Beverage(Base):
    __tablename__ = "beverages"
    __table_args__ = (
        CheckConstraint("default_keg_size_ml > 0", name="ck_beverages_keg_size_positive"),
        CheckConstraint("price_per_liter_cents >= 0", name="ck_beverages_price_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    default_keg_size_ml: Mapped[int] = mapped_column(Integer)
    price_per_liter_cents: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Keg(Base):
    __tablename__ = "kegs"
    __table_args__ = (
        Index(
            "uq_kegs_single_active",
            "active",
            unique=True,
            sqlite_where=text("active = 1"),
        ),
        CheckConstraint("initial_volume_ml > 0", name="ck_kegs_initial_volume_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="RESTRICT"), index=True)
    beverage_id: Mapped[int] = mapped_column(
        ForeignKey("beverages.id", ondelete="RESTRICT"), index=True
    )
    initial_volume_ml: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TapBooking(Base):
    __tablename__ = "tap_bookings"
    __table_args__ = (
        CheckConstraint(
            "target_volume_ml IS NULL OR target_volume_ml > 0",
            name="ck_tap_bookings_target_positive",
        ),
        CheckConstraint("measured_volume_ml >= 0", name="ck_tap_bookings_volume_nonnegative"),
        CheckConstraint("measured_pulses >= 0", name="ck_tap_bookings_pulses_nonnegative"),
        CheckConstraint("price_per_liter_cents >= 0", name="ck_tap_bookings_price_nonnegative"),
        CheckConstraint("amount_cents >= 0", name="ck_tap_bookings_amount_nonnegative"),
        CheckConstraint(
            "chargeable = 1 OR amount_cents = 0",
            name="ck_tap_bookings_free_amount_zero",
        ),
        CheckConstraint(
            "kind != 'maintenance' OR chargeable = 0",
            name="ck_tap_bookings_maintenance_not_chargeable",
        ),
        Index("ix_tap_bookings_event_user", "event_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="RESTRICT"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    beverage_id: Mapped[int] = mapped_column(ForeignKey("beverages.id", ondelete="RESTRICT"))
    keg_id: Mapped[int] = mapped_column(ForeignKey("kegs.id", ondelete="RESTRICT"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    target_volume_ml: Mapped[int | None] = mapped_column(Integer)
    measured_volume_ml: Mapped[int] = mapped_column(Integer)
    measured_pulses: Mapped[int] = mapped_column(Integer)
    price_per_liter_cents: Mapped[int] = mapped_column(Integer)
    amount_cents: Mapped[int] = mapped_column(Integer)
    kind: Mapped[BookingKind] = mapped_column(enum_type(BookingKind, "booking_kind"))
    completion: Mapped[BookingCompletion] = mapped_column(
        enum_type(BookingCompletion, "booking_completion")
    )
    chargeable: Mapped[bool] = mapped_column(Boolean)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )


class AdminAuditEntry(Base):
    __tablename__ = "admin_audit_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    action: Mapped[str] = mapped_column(String(120))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    old_values_json: Mapped[str | None] = mapped_column(Text)
    new_values_json: Mapped[str | None] = mapped_column(Text)


class WebAdminSession(Base):
    __tablename__ = "web_admin_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TechnicalEvent(Base):
    __tablename__ = "technical_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    severity: Mapped[str] = mapped_column(String(20))
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    message: Mapped[str] = mapped_column(Text)
    details_json: Mapped[str | None] = mapped_column(Text)


class ImmutableBookingError(RuntimeError):
    """Raised when application code tries to alter a completed booking."""


@event.listens_for(TapBooking, "before_update", propagate=True)
@event.listens_for(TapBooking, "before_delete", propagate=True)
def prevent_booking_mutation(*_args: object, **_kwargs: object) -> None:
    raise ImmutableBookingError("Completed tap bookings are immutable")
