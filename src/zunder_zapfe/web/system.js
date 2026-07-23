"use strict";

const model = {
  status: null,
  actionPending: false,
};

const elements = {
  modeState: document.querySelector("#mode-state"),
  modeLabel: document.querySelector("#mode-label"),
  connectionName: document.querySelector("#connection-name"),
  ssidName: document.querySelector("#ssid-name"),
  ipAddress: document.querySelector("#ip-address"),
  clientProfile: document.querySelector("#client-profile"),
  statusDetail: document.querySelector("#status-detail"),
  apButton: document.querySelector("#ap-button"),
  clientButton: document.querySelector("#client-button"),
  actionMessage: document.querySelector("#action-message"),
  backButton: document.querySelector("#back-button"),
  logoutButton: document.querySelector("#logout-button"),
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
      // The HTTP status remains useful without a JSON body.
    }
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

function render() {
  const status = model.status;
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
  elements.statusDetail.textContent = status?.detail || "";
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

async function refreshStatus() {
  if (model.actionPending) return;
  try {
    model.status = await api("/api/wifi/status");
    render();
  } catch (error) {
    elements.actionMessage.textContent = error.message;
    elements.actionMessage.classList.add("is-error");
  }
}

async function switchMode(mode) {
  const prompt = mode === "ap"
    ? "Access Point ZUNDER_ZAPFE aktivieren? Die aktuelle WLAN-Verbindung wird getrennt."
    : "Zum bekannten WLAN wechseln? Der Access Point ZUNDER_ZAPFE wird beendet.";
  if (!window.confirm(prompt)) return;
  model.actionPending = true;
  elements.actionMessage.classList.remove("is-error");
  elements.actionMessage.textContent = "NetworkManager schaltet den WLAN-Modus um …";
  render();
  try {
    model.status = await api("/api/admin/wifi/mode", {
      method: "POST",
      body: JSON.stringify({ mode }),
    });
    elements.actionMessage.textContent =
      mode === "ap" ? "Access Point ist aktiv." : "WLAN-Client ist verbunden.";
  } catch (error) {
    elements.actionMessage.textContent = error.message;
    elements.actionMessage.classList.add("is-error");
    await refreshStatus();
  } finally {
    model.actionPending = false;
    render();
  }
}

async function leaveSystem(logout = false) {
  try {
    await api(logout ? "/api/session/logout" : "/api/admin/session/exit", {
      method: "POST",
    });
  } finally {
    window.location.assign("/");
  }
}

async function verifyAdminSession() {
  try {
    const tap = await api("/api/tap/status");
    if (tap.state !== "admin" || !tap.is_admin) window.location.assign("/");
  } catch (_error) {
    window.location.assign("/");
  }
}

elements.apButton.addEventListener("click", () => switchMode("ap"));
elements.clientButton.addEventListener("click", () => switchMode("client"));
elements.backButton.addEventListener("click", () => leaveSystem(false));
elements.logoutButton.addEventListener("click", () => leaveSystem(true));
document.addEventListener(
  "pointerdown",
  () => api("/api/session/activity", { method: "POST" }).catch(() => {}),
  { capture: true },
);

verifyAdminSession();
refreshStatus();
window.setInterval(verifyAdminSession, 1000);
window.setInterval(refreshStatus, 2000);
