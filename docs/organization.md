# Projektorganisation

Stand: 2026-07-19
Status: Arbeitsgrundlage

## Verantwortungsbereiche

### Software

Verantwortet werden Architektur, Backend, WebUI, Persistenz,
Zapfzustandsautomat, Hardwareabstraktion, Installation, Tests und
Softwaredokumentation.

### Zapfanlagen-Hardware

Verantwortet werden elektrische und mechanische Auslegung, Schaltplan,
Treiberstufe, Sensorik, Not-Aus-Kette, Verkabelung, Gehäuse und
Hardwareprüfung. Konkrete GPIOs, Pegel und Signalformen werden gemeinsam mit
der Softwareverantwortung als Schnittstelle freigegeben.

### Optionale Fasswaage

Verantwortet werden Sensorik, Mechanik, Kalibrierung und ein späterer
Messwertvertrag. Die Zapfanlage bleibt ohne Waage vollständig funktionsfähig;
die Waage ist ausschließlich eine sekundäre Plausibilitätsquelle.

## Entscheidungsregeln

- Produktentscheidungen werden im nummerierten Anforderungskatalog gepflegt.
- Langfristige technische Entscheidungen werden als ADR unter
  `docs/decisions/` dokumentiert.
- Schnittstellenänderungen werden nicht einseitig vorgenommen.
- Safety-relevante Entscheidungen zu Ventil und Not-Aus benötigen Zustimmung
  von Software- und Hardwareverantwortung.
- Offene Werte werden nicht durch Implementierungsannahmen zu scheinbar
  verbindlichen Festlegungen.

## Zusammenarbeit mit Entwicklungsagenten

Menschen und KI-gestützte Werkzeuge arbeiten gegen dieselben
Repository-Verträge. Projektweite Agentenanweisungen stehen ausschließlich in
[`AGENTS.md`](../AGENTS.md). Persönliche Agentennamen, lokale Commitidentitäten
und individuelle Push-Berechtigungen werden nicht im Repository festgelegt.

Jeder Contributor bleibt für Inhalt, Tests und Review seiner Beiträge
verantwortlich, unabhängig vom verwendeten Werkzeug.

## Git- und Review-Workflow

- `main` ist der gemeinsame Integrationsstand und bleibt funktionsfähig.
- Änderungen erfolgen auf kurzen, thematisch begrenzten Branches.
- Integration in `main` erfolgt ausschließlich per Pull Request.
- Anforderungen behalten ihre ID und werden nicht stillschweigend geändert.
- Schnittstellen- und Safety-Änderungen benötigen Review der betroffenen
  Verantwortungsbereiche.
- Das verwendete Git-Programm ist frei wählbar; Windows-Contributors können
  SourceTree verwenden, auf Zielsystemen sind CLI-Anleitungen üblich.

## Gemeinsame Schnittstellen

### Software zu Zapfhardware

Der aktuelle Softwarevertrag ist unter
[`docs/interfaces/hardware.md`](interfaces/hardware.md) beschrieben. Elektrisch
noch zu entscheiden sind insbesondere GPIO-Pinbelegung, aktive Pegel,
Impulsform, maximale Frequenz, Entprellung, Bootverhalten und Hardwaretests.

### Software zu WebUI

Der lokale HTTP-Vertrag liegt menschlich lesbar unter
[`docs/interfaces/http-api.md`](interfaces/http-api.md) und maschinenlesbar als
[`docs/interfaces/openapi.json`](interfaces/openapi.json) vor.

### Software zu Fasswaage

Der Vertrag ist noch offen. Vor Implementierung sind Transport, Topic-Namen,
Nachrichtenformat, Einheiten, Zeitstempel, Aktualisierungsintervall und
Offline-Verhalten festzulegen. MQTT ist eine Präferenz, noch keine verbindliche
Entscheidung.

## Dokumentationsverantwortung

- Jeder Bereich pflegt seine Implementierung und Dokumentation gemeinsam.
- Schnittstellendokumente werden von beiden Seiten der Grenze geprüft.
- Schaltpläne und Hardwaretests liegen unter `docs/hardware/`.
- Architektur liegt unter `docs/architecture/`.
- Betrieb und Diagnose liegen unter `docs/operations/`.
- Anforderungen liegen unter `requirements/`.

Der [Dokumentationsindex](README.md) definiert die jeweilige Quelle der
Wahrheit.
