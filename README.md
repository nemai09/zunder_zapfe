# Zunder Zapfe

Offline betriebene, automatisierte Zapfanlage auf Basis eines Raspberry Pi.

## Projektstatus

Das Projekt befindet sich in der Anforderungs- und Planungsphase. Die verbindliche
Ausgangsbasis ist der nummerierte Katalog unter
`requirements/anforderungskatalog.txt`.

Der erste Software-Meilenstein stellt eine lokale Python-Testseite auf dem
Raspberry Pi bereit, startet sie automatisch im Chromium-Kioskmodus und bindet
den vorhandenen ACR122U-NFC-Leser an. Ventil, Durchflussmesser und Not-Aus sind
zunaechst als Simulatoren hinter stabilen Hardware-Vertraegen ausgefuehrt. Die
Architektur ist unter `docs/architecture/hardware-interface.md` beschrieben.

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

## Zusammenarbeit

Aenderungen an Anforderungen behalten ihre ID. Inhaltliche Aenderungen werden in
Git nachvollziehbar vorgenommen; entfernte Anforderungen werden als verworfen
markiert und nicht neu nummeriert.
