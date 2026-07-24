// ESP8266-Durchflussemulator für die Zunder Zapfe.
// Er beobachtet ausschließlich das Ventil-Steuersignal und emuliert einen
// Impulsausgang. Er darf niemals an die Ventilspule angeschlossen werden.

#include <Arduino.h>
#include <ESP8266WebServer.h>
#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>

#include "wifi_config.h"

namespace {

// Testbelegung für einen NodeMCU. Die endgültige Verkabelung wird vor dem
// Anschluss anhand der Pegel des Pi-Adapters freigegeben.
constexpr uint8_t kValveCommandPin = D5;
constexpr uint8_t kFlowPulsePin = D6;
constexpr uint8_t kValveCommandActiveLevel = LOW;

// Der Pi verwendet aktuell standardmäßig 500 Impulse/Liter. 10 Hz entsprechen
// damit 1,2 L/min und reichen für den Durchfluss-Watchdog und Buchungstests.
constexpr uint16_t kPulseFrequencyHz = 10;
constexpr unsigned long kHalfPeriodMs = 1000UL / (kPulseFrequencyHz * 2UL);

ESP8266WebServer server(80);
bool feedbackEnabled = true;
bool pulseIsLow = false;
unsigned long lastPulseChangeMs = 0;
unsigned long generatedPulseCount = 0;
bool wifiWasConnected = false;
bool mdnsStarted = false;

bool valveCommandActive() {
  return digitalRead(kValveCommandPin) == kValveCommandActiveLevel;
}

// Das Ausgabesignal verhält sich wie ein offener Kollektor: LOW zieht die
// Leitung nach Masse, INPUT gibt sie frei. Der Pull-up gehört auf die
// Pi-Seite beziehungsweise in die externe Pegelstufe.
void releaseFlowPulseLine() {
  pinMode(kFlowPulsePin, INPUT);
  pulseIsLow = false;
}

void pullFlowPulseLineLow() {
  digitalWrite(kFlowPulsePin, LOW);
  pinMode(kFlowPulsePin, OUTPUT);
  pulseIsLow = true;
  ++generatedPulseCount;
}

String valveStateText() {
  return valveCommandActive() ? "EIN" : "AUS";
}

String feedbackStateText() {
  return feedbackEnabled ? "AN" : "AUS";
}

void sendOverview() {
  const String nextAction = feedbackEnabled ? "Feedback ausschalten" : "Feedback einschalten";
  const String nextValue = feedbackEnabled ? "off" : "on";
  String page;
  page.reserve(1800);
  page += F("<!doctype html><html lang='de'><meta charset='utf-8'>");
  page += F("<meta name='viewport' content='width=device-width,initial-scale=1'>");
  page += F("<title>Zunder Zapfe Durchflussemulator</title><style>");
  page += F("body{font-family:system-ui,sans-serif;margin:2rem;max-width:34rem;color:#17251e}");
  page += F("main{border:1px solid #c8d6ca;border-radius:1rem;padding:1.25rem}");
  page += F("dl{display:grid;grid-template-columns:1fr auto;gap:.7rem}dt{color:#526258}");
  page += F("dd{margin:0;font-weight:700}button{width:100%;padding:1rem;border:0;border-radius:.7rem;");
  page += F("background:#0d6b39;color:white;font-weight:700;font-size:1rem}</style><main>");
  page += F("<h1>Durchflussemulator</h1><p>Nur Testhardware. Kein Ventilanschluss.</p><dl>");
  page += F("<dt>Ventil-Steuersignal</dt><dd>");
  page += valveStateText();
  page += F("</dd><dt>Impulsfeedback</dt><dd>");
  page += feedbackStateText();
  page += F("</dd><dt>Impulsfrequenz</dt><dd>");
  page += String(kPulseFrequencyHz);
  page += F(" Hz</dd><dt>Erzeugte Impulse</dt><dd>");
  page += String(generatedPulseCount);
  page += F("</dd></dl><form method='post' action='/feedback'><input type='hidden' name='enabled' value='");
  page += nextValue;
  page += F("'><button type='submit'>");
  page += nextAction;
  page += F("</button></form></main></html>");
  server.send(200, "text/html; charset=utf-8", page);
}

void setFeedback() {
  feedbackEnabled = server.arg("enabled") == "on";
  if (!feedbackEnabled) releaseFlowPulseLine();
  server.sendHeader("Location", "/");
  server.send(303, "text/plain", "");
}

void beginWifiConnection() {
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.hostname("zunder-flow-emulator");
  WiFi.setAutoReconnect(true);
  WiFi.begin(ZUNDER_FLOW_EMULATOR_WIFI_SSID, ZUNDER_FLOW_EMULATOR_WIFI_PASSWORD);
  Serial.println(F("WLAN-Verbindung wird im Hintergrund aufgebaut."));
}

void updateWifiServices() {
  const bool connected = WiFi.status() == WL_CONNECTED;
  if (connected && !wifiWasConnected) {
    Serial.print(F("Weboberfläche: http://"));
    Serial.println(WiFi.localIP());
    mdnsStarted = MDNS.begin("zunder-flow-emulator");
    if (mdnsStarted) {
      Serial.println(F("mDNS: http://zunder-flow-emulator.local"));
    }
  } else if (!connected && wifiWasConnected) {
    Serial.println(F("WLAN getrennt; Impulserzeugung läuft unabhängig weiter."));
    mdnsStarted = false;
  }
  wifiWasConnected = connected;
  if (connected && mdnsStarted) MDNS.update();
}

void updatePulseGenerator() {
  const bool shouldGenerate = feedbackEnabled && valveCommandActive();
  if (!shouldGenerate) {
    if (pulseIsLow) releaseFlowPulseLine();
    return;
  }

  const unsigned long now = millis();
  if (now - lastPulseChangeMs < kHalfPeriodMs) return;
  lastPulseChangeMs = now;
  if (pulseIsLow) {
    releaseFlowPulseLine();
  } else {
    pullFlowPulseLineLow();
  }
}

}  // namespace

void setup() {
  Serial.begin(115200);
  // Aktives LOW mit internem Pull-up stellt ohne angeschlossene Quelle einen
  // definierten inaktiven Zustand her. Die externe Testquelle darf den Eingang
  // ausschließlich über Open-Drain/Open-Collector oder Optokoppler auf LOW ziehen.
  pinMode(kValveCommandPin, INPUT_PULLUP);
  releaseFlowPulseLine();

  server.on("/", HTTP_GET, sendOverview);
  server.on("/feedback", HTTP_POST, setFeedback);
  server.begin();
  beginWifiConnection();
}

void loop() {
  updatePulseGenerator();
  updateWifiServices();
  server.handleClient();
}
