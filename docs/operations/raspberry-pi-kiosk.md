# Raspberry Pi 4B – Testseite im Kioskmodus

## Ziel

Nach dem Booten startet ein lokaler Python-Webdienst. Sobald dessen Health-
Endpunkt erreichbar ist, oeffnet Chromium automatisch die Testseite im
Kioskmodus. Die Anwendung ist nur ueber Loopback erreichbar und benoetigt keine
Internetverbindung zur Laufzeit.

Der aktuelle Alpha-Stand bindet den ACR122U-NFC-Leser ein und verbindet ihn mit
Zapfzustandsautomat und SQLite-Persistenz. Ventil, Durchflussmesser und Not-Aus
sind als Simulatoren im Hardware-Zwischenlayer vorhanden; ihre reale
Ansteuerung fehlt noch.

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
git switch main
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

1. installiert `python3-venv`, Chromium, curl, NetworkManager, `iw` und nginx,
2. erzeugt die virtuelle Python-Umgebung `.venv`,
3. installiert Anwendung und Testabhaengigkeiten,
4. konfiguriert den Webdienst fuer den angegebenen Desktop-Benutzer,
5. installiert und startet `zunder-zapfe-web.service`,
6. installiert den Kiosk-Launcher,
7. ergaenzt den labwc-Autostart des Desktop-Benutzers,
8. installiert das Werkzeug zur bewussten Ersteinrichtung des Admin-WLANs,
9. installiert den begrenzten WLAN-Modushelfer und seine NetworkManager-
   Berechtigung für das lokale Low-Level-Menü.

Die produktive Laufzeitkonfiguration liegt unter
`/etc/zunder-zapfe/web.env`. Ihre Vorlage ist `config/web.env.example`.

Das Admin-WLAN wird nicht automatisch aktiviert, weil dies eine bestehende
WLAN-SSH-Verbindung trennen kann. Die einmalige Einrichtung erfolgt nach
gesetztem WLAN-Land interaktiv:

```bash
sudo raspi-config nonint do_wifi_country DE
sudo zunder-zapfe-admin-wifi
```

Dabei wird der neue WLAN-Schlüssel verdeckt abgefragt. Er darf nicht im
Repository, in einem Shellskript oder in der Kommandozeile hinterlegt werden.
Details stehen unter [Admin-WLAN](admin-wifi.md).

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
- nach bewusster Einrichtung den aktiven AP- oder Clientmodus und im AP-Modus
  den Admin-Webzugang.

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

Das HTTP-Access-Log ist im Normalbetrieb deaktiviert, weil die lokale
Kioskseite regelmäßig Statusendpunkte abfragt. Für eine kurze Diagnose kann in
`/etc/zunder-zapfe/web.env` vorübergehend
`ZUNDER_ZAPFE_ACCESS_LOG=1` gesetzt und der Dienst neu gestartet werden. Danach
muss der Wert wieder auf `0`, damit Journal und Datenträger nicht mit
erwartbaren Polling-Zugriffen belastet werden.

Health-Endpunkt:

```bash
curl http://127.0.0.1:8000/api/health
```

### Laufzeitlast prüfen

Für einen vergleichbaren Schnappschuss die Anlage zunächst mindestens eine
Minute ohne Bedienung im Sperrbildschirm laufen lassen:

```bash
ps -eo pid,pcpu,pmem,rss,time,comm,args --sort=-pcpu | head -n 15
```

Danach einmal anmelden, einige Sekunden angemeldet warten und eine simulierte
oder reale Zapfung durchführen. Die Messung jeweils wiederholen. Hohe
Chromium-`VIRT`-Werte bezeichnen reservierten virtuellen Adressraum; für den
physischen Speicher sind `RSS` beziehungsweise `RES` maßgeblich.

Im ruhenden Sperrbildschirm sollen insbesondere `NetworkManager` und
`dbus-daemon` keine durch die Kioskseite verursachte zweisekündliche
Lastspitze mehr zeigen. Der schnelle Zapfstatus bleibt absichtlich aktiv, damit
NFC-Anmeldung und Safety-Rückmeldungen ohne spürbare Zusatzverzögerung
erscheinen.

Initiales oder lokal zurückgesetztes Admin-Webpasswort:

```bash
sudo -u zapfe /home/zapfe/sw/zunder_zapfe/.venv/bin/zunder-zapfe-admin-password
```

Das Kommando listet aktive Admins auf und fragt das Passwort verdeckt zweimal
ab. Ein Passwort darf niemals als Kommandozeilenargument, in `web.env` oder im
Repository hinterlegt werden. Der tatsächliche Desktop-Benutzer und
Repositorypfad sind bei einer abweichenden Installation entsprechend
anzupassen.

Smartphone-Administration nach eingerichtem Admin-WLAN:

1. Smartphone mit `ZUNDER_ZAPFE` verbinden. Eine Warnung „kein Internet“ ist
   im Standalone-Betrieb normal.
2. `http://10.42.0.1/admin` öffnen.
3. Persönlichen Admin auswählen und mit dessen Passwort anmelden.
4. Unter **Benutzer** suchen, bearbeiten oder mit **+ Neu** anlegen.
5. Für eine Armbandzuordnung den Benutzer öffnen, **Zuweisen** drücken und das
   neue Veranstaltungsarmband kurz am ACR122U auflegen.

Lokaler WLAN-Moduswechsel:

1. Admin-Armband kurz auflegen und den blauen **ADMIN**-Button drücken.
2. Im Low-Level-Menü **Access Point aktivieren** oder **Mit bekanntem WLAN
   verbinden** wählen.
3. Für den Clientmodus muss bereits ein automatisch verbindbares
   NetworkManager-Profil vorhanden sein. Das Menü richtet keine Zugangsdaten
   ein.
4. Über **Zurück zum Zapfen** den Adminmodus verlassen. Der
   WLAN-Statusindikator im Kiosk zeigt den erkannten Modus.

Während der Zuordnung zeigt der Kiosk den gesperrten Zustand
`nfc_capture`; das Ventil bleibt geschlossen. Erfolg, Abbruch oder das
serverseitige Zeitlimit geben die Anlage wieder frei. Die finale
Zielsystemabnahme muss mindestens Login, 20 bis 30 sichtbare Benutzer, Suche,
Sperren/Aktivieren/Löschen eines Demo-Armbands, Passwortwechsel und
Neustartverhalten prüfen.

Dienst neu starten:

```bash
sudo systemctl restart zunder-zapfe-web.service
```

## Spaetere Aktualisierungen evaluieren

Dieser Abschnitt gilt erst, nachdem die oben beschriebene Erstinstallation und
das initiale `git clone` abgeschlossen wurden.

Die lokale Datei `/etc/zunder-zapfe/web.env` wird bei Updates nicht
ueberschrieben. Fuer den Alpha-Sitzungstimeout muessen bestehende Installationen
deshalb einmalig folgende Werte eintragen beziehungsweise anpassen:

```text
ZUNDER_ZAPFE_SESSION_TIMEOUT_SECONDS=15
```

```bash
cd ~/sw/zunder_zapfe
sudo ./scripts/deploy-update.sh
```

Das Deployment-Skript aktualisiert den aktuell ausgecheckten Branch nur per
Fast-Forward, installiert geaenderte Abhaengigkeiten beziehungsweise
Systemdateien, startet den Webdienst neu und fuehrt die Zielsystem-Verifikation
aus. Den letzten erfolgreich verifizierten Commit speichert es unter
`/var/lib/zunder-zapfe/deployed-revision`. Dadurch erkennt es notwendige
Neuinstallationen auch dann, wenn vor dem Aufruf bereits auf einen anderen
Branch gewechselt wurde. Fehlende Laufzeitabhängigkeiten erzwingen ebenfalls
eine vollständige Installation. Bei reinen Python-, HTML- oder CSS-Aenderungen
wird nur der Dienst neu
gestartet. Ein Neustart des Raspberry Pi ist nicht erforderlich.

Der Kiosk erkennt einen geaenderten Git-Commit ueber den Health-Endpunkt und
laedt die Seite automatisch neu. Deshalb sind fuer normale Updates weder ein
Raspberry-Pi-Neustart noch ein manueller Browser-Reload erforderlich.

Beim einmaligen Wechsel von der urspruenglichen Testseite auf eine Version mit
dieser Commit-Erkennung muss Chromium noch einmal neu geladen oder der
Raspberry Pi einmal neu gestartet werden. Erst die danach geladene Seite
enthaelt die automatische Aktualisierungslogik.

Das Installationsskript fuehrt die Python-Installation als Besitzer des
Checkouts aus. Dadurch bleiben `.venv` und das generierte `*.egg-info` fuer
spaetere Updates beschreibbar. `sudo pip` darf im Checkout nicht verwendet
werden.

## Bekannte Grenzen dieses Meilensteins

- Das Skript ist fuer aktuelle Raspberry Pi OS Desktop-Images mit labwc gedacht.
- Automatische Desktop-Anmeldung wird vorausgesetzt und nicht veraendert.
- Die Anwendung lauscht nur auf `127.0.0.1`; ausschließlich der eng begrenzte
  nginx-Zugang im Admin-AP wird weitergeleitet.
- NFC-Anmeldung, Zapf-Zustandsautomat und Datenbank sind integriert; die
  aktuelle Kioskseite bietet dafuer aber noch keine vollstaendige Bedienung.
- Die reale Ventil-, Durchfluss- und Not-Aus-Ansteuerung fehlt noch.
- Ein vollstaendig offline durchfuehrbares Dependency-Deployment folgt spaeter.
