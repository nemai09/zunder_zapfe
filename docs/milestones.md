# Entwicklungsmeilensteine

Die Meilensteine entsprechen fachlichen Projektabschnitten und sind unabhängig
von den fortlaufenden Pull-Request-Nummern auf GitHub. Ein Meilenstein ist erst
abgeschlossen, wenn seine
automatisierten Prüfungen und die jeweils notwendige Zielsystemprüfung
bestanden sind.

| Milestone | Inhalt | Status |
| --- | --- | --- |
| 1 | Hardware-Zwischenlayer, Simulatoren und Zapf-Zustandsautomat | abgeschlossen |
| 2 | SQLite-Persistenz, Migrationen und Diagnosezugriff | abgeschlossen |
| 3 | NFC-, Zapf- und Persistenzintegration mit Smoke-Test | abgeschlossen |
| 4 | Dokumentations-, Schnittstellen- und Community-Baseline | abgeschlossen |
| 5 | Touchoptimierte Push-to-Fill-Kiosk-WebUI nach CR-001 | abgeschlossen |
| 6 | Adminmodus, Verwaltungs-API sowie Benutzer- und NFC-Verwaltung | abgeschlossen |
| 7 | Smartphone-Admin-WebUI, Webauthentifizierung und priorisierte Verwaltungsabläufe | abgeschlossen |
| 8 | GPIO-Hardwareintegration, Offline-Betrieb und Beta-Feldkandidat | im Feld bewährt; Safety-Nacharbeit offen |
| 9 | Feldnachbereitung und priorisierte Betriebsverbesserungen | in Planung |

Frühere Bezeichnungen wie `PR 6.1` bleiben historische Checkpointnamen. Seit
mehrere Arbeitspakete in getrennten Pull Requests umgesetzt wurden, darf aus
einer Milestone-Nummer keine GitHub-PR-Nummer abgeleitet werden.

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
Admin-Button bleibt ausschließlich für Admins sichtbar. Als eng begrenzte
Ausnahme öffnet er ein lokales Low-Level-Systemmenü für den Wechsel zwischen
Access Point und einem bereits bekannten WLAN-Clientprofil.

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
| `M7.4 UI` | responsive Adminhülle, Login, Kioskhinweis sowie Benutzer- und NFC-Verwaltung |
| `M7.5 FEAT` | Veranstaltungen, Getränke, Fassverwaltung und geführter Fasswechsel |
| `M7.6 FEAT` | Buchungsansicht, Abrechnungssummen, Audit, technische Ereignisse und Statistik |
| `M7.7 OPS/FEAT` | lokales WLAN-Systemmenü, operativer Fassbereich, zusammengefasste Loginbuchungen, Registrierungsbegrüßung, lokaler Adminschutz sowie Smartphone-Abrechnung mit Top 10, Einzelanalyse, CSV-Gesamtauszug und Diagnose/Safety-Reset |
| `M7.8 TEST` | 142 automatisierte Tests sowie Bedien- und Zielsystemprüfung auf dem Raspberry Pi; abgeschlossen |

Die Arbeitspakete dürfen in mehrere Pull Requests aufgeteilt werden; ihre
Kennung ist unabhängig von der fortlaufenden GitHub-PR-Nummer. Netzwerkzugriff
wird erst nach wirksamer Webauthentifizierung aktiviert. Abgeschlossene
Zapfvorgänge bleiben als unveränderliche Rohdatensätze erhalten und werden
über ihre NFC-Anmeldesitzung fachlich zusammengefasst. Der Teilnehmerexport
ist als Alpha-CSV-Vertrag Bestandteil von `M7.7`. Storno, Korrektur,
allgemeines Backup und Wiederherstellung, Happy-Hour-Regeln und lokaler
Notzugang bleiben entsprechend ihrem Anforderungsstatus außerhalb des
verbindlichen Milestone-7-Umfangs.

Milestone 7 wurde am 25. Juli 2026 nach erfolgreicher automatisierter Prüfung
und Bedienprüfung der Smartphone-Oberfläche auf dem Raspberry Pi abgeschlossen.
Hardwareabhängige Kalibrier- und Safety-Einstellungen werden erst mit den
realen Adaptern in Milestone 8 beziehungsweise der Kalibrierung in Milestone 9
festgelegt. Die lokale Kiosk-Wartungszapfung bleibt ein späteres, eigenständiges
Bedienpaket und blockiert den Smartphone-Meilenstein nicht.

Technische Details stehen unter
[`Smartphone-Admin-WebUI`](architecture/smartphone-admin-webui.md) und
[`Admin-WLAN`](operations/admin-wifi.md).

Traceability: `ZZ-SYS-001`, `ZZ-SYS-004` bis `ZZ-SYS-006`,
`ZZ-AUT-003` bis `ZZ-AUT-007`, `ZZ-AUT-012`, `ZZ-KEG-001` bis
`ZZ-KEG-004`, `ZZ-KEG-006`, `ZZ-SAF-003`, `ZZ-SAF-007`, `ZZ-MNT-001`,
`ZZ-MNT-002`, `ZZ-BIL-001` bis `ZZ-BIL-004`, `ZZ-UI-007` bis `ZZ-UI-009`,
`ZZ-NET-001`, `ZZ-NET-002`, `ZZ-NET-003`, `ZZ-DAT-001` bis `ZZ-DAT-007`
und `ZZ-DAT-009` bis `ZZ-DAT-010`.

## Milestone 8: Hardwareintegration

Milestone 8 führt die bisher simulierten Zapfsignale kontrolliert an reale
Ein-/Ausgänge heran. Der erste Checkpoint ist ein ESP8266 als
Hardware-in-the-Loop-Durchflussemulator. Er reagiert auf das angeforderte
Ventilsignal und erzeugt sensorähnliche Impulse, ohne selbst ein Ventil oder
eine Safety-Funktion zu steuern.

Die Softwareseite verwendet BCM17 für die aktive-HIGH-Ventilfreigabe und
BCM27 für fallende Durchflussflanken. Pegelstufen und Treiber der realen
Hardware werden erst nach elektrischer Freigabe angeschlossen. Alle Adapter
bleiben hinter den bestehenden Hardware-Protocols austauschbar; Simulatoren
bleiben für automatisierte und ausdrücklich aktivierte lokale Tests erhalten.

### Arbeitspakete

| Paket | Ergebnis oder verbleibendes Ziel | Status |
| --- | --- | --- |
| `M8.1 HW` | regulärer Pi-GPIO-Pfad und ESP8266-HIL mit aktivem-HIGH-Ventilsignal, definiertem LOW-Ruhezustand, von WLAN unabhängiger Impulserzeugung und erfolgreichem Normalfluss | abgeschlossen |
| `M8.2 PLAN` | elektrischer Connectorvertrag einschließlich Pegeln, Trennung, Ruhezuständen und Fehlerfällen | teilweise dokumentiert; formale Freigabe offen |
| `M8.3 HW` | reale Ventiltreiber- und Durchflusssensorstufe hinter den GPIO-Adaptern | sechs Tage im Feld bewährt; formale elektrische Abnahme offen |
| `M8.4 HW` | unabhängige elektrische Ventilunterbrechung und realer Not-Aus-Adapter | hardwareseitige Unterbrechung vorhanden; Softwareadapter offen |
| `M8.5 TEST` | HIL- und Zielabnahme für Normalfluss, fehlenden Durchfluss, Neustart, Verbindungsabbruch und Safety-Verriegelung | Normal- und Feldbetrieb nachgewiesen; systematische Fehlerfälle offen |
| `M8.6 UI` | lokale Wartungszapfung für den abgenommenen Hardwareablauf, ohne Zapfbuchung für den ausführenden Benutzer | offen |
| `M8.7 OPS` | DS3231 als Offline-Zeitbasis, Laden vor der Zapfanwendung und lokales CLI zum einmaligen Stellen | implementiert und auf dem Zielsystem geprüft |
| `M8.8 FEAT` | lokale, NFC-adminautorisierte Systemseite für auditierten Neustart und geordnetes Herunterfahren | abgeschlossen |
| `M8.9 DB/OPS` | automatische, integritätsgeprüfte SQLite-Sicherung alle 30 Minuten und authentifizierter CSV-Download aufs Smartphone | abgeschlossen |
| `M8.10 FIX/OPS` | feldtaugliche Bereitschaftsanzeige, rein informativer Fassbestand, entspannte aktive Watchdogs, Chromium-Neustart und Einsatzübergabe | abgeschlossen |
| `M8.11 FIX/OPS/FEAT/DOC` | reparierter Backupdienststart, Kennzeichnung als `0.4.0-beta.1`, erhaltene Sitzungsmenge, Verbrauchsrang, Offline-Notfallhandbuch und bereinigte Kioskdiagnose | abgeschlossen und über PR #12 integriert |

### Abnahmekriterien

- Abgesteckte oder neu startende Komponenten lassen das Ventil geschlossen
  beziehungsweise das HIL-Ventilsignal inaktiv.
- Der ESP erzeugt Impulse auch ohne WLAN; WLAN-Ausfall beeinflusst nur seine
  Diagnoseoberfläche.
- Normaler HIL-Durchfluss wird als Menge gezählt und beim Loslassen korrekt
  abgeschlossen.
- Ausgeschaltetes Impulsfeedback führt mit aktivem
  Durchfluss-Watchdog zu einer verriegelten Safety-Abschaltung.
- Not-Aus, Steuerungs-Watchdog und Zeitlimit bleiben in allen Testmodi aktiv.
- Vor Anschluss realer Ventilhardware steht
  `ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG=0`.

Traceability: `ZZ-HW-002`, `ZZ-HW-004`, `ZZ-HW-005`, `ZZ-SAF-001`,
`ZZ-SAF-004`, `ZZ-SAF-005`, `ZZ-SAF-008`, `ZZ-SAF-009` und `ZZ-MNT-002`.
Die Offline-Zeitbasis aus `M8.7` referenziert zusätzlich `ZZ-TIM-001` und
`ZZ-DAT-002` bis `ZZ-DAT-004`.
Die lokale Systemsteuerung aus `M8.8` referenziert zusätzlich `ZZ-UI-010`,
`ZZ-DAT-003` und `ZZ-SAF-009`.
Die Datensicherung aus `M8.9` referenziert `ZZ-DAT-001`, `ZZ-DAT-002`,
`ZZ-DAT-006`, `ZZ-DAT-008` und `ZZ-DAT-010`.
Die Feldvorbereitung aus `M8.10` referenziert `ZZ-KEG-004`, `ZZ-SAF-004`,
`ZZ-SAF-005`, `ZZ-SAF-008`, `ZZ-SAF-009`, `ZZ-UI-002` und `ZZ-UI-011`.

## Milestone 9: Feldnachbereitung und Betriebsverbesserungen

Der erste reale Beta-Feldeinsatz wurde über sechs Tage erfolgreich
abgeschlossen. Milestone 9 überführt die qualitativen Erfahrungen in klar
abgrenzbare Arbeitspakete. Der Feldnachweis ist keine formale elektrische oder
sicherheitstechnische Abnahme und enthält noch keine im Repository belegte
quantitative Kalibrierauswertung.

### Geplante Arbeitspakete

| Paket | Ziel | Status |
| --- | --- | --- |
| `M9.1 DOC/PLAN` | Feldbericht, bereinigter Projektstatus, priorisiertes Backlog und Anforderungsabgleich | in Umsetzung |
| `M9.2 HW` | vorhandenen hardwareseitigen Not-Aus zusätzlich softwareseitig erkennen, verriegeln und protokollieren | geplant |
| `M9.3 UI` | lokalen, ventilgesperrten Fasswechsel auf Basis der bestehenden Fachoperation bereitstellen | vorgeschlagen; Zugangsweg offen |
| `M9.4 UI` | Smartphone-Buchungsansicht standardmäßig auf zehn Einträge begrenzen und ältere Einträge gezielt nachladen | fachlich entschieden |
| `M9.5 FEAT` | offenen Ausschankmodus ohne persönliche Abrechnung fachlich entscheiden und umsetzen | Konzept offen |
| `M9.6 DB` | Archivierung oder kontrollierte Bereinigung von Fass- und Veranstaltungshistorie festlegen | Konzept offen |
| `M9.7 UI/PLAN` | öffentlichen Top-Listen-Ticker und weitere Gamification definieren | Konzept offen |
| `M9.8 TEST/DOC` | Kalibrierwert, quantitative Feldkennzahlen sowie verbleibende HIL- und elektrische Prüfungen dokumentieren | Daten offen |
| `M9.9 UI` | pauschale Sicherheitsüberschrift durch sachliche, ursachenbezogene Sperrmeldungen ersetzen | fachlich entschieden |

Die Detailentscheidungen und Prioritäten stehen im
[`Produkt-Backlog`](backlog.md). Neue Funktionen werden erst implementiert,
wenn ihre vorgeschlagenen Anforderungen und offenen Entscheidungen ausreichend
konkretisiert sind.

Traceability: `ZZ-SAF-001`, `ZZ-SAF-002`, `ZZ-DAT-004`, `ZZ-KEG-006`,
`ZZ-KEG-007`, `ZZ-AUT-013`, `ZZ-UI-014` bis `ZZ-UI-017`, `ZZ-DAT-006`,
`ZZ-DAT-011` und `OD-015` bis `OD-018`.
