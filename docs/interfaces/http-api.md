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
| `GET /api/wifi/status` | `200 WifiStatusResponse` | lokaler NetworkManager-Modus ohne Zugangsdaten |
| `GET /api/tap/status` | `200 TapStatusResponse` | vollständiger Zapfzustand |
| `POST /api/tap/poll` | `200 TapStatusResponse` | Zustand sofort auswerten; primär Diagnose/Test |

`TapStatusResponse` enthält:

| Feld | Typ | Bedeutung |
| --- | --- | --- |
| `state` | `str` | Zustand aus dem Zustandsautomaten, einschließlich des ventilgesperrten `nfc_capture` |
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
| `registration_welcome` | `str | null` | kurzlebiger Anzeigename nach erfolgreicher Armbandzuordnung; keine Anmeldung |

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
| `POST /api/admin/wifi/mode` | `{"mode":"ap"}` oder `{"mode":"client"}` | vorhandenes AP- oder Clientprofil aktivieren und Aktion auditieren |
| `GET /api/admin/users` | `AdminUserResponse[]` | Benutzer, Rollen-, Aktiv- und Armbandstatus |
| `POST /api/admin/users` | Vorname, optional Nachname/Zusatzfeld, `is_admin` | Benutzer anlegen und auditieren |
| `PATCH /api/admin/users/{id}` | vollständige editierbare Benutzerdaten | Benutzer, Rolle und Aktivstatus ändern und auditieren |
| `DELETE /api/admin/users/{id}` | `204` | Benutzer fachlich löschen; historische Buchungen und ID bleiben erhalten |
| `GET /api/admin/users/{id}/nfc-cards` | `AdminNfcCardResponse[]` | zugeordnete Armbänder mit maskiertem `uid_hint` |
| `POST /api/admin/users/{id}/nfc-cards/capture` | `AdminNfcCaptureResponse` | `remove_card`, `waiting`, `reader_unavailable` oder `assigned` |
| `DELETE /api/admin/nfc-capture` | `204` | laufende Live-Zuordnung abbrechen |
| `PATCH /api/admin/nfc-cards/{id}` | `{"active":false}` | Armband sperren oder reaktivieren und auditieren |
| `DELETE /api/admin/nfc-cards/{id}` | `204` | Zuordnung nach Bestätigung entfernen und auditieren |
| `GET /api/admin/settings` | `AdminSettingsResponse` | wirksamen Admin-Timeout lesen |
| `PATCH /api/admin/settings` | `{"admin_session_timeout_seconds":45}` | Timeout 10 bis 3600 Sekunden persistent und auditiert ändern |

`GET /api/wifi/status` liefert `mode`, `active_connection`, `ssid`,
`ip_address`, `client_profile_available` und bei nicht verfügbarer
Systemintegration einen nicht vertraulichen `detail`-Hinweis. Das schreibende
Gegenstück akzeptiert ausschließlich `ap` oder `client`, erfordert eine aktive
lokale NFC-Adminsitzung und wird nicht über den Smartphone-Proxy veröffentlicht.
Es legt keine Profile an und verarbeitet keine WLAN-Schlüssel.

Dies ist der ausführbare M7.7-Übergangsvertrag. CR-003 sieht vor, die
Autorisierung in M7.9 auf eine physisch präsente externe Superadmin-Karte
umzustellen. Pfade und Antworten bleiben bis zur gemeinsamen Änderung von
Implementierung, Tests, diesem Vertrag und OpenAPI unverändert.

Der Capture-Request besitzt bewusst keinen UID-Parameter. Nach seinem Start
muss der Leser mindestens einmal ohne Karte beobachtet werden, bevor das nächste
kurz aufgelegte Armband übernommen wird. So kann ein noch aufliegendes
Admin-Armband nicht versehentlich zugeordnet werden. Vollständige UIDs werden
weder in Adminantworten noch in Admin-Auditwerten ausgegeben.
Eine entfernte UID darf danach neu zugeordnet werden. Das letzte aktive
Armband eines aktiven Admins kann weder gesperrt noch entfernt werden.
Ein zugeordnetes oder bereits anderweitig vergebenes Armband wird nach Ende
des Capture-Ablaufs nicht als Anmeldung behandelt. Es muss zuerst physisch vom
Leser entfernt und für eine spätere Anmeldung erneut aufgelegt werden.

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
| `DELETE /api/web-admin/users/{id}` | Benutzer fachlich löschen; Buchungen und interne ID erhalten |
| `PUT /api/web-admin/users/{id}/password` | persönliches Passwort eines anderen aktiven Admins setzen oder zurücksetzen |
| `GET /api/web-admin/users/{id}/nfc-cards` | maskierte Armbandzuordnungen lesen |
| `POST /api/web-admin/users/{id}/nfc-cards/capture` | ventilgesperrte Live-Zuordnung starten oder deren Status lesen |
| `DELETE /api/web-admin/nfc-capture` | laufende Live-Zuordnung abbrechen |
| `PATCH /api/web-admin/nfc-cards/{id}` | Armband sperren oder reaktivieren |
| `DELETE /api/web-admin/nfc-cards/{id}` | Armbandzuordnung entfernen |
| `GET /api/web-admin/settings` | bestehenden lokalen Admin-Timeout lesen |
| `PATCH /api/web-admin/settings` | bestehenden lokalen Admin-Timeout ändern |

Der Capture-Request enthält keinen UID-Parameter. Beim ersten Aufruf wechselt
der Zustandsautomat nur aus einem nicht zapfenden Zustand zu `nfc_capture`,
schließt das Ventil und beendet die lokale NFC-Sitzung. NFC-Anmeldungen werden
bis Erfolg, Abbruch oder serverseitigem Timeout ignoriert. Mögliche
Antwortzustände sind `remove_card`, `waiting`, `reader_unavailable`,
`assigned` und `timed_out`. Die Smartphone-Abfragen lesen nur diesen
kurzlebigen Ablauf; der ACR122U selbst bleibt ereignisgesteuert.
Nach Erfolg oder Zuordnungskonflikt bleibt die dabei aufgelegte Karte bis zum
physischen Entfernen für die normale NFC-Anmeldung unterdrückt. Der
Capture-Ablauf selbst kann daher niemals eine Zapfsitzung beginnen.

Beim Löschen eines Benutzers entfernt die Fachlogik dessen Armbänder,
Passwort und aktive Websitzungen. Die Benutzerzeile wird mit einem
Löschzeitpunkt erhalten und aus der Verwaltung ausgeblendet, damit
unveränderliche Buchungen weiterhin eindeutig referenzierbar bleiben. Der
angemeldete Admin darf sich nicht selbst löschen.

## Smartphone-Betriebsverwaltung

Diese Routen benötigen ebenfalls eine gültige Websitzung; schreibende Methoden
zusätzlich den CSRF-Header. Mengen werden in Millilitern und Preise in Cent pro
Liter übertragen.

| Methode und Pfad | Wirkung |
| --- | --- |
| `GET /api/web-admin/events` | Veranstaltungen auflisten |
| `POST /api/web-admin/events` | Veranstaltung mit Name, Jahr, optionalem Zeitraum und Aktivstatus anlegen |
| `PATCH /api/web-admin/events/{id}` | Veranstaltung vollständig ändern oder aktivieren |
| `GET /api/web-admin/beverages` | Getränke einschließlich inaktiver Stammdaten auflisten |
| `POST /api/web-admin/beverages` | Getränk mit Standardfassgröße und Literpreis anlegen |
| `PATCH /api/web-admin/beverages/{id}` | Getränk, Standardfassgröße, Preis oder Aktivstatus ändern |
| `GET /api/web-admin/kegs` | Fasshistorie mit rechnerischer Restmenge auflisten |
| `POST /api/web-admin/kegs/switch` | bisherigen Fasskontext schließen und ausgewähltes neues Fass aktivieren |
| `POST /api/web-admin/kegs/detach` | aktives Fass schließen; danach ist kein Fass am Hahn aktiv |

Der operative Fasswechsel erwartet `beverage_id`. `initial_volume_ml` ist
optional; ohne Angabe wird die Standardfassgröße des Getränks verwendet.
`event_id` bleibt für kompatible Clients optional möglich, die
Smartphone-WebUI übernimmt jedoch die bereits aktive Veranstaltung aus dem
Abrechnungskontext. Fehlt sie, wird das Anzapfen abgelehnt und auf die
allgemeinen Einstellungen verwiesen. Der Wechsel beendet ein bisher aktives
Fass und legt das neue Fass atomar an. Ein inaktives Getränk oder eine
ungültige Menge wird abgelehnt. `detach` schließt nur das aktive Fass und
überträgt keinen Restbestand. Änderungen an Veranstaltungen, Getränken und
Fässern werden mit alten und neuen Werten auditiert.

## Smartphone-Buchungen und Protokolle

Alle folgenden Routen sind ausschließlich lesend und benötigen eine gültige
Websitzung. Sie verändern weder Buchungen noch Audit- oder Technikprotokolle.

| Methode und Pfad | Wirkung |
| --- | --- |
| `GET /api/web-admin/bookings` | unveränderliche Zapf-Rohdatensätze kombiniert filtern und neueste zuerst auflisten |
| `GET /api/web-admin/booking-sessions` | Rohdatensätze je NFC-Anmeldesitzung summiert als fachliche Buchungen auflisten |
| `GET /api/web-admin/statistics?event_id={id}` | Veranstaltungs-, Wartungs- und Abrechnungssummen je Benutzer liefern |
| `GET /api/web-admin/audit` | Adminaktionen mit Admin, Objekt sowie alten und neuen Werten auflisten |
| `GET /api/web-admin/technical-events` | technische Ereignisse mit Schweregrad und Details auflisten |

`bookings` und `booking-sessions` akzeptieren optional `event_id`, `user_id`,
`keg_id`, `kind`, `completion`, `occurred_from` und `occurred_to`. `audit` kann nach
`entity_type` und `action`, `technical-events` nach `severity` und
`event_type` filtern. Alle Listen akzeptieren `limit` von 1 bis 500; die
Smartphone-WebUI verwendet 100 zusammengefasste Anmeldebuchungen und jeweils
50 Protokolleinträge.
Zeitwerte sind ISO-8601-Zeitpunkte. Mengen und Preise bleiben ganzzahlige
Milliliter beziehungsweise Centwerte.

Die Statistik zählt NFC-Anmeldesitzungen als Buchungen und weist die über alle
zugehörigen Rohdatensätze summierte kostenpflichtige Istmenge,
Wartungsmenge sowie den gespeicherten Betrag getrennt aus. Benutzersummen
enthalten ausschließlich kostenpflichtige Buchungen. Historische Namen bleiben
auch nach dem fachlichen Löschen eines Benutzers auflösbar. Eine
Buchungsänderungs- oder Löschroute existiert bewusst nicht.

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
