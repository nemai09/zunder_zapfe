# CR-002: Smartphone statt lokaler Administration

Status: angenommen; um begrenztes lokales Systemmenü ergänzt

Datum: 2026-07-23

Anforderungskatalog: Version 0.8

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
3. Der blaue Admin-Button bleibt für per NFC angemeldete Admins sichtbar. Er
   öffnet nicht die vertagte vollständige Adminoberfläche, sondern
   ausschließlich ein lokales Low-Level-Systemmenü für den WLAN-Moduswechsel.
4. Die weitere Verwaltung wird vorrangig als einfache, übersichtliche und
   smartphone-kompatible WebUI geplant.
5. Die Smartphone-Administration funktioniert ohne Internet über das lokale
   Admin-WLAN. Der WLAN-Zugang bildet die erste Zugriffshürde; die WebUI wird
   zusätzlich durch eine einfache Passwortauthentifizierung geschützt.

## Präzisierungen

- Alle bekannten Personen bleiben in derselben Benutzerdatenbank. Normale
  Benutzer besitzen kein Passwort und erhalten keinen Webzugang.
- Jeder Admin setzt ein eigenes Passwort. Dadurch kann jede Webaktion weiterhin
  der vorhandenen Benutzer-ID zugeordnet und gemäß `ZZ-DAT-003` auditiert
  werden.
- Der Raspberry Pi stellt standardmäßig den eigenständigen Access Point mit der
  SSID `ZUNDER_ZAPFE` bereit. Ein Admin kann ihn am Touchscreen vorübergehend
  zugunsten eines bereits bekannten WLAN-Clientprofils deaktivieren.
- Das lokale Systemmenü richtet keine neuen WLANs ein und verarbeitet keine
  WLAN-Zugangsdaten. Neue Clientprofile werden außerhalb der Anwendung
  vorbereitet.
- HTTPS ist für diese physisch isolierte Alpha-Ausbaustufe nicht erforderlich.
  Eine spätere Freigabe in andere Netze erfordert eine neue Bewertung.
- Der eigene Passwortwechsel wird in das Benutzermenü der Admin-WebUI
  integriert. Für den initialen Admin und vergessene Passwörter werden sichere,
  offlinefähige Setz- und Resetabläufe vorgesehen.
- Die einzige direkte Koordination zwischen Smartphone und NFC-Leser ist die
  Registrierung beziehungsweise Zuordnung eines Veranstaltungsarmbands.
- Die Smartphone-WebUI soll alle akzeptierten Adminanforderungen abdecken,
  insbesondere Benutzer-, Veranstaltungs-, Getränke-, Fass-, Buchungs-,
  Einstellungs-, Diagnose-, Wartungs-, Audit- und Statistikfunktionen.

## Auswirkungen auf Anforderungen

- `ZZ-AUT-011` und der lokale Verwaltungsanteil von `ZZ-UI-006` werden
  vorerst vertagt. Die bereits implementierten Komponenten bleiben bestehen.
- `ZZ-UI-007` beschreibt den auf das Low-Level-Systemmenü begrenzten lokalen
  Einstieg.
- `ZZ-UI-008` beschreibt die responsive Smartphone-Administration.
- `ZZ-AUT-003`, `ZZ-NET-001` bis `ZZ-NET-003` bilden die Grundlage für
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
  NFC-Adminsitzung gekoppelt. Sie werden hinter einer gemeinsamen
  Autorisierungsschicht für persönliche Websitzungen wiederverwendet und
  fachlich erweitert.
- Die Live-Zuordnung eines NFC-Armbands benötigt weiterhin den Leser an der
  Zapfanlage. Die Smartphone-WebUI muss diesen einen hardwaregebundenen Ablauf
  verständlich und sicher koordinieren.
- Persönliche Adminpasswörter lösen die Websitzung eindeutig zu einem
  Benutzerdatensatz auf. Dadurch kann das bestehende Auditmodell ohne
  generischen Webadmin weiterverwendet werden.
- Die vorläufige Deaktivierung des lokalen Einstiegs darf keine vorhandenen
  Daten oder Schnittstellen entfernen und muss später ohne Datenmigration
  revidierbar sein.
- Der Moduswechsel wird über einen fest installierten Systemhelfer und
  eng begrenzte NetworkManager-Berechtigungen ausgeführt. Die Webanwendung
  erhält weder `sudo` noch Zugriff auf gespeicherte WLAN-Schlüssel.

## Safety- und Sicherheitsgrenzen

- Passwortschutz ersetzt nicht die serverseitige Autorisierung jeder
  schreibenden Adminaktion.
- Zugangsdaten dürfen weder im Repository noch in Logs, URLs oder
  Frontendquellen stehen.
- Administrative Aktionen dürfen eine laufende Zapfung nicht unkontrolliert
  verändern. Ventil-, Wartungs- und Fehlerreset-Aktionen benötigen weiterhin
  die vorhandenen serverseitigen Zustands- und Safety-Prüfungen.
- Der Server wird für den Smartphone-Zugriff nicht unkontrolliert in fremde
  Netze freigegeben. Das Backend bleibt an Loopback gebunden; ausschließlich
  der lokale Webzugang des Access Points wird weitergeleitet.
- Die Anwendung bleibt vollständig offlinefähig; externe Identitäts- oder
  Cloud-Dienste sind nicht erforderlich.
- Das Low-Level-Systemmenü und seine schreibende API sind nur über Loopback
  erreichbar und erfordern eine aktive NFC-Adminsitzung. Sie werden nicht vom
  Smartphone-Reverse-Proxy veröffentlicht.

## Verbleibende offene Frage

Benötigen Störungsreset, Wartung oder andere Administrationsabläufe langfristig
einen lokalen Notzugang, falls kein Smartphone verfügbar ist? Umfang und
Ausgestaltung bleiben als `OD-013` offen und blockieren den
Smartphone-Checkpoint nicht.

Zusätzlich bleibt als `OD-014` offen, welche besondere NFC-Rolle oder Karte
das Low-Level-Systemmenü später öffnen darf. In der Alpha-Ausbaustufe ist der
Zugriff für jeden aktiven Admin zulässig.

## Vorläufige Abnahmekriterien

1. Nur bei einem angemeldeten Admin bleibt der blaue Admin-Button sichtbar.
2. Der Button öffnet nur das lokale WLAN-Systemmenü und nicht die vertagte
   vollständige Adminoberfläche.
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
8. Jeder Admin verwendet sein eigenes Passwort aus dem gemeinsamen
   Benutzerdatensatz; normale Benutzer besitzen kein Passwort und keinen
   Webzugang.
9. Der Raspberry Pi stellt standardmäßig den WPA-geschützten Access Point
   `ZUNDER_ZAPFE` bereit; die Admin-WebUI bleibt ohne Internet erreichbar.
10. Der lokale Moduswechsel nutzt nur vorhandene Profile, zeigt keine
    Zugangsdaten und stellt bei einem gescheiterten Clientwechsel soweit
    möglich den Access Point wieder her.

Die technische Umsetzung wird in den Arbeitspaketen von Milestone 7
inkrementell abgenommen. `OD-013` wird in einem späteren Stakeholderentscheid
geklärt.
