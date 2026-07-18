# Raspberry Pi 4B – Testseite im Kioskmodus

## Ziel

Nach dem Booten startet ein lokaler Python-Webdienst. Sobald dessen Health-
Endpunkt erreichbar ist, oeffnet Chromium automatisch die Testseite im
Kioskmodus. Die Anwendung ist nur ueber Loopback erreichbar und benoetigt keine
Internetverbindung zur Laufzeit.

Dieser erste Meilenstein implementiert noch keine NFC-, Ventil- oder
Durchflusssteuerung.

## Voraussetzungen

- Raspberry Pi 4B
- Raspberry Pi OS (64 Bit) mit Desktop
- eingerichteter Desktop-Benutzer mit automatischer grafischer Anmeldung
- SSH-Zugang fuer Installation und Auswertung
- Git-Checkout des zu testenden Branches auf dem Raspberry Pi
- Internetzugang waehrend der Erstinstallation fuer APT- und Python-Pakete

Raspberry Pi OS verwendet ab Bookworm standardmaessig Wayland mit labwc. Der
Kioskstart wird deshalb in `~/.config/labwc/autostart` des Desktop-Benutzers
eingetragen.

## Repository auf dem Pi auschecken

Fuer das private GitHub-Repository sollte der Raspberry einen nur lesenden
Deploy-Key erhalten. Danach:

```bash
git clone git@github.com:nemai09/zunder_zapfe.git
cd zunder_zapfe
git fetch origin
git switch webui_backend
git pull --ff-only
```

Alternativ kann ein exakt benannter Commit getestet werden:

```bash
git fetch origin
git switch --detach <commit-id>
```

## Installation

Im Repository auf dem Raspberry Pi:

```bash
chmod +x scripts/install-pi.sh scripts/pi-verify.sh
sudo ./scripts/install-pi.sh <desktop-benutzer>
sudo reboot
```

Das Installationsskript:

1. installiert `python3-venv`, Chromium und curl,
2. erzeugt die virtuelle Python-Umgebung `.venv`,
3. installiert Anwendung und Testabhaengigkeiten,
4. konfiguriert den Webdienst fuer den angegebenen Desktop-Benutzer,
5. installiert und startet `zunder-zapfe-web.service`,
6. installiert den Kiosk-Launcher,
7. ergaenzt den labwc-Autostart des Desktop-Benutzers.

Die produktive Laufzeitkonfiguration liegt unter
`/etc/zunder-zapfe/web.env`. Ihre Vorlage ist `config/web.env.example`.

## Verifikation auf dem Zielsystem

```bash
./scripts/pi-verify.sh
```

Das Skript prueft:

- Python-Tests,
- aktiven systemd-Dienst,
- lokalen HTTP-Health-Endpunkt.

Nach einem Neustart muss zusaetzlich visuell geprueft werden:

- Chromium erscheint ohne Browserrahmen,
- die Seite zeigt "Zunder Zapfe",
- der Backendstatus wechselt auf "Bereit",
- keine externe Netzwerkverbindung ist fuer die Anzeige erforderlich.

Der Testbericht soll die ausgegebene Commit-ID enthalten.

## Betrieb und Diagnose

Dienststatus:

```bash
systemctl status zunder-zapfe-web.service
```

Live-Protokoll:

```bash
journalctl -u zunder-zapfe-web.service -f
```

Health-Endpunkt:

```bash
curl http://127.0.0.1:8000/api/health
```

Dienst neu starten:

```bash
sudo systemctl restart zunder-zapfe-web.service
```

## Einen neuen Branch oder Commit evaluieren

```bash
cd <repository-pfad>
git fetch origin
git switch <branch>
git pull --ff-only
sudo ./scripts/install-pi.sh <desktop-benutzer>
./scripts/pi-verify.sh
```

Die erneute Installation aktualisiert Python-Paket und systemd-Konfiguration,
ohne die Datei `/etc/zunder-zapfe/web.env` zu ueberschreiben.

## Bekannte Grenzen dieses Meilensteins

- Das Skript ist fuer aktuelle Raspberry Pi OS Desktop-Images mit labwc gedacht.
- Automatische Desktop-Anmeldung wird vorausgesetzt und nicht veraendert.
- Die Anwendung lauscht nur auf `127.0.0.1`; Fernzugriff ist noch nicht vorgesehen.
- Es existiert noch keine Datenbank und keine Hardwaresteuerung.
- Ein vollstaendig offline durchfuehrbares Dependency-Deployment folgt spaeter.
