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
- installierbarer NetworkManager-Access-Point `ZUNDER_ZAPFE` mit
  eingeschränktem nginx-Zugang zur Smartphone-API
- responsive Smartphone-Admin-WebUI mit persönlichem Login, Benutzer-,
  Passwort- und Armbandverwaltung
- ventilgesperrte, zeitbegrenzte NFC-Live-Zuordnung vom Smartphone mit
  sichtbarem Kioskzustand
- Capture-Armbänder bleiben nach Erfolg oder Konflikt bis zum Entfernen von
  einer normalen Zapfanmeldung ausgeschlossen
- fachliches Löschen von Benutzern bei erhaltenen Buchungen und dauerhaft
  einmaligen internen Benutzer-IDs
- Smartphone-Verwaltung für Veranstaltungen und Getränke mit validierten,
  auditierten Stammdatenänderungen
- geführter Fasswechsel mit atomarem Abschluss des bisherigen Fasses,
  Aktivierung der Veranstaltung und Anlage des neuen Fasses
- eigener Smartphone-Fassbereich mit optionalem Anfangsfüllstand,
  Standardfüllung und bewusstem Abzapfen in einen Zustand ohne aktives Fass
- Fasshistorie, rechnerischer Restbestand sowie aktiver Veranstaltungs- und
  Fasskontext in der Smartphone-Übersicht
- filterbare, ausschließlich lesende Smartphone-Buchungsansicht, die alle
  Zapfungen eines NFC-Loginzyklus zusammenfasst und die unveränderlichen
  Einzelvorgänge für Diagnose und Bestand erhält
- Veranstaltungs- und Benutzersummen für kostenpflichtige Istmengen und
  Beträge mit getrennt ausgewiesener Wartungsentnahme
- Smartphone-Ansichten für auditierte Adminaktionen und technische Ereignisse
- lokales, NFC-adminautorisiertes Systemmenü für den Wechsel zwischen
  `ZUNDER_ZAPFE` und einem bereits bekannten WLAN-Clientprofil
- WLAN-Modusindikator in der Kiosk-Kopfleiste sowie automatische
  Access-Point-Rückkehr bei fehlgeschlagenem Clientwechsel
- reduzierte Pi-Laufzeitlast durch gecachten WLAN-Systemstatus, getrennte
  Kiosk-Abfrageintervalle, fachlich inkrementelles Rendering und ruhiges
  HTTP-Access-Log
- kurze persönliche Kiosk-Begrüßung nach erfolgreicher Live-Zuordnung eines
  Armbands ohne automatische Anmeldung

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
Der lokale Stand nach `M7.6` umfasst 127 bestandene automatisierte Tests;
einschließlich des lokalen WLAN-Systemmenüs, der überarbeiteten Fassabläufe,
der Loginbuchungen und der Laufzeitoptimierung in `M7.7` bestehen 136 Tests.
Access Point, Smartphone-Layout und die Live-Zuordnung müssen noch gemeinsam
auf dem Raspberry Pi demonstriert werden.

## Teilweise umgesetzt

| Bereich | Vorhanden | Fehlt |
| --- | --- | --- |
| Adminfunktionen | Rolle, erhaltener lokaler Adminmodus, begrenztes WLAN-Systemmenü, Smartphone-WebUI, Webauthentifizierung, Benutzer-/Armbandverwaltung, Veranstaltungen, Getränke, Fasswechsel, Buchungen, Statistik, Audit und Sicherheitsreset | Diagnose, Einstellungen und weitere priorisierte Fachbereiche |
| Zapfhardware | Verträge, Simulatoren, Sicherheitslogik | reale Adapter und elektrische Abnahme |
| Konfiguration | Umgebungsvariablen, Settings-Tabelle, Admin-WLAN-Installer und lokaler AP-/Client-Moduswechsel | weitere Adminbedienung und verbindliche Grenzwerte |
| Abrechnung | unveränderliche Zapf-Rohdaten, zusammengefasste NFC-Anmeldebuchungen, Filter und Summen je Veranstaltung und Benutzer | verbindliches Einzelabrechnungsformat, Storno und Export |

## Nicht implementiert

- vollständige weitere Smartphone-Fachbereiche; Zielsystemabnahme von Access
  Point, Login und NFC-Zuordnung
- Verwaltungsoberflächen für Einstellungen, Diagnose und Wartung
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
  wird gemäß CR-002 vorerst aber nicht geöffnet oder weiter ausgebaut. Davon
  ausgenommen ist das eng begrenzte lokale WLAN-Systemmenü.
- Das WLAN-Systemmenü kann nur bereits vorhandene, automatisch verbindbare
  Clientprofile verwenden. Die spätere Bindung an eine besondere NFC-Karte
  oder Rolle ist als `OD-014` offen.
