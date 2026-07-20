# Pflege der Anforderungen

Nachvollziehbare fachliche Änderungen stehen im
[`changes`-Verzeichnis](changes/README.md). Der Anforderungskatalog bildet den
jeweils angenommenen Arbeitsstand ab.

- Jede Anforderung besitzt eine dauerhafte ID (`ZZ-<Bereich>-<Nummer>`).
- IDs werden niemals wiederverwendet oder nachtraeglich umnummeriert.
- Statuswerte: `VORGESCHLAGEN`, `AKZEPTIERT`, `VERTAGT`, `VERWORFEN`.
- Prioritaeten: `MUSS`, `SOLL`, `KANN`.
- Offene Detailwerte werden als konfigurierbar oder vertagt ausgewiesen.
- Abnahmekriterien beschreiben die spaetere objektive Verifikation.
- Aenderungen erfolgen nachvollziehbar auf einem Branch und per Pull Request.
- Implementierung, Tests und Dokumentation referenzieren betroffene IDs, ohne
  dadurch eine noch nicht vollstaendig abgenommene Anforderung als erledigt zu
  markieren.
- Offene Entscheidungen `OD-*` werden erst nach dokumentierter Entscheidung zu
  verbindlichem Verhalten.
