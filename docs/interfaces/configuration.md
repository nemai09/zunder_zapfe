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
| `ZUNDER_ZAPFE_ACCESS_LOG` | `0` | schreibt bei `1` jeden HTTP-Zugriff in das Dienstjournal | nur zeitweise zur Diagnose aktivieren; Kiosk-Polling erzeugt sonst unnötige Dauerlast und Logvolumen |
| `ZUNDER_ZAPFE_PULSES_PER_LITER` | `500` | ganzzahlige Impulskalibrierung | Demonstratorwert, vor Realbetrieb kalibrieren |
| `ZUNDER_ZAPFE_STANDARD_PORTIONS_ML` | `300,500` | kommaseparierte Standardportionen des Kiosks | mindestens zwei eindeutige positive Ganzzahlen |
| `ZUNDER_ZAPFE_SESSION_TIMEOUT_SECONDS` | `15` | Inaktivitätszeit bis zum automatischen Logout | positive ganze Sekundenzahl; Alpha-Default |
| `ZUNDER_ZAPFE_ADMIN_SESSION_TIMEOUT_SECONDS` | `30` | Fallback für den lokalen Adminmodus | 10 bis 3600 ganze Sekunden; persistente Admin-Einstellung hat Vorrang |
| `ZUNDER_ZAPFE_MANUAL_PRESS_DEBOUNCE_MS` | `120` | Entprellzeit vor dem Start einer manuellen Touch-Zapfung | nichtnegative ganze Millisekunden; verzögert niemals den Stopp |
| `ZUNDER_ZAPFE_MANUAL_MAXIMUM_POUR_SECONDS` | `30` | maximale Dauer einer manuellen Zapfung | positive ganze Sekundenzahl; Alpha-Wert, vor Realbetrieb kalibrieren |
| `ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG` | `1` | deaktiviert vorübergehend Start- und Folgeimpulsprüfung | nur ohne Durchflusshardware; vor realer Ventilhardware zwingend auf `0` setzen |
| `ZUNDER_ZAPFE_SIMULATE_NFC` | `0` | ersetzt ACR122U durch NFC-Simulator | nur Entwicklung |
| `ZUNDER_ZAPFE_ENABLE_SIMULATOR_API` | `0` | aktiviert Simulator-HTTP-Routen | im Normalbetrieb deaktiviert lassen |

## Änderungsregeln

- Neue Variablen erhalten einen sicheren Default, einen Eintrag in
  `config/web.env.example` und Dokumentation in dieser Tabelle.
- Geheimnisse erhalten niemals einen Beispielwert, der wie ein echtes
  Credential aussieht.
- Safety-relevante Werte werden validiert; ungültige Werte dürfen nicht zu
  einem geöffneten Ventil führen.
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
Sitzungszeit und manuelle Alpha-Grenzwerte folgen in Milestone 7.

Die zeitlich begrenzte Abweichung für Tests ohne Durchflusshardware ist unter
[`../operations/debug-without-flow-hardware.md`](../operations/debug-without-flow-hardware.md)
dokumentiert.
