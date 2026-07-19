# Schnittstellenverträge

Dieser Ordner beschreibt die stabilen Grenzen zwischen WebUI, Backend,
Persistenz und Hardwareentwicklung.

## Vertragsarten

| Vertrag | Maschinenlesbar | Menschlich lesbar |
| --- | --- | --- |
| HTTP-API | [`openapi.json`](openapi.json) | [`http-api.md`](http-api.md) |
| Hardware | Python-`Protocol` und Dataclasses | [`hardware.md`](hardware.md) |
| Persistenz | Alembic und SQLAlchemy-Modelle | [`persistence.md`](persistence.md) |
| Konfiguration | `config/web.env.example` | [`configuration.md`](configuration.md) |
| Zustandsautomat | `TapController` und Tests | [`../architecture/tap-state-machine.md`](../architecture/tap-state-machine.md) |

## Stabilitätsregel

Die Verträge sind innerhalb der Alpha-Phase nicht semantisch
rückwärtskompatibel garantiert. Änderungen müssen dennoch bewusst erfolgen:

1. betroffene Anforderungen und Nutzer identifizieren,
2. ausführbaren Vertrag und Simulatoren ändern,
3. Vertragstests aktualisieren,
4. menschlich lesbare Dokumentation aktualisieren,
5. maschinenlesbare Artefakte regenerieren,
6. Änderung und Migrationsbedarf im PR beschreiben.

Eine Implementierung darf keine nicht dokumentierte Abkürzung über eine
Schichtgrenze einführen.
