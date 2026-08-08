# Lokale Systemsteuerung

Die lokale Systemseite ergänzt das begrenzte Low-Level-Menü um einen
geordneten Neustart und ein geordnetes Herunterfahren des Raspberry Pi. Sie
ist keine allgemeine Betriebssystemverwaltung und erfüllt `ZZ-UI-010`.

## Zugriff

1. Admin-Armband kurz auflegen.
2. Auf der Zapfoberfläche den blauen **ADMIN**-Button drücken.
3. Im Netzwerkmenü **System** wählen.

Die HTML-Seite und alle zugehörigen `/api/admin/system/*`-Routen sind nur über
Loopback erreichbar. Jeder API-Aufruf prüft zusätzlich den ventilgesperrten
lokalen NFC-Adminzustand. Smartphone-Websitzungen erhalten keinen Zugriff.

## Sicherheitsgrenze

`/usr/local/sbin/zunder-zapfe-system-power` akzeptiert ausschließlich:

- `reboot` für einen Neustart,
- `poweroff` für ein vollständiges Herunterfahren.

Andere oder fehlende Argumente werden abgewiesen. Der Dienstbenutzer erhält
über Polkit ausschließlich die zugehörigen `login1`-Aktionen und keine
allgemeine Berechtigung zur Verwaltung von systemd-Diensten oder zur
Ausführung beliebiger Root-Befehle.

Vor dem Systemaufruf speichert das Backend den Auftrag mit der Admin-ID im
Admin-Audit. Der Adminzustand kann nur bei geschlossenem Ventil betreten
werden. Beim anschließenden Stoppen des Webdienstes führt die bestehende
Anwendungs-Lifecycle-Logik erneut den sicheren Hardware-Shutdown aus.

## Zielsystemprüfung

Nach Deployment des Feature-Branches:

1. Prüfen, dass ein normaler Benutzer keinen **ADMIN**-Button sieht.
2. Als Admin anmelden, Low-Level-Menü und anschließend **System** öffnen.
3. Gerätename, Laufzeit und Build kontrollieren.
4. Neustart wählen, die erste Rückfrage abbrechen und prüfen, dass nichts
   passiert.
5. Neustart erneut wählen und bestätigen. Der Kiosk muss den Übergang anzeigen
   und nach dem Boot automatisch zurückkehren.
6. Erneut anmelden, **Herunterfahren** bestätigen und warten, bis Aktivitäts-
   LED und Display den beendeten Zustand zeigen.
7. Versorgung wiederherstellen und prüfen, dass Kiosk, RTC-Dienst und
   Webdienst regulär starten.
8. In der Smartphone-Diagnose beziehungsweise Datenbank prüfen, dass
   `system.reboot_requested` und `system.poweroff_requested` mit der
   ausführenden Admin-ID vorhanden sind.

Ein realer Neustart und ein reales Herunterfahren gehören bewusst zur
Zielsystemprüfung und werden nicht durch automatisierte Entwicklungstests
ausgelöst.
