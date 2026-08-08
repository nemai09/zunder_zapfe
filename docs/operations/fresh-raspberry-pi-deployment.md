# Erstinstallation eines Raspberry Pi aus Git

Status: Alpha-Betriebsanleitung für einen neuen Raspberry Pi 4B

Diese Anleitung beschreibt die erstmalige Installation auf einem Raspberry Pi,
auf dem außer Raspberry Pi OS Desktop und einer Internetverbindung noch keine
Zunder-Zapfe-Komponenten vorhanden sind. Sie trennt bewusst die Vorbereitung
des Betriebssystems, den privaten Git-Zugriff, die Installation, die noch
manuelle Alpha-Dateninitialisierung und die Zielsystemprüfung.

## Kurzantwort

`scripts/install-pi.sh` ist für die Erstinstallation geeignet, übernimmt aber
nicht den gesamten Greenfield-Ablauf. Vor seinem Aufruf müssen bereits
vorhanden sein:

- Raspberry Pi OS 64 Bit mit Desktop;
- ein normaler Desktop-Benutzer mit automatischer grafischer Anmeldung;
- Internetzugang für APT- und Python-Pakete;
- Git und ein Checkout des gewünschten Branches;
- bei dem privaten Repository ein GitHub-Zugang des Pi.

Das Skript legt keinen Linux-Benutzer an, klont Git nicht, aktiviert das
Admin-WLAN nicht und erzeugt keine fachlichen Benutzer, NFC-Zuordnungen oder
Veranstaltungsdaten.

Ein bestimmter Benutzername ist technisch nicht vorgeschrieben. Für ein
einheitliches Zielsystem wird `zapfe` empfohlen. Derselbe Benutzer:

- meldet sich automatisch am Desktop an;
- besitzt den Git-Checkout;
- führt den Kiosk aus;
- führt den systemd-Webdienst aus;
- erhält durch das Installationsskript Zugriff auf die GPIO-Gruppe.

Nicht als `root` klonen und im Checkout niemals `sudo pip` verwenden.

## 1. Vor dem Deployment vorbereiten

Benötigt werden:

- Raspberry Pi 4B mit Netzteil und Touchdisplay;
- aktuelle Raspberry Pi OS 64-Bit-Desktop-Installation mit labwc;
- Tastatur oder SSH-Zugang für die Einrichtung;
- vorübergehender Internetzugang;
- ACR122U-NFC-Leser für die vollständige Verifikation;
- DS3231-Modul mit geeigneter Stützbatterie für die Offline-Zeitbasis;
- mindestens ein NFC-Armband für den initialen Admin;
- GitHub-Adminzugriff, um einen read-only Deploy-Key einzutragen;
- gewünschter Deployment-Branch oder freigegebener Commit;
- später ein eigener WPA-Schlüssel für `ZUNDER_ZAPFE`.

Während der Softwareinstallation dürfen ein echtes Ventil und nicht
elektrisch abgenommene Sensorleitungen nicht angeschlossen sein. Für den
ESP-HIL-Aufbau gilt zusätzlich
[`gpio-hil-test.md`](gpio-hil-test.md).

Vorab entscheiden:

```text
Linux-Benutzer: zapfe
Checkout:        /home/zapfe/sw/zunder_zapfe
Branch:          main
```

Für den aktuellen M8-Prüfstand kann statt `main` gezielt
`codex/m8-esp-hil` verwendet werden. Ein dauerhaftes Zielsystem sollte später
einen freigegebenen Stand aus `main` verwenden.

## 2. Desktop-Benutzer und Betriebssystem

Am einfachsten wird der Benutzer `zapfe` bereits mit Raspberry Pi Imager
angelegt. Er benötigt:

- ein eigenes Linux-Passwort;
- automatische grafische Desktop-Anmeldung;
- `sudo`-Berechtigung;
- passende Sprache, Zeitzone und WLAN-Land;
- optional aktiviertes SSH.

Ist bereits ein anderer normaler Desktop-Benutzer mit automatischer Anmeldung
vorhanden, kann dieser verwendet werden. Dann in allen Beispielen `zapfe` und
`/home/zapfe` entsprechend ersetzen. Ein zusätzlicher spezieller Service-User
ist für den aktuellen Installer nicht erforderlich.

Nach dem ersten Start prüfen:

```bash
whoami
echo "$HOME"
sudo -v
```

Die Ausgabe von `whoami` muss den vorgesehenen Desktop-Benutzer zeigen und
`$HOME` auf dessen Home-Verzeichnis verweisen.

Falls automatische Desktop-Anmeldung noch nicht aktiv ist:

```bash
sudo raspi-config
```

Dort die Desktop-Autologin-Option aktivieren und anschließend neu starten.

## 3. Git und privaten GitHub-Zugriff einrichten

Als Desktop-Benutzer:

```bash
sudo apt update
sudo apt install --yes git openssh-client
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keygen -t ed25519 \
  -C "zunder-zapfe-raspberry-pi" \
  -f ~/.ssh/zunder_zapfe_deploy
cat ~/.ssh/zunder_zapfe_deploy.pub
```

Den ausgegebenen öffentlichen Schlüssel im privaten GitHub-Repository unter
**Settings → Deploy keys → Add deploy key** hinterlegen. **Allow write
access** bleibt deaktiviert. Der private Schlüssel bleibt ausschließlich auf
diesem Raspberry Pi.

Lokalen SSH-Alias anlegen:

```bash
cat >>~/.ssh/config <<'EOF'
Host github-zunder-zapfe
    HostName github.com
    User git
    IdentityFile ~/.ssh/zunder_zapfe_deploy
    IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
ssh -T git@github-zunder-zapfe
```

Beim ersten Kontakt den angezeigten GitHub-Host-Key prüfen. GitHub meldet bei
erfolgreicher Anmeldung, dass kein Shell-Zugriff angeboten wird; das ist
normal.

## 4. Repository klonen und Stand festlegen

Als Desktop-Benutzer:

```bash
mkdir -p ~/sw
cd ~/sw
DEPLOY_BRANCH=main
git clone --branch "$DEPLOY_BRANCH" \
  git@github-zunder-zapfe:nemai09/zunder_zapfe.git
cd zunder_zapfe
git status --short --branch
git log -1 --oneline
```

Für den aktuellen M8-Branch stattdessen vor dem Klonen:

```bash
DEPLOY_BRANCH=codex/m8-esp-hil
```

Die angezeigte Commit-ID notieren und mit dem beabsichtigten Deployment-Stand
vergleichen. Für spätere Updates mit `deploy-update.sh` muss der Checkout auf
einem Branch stehen und frei von lokalen Änderungen sein.

## 5. Anwendung installieren

Im Repository:

```bash
cd ~/sw/zunder_zapfe
chmod +x scripts/install-pi.sh scripts/pi-verify.sh scripts/deploy-update.sh
sudo ./scripts/install-pi.sh "$(whoami)"
```

Das Skript installiert unter anderem Python-Werkzeuge, Chromium, PC/SC,
`liblgpio`, I2C-Werkzeuge, NetworkManager und nginx. Anschließend richtet es ein:

- `.venv` im Checkout, im Besitz des Desktop-Benutzers;
- `zunder-zapfe-web.service`;
- Datenverzeichnis `/var/lib/zunder-zapfe`;
- Laufzeitkonfiguration `/etc/zunder-zapfe/web.env`;
- Chromium-Kioskstart über den labwc-Autostart;
- DS3231-Device-Tree-Overlay und RTC-Startdienst vor der Zapfanwendung;
- Werkzeuge für Admin-WLAN und WLAN-Moduswechsel.

Kontrolle:

```bash
systemctl status zunder-zapfe-web.service --no-pager
curl --fail http://127.0.0.1:8000/api/health
curl --fail http://127.0.0.1:8000/api/hardware/status
systemctl status zunder-zapfe-rtc.service --no-pager
sudo zunder-zapfe-rtc status
```

Die Standardkonfiguration verwendet:

```text
Ventil:       BCM17, aktiv HIGH
Durchfluss:   BCM27, fallende Flanke
Impulse/L:    500, nur Demonstratorwert
Simulation:   aus
Flow-Watchdog: aktiv
Offline-Zeit:  DS3231 auf /dev/rtc0, intern UTC
```

Falls `/dev/rtc0` unmittelbar nach der ersten Installation noch fehlt, muss der
Pi einmal neu gestartet werden. Die RTC wird anschließend gemäß
[`ds3231-rtc.md`](ds3231-rtc.md) einmalig lokal gestellt.

Ist `/dev/rtc0` vorhanden, aber noch nicht initialisiert, fordert der Installer
stattdessen `sudo zunder-zapfe-rtc set` an. Dieser Befehl übernimmt die bereits
korrekte Systemzeit, ohne NTP zu deaktivieren. Danach muss
`deploy-update.sh` erneut ausgeführt werden, damit Startdienst und vollständige
Zielsystemprüfung erfolgreich abschließen.

Vor realer Ventilhardware kontrollieren:

```bash
sudo grep -E \
  'VALVE_GPIO|FLOW_GPIO|PULSES_PER_LITER|SIMULATE_TAP_HARDWARE|DEBUG_DISABLE_FLOW_WATCHDOG' \
  /etc/zunder-zapfe/web.env
```

`ZUNDER_ZAPFE_SIMULATE_TAP_HARDWARE` und
`ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG` müssen beide `0` sein. Die
Demonstratorkalibrierung ist noch keine Freigabe für eine reale Abrechnung.

### PC/SC-Zugriff des Dienstbenutzers

Der Installer installiert die PC/SC-Pakete, legt aktuell aber noch keine
PC/SC-Polkit-Regel für den systemd-Dienst an. Meldet
`/api/nfc/status` den Fehler `Access denied (0x8010006A)`, muss einmalig die
eng begrenzte Regel aus
[`acr122u-nfc.md`](acr122u-nfc.md#pcsc-zugriff-fuer-den-webdienst-freigeben)
für den tatsächlichen Dienstbenutzer eingerichtet werden. Die vom Installer
erzeugte NetworkManager-Regel ersetzt diese Kartenleserfreigabe nicht.

Anschließend müssen diese Prüfungen ohne Zugriffsfehler funktionieren:

```bash
pcsc_scan
curl --fail http://127.0.0.1:8000/api/nfc/status
```

## 6. Leere Alpha-Datenbank initialisieren

### Aktuelle Einschränkung

Der Installer migriert das Datenbankschema, erzeugt aber noch keinen
produktiven initialen Admin. Der vorhandene Alpha-Befehl
`zunder-zapfe-seed-demo` legt gleichzeitig Demo-Admin, Demo-Benutzer,
Veranstaltung, Getränk und Fass an und funktioniert ausschließlich bei leeren
Fachtabellen.

Für einen Entwicklungs- oder zweiten Alpha-Pi kann dieser Weg verwendet
werden. Vor dem produktiven Campingbetrieb sollte ein eigener
Produktiv-Bootstrap implementiert oder ein freigegebener Datenübernahmeprozess
festgelegt werden.

### NFC-UIDs lokal ermitteln

ACR122U anschließen und prüfen:

```bash
pcsc_scan
```

`pcsc_scan` danach mit `Strg+C` beenden. Das Admin-Armband auflegen und lokal
den NFC-Status ansehen:

```bash
curl --silent http://127.0.0.1:8000/api/nfc/status | python3 -m json.tool
```

Die UID nur lokal verwenden. Sie darf nicht committed oder in
Dokumentationsbeispiele übernommen werden.

### Demo-Grundbestand für einen Alpha-Pi erzeugen

Für den Seed werden idealerweise zwei reale Testarmbänder verwendet. Befehle
als Desktop-Benutzer aus dem Checkout:

```bash
cd ~/sw/zunder_zapfe
APP_USER="$(whoami)"
REPO_DIR="$(pwd)"
read -r -p "UID des Admin-Armbands: " ADMIN_UID
read -r -p "UID des Testbenutzer-Armbands: " USER_UID

sudo systemctl stop zunder-zapfe-web.service
sudo -u "$APP_USER" env \
  ZUNDER_ZAPFE_DATABASE_URL=sqlite:////var/lib/zunder-zapfe/zunder-zapfe.db \
  "$REPO_DIR/.venv/bin/zunder-zapfe-seed-demo" \
  --admin-card "$ADMIN_UID" \
  --user-card "$USER_UID"
unset ADMIN_UID USER_UID
sudo systemctl start zunder-zapfe-web.service
```

Die ausgegebene Admin-ID notieren. Danach das persönliche Webpasswort
interaktiv und ohne Kommandozeilenargument setzen:

```bash
sudo -u "$APP_USER" env \
  ZUNDER_ZAPFE_DATABASE_URL=sqlite:////var/lib/zunder-zapfe/zunder-zapfe.db \
  "$REPO_DIR/.venv/bin/zunder-zapfe-admin-password"
```

Optional, aber für den initialen Alpha-Admin empfohlen, das Konto dauerhaft
gegen versehentliches Löschen oder Herabstufen schützen:

```bash
sudo -u "$APP_USER" env \
  ZUNDER_ZAPFE_DATABASE_URL=sqlite:////var/lib/zunder-zapfe/zunder-zapfe.db \
  "$REPO_DIR/.venv/bin/zunder-zapfe-protect-admin" --user-id <ADMIN-ID>
```

Der Schutz kann über die Anwendung nicht wieder aufgehoben werden. Vorher ID,
Adminrolle und aktives Armband sorgfältig prüfen.

## 7. Admin-WLAN bewusst aktivieren

Das Admin-WLAN wird absichtlich nicht durch `install-pi.sh` aktiviert, weil
dies eine laufende WLAN-SSH-Verbindung trennen kann. Diese Schritte möglichst
an Bildschirm und Tastatur oder über Ethernet ausführen:

```bash
sudo raspi-config nonint do_wifi_country DE
sudo zunder-zapfe-admin-wifi
```

Der WPA-Schlüssel wird verdeckt abgefragt und darf nicht in Git, Shellskripten
oder `/etc/zunder-zapfe/web.env` gespeichert werden.

Danach:

```text
SSID:      ZUNDER_ZAPFE
Pi:        10.42.0.1
Admin-URL: http://10.42.0.1/admin
```

Das Smartphone darf „kein Internet“ melden. Die Anwendung ist absichtlich
offline.

## 8. Vollständige Zielsystemprüfung

ACR122U anschließen und dann:

```bash
cd ~/sw/zunder_zapfe
./scripts/pi-verify.sh
```

Das Skript prüft Tests, Migrationen, systemd, Health-Endpunkt, ACR122U und –
nach Einrichtung – das Admin-WLAN. Es verwendet die produktive Datenbank erst
nach Abschluss der isolierten Python-Tests.

Anschließend neu starten:

```bash
sudo reboot
```

Nach dem Neustart manuell prüfen:

1. Der Benutzer `zapfe` wird automatisch grafisch angemeldet.
2. `zunder-zapfe-rtc.service` hat die Systemzeit aus der DS3231 geladen.
3. Chromium startet ohne Browserrahmen im Kioskmodus.
4. Der Kiosk erreicht den Bereitschaftszustand.
5. Eine bekannte NFC-Karte wird erkannt.
6. `ZUNDER_ZAPFE` ist erreichbar.
7. Die Smartphone-Adminseite verlangt das persönliche Adminpasswort.
8. Ventilstatus ist im Ruhezustand geschlossen.
9. Bei ESP-HIL funktionieren Normalfluss und die verriegelte Abschaltung bei
   ausbleibenden Impulsen gemäß `gpio-hil-test.md`.

Nützliche Diagnose:

```bash
systemctl status zunder-zapfe-web.service --no-pager
journalctl -u zunder-zapfe-web.service -n 100 --no-pager
curl --silent http://127.0.0.1:8000/api/health | python3 -m json.tool
curl --silent http://127.0.0.1:8000/api/hardware/status | python3 -m json.tool
```

## 9. Spätere Updates

Updates erfolgen auf dem aktuell ausgecheckten Branch:

```bash
cd ~/sw/zunder_zapfe
git status --short --branch
sudo ./scripts/deploy-update.sh "$(whoami)"
```

Das Skript:

- bricht bei versionierten lokalen Änderungen ab;
- holt ausschließlich den aktuellen Branch;
- erlaubt nur einen Fast-Forward;
- führt bei geänderten Systembestandteilen erneut die Vollinstallation aus;
- startet den Dienst neu;
- führt `pi-verify.sh` aus;
- speichert den erfolgreich geprüften Commit unter
  `/var/lib/zunder-zapfe/deployed-revision`.

Bei der erstmaligen DS3231-Einrichtung kann die neue Bootkonfiguration einen
Neustart oder die einmalige Übernahme der Systemzeit mit
`sudo zunder-zapfe-rtc set` erfordern. Das Skript meldet die notwendige Aktion,
überspringt die noch nicht mögliche Zielsystemprüfung und muss danach erneut
ausgeführt werden. Erst der erfolgreich geprüfte Folgelauf speichert die
Revision.

Vor einem Branchwechsel:

```bash
git fetch origin
git switch <branch>
git pull --ff-only
sudo ./scripts/deploy-update.sh "$(whoami)"
```

Ein detached Checkout ist für `deploy-update.sh` nicht geeignet.

## 10. Bekannte Grenzen des aktuellen Alpha-Deployments

- produktiver Initial-Admin-Bootstrap fehlt; aktuell existiert nur der
  Demo-Seed für eine leere Datenbank;
- eine automatische Wiederherstellung ist nicht implementiert; die
  30-Minuten-Sicherung und der Smartphone-CSV-Download sind unter
  [`database-backup.md`](database-backup.md) beschrieben;
- das Installationsskript installiert auch Entwicklungs- und
  Diagnoseabhängigkeiten;
- ein Internet-unabhängiges Paketdeployment existiert noch nicht;
- die zulässige DS3231-Abweichung über den einwöchigen Einsatz ist noch durch
  einen mehrtägigen Zielsystemtest festzulegen;
- der reale Not-Aus-Adapter und die elektrische Gesamtabnahme fehlen;
- `500` Impulse pro Liter sowie Zeit- und Plausibilitätsgrenzen müssen mit
  realer Hardware kalibriert werden;
- ein echtes Ventil darf erst nach elektrischer und sicherheitstechnischer
  Freigabe angeschlossen werden.

Traceability: `ZZ-SYS-001`, `ZZ-SYS-002`, `ZZ-AUT-002`, `ZZ-AUT-003`,
`ZZ-AUT-006`, `ZZ-HW-002`, `ZZ-HW-003`, `ZZ-HW-004`, `ZZ-SAF-008`,
`ZZ-SAF-009`, `ZZ-UI-002`, `ZZ-NET-001`, `ZZ-NET-002`, `ZZ-DAT-008` und
`ZZ-NFR-001`.
