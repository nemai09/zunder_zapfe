# ADR 0001: GNU GPL Version 3 oder später

Datum: 2026-07-19

Status: angenommen

## Kontext

Zunder Zapfe ist ein nichtkommerzielles Hobbyprojekt. Andere Personen sollen
die Software verwenden, verstehen, verändern, weitergeben und auch kommerziell
anbieten dürfen. Gleichzeitig sollen weitergegebene Änderungen und abgeleitete
Versionen freie Software bleiben.

Eine permissive Lizenz wie MIT erlaubt zwar sehr freie Nutzung, gestattet aber
auch die Weitergabe proprietärer Varianten ohne Quellcode. Das entspricht
nicht dem gewünschten dauerhaften Schutz der Softwarefreiheit.

## Entscheidung

Das Repository wird unter `GPL-3.0-or-later` veröffentlicht: GNU General Public
License Version 3 oder – nach Wahl des jeweiligen Lizenznehmers – jeder späteren
von der Free Software Foundation veröffentlichten Version.

Die Lizenz erlaubt insbesondere:

- private und kommerzielle Nutzung,
- Änderung und Weitergabe,
- Verkauf von Kopien, Geräten und Dienstleistungen,
- private oder rein interne Änderungen ohne Veröffentlichungspflicht.

Bei Weitergabe des Programms oder einer abgeleiteten Version müssen
insbesondere der korrespondierende Quellcode, Lizenz- und Copyright-Hinweise,
Änderungshinweise und dieselben GPL-Freiheiten an die Empfänger weitergegeben
werden.

## Folgen

- Weitergegebene abgeleitete Programme können nicht proprietär gemacht werden.
- Niemand ist verpflichtet, private Änderungen allgemein zu veröffentlichen.
- Reine Nutzung als Netzwerkdienst löst unter GPLv3 keine zusätzliche
  Quellcodepflicht aus; dafür wäre AGPLv3 erforderlich.
- Die Lizenz erlaubt kommerzielle Verwendung und ist keine
  „nichtkommerziell“-Lizenz.
- Das Projekt verwendet den SPDX-Ausdruck `GPL-3.0-or-later` in den
  Paketmetadaten und im maschinenlesbaren HTTP-Vertrag.
- Die Lizenz ersetzt keine elektrische, mechanische oder
  sicherheitstechnische Prüfung einer realen Zapfanlage.

## Erwogene Alternativen

- **MIT:** kürzer und permissiver, schützt die Freiheit abgeleiteter Versionen
  aber nicht.
- **AGPLv3:** erweitert Copyleft auf Netzwerkdienste; für die lokale,
  offlinefähige Anlage derzeit nicht erforderlich.
- **MPL 2.0:** schwächeres Copyleft auf Dateiebene; erlaubt proprietäre
  Kombinationen und schützt deshalb weniger als gewünscht.

Referenzen:

- [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html)
- [GNU GPL FAQ](https://www.gnu.org/licenses/gpl-faq.html)
- [GPLv3-Übersicht von Choose a License](https://choosealicense.com/licenses/gpl-3.0/)
