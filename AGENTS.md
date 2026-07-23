# Agentenleitfaden für Zunder Zapfe

Diese Datei gilt für das gesamte Repository. Sie stellt stabilen Projektkontext
für Entwicklungsagenten bereit. Persönliche Identitäten und lokale
Werkzeugpräferenzen gehören nicht hierher.

## Zuerst lesen

1. `requirements/anforderungskatalog.txt` für das akzeptierte Produktverhalten.
2. `docs/README.md` für Dokumentationsstruktur und Quellen der Wahrheit.
3. `docs/project-status.md`, bevor eine Komponente als implementiert angenommen
   wird.
4. Den relevanten ausführbaren Vertrag, bevor seine Dokumentation geändert
   wird.

## Architekturgrenzen

- Webcode verwendet ausschließlich die lokale HTTP-API und steuert weder
  Hardware noch SQLite direkt.
- Nur `TapController` darf Ventil- und Durchflussvorgänge koordinieren.
- `TapService` verbindet NFC-Identität, Zapfsteuerung, aktiven
  Veranstaltungs-/Fasskontext und Persistenz.
- Der Superadmin ist gemäß CR-003 eine externe, präsenzgebundene
  Wartungsidentität und niemals `User`, `UserRole` oder Webadmin. Sein
  ausführbarer Zielvertrag steht unter `docs/architecture/superadmin.md`.
- Hardwareimplementierungen erfüllen die Protocols unter
  `src/zunder_zapfe/hardware/interfaces.py`.
- Konkrete GPIOs, elektrische Pegel und Bibliotheken bleiben
  Adapterkonfiguration, bis die Hardwareentscheidungen freigegeben sind.
- Die Standardlaufzeit verwendet einen realen ACR122U sowie Simulatoren für
  Ventil, Durchflussmesser und Not-Aus.

## Safety- und Dateninvarianten

- Start, Stopp, Fehler und Shutdown müssen das Ventil geschlossen hinterlassen.
- `ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG=1` ist eine zeitlich begrenzte
  Alpha-Abweichung für Tests ohne Durchflusshardware. Sie darf niemals den
  Steuerungs-Watchdog, Not-Aus oder Zeitlimits deaktivieren und muss vor dem
  Anschluss realer Ventilhardware auf `0` stehen.
- Sicherheitssperren bleiben bis zu einem gültigen Admin-Reset verriegelt. Das
  Wiederherstellen eines Eingangs darf keine Zapfung fortsetzen.
- Volumen werden in Millilitern, Preise in Cent pro Liter und Beträge in Cent
  gespeichert. Gleitkommawerte für Abrechnung sind unzulässig.
- Abgeschlossene Zapfbuchungen sind unveränderlich. Korrekturen benötigen eine
  spätere explizite Fachoperation und dürfen niemals per Update oder Delete
  erfolgen.
- Schemaänderungen benötigen eine Alembic-Migration. Eine ausgelieferte
  SQLite-Datenbank darf nicht als Anwendungsworkflow manuell bearbeitet werden.
- Die Anwendung bleibt offlinefähig und standardmäßig an Loopback gebunden.

## Geheimnisse und lokale Daten

Zugangsdaten, private Schlüssel, Umgebungsdateien, reale NFC-UIDs,
Datenbankdateien, Backups und Logs dürfen niemals committed werden.
`config/web.env.example` und eindeutig erkennbare Demo-IDs dienen als Vorlagen.
Die lokale Datei `superadmin.credential` und ihr Inhalt gelten ebenfalls als
Geheimnis und dürfen weder ausgegeben noch committed werden.
Persönliche Agentennamen, E-Mail-Adressen und Commitidentitäten gehören nicht
in Repository-Anweisungen.

## Entwicklungsbefehle

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install --editable ".[dev,debug]"
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m pytest
```

Raspberry Pi/Linux:

```bash
.venv/bin/python -m pip install --editable '.[dev,debug]'
.venv/bin/python -m ruff check src tests scripts
.venv/bin/python -m ruff format --check src tests scripts
.venv/bin/python -m pytest
```

Im Checkout darf niemals `sudo pip` verwendet werden. Der Pi-Installer führt
die lokale Python-Installation als Besitzer des Repositorys aus.

## Änderungsregeln

- Auf einem kurzen Branch arbeiten; `main` wird ausschließlich per Pull
  Request verändert.
- Alle Commit-Nachrichten folgen verbindlich
  [`docs/commit-konvention.md`](docs/commit-konvention.md).
- Anforderungs-IDs erhalten und bei relevanten Änderungen in Tests, Commit-Text
  oder PR nennen.
- Schnittstellenänderungen aktualisieren Implementierung, Tests,
  menschenlesbaren Vertrag und generiertes Artefakt im selben PR.
- Nach HTTP-Änderungen `docs/interfaces/openapi.json` mit
  `python scripts/export_openapi.py` regenerieren.
- Persistenzänderungen benötigen Migration und Migrationstest.
- Hardwareverträge zuerst in Simulatoren implementieren, bevor reale Adapter
  ergänzt werden.
- Simulatorrouten bleiben standardmäßig deaktiviert und klar gekennzeichnet.
- Projektdokumentation und Commit-Nachrichten werden auf Deutsch gepflegt.

## Definition of Done

- Relevante Anforderungen und offene Entscheidungen sind identifiziert.
- Safety-Invarianten und Architekturgrenzen bleiben erhalten.
- Tests, Ruff und Dokumentationsprüfungen bestehen.
- Menschen- und maschinenlesbare Schnittstellen stimmen überein.
- Betriebsdokumentation beschreibt die Auswirkungen auf das Zielsystem.
- Der Diff enthält keine Geheimnisse, persönlichen Laufzeitdaten oder
  generierten Datenbanken.
