# Vertrag zwischen Backend und Zapfhardware

Status: Alpha-Vertrag
Verbindlicher Code: [`src/zunder_zapfe/hardware/interfaces.py`](../../src/zunder_zapfe/hardware/interfaces.py)

## Zweck und Grenze

Der Vertrag beschreibt ausschließlich, was die Software von einem
Hardwareadapter benötigt. GPIO-Nummern, aktive Pegel, Treiberbibliotheken,
Entprellung und elektrische Schutzschaltungen sind Eigenschaften des späteren
Adapters beziehungsweise der Hardwaredokumentation.

Das Backend entscheidet über Berechtigung, Zapfzustand, Grenzwerte,
Impulsumrechnung und Buchung. Adapter enthalten keine Benutzer-, Preis- oder
Veranstaltungslogik.

## Gemeinsamer Lifecycle

Alle Komponenten unterstützen:

| Methode | Vorbedingung | Wirkung | Fehlerverhalten |
| --- | --- | --- | --- |
| `start()` | Komponente erzeugt | Ressource initialisieren | sicher schließen beziehungsweise nicht verfügbar melden |
| `snapshot()` | jederzeit nach Erzeugung | unveränderlichen aktuellen Status liefern | darf kein Ventil öffnen oder Messung starten |
| `stop()` | beliebiger Zustand | Ressource freigeben | Ventil muss zuerst geschlossen werden |

`HardwareLayer.start()` initialisiert Ventil, Durchflussmesser und Not-Aus vor
dem NFC-Leser. `HardwareLayer.stop()` stoppt zuerst das Ventil. Wiederholte
Statusabfragen müssen seiteneffektfrei und aus Hintergrund- sowie API-Thread
sicher möglich sein.

## `NfcReader`

```python
start() -> None
stop() -> None
snapshot() -> NfcStatus
```

`NfcStatus`:

| Feld | Typ | Semantik |
| --- | --- | --- |
| `state` | `str` | `starting`, `ready`, `card`, `disconnected`, `unavailable` oder `error` |
| `reader` | `str | None` | erkannter Lesername |
| `uid` | `str | None` | UID nur bei `state == "card"` |
| `detail` | `str | None` | Diagnose, nicht für Fachentscheidungen |
| `simulated` | `bool` | Herkunft aus Simulator |

Die UID ist ein technischer Kartenbezeichner und kein Geheimnis, kann aber
personenbezogen zugeordnet sein. Reale UIDs gehören nicht in Quellcode,
Dokumentation oder Logs von Pull Requests.

## `Valve`

```python
start() -> None
stop() -> None
open() -> None
close() -> None
snapshot() -> ValveStatus
```

Verbindliche Invarianten:

- `start()` und `stop()` stellen geschlossen her.
- `close()` ist auch nach Teilfehlern sicher aufrufbar.
- Initialisierungs- oder Kommunikationsfehler dürfen niemals öffnen.
- Ein Softwareadapter ersetzt nicht die hardwareseitige Unterbrechung durch
  den Not-Aus.

`ValveStatus` enthält `is_open`, `available`, `simulated` und eine optionale
Diagnose `detail`.

## `FlowMeter`

```python
start() -> None
stop() -> None
begin_measurement() -> None
end_measurement() -> FlowReading
snapshot() -> FlowReading
```

`begin_measurement()` setzt die Messung für genau einen Zapfvorgang auf null.
`end_measurement()` beendet sie und liefert den letzten Stand. `snapshot()`
verändert die Messung nicht.

`FlowReading`:

| Feld | Typ | Semantik |
| --- | --- | --- |
| `pulse_count` | `int` | nichtnegative Impulse seit Messbeginn |
| `measuring` | `bool` | Messfenster aktiv |
| `last_pulse_at` | `float | None` | monotone Zeit des letzten Impulses |
| `available` | `bool` | Adapter betriebsbereit |
| `simulated` | `bool` | Herkunft aus Simulator |
| `detail` | `str | None` | Diagnoseinformation |

Der Adapter zählt Impulse; die Umrechnung in Milliliter bleibt im Backend.

## `EmergencyStop`

```python
start() -> None
stop() -> None
snapshot() -> EmergencyStopStatus
```

`active` bedeutet, dass die Software eine ausgelöste Sicherheitskette erkennt.
Ein nicht verfügbarer realer Adapter muss später nach dem Fail-safe-Prinzip
behandelt werden. Die konkrete Ausführung als Öffnerkontakt und die direkte
Ventilunterbrechung sind elektrische Anforderungen außerhalb dieses
Softwarevertrags.

## Aktuelle Adaptermatrix

| Komponente | Standardbetrieb | Testbetrieb |
| --- | --- | --- |
| NFC | `Acr122uNfcReader` über PC/SC | `SimulatedNfcReader` |
| Ventil | `SimulatedValve` | `SimulatedValve` |
| Durchfluss | `SimulatedFlowMeter` | `SimulatedFlowMeter` |
| Not-Aus | `SimulatedEmergencyStop` | `SimulatedEmergencyStop` |

Simulatoren dürfen zusätzliche Testmethoden wie `present_card()`,
`add_pulses()` oder `trigger()` anbieten. Produktionscode darf diese Methoden
nicht über den gemeinsamen Vertrag voraussetzen.

## Verfahren für Vertragserweiterungen

1. Bedarf mit Anforderungs-ID oder dokumentierter offener Entscheidung
   begründen.
2. Protocol und Statusmodell erweitern.
3. Simulator inklusive Fehlerfall implementieren.
4. `HardwareLayer`- und Backendtests ergänzen.
5. Diesen Vertrag aktualisieren.
6. Erst danach den realen Adapter implementieren.

Breaking Changes benötigen ein Review von Software- und Hardwareverantwortung.
