# Automatische Datensicherung

Der Raspberry Pi erstellt zwei Minuten nach dem Start und danach alle 30
Minuten eine konsistente Sicherung der laufenden SQLite-Datenbank. Der
Zapfdienst wird dafür nicht angehalten. Vor der Veröffentlichung muss die Kopie
`PRAGMA integrity_check` bestehen.

Die Sicherungen liegen ausschließlich lokal unter
`/var/lib/zunder-zapfe/backups`. Verzeichnis und Dateien sind nur für den
Dienstbenutzer lesbar. Pro Dateityp bleiben die 400 neuesten Stände erhalten;
das deckt bei 30 Minuten Abstand mehr als acht Tage Dauerbetrieb ab. Erst nach
einer neuen erfolgreichen Sicherung werden ältere Sicherungsstände entfernt.

## Gesicherte Dateien

Jeder erfolgreiche Lauf erzeugt:

- eine vollständige SQLite-Kopie mit Konfiguration, Benutzern und Buchungen;
- `buchungen.csv` mit allen unveränderlichen Zapf-Rohdatensätzen;
- `abrechnung.csv` mit kostenpflichtigen Summen je Veranstaltung, Teilnehmer
  und Getränk;
- ein ZIP-Paket aus beiden CSV-Dateien und einer kurzen Sicherungsinformation.

Das CSV-Paket enthält weder NFC-UIDs noch Passwort-Hashes. Die vollständige
SQLite-Kopie bleibt auf dem Gerät und wird nicht über HTTP angeboten.

## Download aufs Smartphone

1. Smartphone mit `ZUNDER_ZAPFE` verbinden.
2. Admin-WebUI öffnen und persönlich anmelden.
3. `Buchungen & Auswertung` öffnen.
4. Unter `Automatische Datensicherung` den angezeigten Zeitpunkt und die Zahl
   der gesicherten Rohbuchungen prüfen.
5. `CSV-Sicherung aufs Telefon` drücken und die ZIP-Datei auf dem Smartphone
   behalten.

Für den sechstägigen Einsatz empfiehlt sich mindestens ein Download pro Tag.
Damit liegt selbst bei einem vollständigen Ausfall der SD-Karte ein externer
Abrechnungsstand vor.

## Prüfung auf dem Raspberry Pi

```bash
systemctl status zunder-zapfe-backup.timer --no-pager
sudo systemctl start zunder-zapfe-backup.service
sudo journalctl -u zunder-zapfe-backup.service -n 20 --no-pager
sudo ls -l /var/lib/zunder-zapfe/backups
```

Ein manueller Start erzeugt sofort einen zusätzlichen Sicherungsstand. Schlägt
ein Lauf fehl, bleibt der Web- und Zapfdienst aktiv. Das Journal enthält dann
die Ursache, die Admin-WebUI zeigt den Fehler und ein vorhandenes letztes
CSV-Paket bleibt herunterladbar.

Dieser Checkpoint stellt Sicherung und Export bereit. Eine
Wiederherstellungsfunktion ist nicht Bestandteil der Anwendung.
