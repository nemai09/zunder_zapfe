# Kiosk-WebUI

Status: Milestone 5 abgeschlossen

Die Kiosk-WebUI ist ein lokaler, zustandsbasierter Client der HTTP-API. Sie
besteht aus statischem HTML, CSS und JavaScript ohne externe
Laufzeitabhängigkeit oder Internetzugriff. Der Browser besitzt keine eigene
Zapflogik: Der Backendzustand entscheidet immer, welche Ansicht und Aktion
zulässig ist.

| Backendzustand | Kioskansicht | Primäre Aktion |
| --- | --- | --- |
| `idle` | NFC-Aufforderung und Leserstatus | Karte auflegen |
| `idle` mit `registration_welcome` | kurze Begrüßung nach Armbandzuordnung | keine; Rückkehr nach drei Sekunden |
| `authenticated` | Benutzer, Verbrauch, Getränk und große Zapffläche | gedrückt halten |
| `manual_pouring` | laufende Istmenge auf der Zapffläche | loslassen |
| `admin` | M7.7-Übergangsstand: lokales WLAN-Systemmenü | vorhandenen WLAN-Modus wechseln |
| kompatibler Portions-/Wartungszustand | neutraler Statushinweis | über auslösenden Client abschließen |
| `fault_locked`, `emergency_stop` | Sperrgrund und Admin-Hinweis | sicher zurücksetzen |
| Backend nicht erreichbar | Verbindungsfehler | automatisch erneut verbinden |

Im Idle-Zustand unterscheidet die Anzeige eine unbekannte Karte (`Karte nicht
erkannt`) von einer gesperrten Karte beziehungsweise einem gesperrten Benutzer
(`Karte gesperrt`). Das Backend hält diese Rückmeldung kurzzeitig vor, damit
sie auch sichtbar bleibt, wenn das Armband direkt nach dem Leserton entfernt
wird. Weder UID noch Benutzerinformationen werden dabei angezeigt.

Die Kioskoberfläche bietet gemäß
[`CR-001`](../../requirements/changes/CR-001-manual-push-to-fill.md) keine
Portionswahl und kein Nachfüllen mehr an. Die entsprechenden Backendaktionen
bleiben als Kompatibilitätsfunktionen vorhanden.

Im Landscape-Kiosk steht die Zapffläche links und erstreckt sich über die Höhe
der beiden Informationsreihen rechts. Dort bleibt das aktive Getränk oben;
persönlicher Verbrauch und Betrag stehen darunter nebeneinander. Für
angemeldete Admins erscheint links neben dem Logout der blaue Einstieg in die
Administration; beide Aktionen belegen zusammen die Breite der rechten
Informationsspalte. Der manuelle Logout bleibt rechts im Kopfbereich sichtbar.
Der Admin-Einstieg öffnet gemäß CR-002 nur das lokale WLAN-Systemmenü; die
vollständige Verwaltungsoberfläche aus Milestone 6 bleibt erhalten, wird aber
nicht geöffnet. Das Systemmenü erfordert weiterhin die NFC-Adminsitzung und
kehrt über „Zurück“ in den normalen Zapfmodus zurück.

CR-003 löst diesen Einstieg ab. Nach M7.10 bleibt der blaue Admin-Button
sichtbar, zeigt aber nur einen Toast zur Smartphone-WebUI. Das Low-Level-Menü
öffnet dann ausschließlich durch die präsente externe Superadmin-Karte. Bis
zur Laufzeitumstellung in M7.9/M7.10 beschreibt der vorige Absatz weiterhin
das tatsächlich ausführbare Übergangsverhalten.
Ein schmaler Balken am unteren
Bildschirmrand zeigt während der gesamten Sitzung die verbleibende Zeit des
15-Sekunden-Inaktivitäts-Timeouts. Jede Touchberührung meldet Aktivität an das
Backend; eine laufende Zapfung hält die Sitzung ebenfalls aktiv.

## Laufzeitverhalten auf dem Raspberry Pi

Der sicherheits- und bedienrelevante Zapfstatus bleibt mit `300 ms` kurz
abgefragt. Sekundäre Informationen werden unabhängig davon gedrosselt:

- NFC-Hardwarestatus höchstens alle `2 s` im Idle-Zustand;
- Verbrauch, Fass und Optionen bei Kontextänderung, ansonsten alle `15 s`;
- Health- und WLAN-Status alle `30 s`.

Der WLAN-Endpunkt hält sein Ergebnis ebenfalls `30 s` im Prozessspeicher.
Ein bewusster AP-/Client-Wechsel aktualisiert den Cache sofort. Dadurch startet
die Kiosk-Anzeige den aus mehreren `nmcli`-Abfragen bestehenden Systemhelfer
nicht mehr alle zwei Sekunden.

Nach jeder Statusantwort wird der sichtbare Timeout fortgeschrieben. Die
übrige Oberfläche wird nur neu gerendert, wenn sich ein fachlich sichtbarer
Wert geändert hat. Der Timeout-Balken verwendet `transform: scaleX()` statt
einer layoutauslösenden Breitenänderung. Datums-, Volumen- und Geldformatierer
werden einmalig wiederverwendet. Die Abfrageschleife plant den nächsten Lauf
erst nach Abschluss des vorherigen und kann daher keine Requests aufstauen.

Diese Optimierungen verändern weder den `650 ms`-Heartbeat während einer
Ventilfreigabe noch die unabhängige Backendüberwachung und ihre Safety-Grenzen.

## Touch- und Sicherheitsverhalten

Eine konfigurierbare Aktivierungsentprellung unterdrückt sehr kurze
Berührungen. Nach dem Start wird das Ventil nur durch den Backendzustandsautomaten
geöffnet. Das Loslassen selbst wird nicht entprellt oder verzögert.

`pointerup`, `pointercancel`, verlorener Pointer-Fokus, ausgeblendete Seite und
Fensterfokusverlust lösen einen Stoppversuch aus. Während jeder Ventilfreigabe
sendet der Client Heartbeats. Fällt Browser oder Verbindung aus, schließt das
Backend unabhängig davon über seinen Watchdog.

Die Alpha-Werte sind `120 ms` Aktivierungsentprellung und `30 s` maximale
manuelle Öffnungsdauer. Beide sind konfigurierbar und vor realem Betrieb gemäß
`OD-012` zu kalibrieren.

Die WebUI zeigt keine NFC-UID. Ihr Buildstring stammt aus `GET /api/health` und
folgt [`../versioning.md`](../versioning.md).

Für die hardwarelose Alpha-Phase zeigt die Kopfleiste außerdem dezent den vom
Backend gemeldeten Sollzustand `valve_open` als `DEBUG · Ventil EIN/AUS`. Dies
ist keine Rückmeldung eines physischen Ventils und muss zusammen mit dem
temporären Flow-Debugmodus vor Produktivbetrieb entfernt werden.
Zwischen Ventil- und Steuerungsstatus zeigt ein weiterer Indikator den vom
Systemhelfer erkannten WLAN-Modus `AP`, `Client` oder einen Fehlerzustand.
Er besteht nur aus Statuspunkt und Text ohne eigene Umrandung; die Umrandung
der temporären Ventil-Debuganzeige bleibt davon unberührt.

Traceability: `ZZ-AUT-010`, `ZZ-TAP-008`, `ZZ-TAP-013`, `ZZ-TAP-014`,
`ZZ-SAF-008`, `ZZ-UI-001`, `ZZ-UI-002`, `ZZ-UI-004`, `ZZ-UI-005` und
`ZZ-NFR-005`, `ZZ-UI-007`, `ZZ-UI-009` und `ZZ-NET-003`.
