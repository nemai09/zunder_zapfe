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

## PC/SC-Zugriff fuer den Webdienst freigeben

Die Debian-PC/SC-Policy erlaubt den Zugriff standardmaessig fuer eine aktive
Desktop-Sitzung. Der Webdienst laeuft jedoch als systemd-Dienst und gilt dabei
nicht als aktive Sitzung. Ohne zusaetzliche Freigabe meldet der NFC-Endpunkt:

```text
Failed to establish context: Access denied. (0x8010006A)
```

Auch der Umstand, dass `sudo pcsc_scan` funktioniert, `pcsc_scan` ohne `sudo`
aber fehlschlaegt, weist auf diese fehlende Berechtigung hin.

Fuer den Benutzer des Webdienstes wird einmalig eine eng begrenzte Polkit-Regel
angelegt. Im folgenden Beispiel heisst dieser Benutzer `zapfe`:

```bash
sudo nano /etc/polkit-1/rules.d/60-zunder-zapfe-pcsc.rules
```

Inhalt:

```javascript
polkit.addRule(function(action, subject) {
    if (
        (
            action.id == "org.debian.pcsc-lite.access_pcsc" ||
            action.id == "org.debian.pcsc-lite.access_card"
        ) &&
        subject.user == "zapfe"
    ) {
        return polkit.Result.YES;
    }
});
```

Falls der Dienst unter einem anderen Benutzer laeuft, muss `zapfe` in der Regel
durch dessen Benutzernamen ersetzt werden. Anschliessend:

```bash
sudo chmod 644 /etc/polkit-1/rules.d/60-zunder-zapfe-pcsc.rules
sudo systemctl restart pcscd.service
sudo systemctl restart zunder-zapfe-web.service
```

Die Regel erlaubt ausschliesslich diesem Benutzer den Zugriff auf PC/SC und die
Smartcard. Sie erteilt weder allgemeinen Root-Zugriff noch Schreibrechte am
Git-Repository.

Danach muss die Leserpruefung ohne `sudo` funktionieren:

```bash
pcsc_scan
```

Der Anwendungsstatus kann separat geprueft werden:

```bash
curl http://127.0.0.1:8000/api/nfc/status
```

Ohne aufgelegte Karte wird `state` als `ready`, mit aufgelegter Karte als
`card` inklusive UID erwartet.

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
journalctl -u zunder-zapfe-web.service --no-pager -n 100
```
