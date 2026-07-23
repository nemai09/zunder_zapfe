# Admin-WLAN auf dem Raspberry Pi

Status: Access Point in `M7.3 OPS`, lokaler Moduswechsel in `M7.7 OPS`;
Zielsystemprüfung ausstehend

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

Der Access Point ist der Standard für den Standalone-Betrieb. Falls das
Ethernetkabel anderweitig benötigt wird, kann der physisch präsente
Superadmin im lokalen Low-Level-Menü vorübergehend zu einem bereits
gespeicherten WLAN-Clientprofil wechseln. Der Sperrbildschirm zeigt dazu
`WLAN · AP` oder `WLAN · Client`.

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

## Lokaler AP-/Client-Moduswechsel

`install-pi.sh` installiert den festen Systemhelfer
`/usr/local/sbin/zunder-zapfe-wifi-mode`. Er unterstützt ausschließlich:

```text
zunder-zapfe-wifi-mode status
zunder-zapfe-wifi-mode ap
zunder-zapfe-wifi-mode client
```

Der Clientwechsel wählt unter den bestehenden NetworkManager-Profilen das
automatisch verbindbare WLAN-Profil mit der höchsten Priorität. Das Profil
`zunder-zapfe-ap` sowie andere AP-Profile sind ausgeschlossen. Das Menü sucht
keine WLANs, fragt keine Schlüssel ab und legt keine Profile an. Ein
Clientprofil muss daher vorher mit den normalen Raspberry-Pi-Werkzeugen
eingerichtet und auf automatisches Verbinden gestellt worden sein.

Beim Wechsel zu `client` wird das automatische Starten des Access Points
deaktiviert und das bekannte Profil aktiviert. Schlägt die Verbindung fehl,
stellt der Helfer den AP-Autostart wieder her und versucht sofort,
`ZUNDER_ZAPFE` zu reaktivieren. Beim Wechsel zu `ap` wird das AP-Profil wieder
auf automatischen Start gesetzt. Die Einstellung bleibt dadurch auch nach
einem Neustart wirksam.

Die Anwendung läuft weiterhin mit `NoNewPrivileges=true` und erhält kein
`sudo`. Eine installierte Polkit-Regel erlaubt dem Dienstbenutzer nur die für
den Profilwechsel erforderlichen NetworkManager-Aktionen einschließlich der
Aktivierung des WPA-geschützten Hotspots. Offene Hotspots und das globale
Ein- oder Ausschalten des Netzwerks werden nicht freigegeben. Das
Low-Level-Menü und `POST /api/system/wifi/mode` sind auf Loopback begrenzt,
verlangen bei jedem Aufruf den Zustand `superadmin` sowie die physisch
präsente externe Superadmin-Karte und werden von nginx nicht an Smartphones
weitergereicht. Normale NFC-Admins erhalten über den blauen Button keinen
Systemzugang; er verweist nur auf die Smartphone-WebUI.

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

1. Der vom Systemhelfer gemeldete Modus ist `ap` oder `client`.
2. Im AP-Modus ist `zunder-zapfe-ap` an `wlan0` aktiv, die SSID lautet exakt
   `ZUNDER_ZAPFE` und der Pi besitzt `10.42.0.1/24`.
3. Im Clientmodus besteht eine IPv4-Verbindung über ein bekanntes Profil.
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
14. Der blaue Button eines NFC-angemeldeten Admins zeigt nur den
    Smartphone-Hinweis und verändert den Backendzustand nicht.
15. AP → Client → AP funktioniert, sofern ein bekanntes Clientprofil vorhanden
    ist und die Superadmin-Karte während der Aktion aufliegt. Der
    Kioskindikator folgt dem jeweils aktiven Modus.
16. Ein absichtlich unerreichbares Clientprofil führt zu einer verständlichen
    Fehlermeldung und reaktiviert soweit möglich `ZUNDER_ZAPFE`.

## Offizielle Referenzen

- [Raspberry Pi: Access Point mit NetworkManager](https://www.raspberrypi.com/documentation/configuration/wireless/wireless-access-point.md)
- [NetworkManager: `nmcli wifi hotspot`](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nmcli.html)
- [NetworkManager: AP-, WPA- und IPv4-Profile](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nm-settings-nmcli.html)

Traceability: `ZZ-SYS-001`, `ZZ-SYS-002`, `ZZ-AUT-003`, `ZZ-UI-007`,
`ZZ-UI-008`, `ZZ-NET-001`, `ZZ-NET-002` und `ZZ-NET-003`.
