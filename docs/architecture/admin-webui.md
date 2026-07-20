# Lokale Admin-WebUI

Status: Milestone-6-Implementierung, Zielsystemprüfung ausstehend

Die lokale Administration ist ein zusätzlicher Modus derselben Kiosk-WebUI.
Ein Admin meldet sich wie jeder andere Benutzer durch kurzes Auflegen seines
NFC-Armbands an und kann normal zapfen. Ausschließlich die serverseitig
ermittelte Adminrolle blendet den Einstieg in den Adminmodus ein.

## Sicherheitsgrenze

Das Backend autorisiert jede Adminroute erneut anhand der aktiven NFC-Sitzung
und des expliziten Adminzustands. Versteckte UI-Elemente sind keine
Autorisierung. Während des Adminmodus bleibt das Ventil geschlossen und eine
Zapfung kann nicht gestartet werden.

Die Anwendung bleibt in Milestone 6 an Loopback gebunden. Eine spätere
Administration über das lokale WLAN benötigt eine eigene passwortgeschützte
Websitzung gemäß `ZZ-AUT-003` und darf nicht stillschweigend die geräteweite
NFC-Sitzung übernehmen.

## Sitzung

Der normale Benutzer-Timeout bleibt bei `15 s`. Beim bewussten Wechsel in den
Adminmodus verwendet dieselbe Sitzung den separat konfigurierbaren
Admin-Timeout, standardmäßig `30 s`. Jede Touchaktivität setzt den jeweils
aktiven Timer zurück. Zurück zum Zapfen stellt den normalen Timeout wieder her;
Timeout oder Logout beenden die Sitzung vollständig.

## Verwaltungsgruppen

- Übersicht
- Benutzer und Armbänder
- Veranstaltung, Getränke und Fässer
- Diagnose und Wartung
- Einstellungen
- Protokolle und Statistik

Milestone 6 implementiert als ersten vollständigen Ablauf Benutzer und
Armbänder. Die übrigen Gruppen bilden die stabile Navigation für spätere
Checkpoints und kennzeichnen noch nicht verfügbare Funktionen eindeutig.

Die Touchansicht ist für `800 × 480` als zweigeteilter Arbeitsbereich aufgebaut:
links eine stabile Bereichsnavigation, rechts der jeweils aktive Verwaltungsbereich.
Die Benutzerverwaltung kombiniert eine kompakte Auswahlliste mit einem Editor
für Vorname, optionalen Nachnamen, Zusatzfeld, Rolle und Aktivstatus. Bereits
zugeordnete Armbänder werden ausschließlich mit maskiertem UID-Hinweis gezeigt.
Für typische Veranstaltungen mit 20 bis 30 Benutzern besitzt die Liste eine
Namenssuche, Filter für Aktiv-, Sperr- und Adminstatus, einen Ergebniszähler
und einen eigenen Scrollbereich.

## Komponentenvertrag

- `TapController` besitzt den ventilgesperrten Zustand `ADMIN` und erzwingt den
  separaten Sitzungstimeout.
- `TapService` hält die vom NFC-Login abgeleitete Identität und gibt nur die
  aktuelle Admin-ID an den Verwaltungsdienst frei.
- `AdminService` prüft bei jedem Aufruf Zustand, Rolle und aktives Konto,
  kapselt Transaktionen, Audit und den kurzlebigen Capture-Zustand.
- `Repository` speichert Benutzerdaten, Kartenstatus, Einstellungen und
  Auditwerte; vollständige UIDs bleiben auf Persistenz und Hardwareadapter
  begrenzt.
- Die WebUI verwendet ausschließlich `/api/admin/*` und besitzt keine direkte
  SQLite- oder Hardwareverbindung.

Selbstdeaktivierung, Selbstdemotion sowie das Sperren oder Entfernen des letzten
aktiven Armbands eines aktiven Admins werden abgelehnt. Ebenso kann der letzte
aktive Admin nicht durch einen anderen Admin deaktiviert oder herabgestuft
werden.

## Live-Zuordnung eines Armbands

1. Admin meldet sich kurz mit seinem Armband an und öffnet den Adminmodus.
2. Admin legt einen Benutzer an oder wählt ihn aus.
3. Admin startet „Armband zuweisen“.
4. Das zuzuordnende Veranstaltungsarmband wird kurz auf den Leser gelegt.
5. Das Backend liest die UID direkt aus dem aktuellen Hardwarestatus, prüft
   Eindeutigkeit und speichert die Zuordnung mit Audit-Eintrag.
6. Das Armband kann sofort entfernt werden und meldet den Benutzer nach dem
   Ende der Adminsitzung an.

Der Webclient übermittelt keine UID. Bereits bekannte Armbänder werden nicht
stillschweigend umgehängt. Eine Zuordnung kann nach einer Bestätigung entfernt
und im selben Transaktionsablauf ohne vollständige UID im Audit protokolliert
werden. Danach steht das Armband für eine neue Live-Zuordnung bereit.

Traceability: `ZZ-AUT-002`, `ZZ-AUT-004`, `ZZ-AUT-005`, `ZZ-AUT-007`,
`ZZ-AUT-011`, `ZZ-DAT-003` und `ZZ-UI-006`.
