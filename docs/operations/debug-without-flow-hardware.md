# Debugbetrieb ohne Durchflusshardware

Status: temporäre Alpha-Abweichung

Solange kein physischer Durchflusssensor angeschlossen ist, verhindert die
reguläre Prüfung gemäß `ZZ-SAF-004` einen längeren UI-Test: Bei geöffnetem
Ventil fehlen erwartungsgemäß die Sensorimpulse und die Anlage verriegelt.

Für diesen begrenzten Entwicklungszeitraum gilt daher:

```text
ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG=1
```

Der Schalter deaktiviert ausschließlich:

- die Zeitüberwachung bis zum ersten Durchflussimpuls;
- die Zeitüberwachung zwischen weiteren Durchflussimpulsen.

Aktiv bleiben insbesondere:

- Not-Aus-Erkennung und verriegelnder Sicherheitszustand;
- Steuerungs-Watchdog für ausbleibende WebUI-Heartbeats;
- maximale manuelle Öffnungsdauer;
- Schließen bei Loslassen, Fehler, Shutdown und Neustart;
- persistente Buchung der tatsächlich gemessenen Menge, im Debugfall also
  gegebenenfalls `0 ml`.

Die Kiosk-Kopfleiste zeigt zusätzlich `DEBUG · Ventil EIN/AUS`. Grundlage ist
das API-Feld `valve_open`, also der angeforderte Softwarezustand. Die Anzeige
bestätigt weder eine elektrische Ausgangsspannung noch die mechanische Stellung
eines realen Ventils.

## Rückbaukriterium

Bevor reale Ventilhardware angeschlossen oder ein sicherheitsrelevanter Test
durchgeführt wird, muss in `/etc/zunder-zapfe/web.env` gelten:

```text
ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG=0
```

Danach ist der Dienst neu zu starten. Spätestens mit dem realen
Durchflussadapter in Milestone 8 werden der temporäre Default und die
Kiosk-Debuganzeige entfernt. Der Produktivstand muss `ZZ-SAF-004` wieder ohne
Abweichung erfüllen.
