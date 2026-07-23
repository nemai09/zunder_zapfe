# Vertrag zwischen Fachlogik und Persistenz

Verbindlicher Code:

- Schema: [`migrations/`](../../migrations)
- Modelle: [`models.py`](../../src/zunder_zapfe/persistence/models.py)
- Operationen: [`repository.py`](../../src/zunder_zapfe/persistence/repository.py)

## Transaktionsgrenze

Der Aufrufer erzeugt und besitzt die SQLAlchemy-`Session`. `Repository` führt
keine versteckten Commits aus. Fachlich zusammengehörige Änderungen werden mit
`sessions.begin()` atomar ausgeführt; Fehler rollen die Transaktion zurück.

## Öffentliche Repository-Operationen

| Bereich | Operation | Wesentliche Bedingung |
| --- | --- | --- |
| Veranstaltung | `create_event`, `get_event`, `list_events`, `update_event`, `activate_event` | Name/Jahr eindeutig, höchstens eine aktive Veranstaltung |
| Benutzer/NFC | `create_user`, `get_user`, `list_users`, `list_web_admins`, `update_user`, `soft_delete_user`, `add_nfc_card`, `list_nfc_cards`, `set_nfc_card_active`, `delete_nfc_card`, `find_active_user_by_card` | Vorname erforderlich; UID kanonisch, eindeutig und nur bei aktiver Karte/Benutzer anmeldbar |
| Websitzung | `find_web_admin_session`, `revoke_web_admin_sessions` | nur Token-Hash persistent; Widerruf bei Passwort- oder Rollenänderung |
| Getränk/Fass | `create_beverage`, `get_beverage`, `list_beverages`, `update_beverage`, `activate_new_keg`, `close_active_keg`, `get_keg`, `list_kegs`, `active_event`, `active_tap_context` | positive Mengen/Preise, höchstens ein aktives Fass und passender Kontext |
| Buchung | `add_tap_booking`, `list_user_bookings`, `list_tap_bookings` | Event und Getränk passen zum Fass; lesende Filter nach Event, Benutzer, Fass, Zeitraum, Art und Abschluss |
| Summen | `user_consumption`, `remaining_keg_volume_ml` | ausschließlich persistierte Istmengen |
| Einstellungen | `get_setting`, `set_setting` | aktiver Admin bei Änderung, Audit im selben Ablauf |
| Audit/Diagnose | `record_admin_action`, `record_superadmin_action`, `list_admin_audit_entries`, `record_technical_event`, `list_technical_events` | normaler Admin mit Benutzer-ID oder technischer Akteur `superadmin` ohne Benutzer-ID; JSON-Details kanonisch serialisiert |

## Datentypen und Einheiten

- Identitäten sind ganzzahlige Datenbank-IDs. `users.id` verwendet unter
  SQLite `AUTOINCREMENT`; eine einmal vergebene Benutzer-ID wird auch nach
  einem versehentlichen physischen Entfernen der Zeile nicht wiederverwendet.
- NFC-UIDs sind uppercase Hex ohne Leerzeichen, Doppelpunkte oder Bindestriche.
- `delete_nfc_card` entfernt nur die Zuordnung; Schutzregeln und Audit liegen im
  aufrufenden `AdminService`. Danach kann dieselbe UID neu zugeordnet werden.
- Benutzer besitzen einen verpflichtenden `first_name`, optionalen `last_name`
  und optionalen `note`; `display_name` wird daraus für bestehende Clients
  abgeleitet.
- Benutzer werden fachlich über `users.deleted_at` gelöscht. Der Datensatz und
  damit alle Buchungs-, Audit- und Protokollreferenzen bleiben erhalten;
  Armbandzuordnungen werden entfernt, Websitzungen widerrufen und der Benutzer
  aus normalen Verwaltungsabfragen ausgeschlossen.
- `users.password_hash` bleibt für normale Benutzer `NULL`. Adminpasswörter
  werden ausschließlich als individuell gesalzene Argon2id-Hashes gespeichert.
- `web_admin_sessions` speichert SHA-256-Hashes zufälliger Sitzungs- und
  CSRF-Token sowie Inaktivitäts-, Absolut- und Widerrufszeit.
- Volumen: Milliliter als `int`.
- Preis: Cent pro Liter als `int`.
- Betrag: Cent als `int`, ganzzahlig auf den nächsten Cent gerundet.
- NFC-Anmeldesitzung: zufällige, nicht vertrauliche Kennung mit höchstens
  64 Zeichen in `tap_bookings.login_session_id`; ausschließlich
  Superadmin-Wartungsentnahmen verwenden `NULL`.
- Zeit: timezone-aware UTC in der Anwendung; SQLite speichert den vom Treiber
  unterstützten Zeitwert.
- strukturierte Settings- und Auditwerte: kanonisches JSON als Text.

Die Buchungsart `manual` kennzeichnet eine kostenpflichtige, durch Loslassen
oder Zeitlimit beendete Push-to-Fill-Zapfung. Ihre `target_volume_ml` ist `NULL`;
Abrechnung und Fassbestand beruhen weiterhin ausschließlich auf der Istmenge.

## Unveränderliche Buchungen

`tap_bookings` sind abgeschlossene historische Fakten. ORM-Events und
SQLite-Trigger verhindern Update und Delete. Eine spätere Korrekturfunktion
muss eine neue Gegenbuchung mit Audit erzeugen; direkte Datenbankkorrekturen
sind kein unterstützter Workflow.

Jede physische Ventilfreigabe bleibt ein eigener Rohdatensatz. Alle
Rohdatensätze zwischen NFC-Anmeldung und Logout tragen dieselbe
`login_session_id`. Fachliche Buchungslisten und Buchungszähler gruppieren
diese Datensätze zu einer Anmeldebuchung und summieren Menge, Impulse und
Betrag. Fassbestand und Diagnose verwenden weiterhin die vollständigen
Rohdatensätze. Die Migration `e18c4f45a501` weist jedem historischen Datensatz
eine eigene `legacy-<id>`-Sitzung zu, sodass vorhandene Buchungen nicht
nachträglich zusammengelegt werden.

Die Migration `f6b942d7183c` erlaubt `user_id=NULL` und
`login_session_id=NULL` nur gemeinsam für `kind=maintenance` und
`chargeable=false`. Dieselbe Migration kennzeichnet bestehende Auditzeilen als
`user_admin` und ermöglicht neue `superadmin`-Einträge ohne Benutzerreferenz.

## Schemaänderungen

1. SQLAlchemy-Modell und Repositorybedarf entwerfen.
2. Neue Alembic-Migration hinzufügen; bestehende Migrationen nicht umschreiben.
3. Migration von leerer Datenbank und vom bisherigen Head testen.
4. Integritäts- und Repositorytests ergänzen.
5. Architektur- und Schnittstellendokumentation aktualisieren.
6. Backup-/Rollback-Auswirkung im PR beschreiben.

Der systemd-Dienst führt vor jedem Start `alembic upgrade head` aus und startet
bei einer fehlgeschlagenen Migration nicht mit einem unpassenden Schema.
