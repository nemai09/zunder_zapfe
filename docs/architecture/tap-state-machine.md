# Zapf-Zustandsautomat

Stand: 2026-07-19

Der Zustandsautomat ist die einzige Backend-Komponente, die Ventil und
Durchflussmessung zu einem Zapfvorgang koordiniert. Die WebUI fordert nur
fachliche Aktionen an; sie schaltet das Ventil nicht direkt.

```mermaid
stateDiagram-v2
    direction LR

    state "Startphase<br/>STARTING" as STARTING
    state "Bereit, wartet auf Karte<br/>IDLE" as IDLE
    state "Benutzer angemeldet<br/>AUTHENTICATED" as AUTHENTICATED
    state "Automatische Portion<br/>PORTION_POURING" as PORTION_POURING
    state "Nachfüllen möglich<br/>TOP_UP_AVAILABLE" as TOP_UP_AVAILABLE
    state "Nachfüllen aktiv<br/>TOP_UP_POURING" as TOP_UP_POURING
    state "Wartungsmodus<br/>MAINTENANCE" as MAINTENANCE
    state "Wartungszapfung<br/>MAINTENANCE_POURING" as MAINTENANCE_POURING
    state "Fehlersperre<br/>FAULT_LOCKED" as FAULT_LOCKED
    state "Not-Aus-Sperre<br/>EMERGENCY_STOP" as EMERGENCY_STOP
    state "Beendet<br/>STOPPED" as STOPPED

    [*] --> STARTING
    STARTING --> IDLE: Hardware bereit<br/>Ventil geschlossen
    STARTING --> EMERGENCY_STOP: Not-Aus beim Start aktiv

    IDLE --> AUTHENTICATED: bekannte aktive Karte
    AUTHENTICATED --> IDLE: Logout

    AUTHENTICATED --> PORTION_POURING: Portionswahl<br/>Messung starten, Ventil öffnen
    PORTION_POURING --> TOP_UP_AVAILABLE: Zielimpulse erreicht<br/>Ventil schließen, Istmenge buchen
    PORTION_POURING --> AUTHENTICATED: manueller Abbruch<br/>Ventil schließen, Istmenge buchen

    TOP_UP_AVAILABLE --> TOP_UP_POURING: Nachfüllen gedrückt
    TOP_UP_AVAILABLE --> AUTHENTICATED: Nachfüllfenster abgelaufen
    TOP_UP_POURING --> AUTHENTICATED: losgelassen oder Limit erreicht<br/>Ventil schließen, Istmenge buchen

    AUTHENTICATED --> MAINTENANCE: Admin startet Wartungsmodus
    MAINTENANCE --> MAINTENANCE_POURING: Wartungszapfung gedrückt
    MAINTENANCE_POURING --> MAINTENANCE: losgelassen<br/>Wartungsmenge buchen
    MAINTENANCE --> AUTHENTICATED: Admin beendet Wartungsmodus

    PORTION_POURING --> FAULT_LOCKED: Durchfluss-, Zeit- oder Watchdogfehler
    TOP_UP_POURING --> FAULT_LOCKED: Durchfluss- oder Watchdogfehler
    MAINTENANCE_POURING --> FAULT_LOCKED: Durchfluss-, Zeit- oder Watchdogfehler
    FAULT_LOCKED --> IDLE: Ursache behoben und Admin-Reset
    FAULT_LOCKED --> EMERGENCY_STOP: Not-Aus

    IDLE --> EMERGENCY_STOP: Not-Aus
    AUTHENTICATED --> EMERGENCY_STOP: Not-Aus
    PORTION_POURING --> EMERGENCY_STOP: Not-Aus<br/>Ventil sofort schließen
    TOP_UP_AVAILABLE --> EMERGENCY_STOP: Not-Aus
    TOP_UP_POURING --> EMERGENCY_STOP: Not-Aus<br/>Ventil sofort schließen
    MAINTENANCE --> EMERGENCY_STOP: Not-Aus
    MAINTENANCE_POURING --> EMERGENCY_STOP: Not-Aus<br/>Ventil sofort schließen
    EMERGENCY_STOP --> IDLE: Kontakt frei und Admin-Reset

    IDLE --> STOPPED: Backend-Stopp
    note right of STOPPED
        Backend-Stopp ist aus jedem Zustand möglich.
        Bei aktivem Zapfen wird zuerst das Ventil geschlossen.
    end note
    STOPPED --> [*]
```

## Sicherheitsinvarianten

Unabhaengig vom dargestellten Ausgangszustand gelten folgende Regeln:

1. Das Ventil wird vor dem Abschluss einer Messung und vor jedem Zustandswechsel
   aus einem aktiven Zapfvorgang geschlossen.
2. Not-Aus, fehlende Durchflussimpulse, Zeitueberschreitungen und ein
   abgelaufener Steuerungs-Watchdog schliessen das Ventil. Eine vom WebUI-Thread
   unabhaengige Hintergrundueberwachung wertet diese Bedingungen zyklisch aus.
3. `EMERGENCY_STOP` und `FAULT_LOCKED` bleiben verriegelt. Das Beheben der
   Ursache allein reicht nicht; fuer den Reset muss eine aktive Admin-Karte
   tatsaechlich auf dem NFC-Leser liegen. Danach startet keine Sitzung
   automatisch.
4. Weitere Kartenereignisse veraendern einen laufenden Zapfvorgang nicht.
5. Buchungen verwenden die gemessenen Impulse, auch bei Abbruch und Fehler.
6. Wartungszapfungen werden gemessen, aber als nicht kostenpflichtig markiert.

## Integration und verbleibende Grenzen

`TapService` ordnet NFC-UIDs aktiven Benutzern zu und speichert die vom
Zustandsautomaten abgeschlossenen `PourRecord`-Objekte als unveraenderliche
Zapfbuchungen. Der aktive Veranstaltungs-, Fass-, Getraenke- und Preiskontext
wird dazu beim Zapfstart festgehalten. Der vollstaendige Fluss ist unter
[`backend-core-integration.md`](backend-core-integration.md) beschrieben.

Die in `development_limits()` enthaltenen Werte und die Demonstrator-Kalibrierung
sind weiterhin keine Produktionswerte. Verbindliche Werte bleiben offene
Produktentscheidungen `OD-002` und `OD-003`; reale Ventil- und
Durchfluss-Hardware sind noch nicht integriert.

## Traceability

Der aktuelle Stand deckt die Struktur und simulatorischen Tests fuer
`ZZ-AUT-008` bis `ZZ-AUT-010`, `ZZ-TAP-005` bis `ZZ-TAP-010`, `ZZ-HW-003` bis
`ZZ-HW-005`, `ZZ-SAF-003` bis `ZZ-SAF-009`, `ZZ-MNT-001`, `ZZ-MNT-002`,
`ZZ-NFR-001` und `ZZ-NFR-002` ab. Persistenz und NFC-Benutzerzuordnung sind nun
simulatorisch integriert. Eine Anforderung gilt erst nach Integration der noch
fehlenden Benutzeroberflaechen und realen Zapfhardware als vollstaendig
umgesetzt.
