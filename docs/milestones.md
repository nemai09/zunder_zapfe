# Entwicklungsmeilensteine

Die Meilensteine entsprechen abgeschlossenen, über Pull Requests integrierten
Projektabschnitten. Ein Meilenstein ist erst abgeschlossen, wenn seine
automatisierten Prüfungen und die jeweils notwendige Zielsystemprüfung
bestanden sind.

| Milestone | Inhalt | Status |
| --- | --- | --- |
| 1 / PR 1 | Hardware-Zwischenlayer, Simulatoren und Zapf-Zustandsautomat | abgeschlossen |
| 2 / PR 2 | SQLite-Persistenz, Migrationen und Diagnosezugriff | abgeschlossen |
| 3 / PR 3 | NFC-, Zapf- und Persistenzintegration mit Smoke-Test | abgeschlossen |
| 4 / PR 4 | Dokumentations-, Schnittstellen- und Community-Baseline | abgeschlossen |
| 5 / PR 5 | Touchoptimierte Kiosk-WebUI für den vollständigen Zapfablauf | in Arbeit |
| 6 / PR 6 | Webauthentifizierung und Verwaltungs-API | geplant |
| 7 / PR 7 | Admin-WebUI für Benutzer, NFC, Getränke, Fässer und Parameter | geplant |
| 8 / PR 8 | Reale Ventil-, Durchfluss- und Not-Aus-Adapter | geplant |
| 9 / PR 9 | Kalibrierung, Gesamttest und Alpha-Härtung | geplant |

## Milestone 5: Kiosk-WebUI Alpha

Der Kiosk bildet den Backend-Zustandsautomaten als lokale Touchoberfläche ab.
Er umfasst NFC-Aufforderung, Benutzer- und Verbrauchsanzeige, die
Standardportionen `300 ml` und `500 ml`, eine optionale persönliche
Sonderportion, Zapffortschritt, Abbruch, gedrückt gehaltenes Nachfüllen,
Logout sowie Sicherheits- und Verbindungsfehler.

Die Bedienoberfläche kommuniziert ausschließlich über die dokumentierte
HTTP-API. Sie steuert weder Hardware noch SQLite direkt. Die erste Fassung ist
ein visueller Review-Checkpoint und darf innerhalb des Milestones nach
Bedienfeedback weiterentwickelt werden.

Traceability: `ZZ-AUT-010`, `ZZ-TAP-001`, `ZZ-TAP-002`, `ZZ-TAP-005`,
`ZZ-TAP-007`, `ZZ-TAP-009`, `ZZ-UI-001`, `ZZ-UI-002`, `ZZ-UI-003` und
`ZZ-NFR-003`.
