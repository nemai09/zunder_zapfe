# Raspberry Pi 4B – Testseite im Kioskmodus

## Ziel

Nach dem Booten startet ein lokaler Python-Webdienst. Sobald dessen Health-
Endpunkt erreichbar ist, oeffnet Chromium automatisch die Testseite im
Kioskmodus. Die Anwendung ist nur ueber Loopback erreichbar und benoetigt keine
Internetverbindung zur Laufzeit.

Dieser erste Meilenstein bindet den ACR122U-NFC-Leser ein. Ventil,
Durchflussmesser und Not-Aus sind als Simulatoren im Hardware-Zwischenlayer
vorhanden; eine reale Ansteuerung und die fachliche Zapfsteuerung folgen spaeter.

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

## Erstinstallation auf einem neuen Raspberry Pi

Auf dem Raspberry Pi existiert zu diesem Zeitpunkt noch kein lokaler Checkout.
Die folgenden Schritte richten deshalb zuerst den GitHub-Zugriff ein und klonen
danach das Repository zum ersten Mal.

### 1. Git installieren

```bash
sudo apt update
sudo apt install --yes git openssh-client
```

### 2. Lesezugriff auf das private GitHub-Repository einrichten

Der Raspberry Pi sollte einen eigenen SSH-Deploy-Key mit ausschliesslichem
Lesezugriff erhalten. Den Schluessel auf dem Pi erzeugen:

```bash
ssh-keygen -t ed25519 -C "zunder-zapfe-raspberry-pi" -f ~/.ssh/zunder_zapfe_deploy
cat ~/.ssh/zunder_zapfe_deploy.pub
```

Den ausgegebenen oeffentlichen Schluessel in GitHub beim Repository
`nemai09/zunder_zapfe` unter **Settings > Deploy keys > Add deploy key**
hinterlegen. **Allow write access** bleibt deaktiviert.

Anschliessend festlegen, dass GitHub diesen Schluessel verwendet:

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

Beim ersten Verbindungsaufbau muss der angezeigte GitHub-Host-Key geprueft und
bestaetigt werden. Die abschliessende Meldung von GitHub darf darauf hinweisen,
dass kein Shell-Zugriff angeboten wird; die erfolgreiche Authentifizierung ist
entscheidend.

### 3. Repository erstmals klonen

```bash
cd ~
git clone git@github-zunder-zapfe:nemai09/zunder_zapfe.git
cd zunder_zapfe
git switch webui_backend
```

Durch `git clone` wird automatisch das Remote `origin` angelegt. Kontrolle:

```bash
git remote -v
git status
```

Erst ab diesem Zeitpunkt kennt der Checkout `origin`; ein vorheriges
`git fetch origin` waere auf einem neuen Raspberry Pi nicht moeglich.

Alternativ kann ein exakt benannter Commit getestet werden:

```bash
git fetch origin
git switch --detach <commit-id>
```

### 4. Anwendung installieren

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

### 5. Auf dem Zielsystem verifizieren

```bash
./scripts/pi-verify.sh
```

Das Skript prueft:

- Python-Tests,
- aktuellen Stand der SQLite-Datenbankmigrationen,
- aktiven systemd-Dienst,
- lokalen HTTP-Health-Endpunkt,
- angeschlossenen und betriebsbereiten ACR122U.

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

## Spaetere Aktualisierungen evaluieren

Dieser Abschnitt gilt erst, nachdem die oben beschriebene Erstinstallation und
das initiale `git clone` abgeschlossen wurden.

```bash
cd ~/sw/zunder_zapfe
sudo ./scripts/deploy-update.sh
```

Das Deployment-Skript aktualisiert den aktuell ausgecheckten Branch nur per
Fast-Forward, installiert geaenderte Abhaengigkeiten beziehungsweise
Systemdateien, startet den Webdienst neu und fuehrt die Zielsystem-Verifikation
aus. Bei reinen Python-, HTML- oder CSS-Aenderungen wird nur der Dienst neu
gestartet. Ein Neustart des Raspberry Pi ist nicht erforderlich.

Der Kiosk erkennt einen geaenderten Git-Commit ueber den Health-Endpunkt und
laedt die Seite automatisch neu. Deshalb sind fuer normale Updates weder ein
Raspberry-Pi-Neustart noch ein manueller Browser-Reload erforderlich.

Beim einmaligen Wechsel von der urspruenglichen Testseite auf eine Version mit
dieser Commit-Erkennung muss Chromium noch einmal neu geladen oder der
Raspberry Pi einmal neu gestartet werden. Erst die danach geladene Seite
enthaelt die automatische Aktualisierungslogik.

## Bekannte Grenzen dieses Meilensteins

- Das Skript ist fuer aktuelle Raspberry Pi OS Desktop-Images mit labwc gedacht.
- Automatische Desktop-Anmeldung wird vorausgesetzt und nicht veraendert.
- Die Anwendung lauscht nur auf `127.0.0.1`; Fernzugriff ist noch nicht vorgesehen.
- NFC-Anmeldung, Zapf-Zustandsautomat und Datenbank sind integriert; die
  aktuelle Kioskseite bietet dafuer aber noch keine vollstaendige Bedienung.
- Die reale Ventil-, Durchfluss- und Not-Aus-Ansteuerung fehlt noch.
- Ein vollstaendig offline durchfuehrbares Dependency-Deployment folgt spaeter.
