# Debugbetrieb ohne Durchflusshardware

Status: temporäre Alpha-Abweichung

Solange kein physischer Durchflusssensor angeschlossen ist, verhindert die
reguläre Prüfung gemäß `ZZ-SAF-004` einen längeren UI-Test: Bei geöffnetem
Ventil fehlen erwartungsgemäß die Sensorimpulse und die Anlage verriegelt.

Für diesen begrenzten Entwicklungszeitraum gilt daher:

```text
ZUNDER_ZAPFE_SIMULATE_TAP_HARDWARE=1
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

Der vom Backend angeforderte Ausgangszustand bleibt über das API-Feld
`valve_open` und geschützte Diagnoseansichten prüfbar, wird aber nicht mehr in
der öffentlichen Kiosk-Kopfleiste angezeigt. Er bestätigt weder eine
elektrische Ausgangsspannung noch die mechanische Stellung eines realen Ventils.

## Rückbaukriterium

Für den Zielsystem- und HIL-Betrieb muss in `/etc/zunder-zapfe/web.env` gelten:

```text
ZUNDER_ZAPFE_SIMULATE_TAP_HARDWARE=0
ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG=0
```

Danach ist der Dienst neu zu starten. Der sichere Default aktiviert bereits
GPIO-Adapter und Durchfluss-Watchdog. Die Abweichung muss daher für lokale
Entwicklung ausdrücklich gewählt werden. Der Produktivstand muss `ZZ-SAF-004`
ohne Abweichung erfüllen.
