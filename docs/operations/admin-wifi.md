# Admin-WLAN auf dem Raspberry Pi

Status: implementiert in `M7.3 OPS`, Zielsystemprüfung ausstehend

## Ziel

Der Raspberry Pi stellt unabhängig von einer vorhandenen Infrastruktur einen
WPA-geschützten Access Point bereit:

| Eigenschaft | Festlegung |
| --- | --- |
| SSID | `ZUNDER_ZAPFE` |
| Verbindungsprofil | `zunder-zapfe-ap` |
| Schnittstelle | `wlan0` |
| Band | 2,4 GHz für breite Smartphone-Kompatibilität |
| Pi-Adresse | `10.42.0.1/24` |
| Adressvergabe | DHCP über NetworkManager |
| Internetzugang | nicht erforderlich |
| Admin-URL | `http://10.42.0.1/admin` |

WLAN-Schlüssel und persönliche Adminpasswörter sind getrennte Zugangsdaten.
Keiner dieser Werte wird im Repository abgelegt.

## Technische Basis

Raspberry Pi OS verwendet seit Bookworm standardmäßig NetworkManager. Das
Installationsskript soll deshalb weder eine parallele `hostapd`-/`dnsmasq`-
Konfiguration noch ein zweites Netzwerkverwaltungssystem einführen.

Das Profil verwendet:

```text
802-11-wireless.mode=ap
802-11-wireless.ssid=ZUNDER_ZAPFE
802-11-wireless.band=bg
802-11-wireless-security.key-mgmt=wpa-psk
802-11-wireless-security.proto=rsn
ipv4.method=shared
ipv4.addresses=10.42.0.1/24
ipv4.never-default=yes
ipv6.method=disabled
connection.autoconnect=yes
```

`ipv4.method=shared` stellt über NetworkManager den lokalen DHCP- und
DNS-Dienst bereit. Die Anlage setzt keinen Internet-Uplink voraus.

## Einmalige Installation

`install-pi.sh` installiert NetworkManager, `iw`, nginx sowie das
Einrichtungswerkzeug, aktiviert den Access Point aber bewusst noch nicht. So
wird eine bestehende SSH-Verbindung nicht überraschend getrennt.

Vor der Einrichtung muss das WLAN-Land gesetzt sein, beispielsweise:

```bash
sudo raspi-config nonint do_wifi_country DE
sudo zunder-zapfe-admin-wifi
```

Das zweite Kommando:

1. NetworkManager, `wlan0`, gesetztes WLAN-Land und AP-Fähigkeit prüfen.
2. Einen neuen WPA-Schlüssel verdeckt abfragen oder ein vorhandenes Profil
   unverändert weiterverwenden.
3. Das Profil ausschließlich unter dem festen Namen `zunder-zapfe-ap`
   erstellen oder gezielt aktualisieren.
4. Den Schlüssel nur im root-lesbaren NetworkManager-Profil speichern.
5. Vor dem Trennen eines anderen aktiven WLAN-Profils die exakte interaktive
   Bestätigung `ZUNDER_ZAPFE` verlangen.
6. Das Profil aktivieren und die lokale Adresse prüfen.
7. Einen lokalen HTTP-Zugang von `10.42.0.1:80` zur weiterhin nur an
   `127.0.0.1:8000` gebundenen Anwendung einrichten.
8. Die Startreihenfolge so festlegen, dass ein fehlgeschlagener Access Point
   weder Kiosk noch Zapfbackend am lokalen Start hindert.

`nginx-light` dient als kleiner Reverse Proxy. Er akzeptiert ausschließlich
Clients aus `10.42.0.0/24` und veröffentlicht nur `/admin`, die
Smartphone-APIs `/api/web-auth/*` und `/api/web-admin/*` sowie
`/api/health`. Kiosk-, lokale Admin-, Zapf- und Simulator-APIs bleiben über
den Proxy unerreichbar. Uvicorn bleibt auf Loopback gebunden.

Das Skript verändert oder löscht keine fremden NetworkManager-Profile. Ein
vorhandenes `zunder-zapfe-ap` wird ohne Änderung seines Schlüssels auf die
festen, nicht geheimen Parameter aktualisiert.

## Zugangsdaten

- Das Repository enthält nur Profilnamen und nicht vertrauliche Parameter.
- Der WLAN-Schlüssel wird bei der Installation verdeckt eingegeben und nicht
  als Kommandozeilenargument übernommen.
- Die NetworkManager-Schlüsseldatei bleibt root-lesbar.
- `config/web.env.example`, Logs und Testdaten enthalten keinen echten
  WLAN-Schlüssel.
- Ein Wechsel des WLAN-Schlüssels erfolgt später über ein explizites
  Zielsystemkommando; bestehende Smartphones müssen sich danach neu verbinden.

## Verifikation auf dem Zielsystem

Nach der bewussten Ersteinrichtung:

```bash
./scripts/pi-verify.sh
```

Vor der Ersteinrichtung überspringt die Prüfung nur die beiden WLAN-Schritte
mit einem eindeutigen Hinweis. Nach gesetzter Markierung sind sie verbindlich.

Die Zielsystemprüfung wird um folgende Punkte ergänzt:

1. `zunder-zapfe-ap` ist aktiv und an `wlan0` gebunden.
2. Die SSID lautet exakt `ZUNDER_ZAPFE`.
3. Der Pi besitzt `10.42.0.1/24`.
4. Ein Smartphone erhält per DHCP eine Adresse.
5. `http://10.42.0.1/api/health` ist erreichbar.
6. `/admin` fordert ohne gültige Sitzung zur persönlichen Anmeldung auf.
7. Der Kiosk bleibt parallel über `127.0.0.1:8000` funktionsfähig.
8. Ein Neustart aktiviert Access Point, Backend und Kiosk erneut.
9. WLAN- und Adminpasswörter erscheinen weder in Git-Diff noch Dienstlogs.
10. Veranstaltungen und Getränke lassen sich anlegen und ein Fass lässt sich
    nach bewusster Bestätigung wechseln.
11. Der neue aktive Fasskontext erscheint anschließend im Kiosk und in der
    Smartphone-Übersicht.
12. Die Datenansicht trennt Buchungen und Summen nach Veranstaltung und
    kombiniert Benutzer-, Fass-, Art-, Abschluss- und Zeitraumfilter.
13. Audit und technische Ereignisse sind lesbar; Buchungen bieten weder
    Bearbeiten noch Löschen an.

## Offizielle Referenzen

- [Raspberry Pi: Access Point mit NetworkManager](https://www.raspberrypi.com/documentation/configuration/wireless/wireless-access-point.md)
- [NetworkManager: `nmcli wifi hotspot`](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nmcli.html)
- [NetworkManager: AP-, WPA- und IPv4-Profile](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nm-settings-nmcli.html)

Traceability: `ZZ-SYS-001`, `ZZ-SYS-002`, `ZZ-AUT-003`, `ZZ-UI-008`,
`ZZ-NET-001` und `ZZ-NET-002`.
