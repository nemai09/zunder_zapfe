# Kiosk-WebUI

Status: Milestone-5-Alpha

Die Kiosk-WebUI ist ein lokaler, zustandsbasierter Client der HTTP-API. Sie
besteht aus statischem HTML, CSS und JavaScript ohne externe Laufzeitabhängigkeit
oder Internetzugriff. Der Browser besitzt keine eigene Zapflogik: Der
Backend-Zustand entscheidet immer, welche Ansicht und Aktion zulässig ist.

| Backendzustand | Kioskansicht | Primäre Aktion |
| --- | --- | --- |
| `idle` | NFC-Aufforderung und Leserstatus | Karte auflegen |
| `authenticated` | Benutzer, Verbrauch, Getränk und Portionswahl | Portion wählen |
| `portion_pouring` | Ist-/Zielmenge und Fortschritt | Abbrechen |
| `top_up_available` | Countdown und Nachfüllfläche | gedrückt halten |
| `top_up_pouring` | aktive Nachfüllanzeige | loslassen |
| `fault_locked`, `emergency_stop` | Sperrgrund und Admin-Hinweis | sicher zurücksetzen |
| Backend nicht erreichbar | Verbindungsfehler | automatisch erneut verbinden |

Während jeder Ventilfreigabe sendet der Client Heartbeats. Das Backend schließt
das Ventil unabhängig davon über seinen Watchdog, wenn Browser oder Verbindung
ausfallen. Beim Nachfüllen lösen `pointerup`, `pointercancel`, verlorener
Pointer-Fokus, ausgeblendete Seite und Fensterfokusverlust einen Stoppversuch
aus. Der Backend-Watchdog bleibt die unabhängige Rückfallebene.

Die WebUI zeigt keine NFC-UID. Ihr Buildstring stammt aus `GET /api/health` und
folgt [`../versioning.md`](../versioning.md).

Traceability: `ZZ-AUT-010`, `ZZ-TAP-001`, `ZZ-TAP-002`, `ZZ-TAP-005`,
`ZZ-TAP-007`, `ZZ-TAP-009`, `ZZ-SAF-008`, `ZZ-UI-001`, `ZZ-UI-002`,
`ZZ-UI-003` und `ZZ-NFR-003`.
