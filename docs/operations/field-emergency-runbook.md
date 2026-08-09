# Offline-Notfallhandbuch für den Feldbetrieb

Dieses Dokument ist für den beaufsichtigten Beta-Feldeinsatz bestimmt, wenn
kein Entwicklungszugang und kein Codex verfügbar sind. Es beschreibt nur
reversible Betriebsmaßnahmen. Buchungen, Datenbank und Git-Historie werden
nicht manuell verändert.

Traceability: `ZZ-NFR-001`, `ZZ-SAF-004`, `ZZ-SAF-005`, `ZZ-SAF-007`,
`ZZ-SAF-008`, `ZZ-SAF-009`, `ZZ-DAT-008` und `ZZ-TIM-001`.

## Sofortregeln

1. Bei unkontrolliertem Durchfluss Touch loslassen und die Ventilversorgung
   beziehungsweise die gesamte Anlage abschalten. Nicht weiterzapfen.
2. Vor Diagnose sicherstellen, dass das Ventil geschlossen ist. Neustarts,
   Konfigurationsänderungen und Kabelarbeiten erfolgen nie während einer
   Zapfung.
3. Immer nur eine Stellschraube ändern, alten Wert und Uhrzeit notieren und
   anschließend eine beaufsichtigte Testzapfung durchführen.
4. Datenbankdateien, Backups und `status.json` niemals bearbeiten oder löschen.
5. Auf realer Hardware niemals NFC-, Zapfhardware- oder Simulator-API aktivieren.
6. Ein Safety-Reset ist erst zulässig, nachdem die angezeigte Ursache behoben
   wurde. Wiederholte Verriegelung bedeutet Betriebsstopp.

## Schnellprüfung

Im Repository ausführen:

```bash
cd ~/sw/zunder_zapfe
git status --short --branch
git rev-parse --short HEAD
systemctl status zunder-zapfe-web.service --no-pager -l
curl --silent --show-error http://127.0.0.1:8000/api/health | python3 -m json.tool
curl --silent --show-error http://127.0.0.1:8000/api/hardware/status | python3 -m json.tool
sudo journalctl -u zunder-zapfe-web.service -n 100 --no-pager -l
df -h / /var/lib/zunder-zapfe
```

Die produktive Laufzeitkonfiguration liegt ausschließlich unter
`/etc/zunder-zapfe/web.env`. Vor einer Änderung eine lokale Kopie anlegen:

```bash
sudo cp -a /etc/zunder-zapfe/web.env \
  "/etc/zunder-zapfe/web.env.notfall-$(date +%Y%m%d-%H%M%S)"
sudoedit /etc/zunder-zapfe/web.env
sudo systemctl restart zunder-zapfe-web.service
```

Nach dem Neustart müssen Health-Endpunkt und Dienststatus wieder erfolgreich
sein. Eine ungültige Konfiguration verhindert den Webdienststart; sie darf nie
durch Aktivieren eines Simulators umgangen werden.

## Ventil schließt nicht

1. Touch sofort loslassen.
2. Ventilversorgung oder gesamte Anlage abschalten.
3. Erst im stromlosen Zustand Treiberstufe und Verdrahtung prüfen lassen.
4. Betrieb nicht durch längere Timeouts oder deaktivierte Watchdogs fortsetzen.

Der geschützte Diagnosebereich zeigt nur den angeforderten GPIO-Zustand, keine
Rückmeldung des realen Ventils. Ein elektrisch klemmendes Ventil ist nicht per
Software behebbar. Da im Beta-Aufbau kein realer Not-Aus-Adapter vorhanden ist,
muss eine erreichbare Abschaltmöglichkeit gewährleistet sein.

## Verriegelung wegen fehlender Durchflussimpulse

Zuerst Stecker, Versorgung, Signalpegel und BCM27 prüfen. Das Journal zeigt den
Grund der Verriegelung:

```bash
sudo journalctl -u zunder-zapfe-web.service -n 100 --no-pager -l
```

Die normalen Feldwerte sind:

```text
ZUNDER_ZAPFE_FIRST_PULSE_TIMEOUT_SECONDS=5
ZUNDER_ZAPFE_BETWEEN_PULSES_TIMEOUT_SECONDS=3
ZUNDER_ZAPFE_CONTROLLER_WATCHDOG_TIMEOUT_SECONDS=5
ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG=0
ZUNDER_ZAPFE_MANUAL_MAXIMUM_POUR_SECONDS=30
```

Auf realer Hardware gelten außerdem unverändert:

```text
ZUNDER_ZAPFE_SIMULATE_NFC=0
ZUNDER_ZAPFE_SIMULATE_TAP_HARDWARE=0
ZUNDER_ZAPFE_ENABLE_SIMULATOR_API=0
ZUNDER_ZAPFE_VALVE_GPIO=17
ZUNDER_ZAPFE_FLOW_GPIO=27
```

Bei nachgewiesenem, aber lediglich verzögertem oder lückenhaftem Signal dürfen
die ersten beiden Zeitwerte in kleinen Schritten erhöht werden. Der
Steuerungs-Watchdog bleibt aktiv. Die maximale manuelle Zapfdauer darf nicht
erhöht werden, um einen Sensorfehler zu verdecken.

### Beaufsichtigter Notbetrieb ohne Durchfluss-Watchdog

Nur wenn das Ventil beim Loslassen nachweislich zuverlässig schließt, die
Anlage dauerhaft von einer Person beaufsichtigt wird und der Ausschank sonst
nicht fortgesetzt werden kann, darf vorübergehend gesetzt werden:

```text
ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG=1
```

Danach:

```bash
sudo systemctl restart zunder-zapfe-web.service
```

Wirkung und Restrisiko:

- Prüfung auf ersten Impuls und Impulspausen ist deaktiviert.
- Steuerungs-Watchdog, Loslassen und maximale manuelle Zapfdauer bleiben aktiv.
- Ein offenes Ventil ohne Messimpulse wird nicht mehr durch den
  Durchfluss-Watchdog erkannt; nicht gemessene Mengen fehlen in Abrechnung und
  Fassbestand.
- Die maximale manuelle Zapfdauer bleibt bei höchstens dem zuvor geprüften
  Feldwert. Sie wird im Notbetrieb nicht gleichzeitig erhöht.

Vor der Freigabe einmal unter direkter Aufsicht testen, dass Loslassen das
Ventil unverzüglich schließt. Nach Reparatur des Sensors sofort auf `0`
zurückstellen, Webdienst neu starten und den normalen Fehlerfall erneut prüfen.

## Menge offensichtlich falsch

Die primäre Stellschraube ist:

```text
ZUNDER_ZAPFE_PULSES_PER_LITER=<Kalibrierwert>
```

Ein größerer Wert reduziert die aus denselben Impulsen berechnete Menge, ein
kleinerer Wert erhöht sie. Nicht nach Gefühl korrigieren. Mindestens drei
Zapfungen mit bekannter Menge durchführen und den Wert als
`Impulse / bekannte Liter` bestimmen. Danach Webdienst neu starten und eine
weitere Kontrollmenge prüfen. Bereits gespeicherte Buchungen werden nicht
nachträglich verändert.

## NFC-Karte wird nicht erkannt

```bash
systemctl status pcscd --no-pager -l
pcsc_scan
```

`pcsc_scan` mit `Ctrl+C` beenden. Leser einmal abziehen und wieder verbinden.
Falls er weiterhin fehlt und das Ventil geschlossen ist:

```bash
sudo systemctl restart pcscd.service
sudo systemctl restart zunder-zapfe-web.service
```

Unbekannte oder gesperrte Karten werden absichtlich nicht angemeldet. Zuerst in
der Admin-WebUI Benutzer-, Karten- und Aktivstatus kontrollieren.

## Webdienst oder Kiosk ausgefallen

```bash
systemctl status zunder-zapfe-web.service --no-pager -l
sudo journalctl -u zunder-zapfe-web.service -n 100 --no-pager -l
sudo systemctl restart zunder-zapfe-web.service
curl --fail http://127.0.0.1:8000/api/health
```

Chromium wird vom Kioskstarter nach einem Absturz automatisch neu gestartet.
Bleibt der Desktop sichtbar, darf der Raspberry Pi bei geschlossenem Ventil
geordnet neu gestartet werden. Kein hartes Ausschalten während eines
Schreibvorgangs oder einer Zapfung.

Nur für eine kurze HTTP-Diagnose kann `ZUNDER_ZAPFE_ACCESS_LOG=1` gesetzt und
der Webdienst neu gestartet werden. Danach die relevanten Journalzeilen sichern
und den Wert wieder auf `0` setzen; andernfalls erzeugt das Kiosk-Polling
unnötige Dauerlast und viele Logeinträge.

## Smartphone-Administration oder WLAN nicht erreichbar

Zuerst das lokale blaue Systemmenü verwenden. Alternativ am Raspberry Pi:

```bash
sudo zunder-zapfe-wifi-mode status
sudo zunder-zapfe-wifi-mode ap
```

Der Wechsel in den AP-Modus kann eine bestehende SSH- oder WLAN-Verbindung
sofort trennen und wird deshalb möglichst direkt am Touchdisplay oder mit
Tastatur ausgeführt. Danach Smartphone erneut mit `ZUNDER_ZAPFE` verbinden.

## Sicherung fehlt oder ist überfällig

```bash
systemctl list-timers --all zunder-zapfe-backup.timer
systemctl status zunder-zapfe-backup.service --no-pager -l
sudo journalctl -u zunder-zapfe-backup.service -n 50 --no-pager -l
grep '^ZUNDER_ZAPFE_BACKUP_DIR=' /etc/zunder-zapfe/web.env
sudo systemctl start zunder-zapfe-backup.service
sudo cat /var/lib/zunder-zapfe/backups/status.json
```

Der Verzeichniswert muss `/var/lib/zunder-zapfe/backups` sein. Ein erfolgreicher
Dienstlauf mit weiterhin leerer WebUI deutet auf einen fehlenden oder anderen
Wert im Webdienst hin; anschließend Webdienst neu starten. Mindestens einmal
täglich das CSV-Paket auf ein Smartphone herunterladen.

## Uhrzeit falsch

```bash
date --iso-8601=seconds
sudo zunder-zapfe-rtc status
```

Mit falscher Zeit nicht weiterbuchen. Webdienst bei geschlossenem Ventil
stoppen, Systemzeit anhand einer zuverlässigen externen Uhr korrigieren, RTC
erneut aus der geprüften Systemzeit setzen und den Dienst wieder starten:

```bash
sudo systemctl stop zunder-zapfe-web.service
sudo timedatectl set-ntp false
sudo timedatectl set-time 'YYYY-MM-DD HH:MM:SS'
sudo zunder-zapfe-rtc set
sudo timedatectl set-ntp true
sudo systemctl start zunder-zapfe-web.service
```

Danach System- und RTC-Zeit erneut vergleichen. `YYYY-MM-DD HH:MM:SS` ist durch
die tatsächlich geprüfte lokale Zeit zu ersetzen.

## Datenbank-, Speicher- oder Buchungsfehler

```bash
df -h / /var/lib/zunder-zapfe
sudo journalctl -u zunder-zapfe-web.service -n 100 --no-pager -l
sudo systemctl start zunder-zapfe-backup.service
```

Bei vollem Datenträger, SQLite-Fehlern oder wiederholtem
`booking.persistence_failed` den Ausschank stoppen. Datenbank nicht mit
`sqlite3`, Dateikopien oder Git-Befehlen reparieren. Zuerst vorhandenes
CSV-Paket extern sichern und technische Unterstützung organisieren.

## Was im Feld nicht geändert wird

- `ZUNDER_ZAPFE_DATABASE_URL`, GPIO-Nummern, Host und Port
- Simulatorflags und Simulator-API
- Git-Branch, Migrationen oder historische Commits
- Datenbank-, Backup- und Protokolldateien
- Preise, Veranstaltung oder Fass während einer laufenden Zapfung

Softwareupdates erfolgen nur bei betriebsverhindernden Fehlern mit sauberem
Checkout über `deploy-update.sh`. Kein `git reset`, kein erzwungener Checkout
und kein manueller Rollback. Vor jedem Update aktuelles CSV-Paket extern
sichern und die Commit-ID notieren.

## Rückkehr zum Normalbetrieb

1. Alle Notfallwerte auf die dokumentierten Feldwerte zurückstellen.
2. `ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG=0` bestätigen.
3. Webdienst neu starten und Health-, Hardware- und Bereitschaftsstatus prüfen.
4. Kontrollzapfung und Durchflussfehler mit anschließendem Admin-Reset testen.
5. Manuelles Backup starten und CSV-Paket auf ein Smartphone herunterladen.
6. Ursache, Uhrzeit, alte und neue Werte sowie betroffene Buchungen notieren.
