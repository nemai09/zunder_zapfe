# Lokaler HTTP-API-Vertrag

Status: Alpha-Vertrag

Interne Basis-URL: `http://127.0.0.1:8000`
Maschinenlesbar: [`openapi.json`](openapi.json)

## Geltungsbereich

Die API ist die einzige vorgesehene Grenze zwischen WebUI und Backend. Sie ist
standardmäßig nur über Loopback erreichbar, verwendet JSON und benötigt zur
Laufzeit kein Netzwerk. Die Alpha-API besitzt noch keinen Versionspräfix;
Änderungen müssen daher in einem gemeinsamen PR mit ihren Clients erfolgen.

## Allgemeine Antworten

- `200`: Aktion oder Abfrage erfolgreich, JSON-Antwort.
- `204`: Aktion erfolgreich, kein Antwortkörper.
- `403`: keine aktive, serverseitig bestätigte Adminsitzung.
- `404`: angeforderte Verwaltungsentität existiert nicht.
- `409`: fachliche Vorbedingung oder Zustandsübergang nicht erfüllt;
  `{"detail":"..."}`.
- `422`: Request-JSON verletzt das Schema.
- `500`: unerwarteter interner Fehler; nicht als normaler Ablauf behandeln.

Die Kiosk-API übernimmt die Benutzeridentität ausschließlich aus der lokalen
NFC-Sitzung. Die Smartphone-Administration verwendet eine davon getrennte,
persönliche Passwortsitzung. Clients dürfen bei Fachoperationen weder eine
ausführende Benutzer-ID noch ein Admin-Flag einspeisen.

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
| `nfc_feedback` | `"unknown" | "blocked" | null` | kurzlebige Ablehnungsursache für die Idle-WebUI |

`valve_open` ist ein angeforderter Softwarezustand und keine physische
Ventilrückmeldung. Die Kiosk-Debuganzeige verwendet genau dieses Feld.

## Sitzung

| Methode und Pfad | Vorbedingung | Ergebnis |
| --- | --- | --- |
| `GET /api/session/status` | keine | aktuelle NFC-Sitzung |
| `POST /api/session/activity` | `authenticated`, `admin` oder `manual_pouring` | `204`, setzt Inaktivität zurück |
| `POST /api/session/logout` | `authenticated`, `admin` oder `top_up_available` | `204`, danach `idle` |

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

## Lokale Administration

Alle folgenden Routen erfordern nach dem Einstieg den Zustand `admin`. Die
Autorisierung wird bei jedem Aufruf serverseitig aus der NFC-Sitzung und dem
aktuellen Datenbankkonto abgeleitet. Der Client übergibt weder Admin-Flag noch
ausführende Benutzer-ID.

| Methode und Pfad | Request/Ergebnis | Wirkung |
| --- | --- | --- |
| `POST /api/admin/session/enter` | `TapStatusResponse` | authentifizierter Admin wechselt bei geschlossenem Ventil zu `admin` |
| `POST /api/admin/session/exit` | `TapStatusResponse` | zurück zu `authenticated` und normalem Timeout |
| `GET /api/admin/users` | `AdminUserResponse[]` | Benutzer, Rollen-, Aktiv- und Armbandstatus |
| `POST /api/admin/users` | Vorname, optional Nachname/Zusatzfeld, `is_admin` | Benutzer anlegen und auditieren |
| `PATCH /api/admin/users/{id}` | vollständige editierbare Benutzerdaten | Benutzer, Rolle und Aktivstatus ändern und auditieren |
| `GET /api/admin/users/{id}/nfc-cards` | `AdminNfcCardResponse[]` | zugeordnete Armbänder mit maskiertem `uid_hint` |
| `POST /api/admin/users/{id}/nfc-cards/capture` | `AdminNfcCaptureResponse` | `remove_card`, `waiting`, `reader_unavailable` oder `assigned` |
| `DELETE /api/admin/nfc-capture` | `204` | laufende Live-Zuordnung abbrechen |
| `PATCH /api/admin/nfc-cards/{id}` | `{"active":false}` | Armband sperren oder reaktivieren und auditieren |
| `DELETE /api/admin/nfc-cards/{id}` | `204` | Zuordnung nach Bestätigung entfernen und auditieren |
| `GET /api/admin/settings` | `AdminSettingsResponse` | wirksamen Admin-Timeout lesen |
| `PATCH /api/admin/settings` | `{"admin_session_timeout_seconds":45}` | Timeout 10 bis 3600 Sekunden persistent und auditiert ändern |

Der Capture-Request besitzt bewusst keinen UID-Parameter. Nach seinem Start
muss der Leser mindestens einmal ohne Karte beobachtet werden, bevor das nächste
kurz aufgelegte Armband übernommen wird. So kann ein noch aufliegendes
Admin-Armband nicht versehentlich zugeordnet werden. Vollständige UIDs werden
weder in Adminantworten noch in Admin-Auditwerten ausgegeben.
Eine entfernte UID darf danach neu zugeordnet werden. Das letzte aktive
Armband eines aktiven Admins kann weder gesperrt noch entfernt werden.

## Smartphone-Webauthentifizierung

Normale Benutzer besitzen kein Passwort und erscheinen nicht in der
Loginauswahl. Jeder aktive Admin mit gesetztem Passwort kann eine persönliche,
von NFC unabhängige Websitzung eröffnen.

| Methode und Pfad | Request/Ergebnis | Wirkung |
| --- | --- | --- |
| `GET /api/web-auth/admins` | `WebAdminLoginOptionResponse[]` | aktive Admins mit gesetztem Passwort für die Loginauswahl |
| `POST /api/web-auth/login` | `user_id`, `password` | prüft Argon2id-Hash und setzt Sitzungs- sowie CSRF-Cookie |
| `GET /api/web-auth/session` | `WebAdminSessionResponse` | aktuelle persönliche Websitzung |
| `POST /api/web-auth/logout` | `204` | widerruft die Sitzung und entfernt Cookies |
| `POST /api/web-auth/password` | bisheriges und neues Passwort | ändert das eigene Passwort und beendet bestehende Sitzungen |

Das opake Sitzungstoken liegt ausschließlich in einem `HttpOnly`-Cookie mit
`SameSite=Strict`; die Datenbank speichert nur seinen SHA-256-Hash. Schreibende
Requests benötigen zusätzlich den Wert des nicht-`HttpOnly`-CSRF-Cookies im
Header `X-CSRF-Token`. Die Alpha-Defaults sind 30 Minuten Inaktivität und
12 Stunden absolute Dauer. Fünf fehlgeschlagene Loginversuche innerhalb einer
Minute sperren weitere Versuche vorübergehend.

Webpasswort und Hash erscheinen weder in Antworten noch in Logs oder
Auditwerten. Da die isolierte Alpha-Ausbaustufe HTTP verwendet, besitzt das
Sitzungscookie noch kein `Secure`-Attribut.

## Smartphone-Benutzerverwaltung

Die folgenden Routen benötigen eine gültige Websitzung; schreibende Methoden
zusätzlich den CSRF-Header. Die Fachlogik und Auditregeln entsprechen der
lokalen Verwaltungs-API.

| Methode und Pfad | Wirkung |
| --- | --- |
| `GET /api/web-admin/users` | Benutzer und maskierten Armbandstatus auflisten |
| `POST /api/web-admin/users` | Benutzer anlegen |
| `PATCH /api/web-admin/users/{id}` | Profil, Rolle und Aktivstatus ändern |
| `PUT /api/web-admin/users/{id}/password` | persönliches Passwort eines anderen aktiven Admins setzen oder zurücksetzen |
| `GET /api/web-admin/users/{id}/nfc-cards` | maskierte Armbandzuordnungen lesen |
| `PATCH /api/web-admin/nfc-cards/{id}` | Armband sperren oder reaktivieren |
| `DELETE /api/web-admin/nfc-cards/{id}` | Armbandzuordnung entfernen |
| `GET /api/web-admin/settings` | bestehenden lokalen Admin-Timeout lesen |
| `PATCH /api/web-admin/settings` | bestehenden lokalen Admin-Timeout ändern |

Die hardwaregebundene Live-Zuordnung wird erst mit dem sicheren
Zuordnungszustand aus `M7.4` über die Smartphone-API freigegeben.

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
