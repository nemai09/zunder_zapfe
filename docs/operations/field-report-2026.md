# Feldbericht 2026

Stand: 2026-08-18

## Ergebnis

Der erste reale Beta-Feldeinsatz lief über sechs Tage. Das Gesamtsystem wurde
mit Kiosk, NFC-Anmeldung, realer Zapfhardware, lokaler Datenhaltung und
Smartphone-Administration im laufenden Ausschank eingesetzt. Nach Rückmeldung
des Betreibers funktionierte die Zapfe in diesem Zeitraum ausgesprochen gut.

Dieser Nachweis ist deutlich stärker als der vorherige ESP8266-HIL-Normalfluss.
Er ist jedoch keine formale elektrische oder sicherheitstechnische Abnahme und
belegt ohne ergänzende Messdaten keine bestimmte Abrechnungsgenauigkeit.

## Bewährte Bereiche

- Der normale NFC- und Push-to-Fill-Ablauf war praktisch einsatzfähig.
- Benutzerverwaltung über die Smartphone-WebUI war im Feld ausreichend gut
  bedienbar.
- Die Anlage blieb als Offline-System über den mehrtägigen Einsatz nutzbar.
- Die bestehende Buchungs- und Verwaltungsbasis war tragfähig genug für den
  realen Veranstaltungsbetrieb.

## Beobachtete Verbesserungen

- Der häufige Fasswechsel war am Smartphone zu umständlich und soll zusätzlich
  lokal am Kiosk angeboten werden.
- Die Buchungsansicht lud standardmäßig zu viele Einträge; zehn aktuelle
  Buchungen sind für den Einstieg angemessener.
- Die pauschale Sperrmeldung „Sicherheit zuerst“ war für technische Ursachen
  wie fehlenden Durchfluss unpassend; der Kiosk soll die konkrete Ursache
  sachlich benennen.
- Teilnehmer fragten häufig nach der Top 10; eine öffentliche Tickeransicht ist
  als Erweiterung zu prüfen.
- Ein realer Not-Aus unterbricht inzwischen die Ventilversorgung, wird von der
  Software aber noch nicht erkannt.
- Für kostenlosen Ausschank ohne persönliche Abrechnung wird ein offener Modus
  benötigt.
- Fass- und Veranstaltungshistorie benötigen langfristig einen kontrollierten
  Lebenszyklus.
- Weitere Gamification ist gewünscht, fachlich aber noch nicht definiert.

Die priorisierte Nachverfolgung und Zuordnung zu Anforderungen steht im
[Produkt-Backlog](../backlog.md).

## Grenzen dieses Berichts

Im Repository liegen keine personenbezogenen Felddaten und keine reale
Produktionsdatenbank. Konkrete Gesamtmengen, Buchungszahlen, Kalibrierwerte und
Fehlerstatistiken wurden mit diesem Dokumentationsstand noch nicht übernommen.
Bis diese Werte ergänzt sind, beschreibt dieser Bericht den qualitativen
Betriebsnachweis und keine quantitative Abnahme.
