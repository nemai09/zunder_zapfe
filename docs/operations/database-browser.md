# SQLite-Datenbank im Browser untersuchen

Stand: 2026-07-19

## Zweck

Fuer die Diagnose verwenden wir das bestehende Werkzeug
[`sqlite-web`](https://github.com/coleifer/sqlite-web). Es zeigt Tabellen,
Spalten, Indizes, Trigger und Datensaetze im Browser und erlaubt SQL-Abfragen.
Es ist kein Bestandteil der Zunder-Zapfe-WebUI und laeuft nicht als dauerhafter
Dienst.

Der Datenbankbrowser wird immer mit `--read-only` gestartet. Schreibzugriffe
ueber ein allgemeines Datenbankwerkzeug wuerden Fachregeln, Admin-Audit und die
Unveraenderlichkeit abgeschlossener Zapfbuchungen umgehen.

## Lokale Entwicklungsdatenbank unter Windows

Die Debug-Abhaengigkeiten werden einmalig in der virtuellen Umgebung
installiert:

```powershell
.\.venv\Scripts\python.exe -m pip install --editable ".[dev,debug]"
```

Danach Schema erzeugen und den Browser starten:

```powershell
$env:ZUNDER_ZAPFE_DATABASE_URL = "sqlite:///data/zunder-zapfe.db"
.\.venv\Scripts\alembic.exe -c alembic.ini upgrade head
.\.venv\Scripts\sqlite_web.exe --host 127.0.0.1 --port 8081 --read-only --no-browser --foreign-keys data\zunder-zapfe.db
```

Die Oberflaeche ist anschliessend unter
[`http://127.0.0.1:8081`](http://127.0.0.1:8081) erreichbar. `Strg+C` beendet
den Datenbankbrowser. Die Datei unter `data/` ist von Git ausgeschlossen.

## Produktivdatenbank auf dem Raspberry Pi

`install-pi.sh` installiert die Debug-Abhaengigkeit, startet sie aber nicht.
Auf dem Raspberry Pi wird sie bei Bedarf manuell und nur auf der
Loopback-Adresse gestartet:

```bash
cd /pfad/zu/zunder_zapfe
.venv/bin/sqlite_web \
  --host 127.0.0.1 \
  --port 8081 \
  --read-only \
  --no-browser \
  --foreign-keys \
  /var/lib/zunder-zapfe/zunder-zapfe.db
```

Die Oberflaeche kann dann direkt auf dem Pi unter `http://127.0.0.1:8081`
geoeffnet werden. Fuer den Zugriff von einem anderen Rechner ist ein
SSH-Tunnel auf Port 8081 vorgesehen; `sqlite-web` selbst bleibt dabei an
`127.0.0.1` gebunden.

## Was sich am aktuellen Checkpoint pruefen laesst

- alle angelegten Tabellen und deren Spalten,
- die Eindeutigkeitsindizes fuer aktive Veranstaltung und aktives Fass,
- die Trigger gegen Aendern oder Loeschen von Zapfbuchungen,
- Fremdschluessel zwischen Benutzern, NFC-Karten, Getraenken, Faessern und
  Buchungen,
- die vom Backend erzeugten Datensaetze und berechneten Betraege,
- die aktuell installierte Migration in `alembic_version`.

Fachliche Demo-Daten koennen mit `zunder-zapfe-seed-demo` ausschliesslich in
einer leeren Alpha-Datenbank angelegt werden. Der Smoke-Test erzeugt danach
vollstaendige Zapfbuchungen ueber den regulaeren Backendablauf.

## Sicherheitsregeln

- `--read-only` niemals entfernen.
- Den Browser nicht als systemd-Dienst einrichten.
- Nicht an `0.0.0.0` binden und keinen Router-Port freigeben.
- Die Datenbankdatei nicht herunterladen oder in Git ablegen; sie enthaelt
  spaeter personenbezogene Nutzungs- und Abrechnungsdaten.
- Nach der Diagnose den Prozess mit `Strg+C` beenden.
