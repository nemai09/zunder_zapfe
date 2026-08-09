# Projektstatus

Stand: 2026-08-09
Phase: Beta-Felderprobung

## Implementiert und geprüft

- Raspberry-Pi-Webdienst und Chromium-Kioskstart
- realer, ereignisgesteuerter ACS-ACR122U-Leser über PC/SC mit Hotplug-Recovery
- Hardwareverträge und Simulatoren für Ventil, Durchfluss und Not-Aus
- sicherheitsorientierter Zapfzustandsautomat
- bekannte, aktive NFC-Karten und Benutzer-/Adminrollen
- manuelles Push-to-Fill sowie kompatible Portion, Abbruch, Nachfüllen und Wartungszapfung im Backend
- Watchdog-, Durchfluss-, Zeit- und Not-Aus-Verriegelung
- Sicherheitsreset mit aufgelegter Admin-Karte oder geschützter Webadminsitzung
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
- einmalig lokal provisionierbarer Fehlbedienungsschutz, der einen Admin aktiv
  hält und mindestens ein aktives Armband bewahrt, ohne HTTP-Schreibpfad
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
- Smartphone-Gesamtstatistik und Top-10-Liste nach kostenpflichtiger Zapfmenge
- Einzelanalyse je Teilnehmer mit Kosten und Menge, getrennt nach Getränk
- vollständiger CSV-Teilnehmerauszug je Veranstaltung mit ganzzahligen Mengen
  und Beträgen
- automatische, integritätsgeprüfte SQLite-Sicherung alle 30 Minuten mit 400
  lokalen Sicherungsständen und Smartphone-Download eines NFC- und
  passwortfreien CSV-Pakets
- fachlicher Kiosk-Bereitschaftsstatus für Steuerung, NFC, GPIO-Adapter,
  Datenbank und aktiven Fasskontext; der rechnerische Fassbestand bleibt
  informativ und sperrt keine Zapfung
- vorläufig entspannte, weiterhin aktive und per Umgebung konfigurierbare
  Watchdogs mit 5 Sekunden Anlaufzeit, 3 Sekunden Impulspause und 5 Sekunden
  Steuerungstimeout
- automatischer Chromium-Neustart nach einem unerwarteten Browserende
- Smartphone-Diagnose mit Steuerungszustand, Safety-Reset sowie standardmäßig
  eingeklapptem Adminaudit und technischen Ereignissen
- lokales, NFC-adminautorisiertes Systemmenü für den Wechsel zwischen
  `ZUNDER_ZAPFE` und einem bereits bekannten WLAN-Clientprofil
- getrennte lokale Systemseite für auditierten Neustart und geordnetes
  Herunterfahren mit ausdrücklicher Touchbestätigung
- WLAN-Modusindikator in der Kiosk-Kopfleiste sowie automatische
  Access-Point-Rückkehr bei fehlgeschlagenem Clientwechsel
- reduzierte Pi-Laufzeitlast durch gecachten WLAN-Systemstatus, getrennte
  Kiosk-Abfrageintervalle, fachlich inkrementelles Rendering und ruhiges
  HTTP-Access-Log
- kurze persönliche Kiosk-Begrüßung nach erfolgreicher Live-Zuordnung eines
  Armbands ohne automatische Anmeldung

Der Stand wurde automatisiert und auf dem Raspberry Pi mit realem NFC-Leser
und simuliertem Durchfluss geprüft. Zusätzlich wurde der reguläre GPIO-Pfad
mit dem ESP8266-HIL erstmals erfolgreich als vollständiger manueller
Zapfvorgang geprüft: BCM17 aktivierte das HIL-Ventilsignal, BCM27 zählte die
erzeugten Impulse, Loslassen schloss den Ausgang und die gemessene Menge wurde
verbucht. Die übrigen HIL-Fehlerfälle sowie die elektrische Abnahme realer
Ventilhardware bleiben offen. Eine bestandene Alpha-Prüfung ist keine Freigabe
für reale Ventilhardware.
Die Kiosk-WebUI wurde lokal mit simulierten API-Zuständen bei `800 × 480`
und anschließend im vollständigen Bedienablauf auf dem Zielsystem geprüft.
Milestone 5 umfasst 84 bestandene automatisierte Tests sowie die erfolgreiche
Prüfung von kurz aufgelegten NFC-Armbändern, Leser-Hotplug und PC/SC-Recovery.
Milestone 6 umfasst 97 bestandene automatisierte Tests sowie die erfolgreiche
Zielsystemprüfung von Adminsitzung, Benutzer- und Armbandverwaltung,
Suche/Filter und den Rückmeldungen für unbekannte und gesperrte Armbänder.
Der lokale Stand nach `M7.6` umfasst 127 bestandene automatisierte Tests;
einschließlich des lokalen WLAN-Systemmenüs, der überarbeiteten Fassabläufe,
der Loginbuchungen, der Laufzeitoptimierung, des Adminschutzes sowie
Teilnehmerabrechnung und Diagnose in `M7.7` bestehen 142 Tests.
Die Smartphone-Administration einschließlich Login, Benutzer- und
Armbandverwaltung, Fassablauf, Buchungen, Auswertung und Diagnose wurde auf
dem Raspberry Pi bedient und für den Alpha-Stand abgenommen. Milestone 7 ist
damit abgeschlossen.

Der lokale Entwicklungsstand nach `M8.10` umfasst 175 bestandene automatisierte
Tests einschließlich rein informativem Fassbestand, fachlicher
Zapfbereitschaft, konfigurierbaren Feld-Watchdogs, RTC, Systemsteuerung und
Datensicherung. Diese PC-Prüfung ersetzt nicht den für den nächsten Tag
vorgesehenen Inbetriebnahme- und Kalibrierungstest auf dem Raspberry Pi.

## Teilweise umgesetzt

| Bereich | Vorhanden | Fehlt |
| --- | --- | --- |
| Adminfunktionen | Rolle, erhaltener lokaler Adminmodus, begrenztes WLAN- und Energiemenü, Smartphone-WebUI, Webauthentifizierung, Benutzer-/Armbandverwaltung, Veranstaltungen, Getränke, Fasswechsel, Buchungen, Teilnehmerabrechnung und -export, Diagnose, Audit und Sicherheitsreset | hardwareabhängige Kalibrier- und Safety-Einstellungen nach Festlegung der realen Adapter |
| Zapfhardware | Verträge, Simulatoren, Sicherheitslogik, ESP8266-HIL-Firmware, aktiver-HIGH-Ventilausgang auf BCM17, Flankenzähler auf BCM27 und erfolgreicher erster HIL-Normalfluss | vollständige HIL-Fehlerfallabnahme, realer Not-Aus-Adapter und elektrische Abnahme der Ventil-/Sensorhardware |
| Offline-Zeit | DS3231-Konfiguration, Startdienst vor der Zapfanwendung und lokales CLI für Status sowie einmalige Übernahme der Systemzeit ohne NTP-Änderung | Zielsystemnachweis nach stromlosem Neustart und Bewertung der Abweichung über den Einsatzzeitraum |
| Konfiguration | Umgebungsvariablen, Settings-Tabelle, Admin-WLAN-Installer und lokaler AP-/Client-Moduswechsel | weitere Adminbedienung und verbindliche Grenzwerte |
| Abrechnung | unveränderliche Zapf-Rohdaten, zusammengefasste NFC-Anmeldebuchungen, Filter, Gesamt- und Einzelanalyse sowie CSV-Gesamtauszug je Veranstaltung | Storno und Korrektur |

## Nicht implementiert

- hardwareabhängige Smartphone-Einstellungen für Kalibrierung,
  Plausibilitäts- und Safety-Grenzen
- lokale Kiosk-Bedienung für Wartungszapfungen
- realer Not-Aus-Adapter
- elektrisch abgenommene Ventiltreiber- und Durchflusshardware
- kalibrierte Mengenmessung und Genauigkeitsnachweis
- automatische Start-Selbsttests für reale Hardware
- Happy Hour, Storno und Korrektur
- optionale Fasswaage und MQTT-Vertrag

## Nächste Entwicklungsreihenfolge

1. Gesamtsystem mit realem Ventil und Durchflusssensor kalibrieren sowie den
   verbindlichen Inbetriebnahmetest für den Beta-Feldeinsatz durchführen.
2. Nach dem Einsatz die bewusst akzeptierten Abweichungen aus
   [`Beta-Feldeinsatz`](operations/alpha-field-operation.md) erneut bewerten.
3. ESP8266-HIL für Neustart, Verbindungsabbruch und Safety-Verriegelung
   vollständig abnehmen.
4. Reale Ventiltreiber- und Sensorstufe elektrisch freigeben sowie später den
   Not-Aus-Adapter implementieren.
5. Lokale Wartungszapfung passend zum realen Hardwareablauf in die Kiosk-UI
   integrieren.

Die abgeschlossenen und geplanten PR-Checkpoints stehen unter
[`milestones.md`](milestones.md).

## Bekannte Beta-Eigenschaften

- Kompatibel gestartete Portionen bleiben im Backend erhalten; nach einer Portion bleibt der Zustand acht Sekunden lang
  `top_up_available`; eine unmittelbar gestartete weitere Portion wird bewusst
  abgelehnt.
- Die Simulator-API ist nur aktiv, wenn
  `ZUNDER_ZAPFE_ENABLE_SIMULATOR_API=1` gesetzt ist.
- Entwicklungsgrenzwerte und `500` Impulse pro Liter sind Demonstratorwerte,
  keine Produktionskalibrierung.
- `120 ms` Touchentprellung und `30 s` maximale manuelle Zapfdauer sind
  konfigurierbare Alpha-Werte und gemäß `OD-012` noch zu kalibrieren.
- Für den ersten Feldeinsatz gelten vorläufig 5 Sekunden bis zum ersten
  Durchflussimpuls, 3 Sekunden zwischen Impulsen und 5 Sekunden für den
  Steuerungs-Watchdog. Die Überwachung bleibt aktiv.
- Der rechnerische Fassbestand ist ausschließlich informativ. Auch null oder
  negative Restmenge verhindert keine Zapfung.
- Der Durchfluss-Watchdog ist standardmäßig aktiv. Ausschließlich lokale
  Entwicklung ohne GPIO-Hardware darf ihn zusammen mit explizit aktivierten
  Ventil-/Durchflusssimulatoren per
  `ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG=1` deaktivieren.
- Der angeforderte Ventilzustand bleibt ausschließlich in geschützten
  Diagnoseansichten sichtbar; die Kiosk-Kopfleiste zeigt WLAN und
  Zapfbereitschaft.
- Der Demo-Seed ist nur für eine leere Datenbank vorgesehen.
- Die in Milestone 6 implementierte lokale Adminoberfläche bleibt erhalten,
  wird gemäß CR-002 vorerst aber nicht geöffnet oder weiter ausgebaut. Davon
  ausgenommen ist das eng begrenzte lokale Systemmenü für WLAN-Modus und
  Energieaktionen.
- Das WLAN-Systemmenü kann nur bereits vorhandene, automatisch verbindbare
  Clientprofile verwenden. Die spätere Bindung an eine besondere NFC-Karte
  oder Rolle ist als `OD-014` offen.
- Die für den bevorstehenden Einsatz akzeptierten Abweichungen und der
  Inbetriebnahmeablauf stehen zentral unter
  [`Beta-Feldeinsatz`](operations/alpha-field-operation.md).
