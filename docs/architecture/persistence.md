# Persistenz und Datenmodell

Stand: 2026-07-19

## Ziel

Die Anwendung speichert ihre fachlichen Daten lokal in SQLite. Sie benoetigt
zur Laufzeit weder Netzwerk noch externen Datenbankserver. SQLAlchemy 2 bildet
das Datenmodell ab; Alembic versioniert und installiert Schemaaenderungen.

Betroffen sind insbesondere `ZZ-SYS-003` bis `ZZ-SYS-006`, `ZZ-AUT-001` bis
`ZZ-AUT-008`, `ZZ-KEG-001` bis `ZZ-KEG-004`, `ZZ-BIL-001` bis `ZZ-BIL-004` und
`ZZ-DAT-001` bis `ZZ-DAT-007`.

## Tabellen

- `events` trennt Buchungen verschiedener Veranstaltungen und Jahre.
- `users` speichert Benutzerstatus, Rolle und individuelle Portionsgroesse.
- `nfc_cards` ordnet normalisierte Karten-UIDs aktiven Benutzern zu.
- `beverages` speichert Sorte, Standard-Fassgroesse und Preis pro Liter.
- `kegs` bildet einzelne angestochene Faesser und deren Startmenge ab.
- `tap_bookings` speichert den vollstaendigen historischen Zapfdatensatz.
- `settings` speichert konfigurierbare Betriebsparameter als JSON-Werte.
- `admin_audit_entries` protokolliert alte und neue Werte von Adminaktionen.
- `technical_events` protokolliert Fehler, Sperren und technische Ereignisse.

## Ganzzahlige Einheiten

Geld- und Mengenberechnungen verwenden keine Gleitkommazahlen:

- Volumen werden in Millilitern gespeichert.
- Preise werden als Cent pro Liter gespeichert.
- Betraege werden als Cent gespeichert.
- Rohe Durchflusswerte werden als ganzzahlige Impulsanzahl gespeichert.

Der bei einer Zapfung gueltige Preis und der berechnete Betrag werden in die
Buchung kopiert. Eine spaetere Aenderung des Getraenkepreises veraendert alte
Buchungen deshalb nicht.

## Integritaetsregeln

- SQLite-Fremdschluessel werden fuer jede Verbindung aktiviert.
- Es kann jeweils nur eine aktive Veranstaltung und ein aktives Fass geben.
- Ein neues aktives Fass schliesst das vorherige Fass mit Zeitstempel.
- Buchung, Veranstaltung und Getraenk muessen zum ausgewaehlten Fass passen.
- Kostenfreie Buchungen besitzen den Betrag null.
- Wartungsbuchungen sind nicht kostenpflichtig.
- Abgeschlossene Zapfbuchungen koennen weder geaendert noch geloescht werden.

Die Unveraenderlichkeit wird doppelt durch SQLAlchemy-Ereignisse und durch
SQLite-Trigger abgesichert. Spaetere Korrekturen muessen als neue, separat
protokollierte Gegenbuchungen modelliert werden, falls `OD-006` entschieden ist.

## Betrieb und Migration

Die produktive Datenbank liegt standardmaessig unter
`/var/lib/zunder-zapfe/zunder-zapfe.db`. Der systemd-Dienst fuehrt vor jedem
Backendstart `alembic upgrade head` aus. Schlaegt eine Migration fehl, startet
das Backend nicht mit einem unpassenden Schema.

Lokale Entwicklungsdaten liegen standardmaessig unter `data/` und sind von Git
ausgeschlossen. Tests erzeugen fuer jeden Testfall eine eigene temporaere
Datenbank und wenden darauf die vollstaendige Migrationshistorie an.

Backup, Export, Wiederherstellung und die verbindliche Offline-Zeitbasis bleiben
gemaess `OD-007` beziehungsweise `OD-008` offene Folgeschritte.
