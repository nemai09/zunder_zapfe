# CR-001: Manuelles Push-to-Fill

Status: angenommen

Datum: 2026-07-20

Anforderungskatalog: Version 0.2

## Anlass und Entscheidung

Die bisher vorgesehene Auswahl aus Standard- und Sonderportionen wird in der
Kioskoberfläche durch genau eine große, gedrückt zu haltende Zapffläche ersetzt.
Damit wird die kognitive Last im vorgesehenen Nutzungskontext reduziert.
Gedrückthalten öffnet das Ventil, Loslassen beendet den Vorgang. Ausschließlich
die gemessene Istmenge wird dem authentifizierten Benutzer berechnet.

Die bestehende Portions-, Sondergrößen- und Nachfülllogik bleibt im Backend als
Kompatibilitätsfunktion erhalten, wird im Kiosk jedoch nicht angeboten. Die
Änderung löscht weder bestehende Daten noch wiederverwendet sie Anforderungen.

## Auswirkungen

- Ersetzt im Kiosk `ZZ-TAP-005`, `ZZ-TAP-007`, `ZZ-TAP-009`, `ZZ-TAP-010`,
  `ZZ-TAP-011`, `ZZ-UI-003` und `ZZ-NFR-003`.
- Vertagt die Kiosknutzung von `ZZ-TAP-001` bis `ZZ-TAP-004` sowie
  `ZZ-TAP-006`; die Backendfähigkeiten bleiben erhalten.
- Ergänzt `ZZ-TAP-013`, `ZZ-TAP-014`, `ZZ-UI-004` und `ZZ-NFR-005`.
- Präzisiert `ZZ-DAT-002`: Eine Zielmenge ist bei manuellen Vorgängen nicht
  vorhanden; Istmenge, Preis, Betrag, Vorgangsart und Abschluss bleiben Pflicht.
- `ZZ-TAP-008`, `ZZ-HW-005`, `ZZ-HW-006`, `ZZ-SAF-004`, `ZZ-SAF-005` und
  `ZZ-SAF-008` gelten unverändert.

## Schnittstellen- und Datenentscheidung

- Eigener Backendzustand `manual_pouring`.
- Eigene Start-/Stop-Aktionen an der HTTP-Schnittstelle.
- Eigene Buchungsart `manual` mit leerer Zielmenge.
- Vorhandene Portion-, Abbruch- und Nachfüllaktionen bleiben kompatibel.

## Sicherheitsentscheidung

Nur die Aktivierung darf entprellt werden. Ein Stopp wird niemals absichtlich
verzögert. Pointer-Abbruch, Fokusverlust und eine ausgeblendete Seite lösen
ebenfalls einen Stopp aus; der Backend-Watchdog schließt unabhängig davon.

Die Alpha-Werte betragen 120 ms Aktivierungsentprellung und 30 Sekunden maximale
Öffnungsdauer. Beide sind konfigurierbar und gemäß `OD-012` vor realem Betrieb
zu kalibrieren. Die 30 Sekunden sind keine Produktivfreigabe.

## Abnahmekriterien

1. Ohne aktive NFC-Sitzung öffnet die Zapffläche das Ventil nicht.
2. Eine Berührung unterhalb der Entprellzeit öffnet nicht.
3. Gedrückthalten startet eine gemessene, kostenpflichtige manuelle Zapfung.
4. Loslassen und Abbruchereignisse schließen unverzüglich.
5. Die gemessene Menge wird genau einmal dem angemeldeten Benutzer gebucht.
6. Die konfigurierte Maximaldauer beendet und bucht den Vorgang automatisch.
7. Watchdog, Durchflussüberwachung, Not-Aus und zweites NFC-Medium behalten ihre
   bisherige sichere Wirkung.
8. Die Backendtests für Standard- und Sonderportionen bleiben erfolgreich.

## Nachverfolgung

Implementierungs-PR, Commits, Tests und Zielsystemprüfung werden nach Erstellung
hier beziehungsweise im PR verlinkt. Die Änderung wurde während der
Alpha-Entwicklung fachlich freigegeben; ein formales Stakeholder-Review ist für
diesen Checkpoint nicht vorgesehen.
