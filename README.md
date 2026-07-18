# Zunder Zapfe

Offline betriebene, automatisierte Zapfanlage auf Basis eines Raspberry Pi.

## Projektstatus

Das Projekt befindet sich in der Anforderungs- und Planungsphase. Die verbindliche
Ausgangsbasis ist der nummerierte Katalog unter
`requirements/anforderungskatalog.txt`.

## Verzeichnisstruktur

- `requirements/` – nummerierte Anforderungen und spaetere Traceability-Artefakte
- `docs/architecture/` – System- und Softwarearchitektur
- `docs/decisions/` – Architekturentscheidungen (ADRs)
- `docs/hardware/` – Schaltplaene, Pinbelegung und Hardwaredokumentation
- `docs/operations/` – Aufbau, Betrieb, Wartung, Backup und Wiederherstellung
- `src/` – Anwendungsquellcode
- `tests/` – automatisierte und manuelle Tests
- `config/` – Beispielkonfigurationen ohne Geheimnisse
- `scripts/` – Entwicklungs-, Installations- und Betriebswerkzeuge

## Zusammenarbeit

Aenderungen an Anforderungen behalten ihre ID. Inhaltliche Aenderungen werden in
Git nachvollziehbar vorgenommen; entfernte Anforderungen werden als verworfen
markiert und nicht neu nummeriert.

