"""Explicit demo data seed for an otherwise empty alpha database."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zunder_zapfe.persistence import create_database_engine, create_session_factory
from zunder_zapfe.persistence.models import Beverage, Event, Keg, NfcCard, User, UserRole
from zunder_zapfe.persistence.repository import Repository


class DemoSeedRefused(RuntimeError):
    """Raised when demo data would mix with an existing data set."""


def seed_demo_data(
    session: Session,
    *,
    year: int | None = None,
    user_card_uid: str = "D00DCAFE",
    admin_card_uid: str = "C0DEC0DE",
) -> dict[str, object]:
    """Create a complete demo tap context, but only in an empty database."""
    populated_tables = [
        model.__tablename__
        for model in (Event, User, NfcCard, Beverage, Keg)
        if session.scalar(select(func.count()).select_from(model))
    ]
    if populated_tables:
        names = ", ".join(populated_tables)
        raise DemoSeedRefused(f"Demo seed requires an empty database; data exists in: {names}")

    repository = Repository(session)
    event_year = year or datetime.now(UTC).year
    event = repository.create_event("Zunder Demo", event_year, active=True)
    user = repository.create_user("Demo", last_name="User")
    user_card = repository.add_nfc_card(user.id, user_card_uid)
    admin = repository.create_user("Demo", last_name="Admin", role=UserRole.ADMIN)
    admin_card = repository.add_nfc_card(admin.id, admin_card_uid)
    beverage = repository.create_beverage(
        "Demo Pils",
        default_keg_size_ml=50_000,
        price_per_liter_cents=450,
    )
    keg = repository.activate_new_keg(
        event_id=event.id,
        beverage_id=beverage.id,
        initial_volume_ml=50_000,
    )
    return {
        "event_id": event.id,
        "user_id": user.id,
        "user_card_uid": user_card.uid,
        "admin_id": admin.id,
        "admin_card_uid": admin_card.uid,
        "beverage_id": beverage.id,
        "keg_id": keg.id,
    }


def run() -> None:
    """Seed the configured database and print the non-secret demo identifiers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, help="Demo event year; defaults to current year")
    parser.add_argument("--user-card", default="D00DCAFE", help="NFC UID for Demo User")
    parser.add_argument("--admin-card", default="C0DEC0DE", help="NFC UID for Demo Admin")
    arguments = parser.parse_args()
    engine = create_database_engine()
    sessions = create_session_factory(engine)
    try:
        with sessions.begin() as session:
            result = seed_demo_data(
                session,
                year=arguments.year,
                user_card_uid=arguments.user_card,
                admin_card_uid=arguments.admin_card,
            )
    finally:
        engine.dispose()

    print("Demo data created.")
    print(f"User NFC UID:  {result['user_card_uid']}")
    print(f"Admin NFC UID: {result['admin_card_uid']}")


if __name__ == "__main__":
    run()
