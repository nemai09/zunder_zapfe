# Smartphone-Admin-WebUI

Status: `M7.2` bis `M7.4` implementiert; weitere Fachbereiche geplant

## Ziel und Abgrenzung

Die Administration wird als responsive lokale Webanwendung für Smartphones
umgesetzt. Sie läuft auf demselben Raspberry Pi und verwendet dieselbe
SQLite-Datenbank und dieselben Fachservices wie der Kiosk. Sie benötigt weder
Internet noch einen Cloud-Dienst.

Der vorhandene lokale Adminmodus aus Milestone 6 bleibt im Code erhalten, wird
aber nicht geöffnet oder weiter ausgebaut. Die Smartphone-WebUI steuert weder
SQLite noch Hardware direkt, sondern ausschließlich dokumentierte HTTP-APIs.
Der blaue Kiosk-Button öffnet deshalb keine lokale Verwaltung mehr, sondern
weist auf Smartphone und WLAN `ZUNDER_ZAPFE` hin.

## Gemeinsames Benutzer- und Anmeldemodell

Alle Personen bleiben Datensätze in `users`:

- normale Benutzer: NFC-Armband, kein Passwort, kein Webzugang;
- Admins: NFC-Armband für das Zapfen und eigenes Passwort für die WebUI;
- Rolle und Aktivstatus gelten für beide Zugangswege gemeinsam;
- eine Sperre oder Herabstufung beendet auch bestehende Websitzungen.

Der Login zeigt die aktiven Admins als Auswahl und fordert das persönliche
Passwort an. Damit ist kein zusätzliches dauerhaftes Login-Feld notwendig.
Das Backend verwendet ausschließlich die ausgewählte interne Benutzer-ID und
prüft Rolle, Aktivstatus und Passwort-Hash.

Passwörter werden mit Argon2id und individuellem Salt gehasht. Das vorhandene
nullable Feld `users.password_hash` bleibt für normale Benutzer leer.
Passwörter und Hashes erscheinen niemals in API-Antworten, Auditwerten oder
Logs.

## Websitzung

Nach erfolgreichem Login erzeugt das Backend ein kryptografisch zufälliges,
opakes Sitzungstoken. Im Browser liegt es ausschließlich als
`HttpOnly`-Cookie mit `SameSite=Strict`; die Datenbank speichert nur einen
Hash des Tokens zusammen mit Admin-ID, Erzeugung, letzter Aktivität und Ablauf.
JWT ist nicht notwendig.

Als Alpha-Defaults gelten:

- Inaktivitätsablauf nach 30 Minuten;
- absolute Sitzungsdauer von 12 Stunden;
- expliziter Logout;
- Widerruf aller Sitzungen bei Sperre, Herabstufung oder Passwortreset;
- beim eigenen Passwortwechsel bleibt höchstens die neu bestätigte Sitzung
  bestehen.

Da die isolierte Alpha-Ausbaustufe bewusst HTTP verwendet, kann das Cookie noch
nicht das Attribut `Secure` tragen. Zustandsändernde Routen prüfen deshalb
zusätzlich Ursprung und CSRF-Token. Fehlgeschlagene Logins werden gedrosselt
und ohne Passwortinhalt als technisches Ereignis protokolliert.

## Autorisierungsgrenze

Die vorhandene `AdminService`-Logik wird von der geräteweiten NFC-Sitzung
entkoppelt. Ein geprüfter Administrationskontext enthält mindestens:

- `admin_user_id`;
- Herkunft `web` oder später wieder `kiosk`;
- Sitzungskennung für Widerruf und Diagnose.

Jede schreibende Fachoperation erhält diesen Kontext serverseitig. Versteckte
Navigationselemente sind keine Autorisierung. Audit-Einträge verwenden immer
die konkrete `admin_user_id`.

## NFC-Armband zuweisen

Die Armbandzuordnung ist der einzige gekoppelte Ablauf zwischen Smartphone und
NFC-Leser:

1. Admin wählt oder erstellt den Benutzer auf dem Smartphone.
2. Admin startet „Armband zuweisen“.
3. Das Backend beendet eine eventuell offene NFC-Benutzersitzung, schließt das
   Ventil, sperrt Zapfstarts und versetzt den Kiosk sichtbar in den
   Zuordnungszustand `nfc_capture`.
4. Ein bislang unbekanntes Armband wird kurz am Leser aufgelegt.
5. Der ereignisgesteuerte NFC-Adapter liefert die UID ausschließlich an das
   Backend.
6. Das Backend ordnet das Armband zu, auditiert die Aktion ohne vollständige
   UID und hebt den Zuordnungszustand wieder auf.

Der Smartphone-Client darf den Status dieses kurzlebigen Ablaufs abfragen. Das
ist eine HTTP-Statusabfrage und kein erneutes Hardware-Polling. Timeout, Abbruch
und Verbindungsverlust schließen den Zuordnungszustand sicher. Ein
serverseitiges Limit von `45 s` verhindert eine dauerhaft liegen gebliebene
Sperre, wenn Browser oder WLAN-Verbindung abbrechen. Not-Aus und verriegelte
Fehlerzustände werden dadurch niemals aufgehoben.

## Navigations- und Funktionsumfang

Die Oberfläche verwendet eine schmale, mobile Navigation und auf größeren
Bildschirmen dieselben Ansichten mit mehrspaltigem Layout. Für die erste
Ausbaustufe bleibt sie bei HTML, CSS und JavaScript ohne zusätzlichen
Frontend-Buildschritt.

### Übersicht (`M7.4`)

- Backendbereitschaft und Buildstring;
- Anzahl bekannter Benutzer und aktiver Armbänder;
- klare Kennzeichnung der folgenden Arbeitspakete.

Event, Fass, Störung und Summen werden mit den zugehörigen Fach-APIs in
`M7.5` bis `M7.7` ergänzt.

### Benutzer und Armbänder (`M7.4`)

- suchen, filtern, anlegen, bearbeiten, aktivieren und sperren;
- Rolle vergeben oder entziehen;
- NFC-Armband zuweisen, sperren und entfernen;
- persönliches Adminpasswort setzen, ändern oder zurücksetzen;
- Schutz des letzten aktiven Adminzugangs.

Die mobile Liste ist such- und filterbar und bleibt damit auch bei 20 bis 30
Personen übersichtlich. Das Bearbeitungsformular erscheint als mobile
Vollbreitenkarte und auf größeren Bildschirmen als begrenztes Dialogfenster.

### Veranstaltungen, Getränke und Fässer

- Veranstaltungen anlegen, auswählen und aktivieren;
- Getränke mit Fassgröße und Preis anlegen und pflegen;
- Fasshistorie und rechnerischen Restbestand anzeigen;
- geführter Fasswechsel mit bewusstem Abschluss des bisherigen Fasses.

### Buchungen und Abrechnung

- Buchungen nach Veranstaltung, Benutzer, Fass, Zeitraum, Art und Abschluss
  filtern;
- Buchungsdetails und Summen pro Benutzer und Veranstaltung anzeigen;
- Einzelabrechnung als nachvollziehbare Bildschirmansicht vorbereiten.

Abgeschlossene Zapfbuchungen bleiben unveränderlich. Bearbeiten und Löschen
werden nicht angeboten. Storno, Korrektur und ein verbindliches Exportformat
bleiben bis zu den Entscheidungen `OD-005` bis `OD-007` außerhalb des
verbindlichen Umfangs.

### Einstellungen

- Sitzungs- und Zapfzeitlimits;
- Aktivierungsentprellung;
- Mengen- und Durchflusskalibrierung;
- Safety- und Plausibilitätsgrenzen;
- ausschließlich validierte, auditierte Änderungen.

### Diagnose, Wartung und Safety

- Hardware- und Dienststatus sowie technische Ereignisse;
- verriegelte Fehlerursache und bewusster Safety-Reset;
- Wartungsmodus und gemessene, nicht berechnete Wartungsentnahme;
- keine Umgehung von Not-Aus, Watchdogs oder Zustandsprüfungen.

### Audit und Statistik

- Auditaktionen mit Admin, Zeitpunkt, Objekt und Änderung;
- technische Ereignisse mit Schweregrad und Filter;
- Verbrauch, Betrag und Mengen nach Veranstaltung, Benutzer, Getränk und Fass.

## Schnittstellen- und Datenarbeit

Milestone 7 benötigt:

- eine Migration für widerrufbare Websitzungen;
- einen Authentifizierungsservice für Hashing, Login, Logout und Passwortpflege;
- eine gemeinsame serverseitige Admin-Autorisierung;
- listen- und filterfähige Repository-Operationen;
- Verwaltungs-APIs für Veranstaltungen, Getränke, Fässer, Buchungen,
  Einstellungen, Diagnose, Wartung, Audit und Statistik;
- aktualisierte OpenAPI- und menschenlesbare Verträge.

Bestehende Fachinvarianten bleiben bestehen: höchstens eine aktive
Veranstaltung und ein aktives Fass, ganzzahlige Mengen und Centwerte,
unveränderliche Zapfbuchungen und Audit im selben Transaktionsablauf wie die
Adminänderung.

## Quellen für die Sicherheitsentscheidung

- [FastAPI: Passwort-Hashing mit Argon2](https://fastapi.tiangolo.com/de/tutorial/security/oauth2-jwt/)
- [OWASP: Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [OWASP: Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)

Traceability: `ZZ-SYS-001`, `ZZ-SYS-004` bis `ZZ-SYS-006`,
`ZZ-AUT-003` bis `ZZ-AUT-007`, `ZZ-AUT-012`, `ZZ-KEG-001` bis
`ZZ-KEG-004`, `ZZ-SAF-003`, `ZZ-SAF-007`, `ZZ-MNT-001`, `ZZ-MNT-002`,
`ZZ-BIL-001` bis `ZZ-BIL-004`, `ZZ-UI-008`, `ZZ-NET-001`, `ZZ-NET-002`
und `ZZ-DAT-001` bis `ZZ-DAT-007`.
