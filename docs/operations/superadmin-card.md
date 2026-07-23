# Superadmin-Karte einrichten

Stand: 2026-07-24

> Experimenteller M7.8-Checkpoint: Das Credential und sein Einrichtungswerkzeug
> sind vorhanden. Das Low-Level-Menü und die Laufzeitauthorisierung folgen in
> M7.9 und M7.10. Bis dahin entsteht durch die Einrichtung noch kein nutzbarer
> Superadmin-Zugang.

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
keine UID an. Eine vorhandene Credential-Datei wird nicht überschrieben.

## Prüfung

```bash
stat -c '%a %U %G %n' /var/lib/zunder-zapfe/superadmin.credential
```

Erwartet wird Modus `600` und der Benutzer, unter dem auch
`zunder-zapfe-web.service` läuft. Dateiinhalt, Hash oder UID werden nicht
ausgegeben oder in Tickets und PRs kopiert.

Fehlt die Datei, läuft der bisherige Betrieb während der experimentellen
Einführung unverändert weiter. Eine vorhandene, unlesbare, zu weit
freigegebene oder fehlerhafte Datei muss später beim Anwendungsstart als
Konfigurationsfehler behandelt werden.

## Verlust und Recovery

Die Anwendung bietet bewusst keinen Austausch an. Vor einer späteren Recovery
müssen Dienst, lokaler Zugriff und exaktes Ziel manuell geprüft werden. Das
Verfahren wird vor Produktivfreigabe separat festgelegt; die Credential-Datei
darf nicht beiläufig durch Deploymentskripte gelöscht oder ersetzt werden.
