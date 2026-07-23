"""Set an admin web password locally without exposing it in shell history."""

from __future__ import annotations

import argparse
import getpass

from zunder_zapfe.backend.web_auth_service import WebAuthService
from zunder_zapfe.persistence import create_database_engine, create_session_factory
from zunder_zapfe.persistence.models import UserRole
from zunder_zapfe.persistence.repository import Repository


def run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user-id",
        type=int,
        help="ID eines aktiven Admins; ohne Angabe erfolgt eine interaktive Auswahl",
    )
    arguments = parser.parse_args()

    engine = create_database_engine()
    sessions = create_session_factory(engine)
    try:
        with sessions() as session:
            admins = [
                user
                for user in Repository(session).list_users()
                if user.active and user.role is UserRole.ADMIN
            ]
        if not admins:
            raise SystemExit("Kein aktiver Admin in der Datenbank vorhanden.")

        user_id = arguments.user_id
        if user_id is None:
            print("Aktive Admins:")
            for admin in admins:
                print(f"  {admin.id}: {admin.display_name}")
            try:
                user_id = int(input("Admin-ID: ").strip())
            except ValueError as error:
                raise SystemExit("Die Admin-ID muss eine ganze Zahl sein.") from error
        if user_id not in {admin.id for admin in admins}:
            raise SystemExit("Die gewählte ID gehört nicht zu einem aktiven Admin.")

        password = getpass.getpass("Neues Admin-Webpasswort: ")
        confirmation = getpass.getpass("Passwort wiederholen: ")
        if password != confirmation:
            raise SystemExit("Die Passwörter stimmen nicht überein.")

        WebAuthService(sessions).set_initial_password(user_id=user_id, password=password)
        print("Admin-Webpasswort wurde gesetzt; bestehende Websitzungen sind beendet.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    run()
