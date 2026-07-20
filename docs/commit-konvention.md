# Commit-Konvention

Diese Konvention ist für alle menschlichen und KI-gestützten Beiträge
verbindlich. Sie trennt fachliche Meilensteine, Arbeitspakete und technische
Änderungsarten von der fortlaufenden PR-Nummer, die GitHub vergibt.

## Betreffsformat

Meilensteinbezogene Commits verwenden:

```text
M<Meilenstein>.<Arbeitspaket> <TYP>: <kurze deutsche Beschreibung>
```

Beispiel:

```text
M7.2 UI: Implementiere den geführten Fasswechsel
```

Milestone-unabhängige Änderungen an Repository, Zusammenarbeit oder
Projektinfrastruktur verwenden:

```text
META <TYP>: <kurze deutsche Beschreibung>
```

Beispiel:

```text
META DOC: Definiere verbindliches Commit-Schema
```

## Meilenstein und Arbeitspaket

- `M7` bezeichnet den fachlichen Meilenstein und ist unabhängig von GitHubs
  PR-Nummer.
- `.1`, `.2` und folgende Nummern bezeichnen vorab geplante, zusammenhängende
  Arbeitspakete innerhalb des Meilensteins. Sie werden nicht pro Commit erhöht.
- Mehrere Commits dürfen dasselbe Arbeitspaket tragen.
- Ein Nachtrag zu einem abgeschlossenen Meilenstein erhält die nächste freie
  Unterkennung, zum Beispiel `M6.1 DOC` oder `M6.2 FIX`.
- `META` ist ausschließlich für Änderungen ohne fachlichen Milestone-Umfang
  vorgesehen.

## Erlaubte Typen

| Typ | Verwendung |
| --- | --- |
| `PLAN` | Anforderungen, Planung, Entscheidungen und Roadmap |
| `FEAT` | neue Backend- oder fachliche Funktion |
| `UI` | sichtbares Verhalten oder Gestaltung der WebUI |
| `FIX` | Fehlerkorrektur ohne neuen fachlichen Umfang |
| `DB` | Datenmodell, Migration oder Persistenzvertrag |
| `HW` | Hardwarevertrag, Simulator oder realer Adapter |
| `TEST` | ausschließlich Tests oder Testwerkzeuge |
| `DOC` | ausschließlich Dokumentation |
| `REF` | Strukturverbesserung ohne beabsichtigte Verhaltensänderung |
| `OPS` | Installation, Deployment, CI oder Laufzeitkonfiguration |

Pro Commit wird genau ein primärer Typ verwendet. Begleitende Tests und
Dokumentation ändern den Typ eines Funktionscommits nicht. Ein Commit mit neuer
Funktion, Tests und Vertrag heißt daher weiterhin `FEAT`, `UI`, `DB` oder `HW`.

## Schreibregeln

- Die Beschreibung ist deutsch, konkret und als aktive Handlungsbeschreibung
  formuliert, zum Beispiel `Ergänze`, `Implementiere`, `Behebe` oder
  `Dokumentiere`.
- Der Betreff endet ohne Punkt und soll höchstens 72 Zeichen lang sein.
- Allgemeine Betreffe wie `Update`, `Änderungen` oder `Fixes` sind unzulässig.
- Ein Commit enthält eine logisch zusammenhängende Änderung.
- Betroffene Anforderungs-IDs, Safety-Auswirkungen, Migrationen und das Warum
  gehören bei Bedarf in den Commit-Text unter dem Betreff.
- Zugangsdaten, reale NFC-UIDs und andere vertrauliche Werte gehören weder in
  Betreff noch Commit-Text.

Automatisch von GitHub erzeugte Merge-Commits sind von diesem Betreffsformat
ausgenommen. Pull-Request-Titel verwenden nach Möglichkeit dieselbe
Milestone-/Arbeitspaketkennung, sind aber nicht an GitHubs PR-Nummer gekoppelt.

## Beispiele

```text
M7.1 DB: Ergänze Veranstaltungs- und Getränkestammdaten
M7.1 FEAT: Stelle Verwaltungsendpunkte für Getränke bereit
M7.2 UI: Implementiere den geführten Fasswechsel
M7.3 FIX: Setze den Admin-Timeout nach Berührung zurück
M7.3 TEST: Prüfe den Wartungsmodus gegen Fehlbedienung
M7.4 DOC: Dokumentiere Statistik- und Auditansichten
M8.1 HW: Ergänze den realen Ventiladapter
META OPS: Aktualisiere die GitHub-Prüfmatrix
```
