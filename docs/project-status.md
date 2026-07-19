# Projektstatus

Stand: 2026-07-19
Phase: Alpha-Entwicklung

## Implementiert und geprüft

- Raspberry-Pi-Webdienst und Chromium-Kioskstart
- realer ACS-ACR122U-Leser über PC/SC
- Hardwareverträge und Simulatoren für Ventil, Durchfluss und Not-Aus
- sicherheitsorientierter Zapfzustandsautomat
- bekannte, aktive NFC-Karten und Benutzer-/Adminrollen
- Portion, Abbruch, Nachfüllen und Wartungszapfung im Backend
- Watchdog-, Durchfluss-, Zeit- und Not-Aus-Verriegelung
- bewusster Sicherheitsreset mit aufgelegter Admin-Karte
- SQLite-Schema, Migrationen und unveränderliche Zapfbuchungen
- Verbrauchssummen, Preisberechnung und rechnerischer Fassbestand
- automatisierter lokaler Smoke-Test mit realem NFC oder NFC-Simulator
- schreibgeschützter SQLite-Datenbankbrowser für Diagnose

Der Stand wurde automatisiert und auf dem Raspberry Pi mit realem NFC-Leser
und simuliertem Durchfluss geprüft. Eine bestandene Alpha-Prüfung ist keine
Freigabe für reale Ventilhardware.

## Teilweise umgesetzt

| Bereich | Vorhanden | Fehlt |
| --- | --- | --- |
| Kiosk-WebUI | Testseite und Statusanzeige | vollständiger Bedienablauf |
| Adminfunktionen | Rolle, Persistenz und Sicherheitsreset | Verwaltungsoberfläche und Webauthentifizierung |
| Zapfhardware | Verträge, Simulatoren, Sicherheitslogik | reale Adapter und elektrische Abnahme |
| Konfiguration | Umgebungsvariablen und Settings-Tabelle | Adminbedienung und verbindliche Grenzwerte |
| Abrechnung | unveränderliche Buchungen und Summen | Einzelabrechnung, Storno und Export |

## Nicht implementiert

- produktive Kiosk- und Adminoberfläche
- reale Ventil-, Durchfluss- und Not-Aus-Adapter
- kalibrierte Mengenmessung und Genauigkeitsnachweis
- automatische Start-Selbsttests für reale Hardware
- WLAN-Administration und Websicherheitskonzept
- Happy Hour, Storno, Export, Backup und Wiederherstellung
- optionale Fasswaage und MQTT-Vertrag
- verbindliche Offline-Zeitquelle

## Nächste Entwicklungsreihenfolge

1. Dokumentations- und Schnittstellenbaseline abschließen.
2. Kiosk-WebUI gegen den versionierten HTTP-Vertrag implementieren.
3. Admin-WebUI und notwendige Verwaltungsendpunkte ergänzen.
4. Mit der Hardwareentwicklung elektrische Verträge und reale Adapter
   festlegen.
5. Gesamtsystem mit realer Zapfhardware kalibrieren und sicherheitstechnisch
   prüfen.

## Bekannte Alpha-Eigenschaften

- Nach einer Portion bleibt der Zustand acht Sekunden lang
  `top_up_available`; eine unmittelbar gestartete weitere Portion wird bewusst
  abgelehnt.
- Die Simulator-API ist nur aktiv, wenn
  `ZUNDER_ZAPFE_ENABLE_SIMULATOR_API=1` gesetzt ist.
- Entwicklungsgrenzwerte und `500` Impulse pro Liter sind Demonstratorwerte,
  keine Produktionskalibrierung.
- Der Demo-Seed ist nur für eine leere Datenbank vorgesehen.
