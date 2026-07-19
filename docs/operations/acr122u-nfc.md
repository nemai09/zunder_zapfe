# ACR122U NFC-Leser einrichten

Diese Anleitung dokumentiert die Einrichtung des USB-NFC-Lesers ACS ACR122U
auf dem Raspberry Pi. Sie betrifft insbesondere `ZZ-AUT-002` und `ZZ-HW-001`.

## Voraussetzungen

- ACS ACR122U an einem USB-Port des Raspberry Pi
- Raspberry Pi OS mit Internetzugang fuer die einmalige Paketinstallation
- Benutzer mit `sudo`-Berechtigung

## USB-Verbindung pruefen

```bash
lsusb
```

Der Leser sollte als ACS ACR122U erscheinen, normalerweise mit der USB-ID
`072f:2200`. Falls er fehlt, einen anderen USB-Port und die Stromversorgung des
Raspberry Pi pruefen.

## PC/SC-Unterstuetzung installieren

```bash
sudo apt update
sudo apt install --yes pcscd pcsc-tools libccid
sudo systemctl enable --now pcscd.socket
sudo systemctl restart pcscd
```

## Funktion pruefen

```bash
pcsc_scan
```

Die Ausgabe muss einen `ACS ACR122U PICC Interface`-Leser zeigen. Beim Auflegen
einer NFC-Karte muss `pcsc_scan` die eingelegte Karte und deren ATR melden. Der
Test wird mit `Ctrl+C` beendet.

Die Kioskseite zeigt den erkannten Leser und die UID einer aufgelegten Karte an.
Der maschinenlesbare Status ist lokal unter
`http://127.0.0.1:8000/api/nfc/status` erreichbar. `scripts/pi-verify.sh`
verlangt fuer eine erfolgreiche Zielsystempruefung einen angeschlossenen und
betriebsbereiten ACR122U.

Wenn der Leser in `lsusb`, aber nicht in `pcsc_scan` erscheint, helfen die
Diagnoseausgaben:

```bash
systemctl status pcscd.service --no-pager
journalctl -u pcscd.service --no-pager -n 100
```
