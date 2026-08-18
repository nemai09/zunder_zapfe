# Produkt-Backlog nach dem ersten Feldeinsatz

Stand: 2026-08-18

Diese Liste sammelt beobachtete Verbesserungen aus dem sechstägigen
Beta-Feldeinsatz. Sie ist die operative Ergänzung zum verbindlichen
[Anforderungskatalog](../requirements/anforderungskatalog.txt). Ein Eintrag im
Backlog bedeutet noch nicht, dass alle fachlichen Details entschieden sind.
Verbindliches Produktverhalten entsteht erst durch eine akzeptierte
Anforderung und die zugehörige Abnahme.

## Priorisierte Arbeitspakete

| Priorität | Thema | Feldbeobachtung und Ziel | Anforderungen | Status / nächste Entscheidung |
| --- | --- | --- | --- | --- |
| hoch | Softwareseitiger Not-Aus | Ein realer Not-Aus trennt das Ventil bereits hardwareseitig. Die Software erkennt Betätigung oder Leitungsbruch noch nicht. | `ZZ-SAF-001`, `ZZ-SAF-002`, `ZZ-DAT-004` | Bestehende Anforderungen umsetzen: Eingang, Adapterstatus, Verriegelung, Ereignis und Resetablauf festlegen und auf Zielhardware prüfen. |
| hoch | Lokaler Fasswechsel | Der Fasswechsel über das Smartphone funktionierte, war im laufenden Betrieb aber umständlich. Der häufige Ablauf soll am Kiosk in einer lokalen Adminansicht verfügbar werden. | `ZZ-KEG-006`, vorgeschlagen `ZZ-KEG-007`, CR-002 | Zugang und Umfang des lokalen Adminwegs entscheiden; bestehende Fassoperation wiederverwenden, keine zweite Fachlogik bauen. |
| hoch | Buchungsansicht auf zehn Einträge begrenzen | Hundert Buchungen beim Öffnen störten die Smartphone-Bedienung. Standard sollen zehn aktuelle Sitzungsbuchungen sein; ältere Daten bleiben nachladbar und exportierbar. | `ZZ-UI-015`, `ZZ-DAT-009`, `ZZ-DAT-010` | Fachlich entschieden; Paging- oder „Mehr laden“-Verhalten im UI-Paket konkretisieren. |
| kurzfristig | Konkrete Sperrmeldungen | Die pauschale Kioskzeile „Sicherheit zuerst“ erklärt die meist technische Durchflusssperre nicht und überhöht den Vorgang. | `ZZ-UI-017`, `ZZ-SAF-004`, `ZZ-SAF-005`, `ZZ-SAF-008` | Fachlich entschieden; bekannte Ursachen auf konkrete Texte abbilden, neutralen Fallback beibehalten. |
| mittel | Offener Ausschankmodus | Für kostenlosen Ausschank oder Betrieb ohne gezählte Veranstaltung soll Zapfen ohne persönliche NFC-Abrechnung möglich sein. | vorgeschlagen `ZZ-AUT-013`, `OD-016` | Aktivierung, Zeitgrenze, Buchungsart, Statistik und sichtbare Kennzeichnung entscheiden. |
| mittel | Historien-Lebenszyklus | Fass- und Veranstaltungshistorie wächst dauerhaft. Es fehlt ein kontrollierter Umgang mit nicht mehr benötigten Einträgen. | `ZZ-DAT-006`, vorgeschlagen `ZZ-DAT-011`, `OD-017` | Zuerst Archivieren/Ausblenden gegen echtes Löschen abwägen. Buchungen und Referenzen bleiben bis zur Entscheidung unverändert. |
| mittel | Top-Liste als Ticker | Teilnehmer fragten häufig nach der Top 10. Eine öffentliche, zurückhaltende Kioskanzeige könnte diese Nachfrage bedienen. | `ZZ-UI-013`, vorgeschlagen `ZZ-UI-014`, `OD-015` | Darstellung, Namen, Datenschutz, Aktualisierung und Abschaltbarkeit festlegen. |
| später | Weitere Gamification | Über Rang und Top-Liste hinaus besteht Interesse an spielerischen Anzeigen. | vorgeschlagen `ZZ-UI-016`, `OD-018` | Ideen sammeln; noch keine Umsetzung ohne eigenes Konzept. |

## Bewusst nicht vermischen

- Der hardwareseitige Not-Aus ist bereits wirksam, ersetzt aber nicht die noch
  fehlende Softwareerkennung nach `ZZ-SAF-001`.
- Historienverwaltung darf die Unveränderlichkeit abgeschlossener Buchungen
  nach `ZZ-BIL-003` nicht beiläufig aufheben.
- Der offene Ausschankmodus ist keine Wartungszapfung und kein gemeinsames
  Benutzerkonto. Seine Mengen müssen als eigener fachlicher Kontext erkennbar
  bleiben.
- Ranglisten und Gamification sind Anzeige- und Motivationsfunktionen. Quelle
  der Abrechnung bleiben ausschließlich die gespeicherten Buchungen.
- Technische Zapfsperren bleiben wirksam und rücksetzpflichtig; geändert wird
  nur ihre verständliche, ursachenbezogene Darstellung im Kiosk.

## Noch zu erfassende Felddaten

Für eine belastbare quantitative Nachauswertung fehlen im Repository noch:

- tatsächlich ausgeschenkte Gesamtmenge und Zahl der Buchungen,
- verwendeter Kalibrierwert und Kontrollmessung,
- Anzahl von Neustarts, Safety-Sperren und manuellen Eingriffen,
- Ergebnis der automatischen Sicherungen und extern heruntergeladenen Exporte,
- bewährte endgültige Watchdog- und Timeoutwerte.

Diese Angaben werden nur als zusammengefasste Betriebswerte dokumentiert;
personenbezogene Buchungsdaten und reale NFC-UIDs bleiben außerhalb von Git.
