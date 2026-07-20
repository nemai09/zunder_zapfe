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
| 5 / PR 5 | Touchoptimierte Push-to-Fill-Kiosk-WebUI nach CR-001 | abgeschlossen |
| 6 / PR 6 | Adminmodus, Verwaltungs-API sowie Benutzer- und NFC-Verwaltung | in Arbeit |
| 7 / PR 7 | Weitere Admin-WebUI, Webauthentifizierung, Getränke, Fässer und Parameter | geplant |
| 8 / PR 8 | Reale Ventil-, Durchfluss- und Not-Aus-Adapter | geplant |
| 9 / PR 9 | Kalibrierung, Gesamttest und Alpha-Härtung | geplant |

## Milestone 5: Kiosk-WebUI Alpha

Der Kiosk bildet den Backend-Zustandsautomaten als lokale Touchoberfläche ab.
Er umfasst NFC-Aufforderung, Benutzer- und Verbrauchsanzeige, genau eine große
gedrückt gehaltene Zapffläche, Istmenge, Logout sowie Sicherheits- und
Verbindungsfehler. Die zweispaltige Kartenanordnung und der sichtbare
Inaktivitäts-Timeout gehören direkt zum Kiosk-Umfang. Standard- und
Sonderportionen bleiben gemäß CR-001 im Backend erhalten, werden im Kiosk aber
nicht mehr angeboten.

Die Bedienoberfläche kommuniziert ausschließlich über die dokumentierte
HTTP-API. Sie steuert weder Hardware noch SQLite direkt. Layout und Bedienablauf
wurden bei `800 × 480` auf dem Raspberry Pi geprüft. Der reale ACR122U erfasst
kurz aufgelegte NFC-Armbänder ereignisgesteuert und erholt sich nach USB- oder
PC/SC-Unterbrechungen ohne Neustart des Webdienstes.

Traceability: `ZZ-AUT-002`, `ZZ-AUT-010`, `ZZ-TAP-008`, `ZZ-TAP-013`,
`ZZ-TAP-014`, `ZZ-HW-001`, `ZZ-UI-001`, `ZZ-UI-002`, `ZZ-UI-004`,
`ZZ-UI-005` und `ZZ-NFR-005`.

## Milestone 6: Admin-Grundlage und Benutzerverwaltung

Der nächste vertikale Checkpoint ergänzt den lokalen Adminmodus auf Basis der
bereits per NFC authentifizierten Adminrolle. Admins behalten denselben
Benutzer- und Zapfablauf; nur ihnen wird zusätzlich der Einstieg in die
Administration angeboten. Der Adminmodus sperrt Zapfaktionen und besitzt einen
separat konfigurierbaren Inaktivitäts-Timeout mit `30 s` Alpha-Default.

Der erste vollständig abnehmbare Verwaltungsablauf umfasst schlanke
Benutzerdaten, Rollen- und Aktivstatus, Sperren und Entfernen bestehender
Armbandzuordnungen sowie die Live-Zuordnung eines kurz aufgelegten
Veranstaltungsarmbands. Die UID stammt
dabei ausschließlich vom Hardwareadapter. Alle schreibenden Adminaktionen
werden mit ausführendem Admin und alten beziehungsweise neuen Werten auditiert.

Weitere Bereiche werden im Admin-Grundgerüst sichtbar gruppiert, aber erst in
Milestone 7 vollständig ausgebaut. Passwortgeschützter Zugriff aus dem späteren
Admin-WLAN bleibt von der lokalen NFC-Adminsitzung getrennt.

Die Benutzerliste bleibt durch Suche, Statusfilter und Scrollen auch bei 20 bis
30 Einträgen bedienbar. Der Lockscreen unterscheidet unbekannte und gesperrte
Armbänder. Milestone 6 bleibt bis zur Zielsystemprüfung in Arbeit.

Traceability: `ZZ-AUT-001`, `ZZ-AUT-003` bis `ZZ-AUT-008`, `ZZ-AUT-011`,
`ZZ-DAT-003`, `ZZ-UI-001` und `ZZ-UI-006`.
