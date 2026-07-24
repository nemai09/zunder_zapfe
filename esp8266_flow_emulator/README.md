# ESP8266-Durchflussemulator

Dieser Aufbau emuliert für die Zunder Zapfe den elektrischen Ausgang eines
Durchflusssensors. Der ESP8266 beobachtet das logische Steuersignal des
Ventiladapters. Nur wenn dieses Signal aktiv und die Weboption
`Impulsfeedback` eingeschaltet ist, erzeugt er eine Impulsfolge für den
Durchfluss-Eingang des Raspberry Pi.

Er emuliert damit einen einfachen Normalfall und den wesentlichen Fehlerfall:
Ventil angefordert, aber kein Durchfluss. Der ESP steuert niemals das Ventil
und darf nicht an Spule, Ventilversorgung oder Not-Aus-Kette angeschlossen
werden.

## Lieferumfang

- PlatformIO-Projekt für einen NodeMCU/ESP8266 (`nodemcuv2`);
- eine lokale, deutschsprachige Weboberfläche;
- ein einziger Schalter `Impulsfeedback an/aus`;
- Statusanzeige für das gelesene Ventil-Steuersignal, den Feedbackzustand und
  die erzeugte Impulszahl.

Die Firmware erzeugt anfänglich 10 Impulse pro Sekunde. Bei der aktuellen
Pi-Standardkalibrierung von 500 Impulsen/Liter entspricht das 1,2 L/min. Dieser
Wert ist nur ein reproduzierbarer Testwert und keine Kalibrierung des
angeschlossenen Sensors.

## Verzeichnis und Build

```powershell
cd esp8266_flow_emulator
Copy-Item src\wifi_config.example.h src\wifi_config.h
# wifi_config.h lokal mit dem Passwort von ZUNDER_ZAPFE ausfüllen
pio run --target upload
pio device monitor --baud 115200
```

`src/wifi_config.h` wird ignoriert und darf nie committed werden. Nach dem
Start schreibt der ESP seine DHCP-Adresse in den seriellen Monitor. Zusätzlich
versucht er, `zunder-flow-emulator.local` per mDNS anzubieten. Die
Weboberfläche läuft auf Port 80.

## Geplante elektrische Schnittstelle

Die beiden Signale sind noch keine freigegebene Pinbelegung. Sie beschreiben
den Connectorvertrag zwischen Pi-Hardwareadapter und Emulator:

| Signal | Richtung | Funktion | Elektrische Forderung |
| --- | --- | --- | --- |
| `VALVE_COMMAND` | Pi-Adapter → ESP | logischer Sollzustand des Ventils | nur über geprüfte Pegelwandlung oder Optokoppler; nie direkt von einer 5-, 12- oder 24-V-Treiberstufe auf den ESP |
| `FLOW_PULSE` | ESP → Pi-Adapter | sensorähnliche Impulse | offener Kollektor beziehungsweise galvanisch getrennt; Pull-up auf der Pi-Seite; Pi zählt ausschließlich fallende Flanken |
| `GND` | gemeinsam | Bezug für nicht galvanisch getrennte Variante | nur nach Freigabe der Pegel- und Erdungsstrategie |

Die Firmware verwendet als vorläufige NodeMCU-Testpins `D5` für
`VALVE_COMMAND` und `D6` für `FLOW_PULSE`. Sie sind keine Raspberry-Pi-GPIOs
und können vor dem Flashen zentral in `src/main.cpp` geändert werden.

Der `FLOW_PULSE`-Ausgang wird durch LOW ziehen und anschließendes Freigeben
erzeugt. Das entspricht dem vorgesehenen offenen-Kollektor-Verhalten und
verhindert, dass der ESP einen fremden Pull-up aktiv auf HIGH treibt.

## Bezug zum angehängten Sensor

Das Bild zeigt einen Sensor mit Kennzeichnung `YF-S201C`, während die aktuelle
Anforderung `ZZ-HW-004` den Dijiang OF07ZAT oder einen funktional gleichwertigen
GPIO-Impulssensor nennt. Vor der Integration des realen Sensors müssen dessen
konkrete Versorgung, Ausgangspegel, Pulszahl pro Liter und zulässige
Durchflussrate am vorliegenden Exemplar gemessen oder über das Datenblatt des
Lieferanten bestätigt werden. Die Angaben auf ähnlichen Angeboten sind hierfür
nicht ausreichend.

## Umsetzungsplan

1. **Elektrik freigeben:** Aktiven Pegel des späteren Pi-Ventiladapters und
   die Sensor-Eingangsstufe bestimmen. Für beide Richtungen einen Schaltplan
   mit Pegelwandler oder Optokoppler festlegen. Der reale Ventiltreiber und
   die Not-Aus-Kette bleiben außerhalb dieses Testaufbaus.
2. **Pi-Adapter ergänzen:** In Milestone 8 einen `Valve`-Adapter und einen
   flankenbasierten `FlowMeter`-Adapter hinter den bestehenden Protocols
   implementieren. Der Durchflussadapter zählt nur Flanken; die Umrechnung in
   Milliliter bleibt wie heute in `TapService`.
3. **Emulator verdrahten:** `VALVE_COMMAND`, `FLOW_PULSE` und gegebenenfalls
   Bezugspotential gemäß freigegebenem Schaltplan verbinden. Zunächst ohne
   reale Ventilspule testen.
4. **Normalfall abnehmen:** NFC-Anmeldung, Zapftaste halten, ESP erkennt
   Ventil-EIN und erzeugt Impulse. Der Pi bleibt im Zapfzustand, zählt Volumen
   und schließt bei Loslassen.
5. **Fehlerfall abnehmen:** Während einer Zapfung am ESP `Impulsfeedback`
   ausschalten. Der Pi muss gemäß `ZZ-SAF-004` das Ventil schließen und in
   `fault_locked` wechseln. Nach dem Reset darf keine Zapfung automatisch
   fortgesetzt werden.
6. **Sensor ersetzen und kalibrieren:** Erst nach erfolgreicher Emulatorabnahme
   den ESP durch den echten Sensor ersetzen, `ZUNDER_ZAPFE_PULSES_PER_LITER`
   kalibrieren und die Zeit- und Plausibilitätsgrenzen mit realem Durchfluss
   bewerten.

## Bewusst nicht enthalten

- keine Ventilbedienung über den ESP oder seine Weboberfläche;
- keine Sicherheitsabschaltung oder Ersatz für den Not-Aus;
- keine WiFi-Zugangsdaten im Repository;
- keine zusätzlichen Fehlerprofile. Der Feedback-Schalter genügt zunächst für
  den kritischen Fall fehlender Impulse bei angefordertem Ventil.

Traceability: `ZZ-HW-002`, `ZZ-HW-004`, `ZZ-HW-005`, `ZZ-SAF-004`,
`ZZ-SAF-008`, `ZZ-SAF-009`.
