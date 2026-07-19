# Integrierten Alpha-Ablauf pruefen

Stand: 2026-07-19

Diese Anleitung prueft NFC-Anmeldung, simulierte Zapfung, SQLite-Buchung,
Abrechnung, Fassbestand und Neustartpersistenz. Die Simulator-API ist
standardmaessig deaktiviert und darf nicht fuer den Normalbetrieb aktiviert
bleiben.

## Windows-Entwicklungsrechner

Virtuelle Umgebung aktualisieren und eine neue lokale Datenbank migrieren:

```powershell
.\.venv\Scripts\python.exe -m pip install --editable ".[dev,debug]"
$env:ZUNDER_ZAPFE_DATABASE_URL = "sqlite:///data/zunder-zapfe-integration.db"
.\.venv\Scripts\alembic.exe -c alembic.ini upgrade head
.\.venv\Scripts\zunder-zapfe-seed-demo.exe
```

Der Seed funktioniert absichtlich nur, solange die fachlichen Kerntabellen leer
sind. Er erzeugt:

- Benutzer `Demo User`, NFC-UID `D00DCAFE`,
- Admin `Demo Admin`, NFC-UID `C0DEC0DE`,
- Veranstaltung `Zunder Demo`,
- Getraenk `Demo Pils` mit 50-Liter-Fass und 450 Cent pro Liter.

Backend mit vollstaendig simulierter Hardware starten:

```powershell
$env:ZUNDER_ZAPFE_SIMULATE_NFC = "1"
$env:ZUNDER_ZAPFE_ENABLE_SIMULATOR_API = "1"
$env:ZUNDER_ZAPFE_PULSES_PER_LITER = "500"
.\.venv\Scripts\zunder-zapfe.exe
```

In einem zweiten PowerShell-Fenster die Karte simuliert auflegen und danach den
vollstaendigen Ablauf ohne manuelle Pause ausloesen. Der Smoke-Test erzeugt eine
echte Buchung in der konfigurierten Alpha-Datenbank:

```powershell
Invoke-RestMethod -Method Post -ContentType "application/json" `
  -Uri "http://127.0.0.1:8000/api/simulator/nfc/present" `
  -Body '{"uid":"D00DCAFE"}'

.\.venv\Scripts\zunder-zapfe-smoke-test.exe
```

Das Werkzeug prueft Sitzung, Zustandswechsel, Buchungszaehler, Menge, Betrag und
Fassbestand. Erwartet werden `Smoke test passed`, 500 ml, 225 Cent und 49.500 ml
rechnerischer Fassbestand.

Nach erfolgreichem Abschluss bleibt der Zustandsautomat acht Sekunden in
`top_up_available`. Ein in diesem Zeitraum erneut gestarteter Smoke-Test wird
bewusst abgelehnt. Fuer wiederholte Laeufe acht Sekunden warten oder ausloggen,
die Karte entfernen und neu auflegen.

## Datenbank im Browser pruefen

Bei laufendem oder gestopptem Backend in einem weiteren Fenster:

```powershell
.\.venv\Scripts\sqlite_web.exe --host 127.0.0.1 --port 8081 --read-only --no-browser --foreign-keys data\zunder-zapfe-integration.db
```

Unter `http://127.0.0.1:8081` muss `tap_bookings` einen vollstaendigen Datensatz
enthalten. `alembic_version`, Benutzer, NFC-Zuordnung, Fass und Getraenk koennen
ebenfalls kontrolliert werden.

## Neustartpersistenz

1. Backend mit `Strg+C` beenden.
2. Backend mit unveraenderter `ZUNDER_ZAPFE_DATABASE_URL` erneut starten.
3. Demo-Karte erneut ueber die Simulatorroute auflegen.
4. `GET /api/consumption/current` und `GET /api/keg/current` wiederholen.

Menge, Betrag und Fassbestand muessen unveraendert erhalten bleiben. Der
Demo-Seed darf nicht erneut ausgefuehrt werden und verweigert dies auch.

## Raspberry Pi mit realem NFC und simuliertem Durchfluss

Auf einer noch leeren Alpha-Datenbank kann die tatsaechliche UID einer Karte
beim manuellen Seed angegeben werden. Der Dienst wird dafuer kurz gestoppt:

```bash
sudo systemctl stop zunder-zapfe-web.service
cd /pfad/zu/zunder_zapfe
export ZUNDER_ZAPFE_DATABASE_URL=sqlite:////var/lib/zunder-zapfe/zunder-zapfe.db
.venv/bin/alembic -c alembic.ini upgrade head
.venv/bin/zunder-zapfe-seed-demo --user-card <ECHTE-UID>
sudo systemctl start zunder-zapfe-web.service
```

Fuer den simulierten Durchfluss wird temporaer
`ZUNDER_ZAPFE_ENABLE_SIMULATOR_API=1` in `/etc/zunder-zapfe/web.env` gesetzt und
der Dienst neu gestartet. Die echte Karte meldet den Demo-Benutzer automatisch
an. Der komplette Test wird danach lokal auf dem Pi ohne Pause zwischen
Zapfstart und simulierten Impulsen ausgefuehrt:

```bash
.venv/bin/zunder-zapfe-smoke-test
```

Nach dem Test muss `ZUNDER_ZAPFE_ENABLE_SIMULATOR_API` wieder auf `0` gesetzt
und der Dienst neu gestartet werden.

## Verriegelten Fehlerzustand zuruecksetzen

Ein Watchdog-, Durchfluss- oder Not-Aus-Fehler bleibt absichtlich verriegelt.
Zum Reset muss die Fehlerursache behoben und eine aktive Admin-Karte auf dem
NFC-Leser liegen. Dann lokal auf dem Zielsystem:

```bash
curl --request POST http://127.0.0.1:8000/api/tap/safety/reset
```

Erwartet wird der Zustand `idle`, ein geschlossenes Ventil und keine aktive
Sitzung. Die Admin-Karte danach entfernen. Fuer die naechste Anmeldung muss die
gewuenschte Karte neu aufgelegt werden. Eine normale Benutzerkarte und eine
deaktivierte oder unbekannte Karte duerfen den Reset nicht ausloesen.
