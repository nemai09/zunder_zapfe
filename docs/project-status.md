# Projektstatus

Stand: 2026-07-20
Phase: Alpha-Entwicklung

## Implementiert und geprüft

- Raspberry-Pi-Webdienst und Chromium-Kioskstart
- realer ACS-ACR122U-Leser über PC/SC
- Hardwareverträge und Simulatoren für Ventil, Durchfluss und Not-Aus
- sicherheitsorientierter Zapfzustandsautomat
- bekannte, aktive NFC-Karten und Benutzer-/Adminrollen
- manuelles Push-to-Fill sowie kompatible Portion, Abbruch, Nachfüllen und Wartungszapfung im Backend
- Watchdog-, Durchfluss-, Zeit- und Not-Aus-Verriegelung
- bewusster Sicherheitsreset mit aufgelegter Admin-Karte
- SQLite-Schema, Migrationen und unveränderliche Zapfbuchungen
- Verbrauchssummen, Preisberechnung und rechnerischer Fassbestand
- automatisierter lokaler Smoke-Test mit realem NFC oder NFC-Simulator
- schreibgeschützter SQLite-Datenbankbrowser für Diagnose
- zustandsbasierte Ein-Knopf-Touch-WebUI für Idle, manuelles Zapfen und Sperren

Der Stand wurde automatisiert und auf dem Raspberry Pi mit realem NFC-Leser
und simuliertem Durchfluss geprüft. Eine bestandene Alpha-Prüfung ist keine
Freigabe für reale Ventilhardware.
Die Kiosk-WebUI wurde lokal mit simulierten API-Zuständen bei `800 × 480`
geprüft; Bedienreview und Zielsystemprüfung sind für Milestone 5 noch offen.

## Teilweise umgesetzt

| Bereich | Vorhanden | Fehlt |
| --- | --- | --- |
| Kiosk-WebUI | manueller Push-to-Fill-Alpha-Ablauf nach CR-001 | Bedienfeedback, Zeitkalibrierung und Pi-Prüfung |
| Adminfunktionen | Rolle, Persistenz und Sicherheitsreset | Verwaltungsoberfläche und Webauthentifizierung |
| Zapfhardware | Verträge, Simulatoren, Sicherheitslogik | reale Adapter und elektrische Abnahme |
| Konfiguration | Umgebungsvariablen und Settings-Tabelle | Adminbedienung und verbindliche Grenzwerte |
| Abrechnung | unveränderliche Buchungen und Summen | Einzelabrechnung, Storno und Export |

## Nicht implementiert

- produktive Adminoberfläche
- reale Ventil-, Durchfluss- und Not-Aus-Adapter
- kalibrierte Mengenmessung und Genauigkeitsnachweis
- automatische Start-Selbsttests für reale Hardware
- WLAN-Administration und Websicherheitskonzept
- Happy Hour, Storno, Export, Backup und Wiederherstellung
- optionale Fasswaage und MQTT-Vertrag
- verbindliche Offline-Zeitquelle

## Nächste Entwicklungsreihenfolge

1. Push-to-Fill-WebUI gemeinsam reviewen und auf dem Raspberry Pi prüfen.
2. Webauthentifizierung und notwendige Verwaltungsendpunkte ergänzen.
3. Admin-WebUI implementieren.
4. Mit der Hardwareentwicklung elektrische Verträge und reale Adapter
   festlegen.
5. Gesamtsystem mit realer Zapfhardware kalibrieren und sicherheitstechnisch
   prüfen.

Die abgeschlossenen und geplanten PR-Checkpoints stehen unter
[`milestones.md`](milestones.md).

## Bekannte Alpha-Eigenschaften

- Kompatibel gestartete Portionen bleiben im Backend erhalten; nach einer Portion bleibt der Zustand acht Sekunden lang
  `top_up_available`; eine unmittelbar gestartete weitere Portion wird bewusst
  abgelehnt.
- Die Simulator-API ist nur aktiv, wenn
  `ZUNDER_ZAPFE_ENABLE_SIMULATOR_API=1` gesetzt ist.
- Entwicklungsgrenzwerte und `500` Impulse pro Liter sind Demonstratorwerte,
  keine Produktionskalibrierung.
- `120 ms` Touchentprellung und `30 s` maximale manuelle Zapfdauer sind
  konfigurierbare Alpha-Werte und gemäß `OD-012` noch zu kalibrieren.
- Der Durchfluss-Watchdog ist für Tests ohne Sensor vorübergehend per
  `ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG=1` deaktiviert. Dies ist eine
  dokumentierte Alpha-Abweichung von `ZZ-SAF-004`; Steuerungs-Watchdog,
  Not-Aus und Zeitlimit bleiben aktiv. Vor realer Ventilhardware ist der Wert
  zwingend auf `0` zu setzen.
- Die Kiosk-Kopfleiste zeigt als Debughilfe den angeforderten Ventilzustand,
  nicht den elektrisch gemessenen Zustand eines Ventils.
- Der Demo-Seed ist nur für eine leere Datenbank vorgesehen.
