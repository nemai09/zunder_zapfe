# Projektorganisation – Zunder Zapfe

Stand: 2026-07-18  
Status: Arbeitsgrundlage fuer die Zusammenarbeit

## 1. Ziel

Dieses Dokument regelt Verantwortlichkeiten, Zusammenarbeit und Uebergaben im
Projekt Zunder Zapfe. Das Projekt wird von drei fachlichen Contributors
entwickelt. Die gesamte Software liegt bewusst in einer Verantwortung, damit
Architektur, Datenmodell, Steuerungslogik und Benutzeroberflaeche aus einem Guss
entstehen.

## 2. Rollen und Verantwortlichkeiten

### Chris mit Codex – gesamte Software

Chris ist fachlicher Owner der Software. Codex unterstuetzt Chris bei Planung,
Implementierung, Tests und Dokumentation.

Verantwortungsbereich:

- Softwarearchitektur und technische Entscheidungen
- Backend und lokale Weboberflaeche
- Kioskmodus auf dem Raspberry Pi
- Datenbank und Datenmodell
- Benutzer-, Rollen- und NFC-Verwaltung
- Getraenke-, Fass- und Veranstaltungsverwaltung
- Zapfsteuerung und Zustandsautomat
- Durchflussauswertung und Mengenbuchung
- Preislogik, Happy Hour und Einzelabrechnung
- Adminoberflaeche und Konfiguration
- Fehlerbehandlung, Watchdog und Protokollierung
- Softwareseitige Hardwareabstraktion
- MQTT-Anbindung der optionalen Fasswaage
- automatisierte Tests, Simulatoren und Softwaredokumentation
- Installation und Betrieb der Software auf dem Raspberry Pi

Software-Commits von Codex verwenden ausschliesslich die lokale Identitaet
`Codex Ai <codex@nemai.de>`. Codex arbeitet nur lokal; Pushes zu GitHub werden
von Chris ausgefuehrt.

### Domenic – Hardware der Zapfanlage

Domenic verantwortet die elektrische und physische Hardware der eigentlichen
Zapfanlage.

Verantwortungsbereich:

- Auswahl und Aufbau der Hardwarekomponenten
- Schaltplan und Stueckliste
- Raspberry-Pi-Anbindung
- NFC-Leser auf Hardwareebene
- Durchflusssensor und Signalaufbereitung
- Ventil, Versorgung und geeignete Treiberstufe
- GPIO-Pinbelegung und elektrische Pegel
- Not-Aus als Oeffnerkontakt
- hardwareseitige Unterbrechung der Ventilansteuerung
- Verkabelung, Gehaeuse und mechanischer Aufbau der Zapfanlage
- elektrische und funktionale Hardwaretests
- Hardware-, Aufbau- und Wartungsdokumentation

Domenic definiert gemeinsam mit Chris die elektrischen Signale. Die Auslegung
der Schaltung liegt bei Domenic; die Verarbeitung der Signale in der Software
liegt bei Chris/Codex.

### Robin – Fasswaage

Robin verantwortet die optionale Waage zur sekundaeren Ueberwachung des
Fassfuellstands.

Verantwortungsbereich:

- Auswahl von Waagensensorik und Messelektronik
- mechanische Konstruktion und Belastbarkeit
- Messwerterfassung und Kalibrierung
- lokale Firmware beziehungsweise Waagensoftware
- Bereitstellung der Messwerte, voraussichtlich ueber MQTT
- Status-, Fehler- und Verbindungsinformationen der Waage
- Testverfahren und Dokumentation

Die Zapfanlage muss auch ohne Waage voll funktionsfaehig bleiben. Die Waage ist
ein optionaler Sensor fuer Second-Level-Monitoring und darf die primaere
Zapfsteuerung nicht blockieren.

## 3. Entscheidungsverantwortung

- Fachliche Produktentscheidungen werden gemeinsam mit den Stakeholdern
  getroffen und im Anforderungskatalog dokumentiert.
- Chris entscheidet ueber die Softwarearchitektur und Softwareimplementierung.
- Domenic entscheidet ueber die konkrete elektrische und mechanische Auslegung
  der Zapfanlagen-Hardware innerhalb der vereinbarten Anforderungen.
- Robin entscheidet ueber die technische Auslegung der Fasswaage innerhalb der
  vereinbarten Schnittstelle.
- Schnittstellenaenderungen werden nicht einseitig vorgenommen. Betroffene
  Contributors muessen ihnen vor der Umsetzung zustimmen.
- Sicherheitsrelevante Entscheidungen zu Ventil und Not-Aus werden von Chris und
  Domenic gemeinsam abgestimmt.

Entscheidungen mit langfristiger technischer Wirkung werden spaeter als
Architecture Decision Record unter `docs/decisions/` festgehalten und
referenzieren die betroffenen Anforderungs-IDs.

## 4. Gemeinsame Schnittstellen

Vor der parallelen Implementierung werden mindestens folgende Vertraege
festgelegt:

### Software zu Zapfanlagen-Hardware

- GPIO-Pinbelegung
- aktive Pegel und sichere Grundzustande
- Ventilfreigabe und Not-Aus-Signal
- elektrisches Format der Durchflussimpulse
- erwartete Impulsfrequenzen und Entprellung
- Verhalten beim Booten, Herunterfahren und Ausfall
- erlaubte Test- und Simulationsverfahren

Owner des Dokuments: Chris/Codex und Domenic gemeinsam.

### Software zu Fasswaage

- Transportprotokoll; derzeit ist MQTT vorgesehen
- Topic-Namen und Nachrichtenformat
- Einheiten und Zahlenformate
- Zeitstempel
- Messwert-, Status- und Fehlermeldungen
- Aktualisierungsintervall
- Verhalten bei Verbindungsabbruch oder veralteten Messwerten
- Test-Publisher und Beispielnachrichten

Owner des Dokuments: Chris/Codex und Robin gemeinsam.

## 5. Git- und Review-Workflow

- `main` ist der gemeinsame Integrationsstand und soll funktionsfaehig bleiben.
- Arbeit erfolgt auf kurzen, thematisch begrenzten Branches.
- Empfohlene Branch-Namen sind beispielsweise:
  - `software/tap-state-machine`
  - `hardware/valve-driver`
  - `scale/mqtt-prototype`
  - `docs/hardware-interface`
- Aenderungen werden ueber Pull Requests in `main` integriert.
- Mindestens ein anderer Contributor prueft einen Pull Request.
- Schnittstellen- und Sicherheitsanderungen benoetigen ein Review des jeweils
  betroffenen Owners.
- Commits sollen klein, thematisch geschlossen und verstaendlich benannt sein.
- Wenn anwendbar, enthalten Commit, Issue oder Pull Request die zugehoerige
  Anforderungs-ID, beispielsweise `ZZ-SAF-002`.
- Anforderungen werden nicht stillschweigend geaendert. Aenderungen erfolgen
  nachvollziehbar per Commit und Review.
- Pushes zum GitHub-Repository werden von Chris durchgefuehrt. Codex fuehrt keine
  Pushes aus.

## 6. Arbeitsaufteilung und parallele Entwicklung

Die Contributors sollen moeglichst unabhaengig arbeiten koennen:

- Chris/Codex entwickelt die Software zunaechst gegen simulierte GPIO-, NFC- und
  Durchflussschnittstellen.
- Domenic kann die Hardware mit eigenstaendigen Testprogrammen beziehungsweise
  definierten Testsignalen pruefen.
- Robin stellt zunaechst einen MQTT-Test-Publisher mit realistischen Beispiel-
  und Fehlerwerten bereit.
- Hardwarezugriffe werden in der Software hinter klaren Adaptern gekapselt.
- Die Waagenschnittstelle bleibt optional und besitzt ein definiertes
  Offline-Verhalten.

Damit blockieren fehlende Hardware oder Waage nicht die Entwicklung der
Kernsoftware.

## 7. Integrationsreihenfolge

1. Anforderungen und Schnittstellenentwuerfe abstimmen.
2. Software mit simulierten Hardwareadaptern entwickeln.
3. Ventil, Not-Aus und Durchflusssensor einzeln mit der Software integrieren.
4. Vollstaendigen Zapfvorgang inklusive Fehlerfaellen testen.
5. Optionale Waage ueber MQTT anbinden.
6. Gesamtsystem auf der Zielhardware testen.
7. Abnahme anhand der Anforderungs-IDs und dokumentierten Testfaelle.

## 8. Dokumentationsverantwortung

- Jeder Contributor dokumentiert seinen eigenen Verantwortungsbereich.
- Schnittstellendokumente werden von beiden beteiligten Seiten gepflegt.
- Dokumentation wird zusammen mit der zugehoerigen Aenderung aktualisiert.
- Schaltplaene, Pinbelegung und Hardwaretests liegen unter `docs/hardware/`.
- Softwarearchitektur liegt unter `docs/architecture/`.
- Aufbau, Betrieb und Wartung liegen unter `docs/operations/`.
- Anforderungen liegen unter `requirements/`.

## 9. Unmittelbare naechste Schritte

1. Stakeholder pruefen und bestaetigen den Anforderungskatalog.
2. Chris und Domenic definieren die erste GPIO- und Hardware-Schnittstelle.
3. Chris und Robin definieren den ersten MQTT-Schnittstellenentwurf.
4. Das Team legt Zielhardware, Entwicklungsmeilensteine und Abnahmetermin fest.
5. Nach dem ersten Push werden Branchschutz und Pull-Request-Reviews fuer `main`
   eingerichtet.

