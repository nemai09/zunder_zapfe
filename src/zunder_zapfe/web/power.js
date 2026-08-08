"use strict";

const model = {
  status: null,
  actionPending: false,
};

const elements = {
  systemState: document.querySelector("#system-state"),
  systemLabel: document.querySelector("#system-label"),
  hostname: document.querySelector("#hostname"),
  uptime: document.querySelector("#uptime"),
  version: document.querySelector("#version"),
  build: document.querySelector("#build"),
  statusDetail: document.querySelector("#status-detail"),
  rebootButton: document.querySelector("#reboot-button"),
  shutdownButton: document.querySelector("#shutdown-button"),
  actionMessage: document.querySelector("#action-message"),
  backButton: document.querySelector("#back-button"),
  logoutButton: document.querySelector("#logout-button"),
  transition: document.querySelector("#power-transition"),
  transitionTitle: document.querySelector("#transition-title"),
  transitionDetail: document.querySelector("#transition-detail"),
};

async function api(path, options = {}) {
  const response = await fetch(path, { cache: "no-store", ...options });
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

function formatUptime(seconds) {
  const totalMinutes = Math.max(0, Math.floor(seconds / 60));
  const days = Math.floor(totalMinutes / 1440);
  const hours = Math.floor((totalMinutes % 1440) / 60);
  const minutes = totalMinutes % 60;
  if (days > 0) return `${days} T ${hours} Std`;
  if (hours > 0) return `${hours} Std ${minutes} Min`;
  return `${minutes} Min`;
}

function render() {
  const status = model.status;
  const available = status?.power_control_available === true;
  elements.systemLabel.textContent = available
    ? "Systemsteuerung bereit"
    : "Systemsteuerung nicht verfügbar";
  elements.systemState.className = `mode-state ${available ? "is-client" : "is-error"}`;
  elements.hostname.textContent = status?.hostname || "–";
  elements.uptime.textContent = status ? formatUptime(status.uptime_seconds) : "–";
  elements.version.textContent = status?.version || "–";
  elements.build.textContent = status?.build || status?.revision || "–";
  elements.statusDetail.textContent = status?.detail || "";
  elements.rebootButton.disabled = model.actionPending || !available;
  elements.shutdownButton.disabled = model.actionPending || !available;
}

async function refreshStatus() {
  if (model.actionPending) return;
  try {
    model.status = await api("/api/admin/system/status");
    elements.actionMessage.textContent = "";
    elements.actionMessage.classList.remove("is-error");
    render();
  } catch (error) {
    elements.actionMessage.textContent = error.message;
    elements.actionMessage.classList.add("is-error");
  }
}

function showTransition(action) {
  const reboot = action === "reboot";
  elements.transitionTitle.textContent = reboot
    ? "Raspberry Pi wird neu gestartet"
    : "Raspberry Pi wird heruntergefahren";
  elements.transitionDetail.textContent = reboot
    ? "Der Kiosk erscheint nach dem Start automatisch wieder."
    : "Das Display kann jetzt dunkel werden.";
  elements.transition.hidden = false;
}

async function requestPower(action) {
  const reboot = action === "reboot";
  const prompt = reboot
    ? "Raspberry Pi jetzt wirklich neu starten?"
    : "Raspberry Pi jetzt wirklich vollständig herunterfahren?";
  if (!window.confirm(prompt)) return;

  model.actionPending = true;
  elements.actionMessage.classList.remove("is-error");
  elements.actionMessage.textContent = reboot
    ? "Neustart wird angefordert …"
    : "Herunterfahren wird angefordert …";
  render();
  try {
    const path = reboot ? "/api/admin/system/reboot" : "/api/admin/system/shutdown";
    await api(path, { method: "POST" });
    showTransition(action);
  } catch (error) {
    model.actionPending = false;
    elements.actionMessage.textContent = error.message;
    elements.actionMessage.classList.add("is-error");
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
  if (model.actionPending) return;
  try {
    const tap = await api("/api/tap/status");
    if (tap.state !== "admin" || !tap.is_admin) window.location.assign("/");
  } catch (_error) {
    window.location.assign("/");
  }
}

elements.rebootButton.addEventListener("click", () => requestPower("reboot"));
elements.shutdownButton.addEventListener("click", () => requestPower("poweroff"));
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
window.setInterval(refreshStatus, 10000);
