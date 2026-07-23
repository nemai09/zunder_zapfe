# Dokumentationsindex

Dieser Index ist der Einstiegspunkt für Menschen und Entwicklungsagenten. Er
nennt für jeden Bereich die verbindliche Quelle, damit Beschreibungen nicht
unbemerkt auseinanderlaufen.

## Quellen der Wahrheit

| Thema | Verbindliche Quelle | Erläuterung |
| --- | --- | --- |
| Produktverhalten | [`requirements/anforderungskatalog.txt`](../requirements/anforderungskatalog.txt) | Nummerierte Anforderungen und Abnahmekriterien |
| Anforderungsänderungen | [`requirements/changes/`](../requirements/changes/README.md) | Annahme, Auswirkungen und Nachverfolgung wesentlicher Change Requests |
| Hardwaremethoden und Statusobjekte | [`src/zunder_zapfe/hardware`](../src/zunder_zapfe/hardware) | Ausführbare Python-Verträge |
| HTTP-Pfade und JSON-Schemata | [`interfaces/openapi.json`](interfaces/openapi.json) | Aus FastAPI generierter, geprüfter Snapshot |
| Zapfübergänge | [`tap_controller.py`](../src/zunder_zapfe/backend/tap_controller.py) | Ausführbarer Zustandsautomat |
| Datenbankschema | [`migrations/`](../migrations) | Versionierte Alembic-Migrationen |
| Fachliche Datenoperationen | [`repository.py`](../src/zunder_zapfe/persistence/repository.py) | Transaktionsgebundene Repository-API |
| Zielsystemkonfiguration | [`config/web.env.example`](../config/web.env.example) | Geheimnisfreie Konfigurationsvorlage |

Markdown-Dokumente erklären diese Quellen. Bei einem Widerspruch gilt die oben
genannte ausführbare oder nummerierte Quelle; der Widerspruch ist im selben PR
zu korrigieren.

## Projekt und Zusammenarbeit

- [Projektstatus](project-status.md)
- [Entwicklungsmeilensteine](milestones.md)
- [Versionierung](versioning.md)
- [Commit-Konvention](commit-konvention.md)
- [Projektorganisation](organization.md)
- [Beiträge](../CONTRIBUTING.md)
- [Agentenleitfaden](../AGENTS.md)
- [Sicherheitsmeldungen](../SECURITY.md)
- [Anforderungen pflegen](../requirements/README.md)

## Schnittstellen

- [Schnittstellenübersicht](interfaces/README.md)
- [Hardwarevertrag](interfaces/hardware.md)
- [HTTP-API-Vertrag](interfaces/http-api.md)
- [Persistenzvertrag](interfaces/persistence.md)
- [Laufzeitkonfiguration](interfaces/configuration.md)
- [OpenAPI 3.1](interfaces/openapi.json)

## Architektur

- [Hardware-Zwischenlayer](architecture/hardware-interface.md)
- [Zapfzustandsautomat](architecture/tap-state-machine.md)
- [Backend-Core-Integration](architecture/backend-core-integration.md)
- [Kiosk-WebUI](architecture/kiosk-webui.md)
- [Lokale Admin-WebUI](architecture/admin-webui.md)
- [Smartphone-Admin-WebUI](architecture/smartphone-admin-webui.md)
- [Externer Superadmin](architecture/superadmin.md)
- [Persistenz und Datenmodell](architecture/persistence.md)
- [ADR 0001: GPL-3.0-or-later](decisions/0001-gpl-3-or-later.md)

## Betrieb und Diagnose

- [Raspberry-Pi-Kiosk](operations/raspberry-pi-kiosk.md)
- [ACR122U-NFC-Leser](operations/acr122u-nfc.md)
- [Alpha-Integrationstest](operations/alpha-integration-test.md)
- [SQLite-Datenbankbrowser](operations/database-browser.md)
- [Debugbetrieb ohne Durchflusshardware](operations/debug-without-flow-hardware.md)
- [Admin-WLAN](operations/admin-wifi.md)
- [Superadmin-Karte einrichten](operations/superadmin-card.md)

## Dokumentationsregeln

1. Schnittstellenänderungen aktualisieren Codevertrag, erklärendes Markdown
   und maschinenlesbares Artefakt gemeinsam.
2. Dokumentierte Anforderungs-IDs müssen im Anforderungskatalog existieren.
3. Offene Entscheidungen werden als offen markiert und nicht als Verhalten
   beschrieben.
4. Beispiele verwenden ausschließlich erkennbare Demo-Daten.
5. Lokale Pfade, Zugangsdaten, reale NFC-UIDs und Datenbanken werden nicht
   dokumentiert oder committed.
6. Relative Links müssen aus dem Repository funktionieren.
