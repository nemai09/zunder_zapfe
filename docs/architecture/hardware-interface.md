# Hardware-Zwischenlayer

Stand: 2026-07-19
Status: erster implementierter Architekturstand

## Zweck

Der Hardware-Zwischenlayer trennt die fachliche Anwendung von konkreten
Geraeten, GPIO-Bibliotheken und Pinbelegungen. Backend und Weboberflaeche greifen
ausschliesslich auf die stabilen Python-Vertraege unter
`src/zunder_zapfe/hardware/interfaces.py` zu.

Methoden, Statusfelder, Lifecycle und Aenderungsverfahren sind als gemeinsamer
Vertrag fuer Software- und Hardwareentwicklung unter
[`docs/interfaces/hardware.md`](../interfaces/hardware.md) dokumentiert.

Betroffene Anforderungen sind insbesondere `ZZ-HW-001` bis `ZZ-HW-005`,
`ZZ-SAF-001` bis `ZZ-SAF-005`, `ZZ-SAF-008`, `ZZ-SAF-009` und `ZZ-NFR-001`.

## Komponenten

Der Zwischenlayer definiert vier aktuelle Komponenten:

- `NfcReader` erkennt Leser und Karten und liefert die Karten-UID.
- `Valve` oeffnet und schliesst das Zapfventil und meldet seinen Zustand.
- `FlowMeter` startet und beendet Messungen und liefert die Anzahl der Impulse.
- `EmergencyStop` liefert den elektrischen Not-Aus-Zustand.

Die Umrechnung von Impulsen in Volumen, die Verriegelung nach einem Not-Aus und
alle Berechtigungsentscheidungen gehoeren in die spaetere Backend-Logik. Der
Zwischenlayer bildet nur die Hardware ab.

## Aktuelle Zusammenstellung

`create_default_hardware()` stellt die derzeit nutzbare hybride Konfiguration
zusammen:

- realer ACR122U ueber PC/SC,
- `GpioValve` als aktiver-HIGH-Ausgang auf konfigurierbarem `BCM17`,
- `GpioFlowMeter` als flankengesteuerter Eingang auf konfigurierbarem `BCM27`,
- simulierter Not-Aus.

Die Simulatoren besitzen dieselben Anwendungsvertraege wie spaetere reale
Adapter. Zusaetzliche Steuerfunktionen wie `present_card()`, `add_pulses()` oder
`trigger()` existieren nur an den Simulatoren und dienen Tests und Entwicklung.
Ventil- und Durchflusssimulatoren werden nur durch
`ZUNDER_ZAPFE_SIMULATE_TAP_HARDWARE=1` ausdruecklich aktiviert. Der
ESP8266-HIL-Test verwendet dagegen die regulaeren GPIO-Adapter.

## Sicherheitsgrenzen

- Ventilstart und -stopp muessen immer einen geschlossenen Zustand herstellen.
- Ein realer Ventiladapter darf bei Initialisierungsfehlern nicht oeffnen.
- Die hardwareseitige Unterbrechung durch den Not-Aus bleibt unabhaengig von
  diesem Softwarevertrag erforderlich.
- Es gibt vorerst absichtlich keinen HTTP-Endpunkt zum Oeffnen des Ventils.
- Der Status-Endpunkt `/api/hardware/status` ist reine Diagnose.

## Reale Ein- und Ausgaenge

Die GPIO-Adapter liegen unter `src/zunder_zapfe/hardware/adapters/`. Backend
und WebUI bleiben unveraendert, wenn der ESP spaeter durch Ventiltreiber und
Durchflusssensor ersetzt wird. Der reale Not-Aus-Adapter fehlt weiterhin.

Eine notwendige Vertragserweiterung wird zuerst simulatorisch implementiert und
getestet. GPIO-Pins, aktive Pegel und konkrete Bibliotheken bleiben
Adapterkonfiguration und gehoeren nicht in die fachliche Anwendung.
