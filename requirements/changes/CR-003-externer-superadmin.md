# CR-003: Externer, präsenzgebundener Superadmin

Status: angenommen; Umsetzung experimentell begonnen

Datum: 2026-07-24

Anforderungskatalog: Version 1.0

## Anlass

Die vollständige Fachadministration erfolgt gemäß CR-002 vorrangig über
Smartphones. Für Störungen ohne verfügbares Smartphone werden dennoch wenige
lokale Funktionen benötigt. Ein normaler Admin ist dafür ungeeignet: Er bleibt
eine abrechenbare Person, darf regulär zapfen und seine Rolle sowie Karten
werden in der gemeinsamen Benutzerdatenbank verwaltet.

Deshalb wird ein separater Wartungszugang eingeführt, der nicht Teil der
Personenverwaltung ist und nur bei physisch aufgelegter Karte gilt.

## Angenommene Entscheidung

1. Es gibt genau eine Superadmin-NFC-Identität außerhalb der Benutzer-,
   Admin- und NFC-Kartentabellen.
2. Die Anwendung bietet weder Ändern noch Löschen dieser Identität an.
3. Die Karte öffnet direkt das lokale Low-Level-Menü und niemals die normale
   Zapfoberfläche.
4. Entfernen der Karte oder Trennen des Lesers beendet die Berechtigung nach
   kurzer technischer Entprellung von höchstens zwei Sekunden.
5. Der blaue Admin-Button normaler Admins bleibt sichtbar, zeigt aber nur noch
   einen Hinweis auf die Smartphone-WebUI.
6. Das Low-Level-Menü enthält WLAN, Notfall-Benutzer, Wartungszapfung und
   lesbare Systemdiagnose.
7. Der Superadmin besitzt keinen Webzugang, kein Passwort, keine persönliche
   Verbrauchssumme und erzeugt keine kostenpflichtige Benutzerbuchung.

## Lokale Identität

Das Credential wird auf dem Zielsystem in einer separaten, nur für den
Dienstbenutzer lesbaren Datei gespeichert. Die UID wird darin nicht im Klartext
abgelegt. Repository, Datenbank, HTTP-API, Frontend und Logs dürfen weder UID
noch Credential enthalten.

Die Ersteinrichtung liest die Karte direkt über den ACR122U. Eine bestehende
Credential-Datei wird nicht überschrieben. Verlust oder Defekt der Karte
erfordern einen bewussten administrativen Eingriff auf dem Raspberry Pi
außerhalb der Anwendung.

Während der experimentellen Einführung darf eine noch nicht vorhandene Datei
den bisherigen Betrieb nicht verhindern. Vor Abnahme des Superadmin-Ablaufs
muss die Zielsystemprüfung eine eingerichtete Karte voraussetzen.

## Notfall-Benutzeranlage mit einem Leser

Zum Erfassen eines neuen Armbands muss die Superadmin-Karte den einzigen Leser
verlassen. Dies ist keine fortgesetzte allgemeine Superadmin-Sitzung:

1. Der Superadmin wählt bewusst „Benutzer erstellen“ oder „Admin erstellen“.
2. Das Backend schränkt die Berechtigung auf genau eine NFC-Erfassung ein.
3. Nach Entfernen der Superadmin-Karte läuft ein Erfassungsfenster von maximal
   15 Sekunden.
4. Das erste unbekannte Armband legt Benutzer und Kartenzuordnung atomar an.
5. Erfolg, Konflikt, Abbruch oder Timeout führen zum Lockscreen.

Normale Benutzer erhalten kein Passwort. Neue Admins erhalten ein zufälliges
Einmalpasswort, das nur einmal lokal angezeigt wird und beim ersten Webzugang
geändert werden muss. Ein gemeinsames Defaultpasswort ist nicht zulässig.

## Wartungszapfung

Die lokale Zapfsteuerung verwendet die bestehenden Safety-Grenzen,
Durchflussmessung und Push-to-fill-Bedienung. Sie erzeugt keine persönliche
oder kostenpflichtige Benutzerbuchung. Die gemessene Menge wird dennoch als
unveränderliche Wartungsentnahme gespeichert, damit Fassbestand und Diagnose
korrekt bleiben.

Kartenentfernung, Lesertrennung, Loslassen, Zeitlimit, Not-Aus, Watchdog und
Durchflussfehler schließen zuerst das Ventil. Erst danach wird die gemessene
Wartungsentnahme abgeschlossen. Ein Persistenzfehler darf die Anlage nicht in
einem zapfbereiten Zustand hinterlassen.

## Audit und Diagnose

Privilegierte Superadmin-Aktionen bleiben nachvollziehbar. Auditdatensätze
verwenden den technischen Akteur `Superadmin`, aber keine erfundene Benutzer-ID
und keine NFC-Information. Reine Diagnosezugriffe verändern keine Daten.

Die lokale Diagnose zeigt mindestens Version, Revision, Leserstatus,
WLAN-Modus, angeforderten Ventilstatus, Durchfluss, Not-Aus, aktiven Fasskontext
und letzten Safety-Grund.

## Auswirkungen

- `ZZ-AUT-001` bleibt für die Benutzertabelle bei Benutzer und Admin.
- `ZZ-AUT-013` bis `ZZ-AUT-015` definieren Identität, Kartenpräsenz und
  Notfallanlage.
- `ZZ-UI-007` entzieht normalen Admins den lokalen Systemzugang.
- `ZZ-UI-010` definiert das neue Low-Level-Menü.
- `ZZ-NET-003` wird ausschließlich dem Superadmin zugeordnet.
- `ZZ-MNT-001`, `ZZ-MNT-002`, `ZZ-DAT-002` und `ZZ-DAT-003` unterscheiden
  technische Wartungsentnahmen von Benutzerbuchungen.
- OD-013 und OD-014 sind entschieden; OD-015 dokumentiert das eng begrenzte
  NFC-Übergabefenster.

## Abnahmekriterien

1. Die Superadmin-Identität existiert außerhalb sämtlicher Benutzertabellen.
2. Keine Anwendungsschnittstelle kann sie anzeigen, ändern oder löschen.
3. Auflegen öffnet ausschließlich das Low-Level-Menü.
4. Entfernen oder Lesertrennung beendet den Zugang innerhalb von zwei Sekunden.
5. Eine laufende Wartungszapfung wird dabei sicher geschlossen und gespeichert.
6. Wartungsmengen reduzieren den Fassbestand, aber niemals einen
   Benutzerverbrauch oder -betrag.
7. Die Einmalerfassung legt genau einen Benutzer samt unbekanntem Armband an.
8. Einmalpasswörter erscheinen genau einmal und niemals in Log oder Audit.
9. Der blaue Admin-Button verändert keinen Backendzustand.
10. Alle schreibenden Low-Level-Endpunkte sind loopbackbeschränkt und prüfen
    die physische Kartenpräsenz serverseitig.
