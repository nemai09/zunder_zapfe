# GPIO- und ESP8266-Hardware-in-the-Loop-Test

Status: Alpha-Prüfaufbau für Milestone 8

Die Anwendung verwendet in diesem Aufbau bereits ihre regulären
Raspberry-Pi-Adapter. Der ESP8266 ist ausschließlich externe Prüfhardware: Er
beobachtet das Ventil-Sollsignal und liefert anstelle des späteren
Durchflusssensors Impulse zurück. In der Anwendung existiert kein besonderer
HIL-Betriebsmodus.

## Prüfstatus

Der erste vollständige HIL-Normalfluss wurde am 25. Juli 2026 mit der
Zielsoftware auf Commit `33cc77b` erfolgreich durchgeführt. Dabei wurde
`BCM17` beim Gedrückthalten aktiv, der ESP erkannte das Ventilsignal und
lieferte über `D6` Impulse an `BCM27`. Die Software zählte eine Istmenge,
schloss den Ausgang beim Loslassen und verbuchte den Zapfvorgang.

Diese erfolgreiche Normalflussprüfung schließt `M8.1` ab, aber nicht die
vollständige HIL-Abnahme aus `M8.5`. Ausbleibender Durchfluss, Neustart,
Verbindungsabbruch und Safety-Verriegelung bleiben anhand der folgenden
Prüfschritte nachzuweisen.

## Benötigte Teile

- Raspberry Pi 4B mit dem aktuellen Branch `codex/m8-esp-hil`;
- ESP8266 D1 mini mit USB-Kabel;
- empfohlen zwei Widerstände mit jeweils 1 kΩ für die Signalleitungen;
- Steckbrett und Jumperkabel;
- ein zweiter Rechner oder ein Smartphone für die ESP-Diagnose-Webseite.

Ein Magnetventil und seine Versorgung werden für diesen Test ausdrücklich
nicht benötigt.

## Festgelegte Raspberry-Pi-Anschlüsse

Alle GPIO-Angaben sind BCM-Nummern:

| Funktion | BCM-GPIO | Physischer Pin | Softwareverhalten |
| --- | --- | --- | --- |
| Ventilfreigabe | `BCM17` | Pin 11 | HIGH öffnet beziehungsweise bestromt; LOW schließt |
| Durchflussimpulse | `BCM27` | Pin 13 | Eingang mit internem 3,3-V-Pull-up; fallende Flanke zählt |
| Bezugspotential | `GND` | Pin 14 | gemeinsame Masse des 3,3-V-HIL-Aufbaus |

`BCM17` darf niemals direkt eine Ventilspule treiben. Im Zielaufbau führt der
Pin ausschließlich zum 3,3-V-kompatiblen Eingang einer geeigneten
Ventiltreiberstufe. Diese benötigt einen eigenen Pull-down, eine passende
Ventilversorgung, Freilaufbeschaltung und die unabhängige
Not-Aus-Unterbrechung. Das stromlos geschlossene Ventil liegt erst hinter
dieser Treiberstufe.

Der reale Durchflusssensor darf erst nach Prüfung seines Ausgangspegels mit
`BCM27` verbunden werden. Spannungen über 3,3 V benötigen eine geeignete
Eingangsstufe oder galvanische Trennung.

## Verdrahtung mit dem ESP8266 D1 mini

| Raspberry Pi 4B | Zwischenbeschaltung | ESP8266 D1 mini |
| --- | --- | --- |
| Pin 11, `BCM17` | empfohlen 1 kΩ in Reihe | `D0`, Ventil-Sollsignal |
| Pin 13, `BCM27` | empfohlen 1 kΩ in Reihe | `D6`, Durchflussimpulse |
| Pin 14, `GND` | direkte Verbindung | `GND` |

`D0` entspricht GPIO16 und ist der einzige ESP8266-Pin mit internem Pull-down.
Die Firmware aktiviert ihn, sodass eine abgezogene Pi-Leitung LOW bedeutet.
Der ESP wird über seinen eigenen USB-Anschluss versorgt. `3V3`, `VIN`, 5 V,
12 V, 24 V und eine Ventilspule werden nicht mit diesem Testaufbau verbunden.

Vor dem Einschalten prüfen:

1. `BCM17` führt nur zu `D0`, `BCM27` nur zu `D6`.
2. Pi und ESP besitzen ein gemeinsames GND.
3. Es besteht keine Verbindung zu einer Spannung über 3,3 V.

## Aufbau in sicherer Reihenfolge

1. Raspberry Pi herunterfahren und ESP vom USB trennen.
2. Pin 14 des Pi mit `GND` des ESP verbinden.
3. Pin 11/`BCM17` des Pi über 1 kΩ mit `D0` verbinden.
4. Pin 13/`BCM27` des Pi über 1 kΩ mit `D6` verbinden.
5. Verdrahtung anhand der Tabelle ein zweites Mal prüfen.
6. Zuerst den ESP über USB, danach den Raspberry Pi einschalten.

Falls keine Reihenwiderstände vorhanden sind, ist eine direkte
3,3-V-Verbindung elektrisch grundsätzlich möglich. Für den Prüfaufbau werden
die Widerstände dennoch empfohlen, weil sie den Strom bei einer versehentlichen
Fehlkonfiguration begrenzen.

## ESP-Firmware vorbereiten und prüfen

Nach jeder Änderung des aktiven Pegels muss der ESP neu geflasht werden. Unter
Windows PowerShell:

```powershell
cd esp8266_flow_emulator
Copy-Item src\wifi_config.example.h src\wifi_config.h
# Nur die lokale wifi_config.h mit den Zugangsdaten ausfüllen.
pio run --target upload
pio device monitor --baud 115200
```

`src/wifi_config.h` ist absichtlich ignoriert und darf nicht committed werden.
Nach dem Start nennt der serielle Monitor die IP-Adresse der Weboberfläche.
Der ESP erzeugt kein eigenes WLAN, sondern verbindet sich als Client mit
`ZUNDER_ZAPFE`.

Den ESP vor der Verbindung mit dem Pi einzeln prüfen:

1. `D0` unbeschaltet lassen.
2. Erwartung: `Ventil-Steuersignal AUS`, der Impulszähler bleibt stehen.
3. `D0` kurz über 1 kΩ mit `3V3` des ESP verbinden.
4. Erwartung: `Ventil-Steuersignal EIN`, der Impulszähler steigt ungefähr um
   zehn pro Sekunde.
5. Die Verbindung zu `3V3` wieder entfernen.
6. Erwartung: `AUS`, der Impulszähler bleibt erneut stehen.

## Raspberry Pi installieren

Auf dem Branch `codex/m8-esp-hil`:

```bash
cd ~/sw/zunder_zapfe
git pull
sudo apt update
sudo apt install --yes liblgpio-dev
.venv/bin/python -m pip install --editable '.[dev,debug]'
sudo usermod -a -G gpio zapfe
```

`liblgpio-dev` stellt die native Bibliothek bereit, gegen die das
Python-Paket `lgpio` auf dem Raspberry Pi gebaut wird. Ohne dieses Paket endet
die Installation mit `cannot find -llgpio`.

In `/etc/zunder-zapfe/web.env`:

```text
ZUNDER_ZAPFE_VALVE_GPIO=17
ZUNDER_ZAPFE_FLOW_GPIO=27
ZUNDER_ZAPFE_SIMULATE_TAP_HARDWARE=0
ZUNDER_ZAPFE_PULSES_PER_LITER=500
ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG=0
```

Danach:

```bash
sudo systemctl restart zunder-zapfe-web.service
sudo systemctl status zunder-zapfe-web.service --no-pager
curl http://127.0.0.1:8000/api/hardware/status
```

Erwartet werden:

- Ventil: `"available": true`, `"simulated": false`, Detail
  `Ventilausgang BCM 17, aktiv HIGH`;
- Durchfluss: `"available": true`, `"simulated": false`, Detail
  `Durchflusseingang BCM 27, fallende Flanke`;
- Not-Aus vorerst noch `"simulated": true`.

Bei einem Startfehler:

```bash
id zapfe
ls -l /dev/gpiochip*
sudo journalctl -u zunder-zapfe-web.service -n 80 --no-pager
```

`lgpio` legt zur Laufzeit Benachrichtigungs-Pipes an. Der systemd-Dienst
arbeitet deshalb in `/run/zunder-zapfe`, das systemd bei jedem Dienststart
beschreibbar und mit passenden Besitzrechten anlegt. Meldungen wie
`xCreatePipe: Can't set permissions` oder ein Rückfall auf
`NativePinFactory` bedeuten, dass noch eine ältere Service-Datei mit dem
schreibgeschützten Repository als Arbeitsverzeichnis installiert ist. In
diesem Fall das aktuelle `scripts/install-pi.sh` erneut ausführen.

Die Verdrahtung noch nicht durch Betätigung der Zapffläche testen, solange
Ventil oder Durchfluss im Status `available: false` melden.

## Normaler Zapfvorgang

1. ESP mit der aktuellen aktiven-HIGH-Firmware starten.
2. In der ESP-Weboberfläche `Impulsfeedback AN` prüfen.
3. Ein bekanntes Armband kurz am Kiosk auflegen.
4. Die Zapffläche ungefähr fünf Sekunden gedrückt halten.
5. Zapffläche loslassen.

Bei 10 Hz und 500 Impulsen/Liter wird erwartet:

- `BCM17` wird beim Start HIGH; der ESP zeigt `Ventil-Steuersignal EIN`;
- der ESP erzeugt ungefähr 50 fallende Impulse in fünf Sekunden;
- das Backend misst ungefähr 100 ml;
- Loslassen setzt `BCM17` sofort LOW, der ESP zeigt `AUS`;
- die Durchflussmessung endet und die gemessene Menge wird dem angemeldeten
  Benutzer zugeordnet.

Diagnose während des Vorgangs:

```bash
watch -n 0.5 'curl -s http://127.0.0.1:8000/api/tap/status'
```

## Ausbleibender Durchfluss

1. In der ESP-Weboberfläche `Impulsfeedback AUS` wählen.
2. Benutzer anmelden und die Zapffläche gedrückt halten.

Erwartetes Ergebnis:

- `BCM17` wird zunächst HIGH;
- ohne ersten Impuls verriegelt die Steuerung nach ungefähr zwei Sekunden;
- `BCM17` wird LOW und der ESP zeigt `Ventil-Steuersignal AUS`;
- `/api/tap/status` meldet `fault_locked` sowie
  `safety_reason: "Kein Durchfluss erkannt"`;
- erneutes Einschalten des Feedbacks setzt die Zapfung nicht fort;
- ein Admin muss die Sperre bewusst über Diagnose zurücksetzen.

Wird das Feedback erst während einer laufenden Zapfung ausgeschaltet, greift
der aktuelle Entwicklungsgrenzwert für ausbleibende Folgeimpulse nach ungefähr
einer Sekunde.

## Abbruchbedingungen

Den Aufbau sofort spannungsfrei machen, wenn:

- der ESP im Ruhezustand `Ventil-Steuersignal EIN` meldet;
- an einer Signalleitung mehr als 3,3 V gemessen werden;
- ein Widerstand, Kabel, Pi oder ESP ungewöhnlich warm wird;
- `BCM17` nach Loslassen der Zapffläche nicht wieder LOW wird;
- die Anwendung trotz `available: false` weiter betrieben werden soll.

Ein fehlender gemeinsamer GND und vertauschte `D0`/`D6`-Leitungen sind die
zuerst zu prüfenden Aufbaufehler.

## Entwicklung ohne Raspberry-Pi-GPIO

Nur für lokale Softwareentwicklung kann ausdrücklich gesetzt werden:

```text
ZUNDER_ZAPFE_SIMULATE_TAP_HARDWARE=1
ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG=1
```

Der Zielsystem-Default verwendet dagegen immer die GPIO-Adapter. Der
Simulationsschalter darf nicht für die HIL-Abnahme oder mit realer
Ventilhardware verwendet werden.

Traceability: `ZZ-HW-002`, `ZZ-HW-003`, `ZZ-HW-004`, `ZZ-HW-005`,
`ZZ-SAF-004`, `ZZ-SAF-005`, `ZZ-SAF-008` und `ZZ-SAF-009`.
