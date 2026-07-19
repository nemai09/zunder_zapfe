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

In einem zweiten PowerShell-Fenster den Ablauf ausloesen:

```powershell
Invoke-RestMethod -Method Post -ContentType "application/json" `
  -Uri "http://127.0.0.1:8000/api/simulator/nfc/present" `
  -Body '{"uid":"D00DCAFE"}'

Invoke-RestMethod -Method Post -ContentType "application/json" `
  -Uri "http://127.0.0.1:8000/api/tap/portion" `
  -Body '{"target_volume_ml":500}'

Invoke-RestMethod -Method Post -ContentType "application/json" `
  -Uri "http://127.0.0.1:8000/api/simulator/flow/pulses" `
  -Body '{"count":250}'

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/consumption/current"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/keg/current"
```

Erwartet werden 500 ml, 225 Cent und 49.500 ml rechnerischer Fassbestand.

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
an. Portion und Impulse koennen lokal auf dem Pi ausgeloest werden:

```bash
curl --request POST --header 'Content-Type: application/json' \
  --data '{"target_volume_ml":500}' \
  http://127.0.0.1:8000/api/tap/portion

curl --request POST --header 'Content-Type: application/json' \
  --data '{"count":250}' \
  http://127.0.0.1:8000/api/simulator/flow/pulses
```

Nach dem Test muss `ZUNDER_ZAPFE_ENABLE_SIMULATOR_API` wieder auf `0` gesetzt
und der Dienst neu gestartet werden.
