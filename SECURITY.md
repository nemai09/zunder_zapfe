# Sicherheitsrichtlinie

## Unterstützter Stand

Zunder Zapfe befindet sich in der Alpha-Entwicklung. Sicherheitskorrekturen
werden nur für den aktuellen Stand von `main` vorgenommen; es gibt noch keine
unterstützten Releases oder garantierten Reaktionszeiten.

## Sicherheitsproblem melden

Schwachstellen, die Zugangsdaten, personenbezogene Daten, Authentifizierung
oder eine ausnutzbare Fernwirkung betreffen, bitte nicht als öffentliches Issue
veröffentlichen. Stattdessen die private Funktion **Security > Advisories > New
draft security advisory** im GitHub-Repository verwenden.

Die Meldung sollte enthalten:

- betroffene Revision,
- reproduzierbare Schritte,
- erwartete und tatsächliche Auswirkung,
- mögliche Abhilfe, falls bekannt,
- keine fremden Zugangsdaten oder vollständigen personenbezogenen Datensätze.

Allgemeine Safety-Probleme ohne vertrauliche Details können als Issue gemeldet
werden. Bei einem möglichen unkontrollierten Ventil- oder Not-Aus-Verhalten die
reale Anlage sofort außer Betrieb nehmen und die elektrische Versorgung des
Ventils fachgerecht trennen.

## Sicherheitsgrenzen des Alpha-Stands

- Die Software ersetzt keine hardwareseitige Not-Aus-Unterbrechung.
- Simulierte Komponenten sind kein Nachweis für elektrische Sicherheit.
- Entwicklungsgrenzwerte sind keine Produktionsfreigabe.
- Die lokale API besitzt noch keine Netzwerkauthentifizierung und muss auf
  `127.0.0.1` gebunden bleiben.
- Die SQLite-Datenbank kann personenbezogene Verbrauchsdaten enthalten und darf
  nicht veröffentlicht werden.

## Umgang mit Meldungen

Die Maintainer bestätigen Meldungen nach Möglichkeit, bewerten Auswirkung und
Reproduzierbarkeit und koordinieren eine Korrektur vor einer öffentlichen
Beschreibung. Da es sich um ein Hobbyprojekt handelt, besteht keine Zusage für
eine bestimmte Bearbeitungszeit.
