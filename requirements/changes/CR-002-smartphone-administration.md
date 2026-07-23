# CR-002: Smartphone statt lokaler Administration

Status: Grundsatzentscheidung angenommen, Detailfragen offen

Datum: 2026-07-23

Anforderungskatalog: Version 0.5

## Anlass

Der in Milestone 6 entstandene lokale Adminmodus zeigt, dass eine vollständige
Verwaltung auf dem `800 × 480` großen Zapfdisplay technisch möglich ist. Es ist
jedoch unklar, ob diese Oberfläche im realen Veranstaltungsbetrieb ausreichend
genutzt würde, um den weiteren Entwicklungs- und Pflegeaufwand zu rechtfertigen.
Für umfangreiche Listen, Formulare und Auswertungen ist ein Smartphone
voraussichtlich das geeignetere Bediengerät.

Der Umfang von Milestone 7 soll deshalb reduziert und auf den wahrscheinlichen
Hauptzugang zur Administration ausgerichtet werden.

## Angenommene Grundsatzentscheidung

1. Die lokale Adminoberfläche wird vorerst nicht weiterentwickelt und im
   Kioskbetrieb nicht geöffnet.
2. Der vorhandene Entwicklungsstand aus Milestone 6 bleibt im Repository
   erhalten. Datenmodell, Verwaltungs-API, Auditlogik, Adminzustand und
   Benutzer-/Armbandverwaltung werden weder gelöscht noch zurückgebaut.
3. Der blaue Admin-Button bleibt für per NFC angemeldete Admins sichtbar. Beim
   Betätigen erscheint vorübergehend ein Hinweis, dass die lokale
   Adminoberfläche deaktiviert ist; ein Wechsel in den Adminmodus findet nicht
   statt.
4. Die weitere Verwaltung wird vorrangig als einfache, übersichtliche und
   smartphone-kompatible WebUI geplant.
5. Die Smartphone-Administration funktioniert ohne Internet über das lokale
   Admin-WLAN. Der WLAN-Zugang bildet die erste Zugriffshürde; die WebUI wird
   zusätzlich durch eine einfache Passwortauthentifizierung geschützt.

Diese Entscheidung legt weder das endgültige visuelle Design noch alle
Sicherheits- und Betriebsdetails der Smartphone-Administration fest.

## Auswirkungen auf Anforderungen

- `ZZ-AUT-011` und der lokale Verwaltungsanteil von `ZZ-UI-006` werden
  vorerst vertagt. Die bereits implementierten Komponenten bleiben bestehen.
- `ZZ-UI-007` beschreibt den vorübergehend deaktivierten lokalen Einstieg mit
  sichtbarem Hinweis.
- `ZZ-UI-008` beschreibt die responsive Smartphone-Administration.
- `ZZ-AUT-003`, `ZZ-NET-001` und `ZZ-NET-002` bilden die Grundlage für
  passwortgeschützten Zugriff im lokalen WLAN.
- `ZZ-AUT-004` bis `ZZ-AUT-007`, `ZZ-SYS-006`, `ZZ-KEG-002`,
  `ZZ-SAF-003`, `ZZ-SAF-007`, `ZZ-MNT-001` und `ZZ-DAT-003` bleiben fachlich
  erforderlich. Ihr bevorzugter Bedienweg verschiebt sich zur
  Smartphone-WebUI.
- `ZZ-SYS-001` bleibt unverändert: Zapfen und Administration müssen ohne
  Internetverbindung funktionieren.

## Technische und organisatorische Konsequenzen

- Die bestehende NFC-Sitzung am Kiosk und eine passwortgeschützte Websitzung
  auf einem Smartphone sind getrennte Authentifizierungskontexte.
- Die Verwaltungslogik und ihre Sicherheitsprüfungen sollen von beiden
  Bedienwegen unabhängig bleiben. Die WebUI steuert weiterhin weder Hardware
  noch SQLite direkt.
- Bereits vorhandene `/api/admin/*`-Funktionen sind aktuell an die lokale
  NFC-Adminsitzung gekoppelt. Ob diese Routen erweitert oder hinter einer
  gemeinsamen Autorisierungsschicht wiederverwendet werden, wird in der
  technischen Planung entschieden.
- Hardwaregebundene Abläufe wie die Live-Zuordnung eines NFC-Armbands benötigen
  weiterhin den Leser an der Zapfanlage. Die Smartphone-WebUI muss einen
  verständlichen, sicheren Ablauf zwischen Smartphone und Leser koordinieren.
- Ein gemeinsames Passwort reduziert den Einrichtungsaufwand, kann aber die
  eindeutige Zuordnung einer Änderung zu einem konkreten Admin erschweren.
  Dieser Konflikt mit der Audit-Anforderung `ZZ-DAT-003` ist vor der
  Implementierung aufzulösen.
- Die vorläufige Deaktivierung des lokalen Einstiegs darf keine vorhandenen
  Daten oder Schnittstellen entfernen und muss später ohne Datenmigration
  revidierbar sein.

## Safety- und Sicherheitsgrenzen

- Passwortschutz ersetzt nicht die serverseitige Autorisierung jeder
  schreibenden Adminaktion.
- Zugangsdaten dürfen weder im Repository noch in Logs, URLs oder
  Frontendquellen stehen.
- Administrative Aktionen dürfen eine laufende Zapfung nicht unkontrolliert
  verändern. Ventil-, Wartungs- und Fehlerreset-Aktionen benötigen weiterhin
  die vorhandenen serverseitigen Zustands- und Safety-Prüfungen.
- Der Server wird für den Smartphone-Zugriff nicht unkontrolliert in fremde
  Netze freigegeben. Bind-Adresse, Firewall und WLAN-Betriebsart sind Teil der
  noch offenen Betriebsentscheidung.
- Die Anwendung bleibt vollständig offlinefähig; externe Identitäts- oder
  Cloud-Dienste sind nicht erforderlich.

## Offene Fragen

1. Stellt der Raspberry Pi selbst das Admin-WLAN bereit oder wird ein bereits
   vorhandenes, ausschließlich für Admins zugängliches WLAN verwendet?
2. Wird ein gemeinsames Adminpasswort oder ein Passwort je Admin verwendet?
3. Wie wird bei einem gemeinsamen Passwort der ausführende Admin für
   `ZZ-DAT-003` nachvollziehbar bestimmt?
4. Wie werden Erstpasswort, Passwortwechsel, sicherer Reset und Speicherung des
   Passwort-Hashes umgesetzt?
5. Welche Sitzungsdauer, Logoutregeln und Schutzmaßnahmen gegen fremde
   Browseranfragen sind für den einwöchigen Betrieb angemessen?
6. Wird der lokale WLAN-Verkehr für die erste Ausbaustufe verschlüsselt und wie
   wird ein dafür notwendiges Zertifikat auf Smartphones praktikabel
   gehandhabt?
7. Welche Funktionen gehören zwingend in den ersten Smartphone-Checkpoint:
   Benutzer und Armbänder, Veranstaltung, Getränke, Fasswechsel, Parameter,
   Diagnose, Wartung, Protokolle oder Statistik?
8. Benötigen Störungsreset, Wartungszapfung oder Fasswechsel langfristig einen
   lokalen Notfallzugang, falls kein Smartphone verfügbar ist?
9. Wie zeigt die Zapfanlage einen vom Smartphone gestarteten
   hardwaregebundenen Ablauf, insbesondere die Armbandzuordnung, eindeutig an?

## Vorläufige Abnahmekriterien

1. Nur bei einem angemeldeten Admin bleibt der blaue Admin-Button sichtbar.
2. Der Button zeigt einen verständlichen Hinweis zur vorübergehenden
   Deaktivierung und öffnet keine lokale Adminsitzung.
3. Der vorhandene lokale Entwicklungsstand bleibt automatisiert testbar und
   wird nicht gelöscht.
4. Die spätere Admin-WebUI ist auf üblichen Smartphone-Breiten ohne
   horizontales Scrollen bedienbar.
5. Ohne gültige Passwortsitzung sind geschützte Adminfunktionen nicht
   erreichbar.
6. Die Administration funktioniert bei physisch getrennter
   Internetverbindung im vorgesehenen lokalen WLAN.
7. Schreibende Adminaktionen bleiben serverseitig autorisiert und
   nachvollziehbar.

Die konkrete Implementierungsabnahme wird nach Klärung der offenen Fragen in
den Arbeitspaketen von Milestone 7 präzisiert.
