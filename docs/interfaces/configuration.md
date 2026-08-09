# Laufzeitkonfiguration

Verbindliche Vorlage: [`config/web.env.example`](../../config/web.env.example)

Die Anwendung liest Konfiguration aus Umgebungsvariablen. Auf dem Raspberry Pi
lädt systemd `/etc/zunder-zapfe/web.env`; diese lokale Datei gehört nicht in
Git. Änderungen werden erst nach einem Dienstneustart wirksam.

| Variable | Standard/Beispiel | Wirkung | Sicherheitsregel |
| --- | --- | --- | --- |
| `ZUNDER_ZAPFE_HOST` | `127.0.0.1` | Bind-Adresse der HTTP-API | nicht ohne Sicherheitskonzept ins Netz öffnen |
| `ZUNDER_ZAPFE_PORT` | `8000` | lokaler HTTP-Port | ganzzahliger freier Port |
| `ZUNDER_ZAPFE_DATABASE_URL` | SQLite unter `/var/lib/zunder-zapfe` | SQLAlchemy-Datenbankziel | Datenbank nicht ins Repository legen |
| `ZUNDER_ZAPFE_BACKUP_DIR` | `/var/lib/zunder-zapfe/backups` | lokales Ziel für SQLite- und CSV-Sicherungen | nur für den Dienstbenutzer lesbar; nicht ins Repository legen |
| `ZUNDER_ZAPFE_ACCESS_LOG` | `0` | schreibt bei `1` jeden HTTP-Zugriff in das Dienstjournal | nur zeitweise zur Diagnose aktivieren; Kiosk-Polling erzeugt sonst unnötige Dauerlast und Logvolumen |
| `ZUNDER_ZAPFE_PULSES_PER_LITER` | `500` | ganzzahlige Impulskalibrierung | Demonstratorwert, vor Realbetrieb kalibrieren |
| `ZUNDER_ZAPFE_VALVE_GPIO` | `17` | BCM-GPIO des aktiven-HIGH-Ventilausgangs | nur Eingang einer geeigneten Treiberstufe; niemals Ventilspule direkt anschließen |
| `ZUNDER_ZAPFE_FLOW_GPIO` | `27` | BCM-GPIO für fallende Durchflussflanken | Eingang mit internem 3,3-V-Pull-up |
| `ZUNDER_ZAPFE_STANDARD_PORTIONS_ML` | `300,500` | kommaseparierte Standardportionen des Kiosks | mindestens zwei eindeutige positive Ganzzahlen |
| `ZUNDER_ZAPFE_SESSION_TIMEOUT_SECONDS` | `15` | Inaktivitätszeit bis zum automatischen Logout | positive ganze Sekundenzahl; Alpha-Default |
| `ZUNDER_ZAPFE_ADMIN_SESSION_TIMEOUT_SECONDS` | `30` | Fallback für den lokalen Adminmodus | 10 bis 3600 ganze Sekunden; persistente Admin-Einstellung hat Vorrang |
| `ZUNDER_ZAPFE_MANUAL_PRESS_DEBOUNCE_MS` | `120` | Entprellzeit vor dem Start einer manuellen Touch-Zapfung | nichtnegative ganze Millisekunden; verzögert niemals den Stopp |
| `ZUNDER_ZAPFE_MANUAL_MAXIMUM_POUR_SECONDS` | `30` | maximale Dauer einer manuellen Zapfung | positive ganze Sekundenzahl; Alpha-Wert, vor Realbetrieb kalibrieren |
| `ZUNDER_ZAPFE_FIRST_PULSE_TIMEOUT_SECONDS` | `5` | maximale Anlaufzeit bis zum ersten Durchflussimpuls | positive Sekundenzahl; vorläufiger Feldtestwert |
| `ZUNDER_ZAPFE_BETWEEN_PULSES_TIMEOUT_SECONDS` | `3` | maximal tolerierte Pause zwischen Durchflussimpulsen | positive Sekundenzahl; vorläufiger Feldtestwert |
| `ZUNDER_ZAPFE_CONTROLLER_WATCHDOG_TIMEOUT_SECONDS` | `5` | maximale Zeit ohne Kiosk-Heartbeat bei geöffnetem Ventil | positive Sekundenzahl; vorläufiger Feldtestwert |
| `ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG` | `0` | deaktiviert bei expliziter `1` Start- und Folgeimpulsprüfung | ausschließlich lokale Entwicklung ohne Durchflusshardware |
| `ZUNDER_ZAPFE_SIMULATE_NFC` | `0` | ersetzt ACR122U durch NFC-Simulator | nur Entwicklung |
| `ZUNDER_ZAPFE_SIMULATE_TAP_HARDWARE` | `0` | ersetzt GPIO-Ventil und GPIO-Durchfluss durch Simulatoren | niemals für HIL-Abnahme oder reale Ventilhardware |
| `ZUNDER_ZAPFE_ENABLE_SIMULATOR_API` | `0` | aktiviert Simulator-HTTP-Routen | im Normalbetrieb deaktiviert lassen |

## Änderungsregeln

- Neue Variablen erhalten einen sicheren Default, einen Eintrag in
  `config/web.env.example` und Dokumentation in dieser Tabelle.
- Geheimnisse erhalten niemals einen Beispielwert, der wie ein echtes
  Credential aussieht.
- Safety-relevante Werte werden validiert; ungültige Werte dürfen nicht zu
  einem geöffneten Ventil führen.
- Ventil- und Durchfluss-GPIO müssen verschieden und gültige BCM-Nummern sein.
- Der Zielsystem-Default verwendet reale GPIO-Adapter. Simulation erfordert
  eine ausdrückliche lokale Entwicklungsoption.
- Der Debugschalter für den Durchfluss-Watchdog akzeptiert ausschließlich `0`
  oder `1`. Er verändert weder Steuerungs-Watchdog, Not-Aus noch Zeitlimit.
- Das HTTP-Access-Log ist im Normalbetrieb deaktiviert. Fachliche Fehler,
  technische Ereignisse und Safety-Protokolle bleiben davon unberührt.
- Persistente fachliche Einstellungen gehören langfristig in die
  `settings`-Tabelle und benötigen Admin-Audit. Systemstartparameter und
  Geheimnisse bleiben Umgebungsvariablen.

Der Admin-Timeout ist bereits über die Admin-WebUI auditiert in
`settings["session.admin_timeout_seconds"]` pflegbar; der Umgebungswert ist der
Fallback für eine noch nicht gesetzte Datenbank. Standardportionen, normale
Sitzungszeit und manuelle Alpha-Grenzwerte sind als Startkonfiguration
vorhanden. Eine administrative Bedienung hardwareabhängiger Kalibrier-,
Plausibilitäts- und Safety-Werte folgt erst nach Festlegung der realen Adapter
in Milestone 8 beziehungsweise der Kalibrierung in Milestone 9. Bis dahin sind
die drei Watchdogzeiten bewusst als lokale Umgebungsparameter verfügbar; ihre
vorläufigen Werte und Abweichungen stehen unter
[`Alpha-Feldeinsatz`](../operations/alpha-field-operation.md).

Die zeitlich begrenzte Abweichung für lokale Tests ohne Durchflusshardware ist unter
[`../operations/debug-without-flow-hardware.md`](../operations/debug-without-flow-hardware.md)
dokumentiert.
Der davon getrennte, ständig beaufsichtigte Notbetrieb während des
Beta-Feldeinsatzes ist einschließlich Abbruchkriterien und Rückbau unter
[`Offline-Notfallhandbuch`](../operations/field-emergency-runbook.md)
dokumentiert.

Zielverdrahtung und ESP-Prüfablauf stehen unter
[`GPIO- und ESP8266-HIL-Test`](../operations/gpio-hil-test.md).
