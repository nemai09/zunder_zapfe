# Projektstatus

Stand: 2026-07-23
Phase: Alpha-Entwicklung

## Implementiert und geprüft

- Raspberry-Pi-Webdienst und Chromium-Kioskstart
- realer, ereignisgesteuerter ACS-ACR122U-Leser über PC/SC mit Hotplug-Recovery
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
- sichtbarer, durch Touch zurückgesetzter Inaktivitäts-Timeout mit manuellem Logout
- ventilgesperrter lokaler Adminmodus mit eigenem, auditiert einstellbarem Timeout
- geschützte Verwaltungs-API für schlanke Benutzerdaten, Rollen und Aktivstatus
- Live-Zuordnung, Sperre und Entfernen von NFC-Armbändern ohne UID-Eingabe im Webclient
- eindeutige Lockscreen-Rückmeldung für unbekannte und gesperrte Armbänder
- kompakte, durchsuch- und filterbare Benutzerliste für typische Veranstaltungen
- persönliche Admin-Webpasswörter mit Argon2id sowie widerrufbare,
  CSRF-geschützte Websitzungen
- getrennte, geschützte Smartphone-API für Benutzer-, Armband- und
  Passwortverwaltung

Der Stand wurde automatisiert und auf dem Raspberry Pi mit realem NFC-Leser
und simuliertem Durchfluss geprüft. Eine bestandene Alpha-Prüfung ist keine
Freigabe für reale Ventilhardware.
Die Kiosk-WebUI wurde lokal mit simulierten API-Zuständen bei `800 × 480`
und anschließend im vollständigen Bedienablauf auf dem Zielsystem geprüft.
Milestone 5 umfasst 84 bestandene automatisierte Tests sowie die erfolgreiche
Prüfung von kurz aufgelegten NFC-Armbändern, Leser-Hotplug und PC/SC-Recovery.
Milestone 6 umfasst 97 bestandene automatisierte Tests sowie die erfolgreiche
Zielsystemprüfung von Adminsitzung, Benutzer- und Armbandverwaltung,
Suche/Filter und den Rückmeldungen für unbekannte und gesperrte Armbänder.

## Teilweise umgesetzt

| Bereich | Vorhanden | Fehlt |
| --- | --- | --- |
| Adminfunktionen | Rolle, erhaltener lokaler Adminmodus, Webauthentifizierung, Benutzer-/Armbandverwaltung und Sicherheitsreset | Smartphone-WebUI und weitere priorisierte Fachbereiche |
| Zapfhardware | Verträge, Simulatoren, Sicherheitslogik | reale Adapter und elektrische Abnahme |
| Konfiguration | Umgebungsvariablen und Settings-Tabelle | Adminbedienung und verbindliche Grenzwerte |
| Abrechnung | unveränderliche Buchungen und Summen | Einzelabrechnung, Storno und Export |

## Nicht implementiert

- Access Point `ZUNDER_ZAPFE` und vollständige Smartphone-Admin-WebUI
- Verwaltungsoberflächen für Veranstaltung, Getränke, Fässer, Buchungen,
  Einstellungen, Diagnose und Wartung
- reale Ventil-, Durchfluss- und Not-Aus-Adapter
- kalibrierte Mengenmessung und Genauigkeitsnachweis
- automatische Start-Selbsttests für reale Hardware
- Happy Hour, Storno, Export, Backup und Wiederherstellung
- optionale Fasswaage und MQTT-Vertrag
- verbindliche Offline-Zeitquelle

## Nächste Entwicklungsreihenfolge

1. Milestone 7 gemäß den festgelegten Arbeitspaketen mit Webauthentifizierung
   vor Netzwerkfreigabe umsetzen; danach Smartphone-UI und Verwaltungsbereiche
   inkrementell ergänzen.
2. Mit der Hardwareentwicklung elektrische Verträge und reale Adapter
   festlegen.
3. Gesamtsystem mit realer Zapfhardware kalibrieren und sicherheitstechnisch
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
- Die in Milestone 6 implementierte lokale Adminoberfläche bleibt erhalten,
  wird gemäß CR-002 vorerst aber nicht geöffnet oder weiter ausgebaut.
