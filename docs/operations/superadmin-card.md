# Superadmin-Karte einrichten

Stand: 2026-07-24

> Experimenteller M7.9-Checkpoint: Credential, Kollisionsprüfung und
> präsenzgebundener Backendzustand sind vorhanden. Das vollständige
> Low-Level-Menü folgt in M7.10. Bis dahin ist noch kein produktiv nutzbarer
> Wartungszugang freigegeben.

Die Karte wird nicht über eine UID in der Shell eingerichtet. Das Werkzeug liest
sie direkt am ACR122U und schreibt standardmäßig
`/var/lib/zunder-zapfe/superadmin.credential`.

## Voraussetzungen

- Zielsysteminstallation ist aktuell.
- Der ACR122U ist angeschlossen.
- Keine reale Ventilhardware ist für diesen experimentellen Schritt freigegeben.
- Der Dienst wird gestoppt, damit nur das Einrichtungswerkzeug den Leser nutzt.

## Einrichtung

```bash
cd ~/sw/zunder_zapfe
sudo systemctl stop zunder-zapfe-web.service
.venv/bin/zunder-zapfe-superadmin-card
sudo systemctl start zunder-zapfe-web.service
```

Das Werkzeug fordert zum Auflegen auf und bestätigt nur den Erfolg. Es zeigt
keine UID an. Vor dem Schreiben vergleicht es die Karte mit der produktiven
SQLite-Benutzerdatenbank. Eine bereits zugeordnete Karte wird abgelehnt. Eine
vorhandene Credential-Datei wird nicht überschrieben.

Die Datenbank wird standardmäßig unter
`/var/lib/zunder-zapfe/zunder-zapfe.db` erwartet. Eine fehlende, nicht
migrierte oder nicht lesbare Datenbank bricht die Einrichtung ab; es wird dann
kein Credential erzeugt.

## Prüfung

```bash
stat -c '%a %U %G %n' /var/lib/zunder-zapfe/superadmin.credential
```

Erwartet wird Modus `600` und der Benutzer, unter dem auch
`zunder-zapfe-web.service` läuft. Dateiinhalt, Hash oder UID werden nicht
ausgegeben oder in Tickets und PRs kopiert.

Fehlt die Datei, läuft der bisherige Betrieb während der experimentellen
Einführung unverändert weiter. Eine vorhandene, unlesbare, zu weit
freigegebene oder fehlerhafte Datei beendet den Anwendungsstart mit einem
Konfigurationsfehler.

Auch die lokale Zuordnung, die Smartphone-NFC-Zuordnung und der Demo-Seed
vergleichen jedes neue Armband gegen dieses Credential. Die Superadmin-Karte
kann daher nicht nachträglich einem normalen Benutzer, Admin oder Demo-Konto
zugeordnet werden.

## Verlust und Recovery

Die Anwendung bietet bewusst keinen Austausch an. Vor einer späteren Recovery
müssen Dienst, lokaler Zugriff und exaktes Ziel manuell geprüft werden. Das
Verfahren wird vor Produktivfreigabe separat festgelegt; die Credential-Datei
darf nicht beiläufig durch Deploymentskripte gelöscht oder ersetzt werden.
