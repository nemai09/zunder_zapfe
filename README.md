# Zunder Zapfe

Offline betriebene, automatisierte Zapfanlage auf Basis eines Raspberry Pi.

## Projektstatus

Das Projekt befindet sich in der Anforderungs- und Planungsphase. Die verbindliche
Ausgangsbasis ist der nummerierte Katalog unter
`requirements/anforderungskatalog.txt`.

Der erste Software-Meilenstein stellt eine lokale Python-Testseite auf dem
Raspberry Pi bereit und startet sie automatisch im Chromium-Kioskmodus. Die
Einrichtung ist unter `docs/operations/raspberry-pi-kiosk.md` beschrieben.

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
