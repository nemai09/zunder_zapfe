# Beta-Feldeinsatz: Übergabe und bewusste Abweichungen

Stand: 2026-08-18

Diese Seite war der operative Übergabepunkt für den ersten sechstägigen
Feldeinsatz mit ungefähr 300 Litern geplantem Ausschank. Sie ergänzt den
Anforderungskatalog um bewusst akzeptierte Beta-Abweichungen. Ein neuer
Entwicklungsagent liest zuerst `AGENTS.md`, `docs/project-status.md`, diese
Seite und anschließend die jeweils verlinkte Detailanleitung.

## Ziel für den ersten Einsatz

Nach der Inbetriebnahme auf der realen Zapfe wird die Software eingefroren.
Während des Einsatzes zählen zuverlässiges manuelles Zapfen, nachvollziehbare
Abrechnung und der Erhalt bereits gespeicherter Buchungen. Deployment ohne
Internet, allgemeine Fertigungsreife und zusätzliche Komfortfunktionen gehören
nicht zu diesem Einsatzumfang.

## Bewusst akzeptierte Beta-Abweichungen

| Thema | Aktueller Feldstand | Konsequenz |
| --- | --- | --- |
| Durchflusskalibrierung | `500` Impulse/Liter ist nur ein Demonstratorwert | Vor dem Ausschank zwingend mit realem Sensor und bekannter Flüssigkeitsmenge kalibrieren. Bis dahin sind Mengen und Beträge nicht belastbar. |
| Not-Aus | Der Softwareadapter ist weiterhin simuliert; ein realer Öffnerkontakt und eine unabhängige elektrische Ventilunterbrechung sind nicht umgesetzt | Bewusste Abweichung von `ZZ-SAF-001` und `ZZ-SAF-002` für diesen beaufsichtigten Beta-Einsatz. |
| Watchdogs | Durchfluss- und Steuerungsüberwachung bleiben aktiv, verwenden aber vorläufig entspannte Werte von 5/3/5 Sekunden | Kurze Laufzeitverzögerungen verriegeln die Anlage seltener; ein echter Ausfall wird entsprechend später erkannt. |
| Fassbestand | Startmenge minus Buchungen wird weiter angezeigt, sperrt aber auch bei null oder negativem Ergebnis keine Zapfung | Der Bestand ist nur eine Orientierung. Das tatsächliche Fassende erkennt das Bedienpersonal. |
| Bereitschaft | Der Kiosk prüft Softwarezustand, Adapterverfügbarkeit, NFC und aktiven Fasskontext | Die Anzeige ist keine elektrische Rückmeldung des physischen Ventils und kein Genauigkeitsnachweis des Sensors. |
| Datenwiederherstellung | Alle 30 Minuten entstehen lokale SQLite- und CSV-Sicherungen; eine automatische Wiederherstellung ist absichtlich nicht vorhanden | Die Sicherung schützt vor logischen Schäden bei erhaltener SD-Karte. Gegen einen vollständigen Kartenausfall hilft nur der regelmäßige CSV-Download auf ein Telefon. |
| Langzeitnachweis | Der sechstägige Betrieb mit realer Zapfhardware verlief nach Betreiberangabe ausgesprochen gut | Der qualitative Beta-Nachweis ist erbracht; quantitative Betriebsdaten und die formale elektrische, Kalibrier- und Safety-Abnahme bleiben getrennte Aufgaben. |

## Ergebnis des ersten Einsatzes

Der vorgesehene sechstägige Feldbetrieb wurde erfolgreich abgeschlossen. Die
beobachteten Stärken, Bedienprobleme und daraus abgeleiteten Arbeitspakete sind
im [`Feldbericht 2026`](field-report-2026.md) und im
[`Produkt-Backlog`](../backlog.md) festgehalten. Die folgenden Prüfschritte
bleiben als Checkliste für künftige Inbetriebnahmen erhalten.

## Vorläufige Feldparameter

Die lokale Datei `/etc/zunder-zapfe/web.env` enthält für den Feldtest:

```text
ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG=0
ZUNDER_ZAPFE_FIRST_PULSE_TIMEOUT_SECONDS=5
ZUNDER_ZAPFE_BETWEEN_PULSES_TIMEOUT_SECONDS=3
ZUNDER_ZAPFE_CONTROLLER_WATCHDOG_TIMEOUT_SECONDS=5
ZUNDER_ZAPFE_MANUAL_MAXIMUM_POUR_SECONDS=30
ZUNDER_ZAPFE_PULSES_PER_LITER=<Ergebnis der realen Kalibrierung>
```

Die Watchdogs dürfen für den realen Ausschank nicht vollständig deaktiviert
werden. Details zu allen Variablen stehen unter
[`Laufzeitkonfiguration`](../interfaces/configuration.md).
Für einen betriebsverhindernden Sensorfehler beschreibt das
[`Offline-Notfallhandbuch`](field-emergency-runbook.md) einen zeitlich
begrenzten, ständig beaufsichtigten Notbetrieb sowie die verbindliche Rückkehr
zu diesen Feldwerten.

## Verbindlicher Inbetriebnahmetest

1. Richtige Software-Revision, reale GPIO-Adapter und deaktivierte
   Simulatorrouten prüfen.
2. Aktive Veranstaltung, Getränk, Literpreis und aktives Fass kontrollieren.
3. Mindestens drei Messzapfungen mit bekannter Menge bei realistischer
   Zapfgeschwindigkeit durchführen und Impulse/Liter bestimmen.
4. Kalibrierwert eintragen, Dienst neu starten und eine weitere Kontrollmenge
   zapfen. Angezeigte Menge, Buchung und Betrag vergleichen.
5. Mindestens 20 bis 30 reale Ventilzyklen durchführen. Dabei auf Pi-Neustarts,
   Fehlersperren, ausbleibende oder zusätzliche Impulse und verzögertes
   Schließen achten.
6. Impulsfeedback kurz unterbrechen und prüfen, dass die entspannte
   Durchflussüberwachung weiterhin schließt und verriegelt. Den Reset mit einem
   Admin praktisch durchführen.
7. Größtes vorgesehenes Gefäß testen. Falls 30 Sekunden nicht reichen, den
   Wert bewusst in der lokalen Konfiguration ändern und erneut prüfen.
8. Kiosk mindestens über Nacht laufen lassen. Chromium muss nach einem
   absichtlichen Beenden nach ungefähr zwei Sekunden erneut starten.
9. Automatische Sicherung und CSV-Download auf ein Telefon prüfen sowie freien
   Speicher kontrollieren.
10. Pi vor Veranstaltungsbeginn bewusst in den AP-Modus `ZUNDER_ZAPFE` setzen.

Die Verdrahtung und der technische HIL-Ablauf stehen unter
[`GPIO- und ESP8266-Hardware-in-the-Loop-Test`](gpio-hil-test.md). Die
vollständige Zielsystemprüfung steht unter
[`Erstinstallation und Zielsystemprüfung`](fresh-raspberry-pi-deployment.md).

## Verhalten im laufenden Betrieb

- `Bereit zum Zapfen` erscheint nur bei fachlicher Bereitschaft. Ein fehlendes
  Fass oder ein nicht verfügbarer Adapter wird stattdessen ausdrücklich
  angezeigt.
- Eine Watchdog-Sperre schließt das Ventil, bucht die bis dahin gemessene Menge
  und benötigt einen Admin-Reset über die Smartphone-Diagnose oder eine
  aufgelegte Admin-Karte.
- Der Webdienst startet nach einem Prozessfehler automatisch neu. Chromium wird
  vom Kioskstarter nach einem unerwarteten Ende ebenfalls neu gestartet.
- Ein harter Stromausfall während einer Zapfung kann genau diesen laufenden
  Vorgang verlieren. Bereits abgeschlossene Buchungen liegen transaktional in
  SQLite.
- Das lokale WLAN-Menü kann den Access Point wieder aktivieren. Ein vorheriger
  Clientmodus blockiert den Backendstart nicht.

Während eines Feldeinsatzes wird mindestens einmal täglich das aktuelle
CSV-Sicherungspaket über die
Smartphone-Administration heruntergeladen. Weitere Funktionsentwicklung
während des Einsatzes unterbleibt; bei Problemen werden zuerst Konfiguration,
Verkabelung und die vorhandenen Diagnoseanzeigen geprüft.
Die dafür ohne Entwicklungszugang zulässigen Maßnahmen und Abbruchkriterien
stehen im [`Offline-Notfallhandbuch`](field-emergency-runbook.md).
