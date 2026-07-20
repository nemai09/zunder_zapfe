# Lokaler HTTP-API-Vertrag

Status: Alpha-Vertrag

Basis-URL: `http://127.0.0.1:8000`
Maschinenlesbar: [`openapi.json`](openapi.json)

## Geltungsbereich

Die API ist die einzige vorgesehene Grenze zwischen WebUI und Backend. Sie ist
standardmäßig nur über Loopback erreichbar, verwendet JSON und benötigt zur
Laufzeit kein Netzwerk. Die Alpha-API besitzt noch keinen Versionspräfix;
Änderungen müssen daher in einem gemeinsamen PR mit ihren Clients erfolgen.

## Allgemeine Antworten

- `200`: Aktion oder Abfrage erfolgreich, JSON-Antwort.
- `204`: Aktion erfolgreich, kein Antwortkörper.
- `409`: fachliche Vorbedingung oder Zustandsübergang nicht erfüllt;
  `{"detail":"..."}`.
- `422`: Request-JSON verletzt das Schema.
- `500`: unerwarteter interner Fehler; nicht als normaler Ablauf behandeln.

Die API übernimmt Benutzer- und Adminidentität ausschließlich aus der lokalen
NFC-Sitzung. Clients dürfen keine fremde Benutzer-ID oder ein Admin-Flag
einspeisen.

## Diagnose und Status

| Methode und Pfad | Erfolg | Beschreibung |
| --- | --- | --- |
| `GET /api/health` | `200 HealthResponse` | Prozess-, Release-, Build- und Revisionsstatus |
| `GET /api/nfc/status` | `200 NfcStatusResponse` | NFC-Leser und aktuell aufgelegte Karte |
| `GET /api/hardware/status` | `200 HardwareStatusResponse` | Status aller Hardwarekomponenten |
| `GET /api/tap/status` | `200 TapStatusResponse` | vollständiger Zapfzustand |
| `POST /api/tap/poll` | `200 TapStatusResponse` | Zustand sofort auswerten; primär Diagnose/Test |

`TapStatusResponse` enthält:

| Feld | Typ | Bedeutung |
| --- | --- | --- |
| `state` | `str` | Zustand aus dem Zustandsautomaten |
| `user_id` | `str | null` | intern angemeldeter Benutzer |
| `is_admin` | `bool` | Rolle der aktuellen Sitzung |
| `valve_open` | `bool` | angeforderter Ventilzustand |
| `measured_pulses` | `int` | Impulse des aktiven Vorgangs |
| `target_pulses` | `int | null` | Ziel einer Portion |
| `measured_volume_ml` | `int` | backendseitig aus Impulsen berechnete Istmenge |
| `target_volume_ml` | `int | null` | gewählte Zielmenge während einer Portion |
| `top_up_remaining_ms` | `int | null` | verbleibendes Nachfüllfenster in Millisekunden |
| `session_remaining_ms` | `int | null` | verbleibende Inaktivitätszeit der aktuellen Sitzung |
| `safety_reason` | `str | null` | Ursache einer Verriegelung |
| `user_display_name` | `str | null` | Anzeigename |
| `special_portion_ml` | `int | null` | individuelle Portion |
| `persistence_error` | `str | null` | letzter Buchungsfehler |
| `last_booking` | `object | null` | letzte im Prozess persistierte Buchung |

`valve_open` ist ein angeforderter Softwarezustand und keine physische
Ventilrückmeldung. Die Kiosk-Debuganzeige verwendet genau dieses Feld.

## Sitzung

| Methode und Pfad | Vorbedingung | Ergebnis |
| --- | --- | --- |
| `GET /api/session/status` | keine | aktuelle NFC-Sitzung |
| `POST /api/session/activity` | `authenticated` oder `manual_pouring` | `204`, setzt Inaktivität zurück |
| `POST /api/session/logout` | `authenticated` oder `top_up_available` | `204`, danach `idle` |

Anmeldung geschieht ereignisgesteuert durch Auflegen einer bekannten, aktiven
Karte. Eine liegen gebliebene Karte meldet sich nach Logout nicht sofort erneut
an; sie muss entfernt und neu aufgelegt werden.
Eine Sitzung endet außerdem nach der konfigurierten Inaktivitätszeit. Eine
bewusste Touchinteraktion wird über `POST /api/session/activity` serverseitig
registriert. Aktive
Zapfungen und das Nachfüllfenster werden dadurch nicht unterbrochen.

## Zapfen

| Methode und Pfad | Vorbedingung | Erfolg und Zustandswirkung |
| --- | --- | --- |
| `GET /api/tap/options` | keine | kompatible Portionen, Sitzungszeit, manuelle Grenzen und temporärer Flow-Debugstatus |
| `POST /api/tap/manual/start` | `authenticated`, aktiver Kontext und Fassbestand | wechselt zu `manual_pouring` |
| `POST /api/tap/manual/stop` | `manual_pouring` | schließt, bucht Istmenge, zurück zu `authenticated` |
| `POST /api/tap/portion` | `authenticated`, aktiver Kontext und Fassbestand | `{"target_volume_ml":500}`; wechselt zu `portion_pouring` |
| `POST /api/tap/portion/abort` | `portion_pouring` | schließt, bucht Istmenge, zurück zu `authenticated` |
| `POST /api/tap/top-up/start` | `top_up_available` innerhalb Zeitfenster | wechselt zu `top_up_pouring` |
| `POST /api/tap/top-up/stop` | `top_up_pouring` | schließt, bucht Istmenge, zurück zu `authenticated` |
| `POST /api/tap/heartbeat` | aktiver Zapfvorgang | `204`, erneuert Steuerungs-Watchdog |

Eine vollständig erreichte Portion endet in `top_up_available`. Der aktuelle
Alpha-Grenzwert hält diesen Zustand acht Sekunden; erst danach ist eine neue
Portion möglich.
Die Kiosk-WebUI verwendet ausschließlich die manuellen Start-/Stop-Aktionen.
Die Portions- und Nachfüllaktionen bleiben nach CR-001 für kompatible Clients
erhalten. `POST /api/tap/portion` akzeptiert ausschließlich eine konfigurierte
Standardportion oder die Sonderportion des angemeldeten Benutzers.

Ein manueller Vorgang besitzt keine Zielmenge. Er endet beim ersten Stoppsignal
oder nach der konfigurierten Maximaldauer. In beiden Fällen wird genau die
gemessene Istmenge als Buchungsart `manual` gespeichert.

## Wartung und Sicherheit

| Methode und Pfad | Vorbedingung | Ergebnis |
| --- | --- | --- |
| `POST /api/tap/maintenance/enter` | authentifizierter Admin | `204`, Zustand `maintenance` |
| `POST /api/tap/maintenance/start` | `maintenance` | nicht kostenpflichtige Messung startet |
| `POST /api/tap/maintenance/stop` | `maintenance_pouring` | Istmenge wird kostenfrei gebucht |
| `POST /api/tap/maintenance/exit` | `maintenance` | `204`, zurück zu `authenticated` |
| `POST /api/tap/safety/reset` | verriegelt, Ursache behoben, aktive Admin-Karte liegt auf | Zustand `idle`, keine Sitzung |

Beim Sicherheitsreset werden weder UID, Benutzer-ID noch Admin-Flag im Request
übergeben. Ein aktiver Not-Aus verhindert den Reset.

## Verbrauch und Fass

| Methode und Pfad | Vorbedingung | Antwort |
| --- | --- | --- |
| `GET /api/consumption/current` | aktive Sitzung und aktiver Veranstaltungskontext | Buchungsanzahl, Milliliter und Cent des Benutzers |
| `GET /api/keg/current` | aktiver Veranstaltung-/Getränk-/Fasskontext | Stammdaten und rechnerische Restmenge |

Alle Geld- und Mengenwerte sind Ganzzahlen: Milliliter, Cent pro Liter und
Cent. Clients dürfen daraus keine Gleitkomma-Buchungswerte erzeugen.

## Ausschließlich für Simulatorbetrieb

Diese Routen existieren nur mit `ZUNDER_ZAPFE_ENABLE_SIMULATOR_API=1`:

| Methode und Pfad | Request | Wirkung |
| --- | --- | --- |
| `POST /api/simulator/nfc/present` | `{"uid":"D00DCAFE"}` | Karte am NFC-Simulator auflegen |
| `POST /api/simulator/nfc/remove` | keiner | simulierte Karte entfernen |
| `POST /api/simulator/flow/pulses` | `{"count":250}` | Impulse hinzufügen, Heartbeat und Poll ausführen |

Die NFC-Routen antworten bei einem realen NFC-Adapter mit `409`. Die
Simulator-API darf im Normalbetrieb nicht aktiviert bleiben und bietet keine
Produktionsauthentifizierung.

## OpenAPI aktualisieren

Nach jeder Änderung an Routen oder Request-/Response-Modellen:

```bash
python scripts/export_openapi.py
python -m pytest tests/test_documentation.py
```

Der Test schlägt fehl, wenn Anwendung und committed Snapshot voneinander
abweichen.
