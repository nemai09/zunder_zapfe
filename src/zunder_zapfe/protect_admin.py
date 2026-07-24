"""Protect one active admin account against basic application-level lockout."""

from __future__ import annotations

import argparse

from zunder_zapfe.persistence import create_database_engine, create_session_factory
from zunder_zapfe.persistence.repository import Repository


def protect_admin(user_id: int) -> str:
    engine = create_database_engine()
    sessions = create_session_factory(engine)
    try:
        with sessions.begin() as session:
            admin = Repository(session).protect_admin_account(user_id)
            return admin.display_name
    finally:
        engine.dispose()


def run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user-id",
        type=int,
        required=True,
        help="ID des aktiven Admins, der dauerhaft gegen Fehlbedienung geschützt wird",
    )
    arguments = parser.parse_args()

    try:
        display_name = protect_admin(arguments.user_id)
    except (LookupError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(f"Admin dauerhaft gegen Fehlbedienung geschützt: {display_name}")


if __name__ == "__main__":
    run()
