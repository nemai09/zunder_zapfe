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
| Veranstaltung | `create_event`, `activate_event` | höchstens eine aktive Veranstaltung |
| Benutzer/NFC | `create_user`, `add_nfc_card`, `find_active_user_by_card` | UID kanonisch, Karte und Benutzer aktiv |
| Getränk/Fass | `create_beverage`, `activate_new_keg`, `active_tap_context` | höchstens ein aktives Fass und passender Kontext |
| Buchung | `add_tap_booking`, `list_user_bookings` | Event und Getränk passen zum Fass |
| Summen | `user_consumption`, `remaining_keg_volume_ml` | ausschließlich persistierte Istmengen |
| Einstellungen | `set_setting` | aktiver Admin, Audit im selben Ablauf |
| Audit/Diagnose | `record_admin_action`, `record_technical_event` | JSON-Details kanonisch serialisiert |

## Datentypen und Einheiten

- Identitäten sind ganzzahlige Datenbank-IDs.
- NFC-UIDs sind uppercase Hex ohne Leerzeichen, Doppelpunkte oder Bindestriche.
- Volumen: Milliliter als `int`.
- Preis: Cent pro Liter als `int`.
- Betrag: Cent als `int`, ganzzahlig auf den nächsten Cent gerundet.
- Zeit: timezone-aware UTC in der Anwendung; SQLite speichert den vom Treiber
  unterstützten Zeitwert.
- strukturierte Settings- und Auditwerte: kanonisches JSON als Text.

## Unveränderliche Buchungen

`tap_bookings` sind abgeschlossene historische Fakten. ORM-Events und
SQLite-Trigger verhindern Update und Delete. Eine spätere Korrekturfunktion
muss eine neue Gegenbuchung mit Audit erzeugen; direkte Datenbankkorrekturen
sind kein unterstützter Workflow.

## Schemaänderungen

1. SQLAlchemy-Modell und Repositorybedarf entwerfen.
2. Neue Alembic-Migration hinzufügen; bestehende Migrationen nicht umschreiben.
3. Migration von leerer Datenbank und vom bisherigen Head testen.
4. Integritäts- und Repositorytests ergänzen.
5. Architektur- und Schnittstellendokumentation aktualisieren.
6. Backup-/Rollback-Auswirkung im PR beschreiben.

Der systemd-Dienst führt vor jedem Start `alembic upgrade head` aus und startet
bei einer fehlgeschlagenen Migration nicht mit einem unpassenden Schema.
