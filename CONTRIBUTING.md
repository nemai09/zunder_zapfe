# Zu Zunder Zapfe beitragen

Beiträge zu Software, Dokumentation und Hardwareentwürfen sind willkommen.
Das Projekt befindet sich in der Alpha-Phase; klare Schnittstellen und sichere
Fehlerzustände sind wichtiger als Rückwärtskompatibilität um jeden Preis.

## Vor einer Änderung

1. [Anforderungskatalog](requirements/anforderungskatalog.txt),
   [Projektstatus](docs/project-status.md) und relevante Schnittstelle lesen.
2. Bei neuen Funktionen oder Schnittstellenänderungen zunächst ein GitHub-Issue
   anlegen oder die Änderung mit den betroffenen Verantwortlichen abstimmen.
3. Sicherheitsrelevante Änderungen an Ventil, Not-Aus oder Fehlerreset brauchen
   Review von Software- und Hardwareverantwortung.

## Lokale Einrichtung

Python 3.11 oder neuer wird benötigt. Unter Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --editable ".[dev,debug]"
.\.venv\Scripts\python.exe -m pytest
```

Unter Linux beziehungsweise auf dem Raspberry Pi dieselben Befehle mit
`.venv/bin/python` ausführen. Niemals `sudo pip` im Checkout verwenden.

## Git-Workflow

- `main` bleibt funktionsfähig und wird nur über Pull Requests verändert.
- Pro Änderung einen kurzen, thematisch begrenzten Branch verwenden.
- Beispiele: `feature/kiosk-ui`, `fix/nfc-reconnect`, `docs/http-contract`.
- Keine fremden oder lokalen Änderungen verwerfen oder überschreiben.
- Commits beschreiben das Ergebnis und nennen eine Anforderungs-ID, wenn sie
  eindeutig betroffen ist.

Das verwendete Git-Programm ist frei wählbar. Unter Windows eignet sich
SourceTree; Kommandobeispiele in der Dokumentation dienen vor allem dem
Raspberry-Pi-Zielsystem und automatisierten Prüfungen.

## Entwicklungsregeln

- Neue Datenbankfelder oder Constraints benötigen eine Alembic-Migration.
- Hardwareverträge zuerst in Protocol, Statusmodell und Simulator umsetzen.
- WebUI darf weder GPIOs noch SQLite direkt ansprechen.
- Mengen und Geld ausschließlich als ganzzahlige Einheiten verarbeiten.
- Abgeschlossene Zapfbuchungen niemals ändern oder löschen.
- Simulatorrouten müssen standardmäßig deaktiviert bleiben.
- Keine Zugangsdaten, privaten Schlüssel, echten NFC-UIDs, Datenbanken,
  Backups oder Logs committen.

## Dokumentation und Schnittstellen

Schnittstellenänderungen umfassen immer:

1. ausführbaren Vertrag,
2. automatisierten Vertragstest,
3. menschlich lesbare Schnittstellendokumentation,
4. maschinenlesbares Artefakt, sofern vorhanden,
5. Auswirkungen und Migration im PR.

Nach HTTP-Änderungen den OpenAPI-Snapshot aktualisieren:

```bash
python scripts/export_openapi.py
```

## Prüfung vor dem Pull Request

```bash
python -m ruff check src tests scripts
python -m ruff format --check src tests scripts
python -m pytest
```

Auf dem Raspberry Pi zusätzlich, soweit relevant:

```bash
./scripts/pi-verify.sh
```

Der PR beschreibt Ziel, Änderungen, Sicherheitsauswirkungen, durchgeführte
Tests, offene Grenzen und betroffene Anforderungen. Die Checkliste aus der
PR-Vorlage wird nicht ohne Prüfung abgehakt.

## Lizenz der Beiträge

Mit einem Beitrag erklärst du dich damit einverstanden, ihn unter der
[GNU GPL Version 3 oder später](LICENSE) (`GPL-3.0-or-later`) des Projekts zu
veröffentlichen.
