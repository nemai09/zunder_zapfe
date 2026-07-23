"use strict";

const ACCESS_REFRESH_MS = 250;
const MAINTENANCE_HEARTBEAT_MS = 650;

const model = {
  tap: null,
  wifi: null,
  diagnostics: null,
  actionPending: false,
  currentView: "home",
  maintenanceHeld: false,
  maintenanceStartPending: false,
  maintenanceStopPending: false,
  maintenanceReleaseRequested: false,
  maintenanceTimer: null,
  provisioningActive: false,
  provisioningTimer: null,
  resultVisible: false,
  toastTimer: null,
};

const elements = {
  views: [...document.querySelectorAll("[data-system-view]")],
  homeButton: document.querySelector("#home-button"),
  presenceStatus: document.querySelector("#presence-status"),
  modeState: document.querySelector("#mode-state"),
  modeLabel: document.querySelector("#mode-label"),
  connectionName: document.querySelector("#connection-name"),
  ssidName: document.querySelector("#ssid-name"),
  ipAddress: document.querySelector("#ip-address"),
  clientProfile: document.querySelector("#client-profile"),
  apButton: document.querySelector("#ap-button"),
  clientButton: document.querySelector("#client-button"),
  wifiMessage: document.querySelector("#wifi-message"),
  maintenanceButton: document.querySelector("#maintenance-button"),
  maintenanceVolume: document.querySelector("#maintenance-volume"),
  maintenanceLabel: document.querySelector("#maintenance-label"),
  maintenanceKeg: document.querySelector("#maintenance-keg"),
  maintenanceState: document.querySelector("#maintenance-state"),
  maintenanceMessage: document.querySelector("#maintenance-message"),
  captureOverlay: document.querySelector("#capture-overlay"),
  captureTitle: document.querySelector("#capture-title"),
  captureInstruction: document.querySelector("#capture-instruction"),
  resultOverlay: document.querySelector("#result-overlay"),
  resultEyebrow: document.querySelector("#result-eyebrow"),
  resultTitle: document.querySelector("#result-title"),
  resultMessage: document.querySelector("#result-message"),
  passwordResult: document.querySelector("#password-result"),
  oneTimePassword: document.querySelector("#one-time-password"),
  systemToast: document.querySelector("#system-toast"),
  diagnosticsMessage: document.querySelector("#diagnostics-message"),
  diagVersion: document.querySelector("#diag-version"),
  diagNfc: document.querySelector("#diag-nfc"),
  diagWifi: document.querySelector("#diag-wifi"),
  diagValve: document.querySelector("#diag-valve"),
  diagFlow: document.querySelector("#diag-flow"),
  diagEstop: document.querySelector("#diag-estop"),
  diagKeg: document.querySelector("#diag-keg"),
  diagSafety: document.querySelector("#diag-safety"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    cache: "no-store",
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
    ...options,
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      detail = (await response.json()).detail || detail;
    } catch (_error) {
      // The status remains useful without JSON.
    }
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

function showToast(message, isError = false) {
  elements.systemToast.textContent = message;
  elements.systemToast.classList.toggle("is-error", isError);
  elements.systemToast.classList.add("is-visible");
  if (model.toastTimer !== null) window.clearTimeout(model.toastTimer);
  model.toastTimer = window.setTimeout(
    () => elements.systemToast.classList.remove("is-visible"),
    3200,
  );
}

function showView(name) {
  if (model.provisioningActive || model.resultVisible) return;
  model.currentView = name;
  for (const view of elements.views) {
    view.classList.toggle("is-active", view.dataset.systemView === name);
  }
  elements.homeButton.hidden = name === "home";
  if (name === "wifi") refreshWifi();
  if (name === "diagnostics") refreshDiagnostics();
  if (name === "maintenance") refreshMaintenanceContext();
}

function renderTap() {
  const pouring = model.tap?.state === "superadmin_maintenance_pouring";
  elements.maintenanceButton.classList.toggle(
    "is-holding",
    pouring || model.maintenanceHeld,
  );
  elements.maintenanceButton.setAttribute(
    "aria-pressed",
    String(pouring || model.maintenanceHeld),
  );
  elements.maintenanceVolume.textContent = `${model.tap?.measured_volume_ml || 0} ml`;
  elements.maintenanceLabel.textContent = pouring ? "Ventil geöffnet" : "Gedrückt halten";
  elements.maintenanceState.textContent = pouring ? "Ventil angefordert: EIN" : "Ventil geschlossen";
}

async function refreshAccess() {
  try {
    model.tap = await api("/api/tap/status");
    const state = model.tap.state;
    const allowed = ["superadmin", "superadmin_maintenance_pouring", "provisioning_handover"];
    if (!allowed.includes(state)) {
      if (!model.resultVisible) window.location.assign("/");
      return;
    }
    const provisioning = state === "provisioning_handover";
    elements.presenceStatus.classList.toggle("is-ending", provisioning);
    elements.presenceStatus.querySelector("strong").textContent = provisioning
      ? "Einmalige NFC-Übergabe aktiv"
      : "Superadmin-Karte liegt auf";
    renderTap();
  } catch (_error) {
    if (!model.resultVisible) window.location.assign("/");
  } finally {
    window.setTimeout(refreshAccess, ACCESS_REFRESH_MS);
  }
}

function renderWifi() {
  const status = model.wifi;
  const labels = {
    ap: "Access Point aktiv",
    client: "WLAN-Client aktiv",
    disconnected: "WLAN nicht verbunden",
    unavailable: "WLAN-Steuerung nicht verfügbar",
    unknown: "WLAN-Zustand unbekannt",
  };
  elements.modeLabel.textContent = labels[status?.mode] || "Wird geprüft …";
  elements.modeState.className = "mode-state";
  if (status?.mode === "ap") elements.modeState.classList.add("is-ap");
  if (status?.mode === "client") elements.modeState.classList.add("is-client");
  if (["unavailable", "unknown"].includes(status?.mode)) {
    elements.modeState.classList.add("is-error");
  }
  elements.connectionName.textContent = status?.active_connection || "–";
  elements.ssidName.textContent = status?.ssid || "–";
  elements.ipAddress.textContent = status?.ip_address || "–";
  elements.clientProfile.textContent = status?.client_profile_available
    ? "gespeichert"
    : "nicht vorhanden";
  elements.apButton.classList.toggle("is-active", status?.mode === "ap");
  elements.clientButton.classList.toggle("is-active", status?.mode === "client");
  const unavailable = !status || status.mode === "unavailable";
  elements.apButton.disabled =
    model.actionPending || unavailable || status?.mode === "ap";
  elements.clientButton.disabled =
    model.actionPending
    || unavailable
    || !status?.client_profile_available
    || status?.mode === "client";
}

async function refreshWifi() {
  if (model.actionPending) return;
  try {
    model.wifi = await api("/api/wifi/status");
    renderWifi();
  } catch (error) {
    elements.wifiMessage.textContent = error.message;
    elements.wifiMessage.classList.add("is-error");
  }
}

async function switchWifi(mode) {
  if (model.actionPending) return;
  const prompt = mode === "ap"
    ? "Access Point ZUNDER_ZAPFE aktivieren? Die aktuelle WLAN-Verbindung wird getrennt."
    : "Zum bekannten WLAN wechseln? Der Access Point wird beendet.";
  if (!window.confirm(prompt)) return;
  model.actionPending = true;
  elements.wifiMessage.classList.remove("is-error");
  elements.wifiMessage.textContent = "WLAN-Modus wird umgeschaltet …";
  renderWifi();
  try {
    model.wifi = await api("/api/system/wifi/mode", {
      method: "POST",
      body: JSON.stringify({ mode }),
    });
    elements.wifiMessage.textContent =
      mode === "ap" ? "Access Point ist aktiv." : "WLAN-Client ist verbunden.";
  } catch (error) {
    elements.wifiMessage.textContent = error.message;
    elements.wifiMessage.classList.add("is-error");
    await refreshWifi();
  } finally {
    model.actionPending = false;
    renderWifi();
  }
}

async function refreshMaintenanceContext() {
  try {
    const keg = await api("/api/keg/current");
    elements.maintenanceKeg.textContent =
      `${keg.beverage_name} · ${keg.remaining_volume_ml} ml rechnerisch verfügbar`;
    elements.maintenanceButton.disabled = keg.remaining_volume_ml <= 0;
  } catch (error) {
    elements.maintenanceKeg.textContent = "Kein aktives Fass";
    elements.maintenanceButton.disabled = true;
    elements.maintenanceMessage.textContent = error.message;
  }
}

async function requestMaintenanceStop() {
  if (model.maintenanceStopPending) return;
  if (model.maintenanceStartPending) {
    model.maintenanceReleaseRequested = true;
    return;
  }
  if (model.tap?.state !== "superadmin_maintenance_pouring") return;
  model.maintenanceStopPending = true;
  try {
    await api("/api/system/maintenance/stop", { method: "POST" });
  } catch (error) {
    elements.maintenanceMessage.textContent = error.message;
    elements.maintenanceMessage.classList.add("is-error");
  } finally {
    model.maintenanceStopPending = false;
    await refreshMaintenanceContext();
  }
}

function startMaintenance(event) {
  if (event.pointerType === "mouse" && event.button !== 0) return;
  if (model.maintenanceHeld || model.tap?.state !== "superadmin") return;
  model.maintenanceHeld = true;
  model.maintenanceReleaseRequested = false;
  elements.maintenanceMessage.textContent = "";
  renderTap();
  try {
    elements.maintenanceButton.setPointerCapture(event.pointerId);
  } catch (_error) {
    // Global release handlers remain active.
  }
  model.maintenanceTimer = window.setTimeout(async () => {
    model.maintenanceTimer = null;
    if (!model.maintenanceHeld) return;
    model.maintenanceStartPending = true;
    try {
      model.tap = await api("/api/system/maintenance/start", { method: "POST" });
    } catch (error) {
      elements.maintenanceMessage.textContent = error.message;
      elements.maintenanceMessage.classList.add("is-error");
      model.maintenanceHeld = false;
    } finally {
      model.maintenanceStartPending = false;
    }
    if (model.maintenanceReleaseRequested || !model.maintenanceHeld) {
      await requestMaintenanceStop();
    }
    renderTap();
  }, 120);
}

function releaseMaintenance() {
  if (model.maintenanceTimer !== null) {
    window.clearTimeout(model.maintenanceTimer);
    model.maintenanceTimer = null;
  }
  const wasHeld = model.maintenanceHeld;
  model.maintenanceHeld = false;
  model.maintenanceReleaseRequested = true;
  renderTap();
  if (
    wasHeld
    || model.maintenanceStartPending
    || model.tap?.state === "superadmin_maintenance_pouring"
  ) {
    requestMaintenanceStop();
  }
}

async function startProvisioning(role) {
  if (model.actionPending) return;
  model.actionPending = true;
  try {
    const result = await api("/api/system/provisioning/start", {
      method: "POST",
      body: JSON.stringify({ role }),
    });
    model.provisioningActive = true;
    elements.captureOverlay.hidden = false;
    renderProvisioning(result);
    pollProvisioning();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    model.actionPending = false;
  }
}

function renderProvisioning(result) {
  const content = {
    remove_card: [
      "Superadmin-Karte entfernen",
      "Danach das neue Veranstaltungsarmband kurz auflegen.",
    ],
    waiting: [
      "Neues Armband auflegen",
      "Das erste unbekannte Armband wird einmalig übernommen.",
    ],
    reader_unavailable: [
      "NFC-Leser nicht verfügbar",
      "Leser prüfen. Das Zeitfenster läuft weiter.",
    ],
  };
  const [title, instruction] = content[result.state] || [
    "Armband wird geprüft",
    "Bitte kurz warten.",
  ];
  elements.captureTitle.textContent = title;
  elements.captureInstruction.textContent = instruction;
}

async function pollProvisioning() {
  if (!model.provisioningActive) return;
  try {
    const result = await api("/api/system/provisioning/poll", { method: "POST" });
    if (["remove_card", "waiting", "reader_unavailable"].includes(result.state)) {
      renderProvisioning(result);
      model.provisioningTimer = window.setTimeout(pollProvisioning, 300);
      return;
    }
    showProvisioningResult(result);
  } catch (error) {
    showProvisioningResult({ state: "failed", display_name: null });
    showToast(error.message, true);
  }
}

function showProvisioningResult(result) {
  model.provisioningActive = false;
  model.resultVisible = true;
  elements.captureOverlay.hidden = true;
  elements.resultOverlay.hidden = false;
  const failures = {
    timeout: "Das 15-Sekunden-Zeitfenster ist abgelaufen.",
    card_assigned: "Dieses Armband ist bereits einem Benutzer zugeordnet.",
    superadmin_card: "Die Superadmin-Karte kann nicht als Benutzerarmband verwendet werden.",
    invalid_card: "Das aufgelegte Armband konnte nicht gelesen werden.",
    cancelled: "Die Notfallanlage wurde abgebrochen.",
    failed: "Der Benutzer konnte nicht sicher angelegt werden.",
  };
  const created = result.state === "created";
  elements.resultEyebrow.textContent = created ? "Erfolgreich angelegt" : "Nicht angelegt";
  elements.resultTitle.textContent = created
    ? result.display_name
    : "Notfallanlage beendet";
  elements.resultMessage.textContent = created
    ? "Das neue Armband ist sofort verwendbar."
    : failures[result.state] || "Der Vorgang wurde beendet.";
  elements.passwordResult.hidden = !result.one_time_password;
  elements.oneTimePassword.textContent = result.one_time_password || "";
}

async function cancelProvisioning() {
  model.provisioningActive = false;
  if (model.provisioningTimer !== null) window.clearTimeout(model.provisioningTimer);
  try {
    const result = await api("/api/system/provisioning", { method: "DELETE" });
    showProvisioningResult(result);
  } catch (_error) {
    window.location.assign("/");
  }
}

async function refreshDiagnostics() {
  elements.diagnosticsMessage.textContent = "";
  try {
    model.diagnostics = await api("/api/system/diagnostics");
    const data = model.diagnostics;
    elements.diagVersion.textContent = data.application.build;
    elements.diagNfc.textContent = `${data.nfc.state} · ${data.nfc.reader || "kein Leser"}`;
    elements.diagWifi.textContent = `${data.wifi.mode} · ${data.wifi.ssid || "ohne SSID"}`;
    elements.diagValve.textContent = data.valve.is_open ? "ANGEFORDERT OFFEN" : "geschlossen";
    elements.diagFlow.textContent =
      `${data.flow_meter.pulse_count} Impulse · ${data.flow_meter.measuring ? "misst" : "bereit"}`;
    elements.diagEstop.textContent = data.emergency_stop.active ? "AKTIV" : "frei";
    elements.diagKeg.textContent = data.keg
      ? `${data.keg.beverage_name} · ${data.keg.remaining_volume_ml} ml`
      : "kein aktives Fass";
    elements.diagSafety.textContent = data.tap.safety_reason || "keine Sperre";
  } catch (error) {
    elements.diagnosticsMessage.textContent = error.message;
    elements.diagnosticsMessage.classList.add("is-error");
  }
}

for (const button of document.querySelectorAll("[data-open-view]")) {
  button.addEventListener("click", () => showView(button.dataset.openView));
}
elements.homeButton.addEventListener("click", () => showView("home"));
elements.apButton.addEventListener("click", () => switchWifi("ap"));
elements.clientButton.addEventListener("click", () => switchWifi("client"));
document.querySelector("#create-user-button").addEventListener(
  "click",
  () => startProvisioning("user"),
);
document.querySelector("#create-admin-button").addEventListener(
  "click",
  () => startProvisioning("admin"),
);
document.querySelector("#cancel-provisioning").addEventListener("click", cancelProvisioning);
document.querySelector("#finish-result").addEventListener(
  "click",
  () => window.location.assign("/"),
);
document.querySelector("#refresh-diagnostics").addEventListener("click", refreshDiagnostics);

elements.maintenanceButton.addEventListener("pointerdown", startMaintenance);
elements.maintenanceButton.addEventListener("pointerup", releaseMaintenance);
elements.maintenanceButton.addEventListener("pointercancel", releaseMaintenance);
elements.maintenanceButton.addEventListener("lostpointercapture", releaseMaintenance);
window.addEventListener("pointerup", releaseMaintenance);
window.addEventListener("blur", releaseMaintenance);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) releaseMaintenance();
});
document.addEventListener("contextmenu", (event) => event.preventDefault());

window.setInterval(() => {
  if (model.tap?.state === "superadmin_maintenance_pouring") {
    api("/api/system/maintenance/heartbeat", { method: "POST" }).catch(() => {});
  }
}, MAINTENANCE_HEARTBEAT_MS);

window.addEventListener("pagehide", () => {
  releaseMaintenance();
  if (model.provisioningActive) {
    api("/api/system/provisioning", { method: "DELETE", keepalive: true }).catch(() => {});
  }
});

refreshAccess();
