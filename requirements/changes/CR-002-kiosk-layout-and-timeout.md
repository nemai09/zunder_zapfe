# CR-002: Kiosk-Kartenreihe und sichtbarer Timeout

Status: angenommen

Datum: 2026-07-20

Anforderungskatalog: Version 0.3

## Anlass und Entscheidung

Die kreisrunde Zapffläche wird durch eine große rechteckige Fläche mit
abgerundeten Ecken ersetzt. Im Landscape-Kiosk steht sie links und ist so hoch
wie die beiden Informationsreihen rechts zusammen. Rechts bleibt das aktive
Getränk oben; persönlicher Verbrauch und Betrag stehen darunter nebeneinander.
Der weiterhin notwendige manuelle Logout steht rechts und wird in einem
zurückhaltenden Rot dargestellt.

Die Inaktivität wird sichtbar: Der automatische Logout erfolgt nach insgesamt
15 Sekunden ohne Touchaktivität. Ein Balken am unteren Bildschirmrand stellt
die gesamte verbleibende Inaktivitätszeit dar. Jede Berührung setzt die
serverseitige Inaktivitätszeit wieder auf 15 Sekunden.
Eine aktive manuelle Zapfung wird nicht durch Inaktivität beendet und setzt den
Timeout beim Abschluss ebenfalls zurück.

## Auswirkungen

- Präzisiert `ZZ-AUT-010` um den Alpha-Default und Touchaktivität.
- Ergänzt `ZZ-UI-005` für den sichtbaren Timeout.
- Verändert keine Hardware-, Abrechnungs- oder Buchungslogik.
- Behält den manuellen Logout als explizite Benutzeraktion bei.

## Abnahmekriterien

1. Der Zapfbutton ist rechteckig, groß und so hoch wie die beiden rechts
   angeordneten Informationsreihen zusammen.
2. Der Logout steht rechts und ist zurückhaltend rot gestaltet.
3. Der Timeout-Balken bildet die gesamten 15 Sekunden bis zum Logout ab.
4. Touchaktivität setzt die Inaktivität im Backend zurück.
5. Nach 15 Sekunden ohne Aktivität kehrt der Kiosk zur NFC-Aufforderung zurück.
6. Manueller Logout funktioniert weiterhin sofort.
