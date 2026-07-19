# Zunder Zapfe

Offline betriebene, automatisierte Zapfanlage auf Basis eines Raspberry Pi.

## Projektstatus

Das Projekt befindet sich im Aufbau der Softwaregrundlagen. Die verbindliche
Ausgangsbasis bleibt der nummerierte Katalog unter
`requirements/anforderungskatalog.txt`; Implementierung und Tests referenzieren
die betroffenen Anforderungs-IDs.

Der erste Software-Meilenstein stellt eine lokale Python-Testseite auf dem
Raspberry Pi bereit, startet sie automatisch im Chromium-Kioskmodus und bindet
den vorhandenen ACR122U-NFC-Leser an. Ventil, Durchflussmesser und Not-Aus sind
zunaechst als Simulatoren hinter stabilen Hardware-Vertraegen ausgefuehrt. Die
Architektur ist unter `docs/architecture/hardware-interface.md` beschrieben.

Der aktuelle Backend-Alpha-Stand verbindet bekannte NFC-Karten, den
Zapf-Zustandsautomaten und die SQLite-Persistenz. Simulierte Portionen erzeugen
unveraenderliche Buchungen; Verbrauch, Betrag und Fassbestand bleiben ueber
einen Backend-Neustart erhalten. Die Kiosk- und Adminoberflaechen sind noch
nicht als Produktoberflaechen umgesetzt.

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

## Architektur

Die Anwendung ist in drei Verantwortungsbereiche gegliedert:

- `hardware/` kapselt reale Geraete und Simulatoren hinter stabilen Vertraegen,
- das Backend enthaelt spaeter Fachlogik, Datenhaltung und Zapfsteuerung,
- `web/` stellt Kiosk- und Adminoberflaeche bereit.

Die WebUI greift nicht direkt auf Hardware zu. Der aktuelle Standardaufbau
verwendet den realen ACR122U und Simulatoren fuer die noch nicht vorhandenen
Komponenten.

Der sicherheitsorientierte Zapfablauf und seine Zustaende sind unter
[`docs/architecture/tap-state-machine.md`](docs/architecture/tap-state-machine.md)
grafisch dokumentiert.

Das lokale SQLite-Datenmodell und die Migrationsstrategie sind unter
[`docs/architecture/persistence.md`](docs/architecture/persistence.md)
dokumentiert.

Die Verbindung von NFC, Zustandsautomat und dauerhafter Zapfbuchung beschreibt
[`docs/architecture/backend-core-integration.md`](docs/architecture/backend-core-integration.md).

## Zielsystem installieren

Voraussetzung ist Raspberry Pi OS (64 Bit) mit Desktop auf einem Raspberry Pi 4B.
Nach dem Checkout dieses Branches auf dem Zielsystem:

```bash
sudo ./scripts/install-pi.sh <desktop-benutzer>
sudo reboot
```

Nach dem Neustart muss die Testseite automatisch im Kioskmodus erscheinen. Die
Verifikation erfolgt ausschliesslich auf dem Raspberry Pi:

```bash
./scripts/pi-verify.sh
```

Die Einrichtung des USB-NFC-Lesers ACS ACR122U ist unter
[`docs/operations/acr122u-nfc.md`](docs/operations/acr122u-nfc.md) beschrieben.

Fuer die Diagnose kann die SQLite-Datenbank mit einer separat gestarteten,
schreibgeschuetzten Weboberflaeche untersucht werden. Die sichere Verwendung ist
unter
[`docs/operations/database-browser.md`](docs/operations/database-browser.md)
beschrieben.

Ein vollstaendiger Alpha-Test mit Demo-Benutzer, simulierter Zapfung,
Datenbankkontrolle und Neustart ist unter
[`docs/operations/alpha-integration-test.md`](docs/operations/alpha-integration-test.md)
dokumentiert.

## Zusammenarbeit

Aenderungen an Anforderungen behalten ihre ID. Inhaltliche Aenderungen werden in
Git nachvollziehbar vorgenommen; entfernte Anforderungen werden als verworfen
markiert und nicht neu nummeriert.
