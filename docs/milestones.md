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
| 6 / PR 6 + PR 6.1 | Adminmodus, Verwaltungs-API sowie Benutzer- und NFC-Verwaltung | abgeschlossen |
| 7 / PR 7 | Smartphone-Admin-WebUI, Webauthentifizierung und priorisierte Verwaltungsabläufe | in Umsetzung |
| 8 / PR 8 | Reale Ventil-, Durchfluss- und Not-Aus-Adapter | geplant |
| 9 / PR 9 | Kalibrierung, Gesamttest und Alpha-Härtung | geplant |

`PR 6.1` ist ausschließlich der Dokumentationsnachtrag zum bereits integrierten
PR 6. Er erzeugt keinen neuen Meilenstein und verändert weder Produktversion
noch die folgenden logischen PR-Bezeichnungen. Die fortlaufende Nummer, die
GitHub dem Nachtrags-PR technisch zuweist, kann davon abweichen.

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

Dieser vertikale Checkpoint ergänzt den lokalen Adminmodus auf Basis der
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
Armbänder. Die automatisierten Prüfungen sowie die Bedienprüfung mit realem
ACR122U auf dem Raspberry Pi wurden erfolgreich abgeschlossen.

Traceability: `ZZ-AUT-001`, `ZZ-AUT-002`, `ZZ-AUT-004`, `ZZ-AUT-005`,
`ZZ-AUT-007`, `ZZ-AUT-008`, `ZZ-AUT-011`, `ZZ-DAT-003`, `ZZ-UI-001` und
`ZZ-UI-006`. Passwort-Webauthentifizierung (`ZZ-AUT-003`) und der produktive
Initial-Admin-Prozess (`ZZ-AUT-006`) bleiben ausdrücklich außerhalb dieses
Milestones.

## Milestone 7: Smartphone-Administration

Gemäß [CR-002](../requirements/changes/CR-002-smartphone-administration.md)
wird die lokale Adminoberfläche vorerst weder geöffnet noch weiter ausgebaut.
Ihr in Milestone 6 geprüfter Entwicklungsstand bleibt erhalten. Der blaue
Admin-Button bleibt ausschließlich für Admins sichtbar. Der in M7.7
implementierte Zugriff auf das WLAN-Systemmenü über diesen Button ist gemäß
[CR-003](../requirements/changes/CR-003-externer-superadmin.md) ein
Übergangsstand. Im Zielzustand zeigt der Button nur einen Hinweis; das
Low-Level-Menü wird an eine externe, präsenzgebundene Superadmin-Karte gebunden.

Der Schwerpunkt verschiebt sich auf eine einfache, responsive Admin-WebUI für
Smartphones im eigenständigen WLAN `ZUNDER_ZAPFE`. Jeder Admin verwendet ein
persönliches Passwort im gemeinsamen Benutzerdatensatz. Die Websitzung bleibt
von der NFC-Kiosksitzung getrennt und funktioniert ohne Internet.

### Arbeitspakete

| Paket | Ergebnis |
| --- | --- |
| `M7.1 PLAN` | CR-002, Zielarchitektur, Anforderungsversion 0.6 und WLAN-Plan |
| `M7.2 FEAT` | persönliche Adminpasswörter, Websitzungen, Initial-Admin, Passwortwechsel und gemeinsame Autorisierung |
| `M7.3 OPS` | NetworkManager-Access-Point `ZUNDER_ZAPFE`, lokaler Webzugang und Pi-Verifikation |
| `M7.4 UI` | responsive Adminhülle, Login, Kioskhinweis sowie Benutzer- und NFC-Verwaltung; implementiert, Pi-Abnahme offen |
| `M7.5 FEAT` | Veranstaltungen, Getränke, Fassverwaltung und geführter Fasswechsel; implementiert, Pi-Abnahme offen |
| `M7.6 FEAT` | Buchungsansicht, Abrechnungssummen, Audit, technische Ereignisse und Statistik; implementiert, Pi-Abnahme offen |
| `M7.7 OPS/FEAT` | lokales WLAN-Systemmenü, operativer Fassbereich, zusammengefasste Loginbuchungen und Registrierungsbegrüßung implementiert; Diagnose, technische Einstellungen, Wartung und Safety-Reset folgen |
| `M7.8 PLAN/FEAT` | CR-003, externer Superadmin-Vertrag und unveränderliche lokale Kartenidentität |
| `M7.9 DB/FEAT` | präsenzgebundener Backendzustand, beidseitige Kartenkollisionssperre, actorfähiges Audit und benutzerlose Wartungsentnahme implementiert; Pi-Abnahme offen |
| `M7.10 UI` | Low-Level-Menü mit WLAN, Notfallanlage, Wartungszapfung und Diagnose sowie wirkungsloser normaler Admin-Button implementiert; Pi-Abnahme offen |
| `M7.11 TEST` | vollständige Schnittstellen-, Smartphone-, Superadmin-, Neustart- und Zielsystemabnahme |

Die Arbeitspakete dürfen in mehrere Pull Requests aufgeteilt werden; ihre
Kennung ist unabhängig von der fortlaufenden GitHub-PR-Nummer. Netzwerkzugriff
wird erst nach wirksamer Webauthentifizierung aktiviert. Abgeschlossene
Zapfvorgänge bleiben als unveränderliche Rohdatensätze erhalten und werden
über ihre NFC-Anmeldesitzung fachlich zusammengefasst. Storno, verbindlicher
Export, Backup,
Happy-Hour-Regeln und lokaler Notzugang bleiben entsprechend ihrem
Anforderungsstatus außerhalb des verbindlichen Milestone-7-Umfangs.

Technische Details stehen unter
[`Smartphone-Admin-WebUI`](architecture/smartphone-admin-webui.md) und
[`Admin-WLAN`](operations/admin-wifi.md). Der durch CR-003 ergänzte lokale
Wartungszugang ist unter [`Externer Superadmin`](architecture/superadmin.md)
abgegrenzt.

Traceability: `ZZ-SYS-001`, `ZZ-SYS-004` bis `ZZ-SYS-006`,
`ZZ-AUT-003` bis `ZZ-AUT-007`, `ZZ-AUT-012`, `ZZ-KEG-001` bis
`ZZ-KEG-004`, `ZZ-KEG-006`, `ZZ-SAF-003`, `ZZ-SAF-007`, `ZZ-MNT-001`,
`ZZ-MNT-002`, `ZZ-BIL-001` bis `ZZ-BIL-004`, `ZZ-UI-007` bis `ZZ-UI-009`,
`ZZ-NET-001`, `ZZ-NET-002`, `ZZ-NET-003`, `ZZ-DAT-001` bis `ZZ-DAT-007`
und `ZZ-DAT-009`.
