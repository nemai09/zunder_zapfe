# Admin dauerhaft gegen Fehlbedienung schützen

Ein aktiver Admin kann einmalig lokal auf dem Raspberry Pi gegen einfache
Fehlbedienung und versehentlichen Zugangsverlust geschützt werden. Der Schutz
ist kein separates Konto und verändert weder Passwort noch Zapfverhalten.

Nach Installation beziehungsweise Update und ausgeführter Datenbankmigration:

```bash
.venv/bin/zunder-zapfe-protect-admin --user-id 2
```

Die ID muss zu einem vorhandenen, aktiven Admin mit mindestens einem aktiven
Armband gehören. Der Demo-Seed gibt die `Admin user ID` nach dem Anlegen aus;
auf einer bestehenden Datenbank muss die tatsächliche ID des gewünschten
Admins verwendet werden.

Der Befehl setzt `users.administration_protected` dauerhaft auf `true`. Er
besitzt absichtlich keine Option zum Aufheben. WebUI und HTTP-API können den
Zustand nur lesen. Das Konto kann danach nicht gelöscht, deaktiviert oder zum
normalen Benutzer herabgestuft werden. Das letzte aktive Armband kann weder
gesperrt noch entfernt werden; entsprechende direkte Requests werden mit HTTP
`409 Conflict` abgewiesen.

Ein Kartenwechsel bleibt möglich: Zuerst wird ein weiteres Armband zugeordnet,
danach darf das alte gesperrt oder entfernt werden. Namen, Zusatzfeld, Passwort
und weitere Armbänder bleiben normal verwaltbar. Datenbanken dürfen nicht
manuell bearbeitet werden, um den Schutz zu umgehen.
