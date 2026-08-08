# DS3231-Offline-Zeitbasis

## Zweck

Die DS3231 stellt dem Raspberry Pi ohne Internet eine batteriegepufferte
Zeitbasis bereit. Linux bindet sie über den vorhandenen RTC-Treiber ein. Der
Dienst `zunder-zapfe-rtc.service` kopiert ihre in UTC gespeicherte Zeit beim
Systemstart in die Systemuhr, bevor `zunder-zapfe-web.service` startet.

Die Zapfanwendung greift nicht direkt auf I2C oder `/dev/rtc0` zu. Buchungen,
Adminaudit und technische Ereignisse verwenden weiterhin die normale
timezone-aware Systemzeit. Es gibt bewusst keine RTC-Einstellung in Kiosk oder
Smartphone-WebUI.

Traceability: `ZZ-TIM-001`, `ZZ-DAT-002`, `ZZ-DAT-003`, `ZZ-DAT-004` und
`ZZ-SYS-001`.

## Verdrahtung am Raspberry Pi 4B

Nur im ausgeschalteten Zustand verdrahten:

| DS3231 | Raspberry Pi | Funktion |
| --- | --- | --- |
| `VCC` | Pin 1, `3V3` | Versorgung mit 3,3 V |
| `GND` | Pin 6, `GND` | gemeinsames Bezugspotential |
| `SDA` | Pin 3, `GPIO2/SDA1` | I2C-Daten |
| `SCL` | Pin 5, `GPIO3/SCL1` | I2C-Takt |

`SQW` und `32K` bleiben unbeschaltet. Das Modul darf in diesem Aufbau nicht an
5 V angeschlossen werden. Batterietyp und eine eventuell vorhandene
Ladeschaltung müssen zum konkreten Modul passen; eine CR2032 darf nicht geladen
werden.

## Installation

Der normale Pi-Installer:

```bash
cd ~/sw/zunder_zapfe
sudo ./scripts/install-pi.sh "$(whoami)"
```

- installiert `i2c-tools` und `hwclock` aus `util-linux`;
- aktiviert I2C;
- ergänzt `dtoverlay=i2c-rtc,ds3231` in der Bootkonfiguration;
- installiert und aktiviert `zunder-zapfe-rtc.service`;
- ordnet den RTC-Ladeversuch vor dem Webdienst ein.

Das Skript versucht, das Overlay zur direkten Prüfung auch zur Laufzeit zu
laden. Falls `/dev/rtc0` dabei noch nicht entsteht, ist ein Neustart zwingend:

```bash
sudo reboot
```

Danach prüfen:

```bash
ls -l /dev/rtc0
cat /sys/class/rtc/rtc0/name
sudo i2cdetect -y 1
sudo zunder-zapfe-rtc status
```

Der Kernelname soll `ds3231` enthalten. In `i2cdetect` erscheint die Adresse
`0x68` nach der Treiberbindung typischerweise als `UU`; das bedeutet, dass der
Kernel das Gerät bereits verwendet.

## Uhr einmalig manuell stellen

Zuerst die lokale Zeitzone prüfen, beispielsweise:

```bash
timedatectl
sudo timedatectl set-timezone Europe/Berlin
```

Dann die lokale Uhrzeit interaktiv stellen:

```bash
sudo zunder-zapfe-rtc set
```

Dies erfolgt nur während der Inbetriebnahme, ohne laufende Zapfung und bevor
produktive Buchungen entstehen.

Das CLI erwartet `JJJJ-MM-TT HH:MM:SS`, zeigt den Wert vor der Änderung noch
einmal an, deaktiviert die NTP-Synchronisierung und schreibt die resultierende
UTC-Zeit in die DS3231. Der interaktiv eingegebene Stellwert landet weder in
der Shell-History noch im Repository.

Ist die Systemzeit bereits korrekt, beispielsweise nach einer vorübergehenden
NTP-Synchronisierung, genügt:

```bash
sudo zunder-zapfe-rtc set-from-system
```

Dieser zweite Befehl verändert die NTP-Einstellung nicht.

## Startreihenfolge und Fehlerverhalten

`zunder-zapfe-web.service` deklariert ein `Wants` und `After` auf den
RTC-Dienst. Bei vorhandener DS3231 wird die Systemzeit deshalb zuerst geladen.
Ein fehlendes RTC-Gerät verhindert den Webdienst nicht: Kiosk und Diagnose
bleiben erreichbar. Der RTC-Dienst ist dann jedoch nicht aktiv und
`pi-verify.sh` bewertet den Zielsystemzustand als fehlerhaft. Damit bleibt eine
Hardwarestörung sichtbar, ohne die lokale Fehlerdiagnose abzuschneiden.

Diagnose:

```bash
systemctl status zunder-zapfe-rtc.service --no-pager
sudo journalctl -u zunder-zapfe-rtc.service -b --no-pager
sudo zunder-zapfe-rtc status
```

## Offline-Abnahme

1. RTC stellen und mit `status` kontrollieren.
2. Internet und alle bekannten WLAN-Clientverbindungen trennen.
3. Raspberry Pi sauber herunterfahren und danach mindestens zehn Minuten
   vollständig von seiner Versorgung trennen.
4. Wieder einschalten und den RTC-Dienst prüfen.
5. Systemzeit mit einer unabhängigen Uhr vergleichen.
6. Eine Testzapfung ausführen und den Buchungszeitpunkt in der Admin-WebUI
   kontrollieren.
7. Vor dem einwöchigen Einsatz einen mehrtägigen Abweichungstest durchführen.

Die konkrete zulässige Zeitabweichung über den Einsatzzeitraum ist noch durch
den Zielsystemtest zu bestimmen. Eine leere oder ungeeignete Stützbatterie wird
durch die Software nicht kompensiert.
