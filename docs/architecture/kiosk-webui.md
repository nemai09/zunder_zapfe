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
| `authenticated` | Benutzer, Verbrauch, Getränk und große Zapffläche | gedrückt halten |
| `manual_pouring` | laufende Istmenge auf der Zapffläche | loslassen |
| kompatibler Portions-/Wartungszustand | neutraler Statushinweis | über auslösenden Client abschließen |
| `fault_locked`, `emergency_stop` | Sperrgrund und Admin-Hinweis | sicher zurücksetzen |
| Backend nicht erreichbar | Verbindungsfehler | automatisch erneut verbinden |

Die Kioskoberfläche bietet gemäß
[`CR-001`](../../requirements/changes/CR-001-manual-push-to-fill.md) keine
Portionswahl und kein Nachfüllen mehr an. Die entsprechenden Backendaktionen
bleiben als Kompatibilitätsfunktionen vorhanden.

Im Landscape-Kiosk steht die Zapffläche links und erstreckt sich über die Höhe
der beiden Informationsreihen rechts. Dort bleibt das aktive Getränk oben;
persönlicher Verbrauch und Betrag stehen darunter nebeneinander. Der manuelle
Logout bleibt rechts im Kopfbereich sichtbar. Ein schmaler Balken am unteren
Bildschirmrand zeigt gemäß CR-002 während der gesamten Sitzung die verbleibende
Zeit des 15-Sekunden-Inaktivitäts-Timeouts. Jede Touchberührung meldet Aktivität
an das Backend; eine laufende Zapfung hält die Sitzung ebenfalls aktiv.

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

Traceability: `ZZ-AUT-010`, `ZZ-TAP-008`, `ZZ-TAP-013`, `ZZ-TAP-014`,
`ZZ-SAF-008`, `ZZ-UI-001`, `ZZ-UI-002`, `ZZ-UI-004`, `ZZ-UI-005` und
`ZZ-NFR-005`.
