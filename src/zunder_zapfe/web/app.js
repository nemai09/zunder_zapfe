"use strict";

const ACTIVE_POUR_STATES = new Set([
  "manual_pouring",
  "portion_pouring",
  "top_up_pouring",
  "maintenance_pouring",
]);

const model = {
  connected: false,
  tap: null,
  nfc: null,
  options: null,
  consumption: null,
  keg: null,
  health: null,
  actionPending: false,
  manualHeld: false,
  manualStartPending: false,
  manualStopPending: false,
  manualReleaseRequested: false,
  manualActivationTimer: null,
  refreshRunning: false,
  lastContextRefresh: 0,
  lastHealthRefresh: 0,
};

const elements = {
  screens: [...document.querySelectorAll("[data-screen]")],
  connection: document.querySelector("#connection"),
  connectionLabel: document.querySelector("#connection-label"),
  valveStatus: document.querySelector("#valve-status"),
  valveLabel: document.querySelector("#valve-label"),
  readerStatus: document.querySelector("#reader-status"),
  readerLabel: document.querySelector("#reader-label"),
  buildVersion: document.querySelector("#build-version"),
  clock: document.querySelector("#clock"),
  userName: document.querySelector("#user-name"),
  actionError: document.querySelector("#action-error"),
  beverageName: document.querySelector("#beverage-name"),
  beverageDetail: document.querySelector("#beverage-detail"),
  consumptionVolume: document.querySelector("#consumption-volume"),
  consumptionAmount: document.querySelector("#consumption-amount"),
  manualButton: document.querySelector("#manual-button"),
  manualVolume: document.querySelector("#manual-volume"),
  manualLabel: document.querySelector("#manual-label"),
  manualHint: document.querySelector("#manual-hint"),
  legacyState: document.querySelector("#legacy-state"),
  safetyReason: document.querySelector("#safety-reason"),
  resetError: document.querySelector("#reset-error"),
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
      // A non-JSON response still produces a useful HTTP error.
    }
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

function setScreen(name) {
  for (const screen of elements.screens) {
    screen.classList.toggle("is-active", screen.dataset.screen === name);
  }
}

function currentScreen() {
  if (!model.connected) return "offline";
  const state = model.tap?.state || "starting";
  if (["fault_locked", "emergency_stop"].includes(state)) return "locked";
  if (["authenticated", "manual_pouring"].includes(state)) return "tap";
  if (["portion_pouring", "top_up_available", "top_up_pouring", "maintenance", "maintenance_pouring"].includes(state)) {
    return "legacy";
  }
  return state === "idle" ? "idle" : "offline";
}

function formatVolume(volumeMl) {
  if (!Number.isFinite(volumeMl)) return "–";
  return volumeMl >= 1000
    ? `${new Intl.NumberFormat("de-DE", { maximumFractionDigits: 2 }).format(volumeMl / 1000)} l`
    : `${volumeMl} ml`;
}

function formatMoney(amountCents) {
  if (!Number.isFinite(amountCents)) return "–";
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
  }).format(amountCents / 100);
}

function render() {
  setScreen(currentScreen());
  elements.connection.className = `connection ${model.connected ? "is-online" : "is-offline"}`;
  elements.connectionLabel.textContent = model.connected ? "Steuerung bereit" : "Keine Verbindung";
  const valveOpen = Boolean(model.tap?.valve_open);
  elements.valveStatus.classList.toggle("is-open", valveOpen);
  elements.valveStatus.classList.toggle(
    "flow-debug",
    Boolean(model.options?.debug_flow_watchdog_disabled),
  );
  elements.valveLabel.textContent = `DEBUG · Ventil ${valveOpen ? "EIN" : "AUS"}`;
  if (model.health?.build) elements.buildVersion.textContent = model.health.build;

  if (model.nfc) {
    const ready = ["ready", "card"].includes(model.nfc.state);
    elements.readerStatus.classList.toggle("is-ready", ready);
    const labels = {
      starting: "NFC-Leser startet …",
      unavailable: "NFC-Unterstützung nicht verfügbar",
      disconnected: "NFC-Leser nicht verbunden",
      ready: "NFC-Leser bereit",
      card: "Karte erkannt …",
      error: "NFC-Leser meldet einen Fehler",
    };
    elements.readerLabel.textContent = labels[model.nfc.state] || "NFC-Status unbekannt";
  }

  elements.userName.textContent = model.tap?.user_display_name || "Zapfer";
  elements.beverageName.textContent = model.keg?.beverage_name || "Kein aktives Getränk";
  elements.beverageDetail.textContent = model.keg
    ? `${formatMoney(model.keg.price_per_liter_cents)} / Liter · ${formatVolume(model.keg.remaining_volume_ml)} im Fass`
    : "Fassdaten sind noch nicht verfügbar.";
  elements.consumptionVolume.textContent = formatVolume(model.consumption?.measured_volume_ml);
  elements.consumptionAmount.textContent = formatMoney(model.consumption?.amount_cents);

  const manualPouring = model.tap?.state === "manual_pouring";
  const holding = manualPouring || model.manualHeld;
  const limitReachedWhileHeld =
    model.manualHeld &&
    !manualPouring &&
    model.tap?.last_booking?.kind === "manual" &&
    model.tap?.last_booking?.completion === "limit_reached";
  elements.manualVolume.textContent = String(model.tap?.measured_volume_ml || 0);
  elements.manualLabel.textContent = limitReachedWhileHeld
    ? "Zeitlimit erreicht"
    : manualPouring
      ? "Zapfung läuft"
      : "Gedrückt halten";
  elements.manualHint.textContent = limitReachedWhileHeld
    ? "Loslassen und erneut drücken"
    : manualPouring
      ? "Loslassen stoppt sofort"
      : "zum Zapfen";
  elements.manualButton.classList.toggle("is-holding", holding);
  elements.manualButton.setAttribute("aria-pressed", String(holding));
  elements.manualButton.disabled = !["authenticated", "manual_pouring"].includes(
    model.tap?.state,
  );

  elements.legacyState.textContent = model.tap?.state || "unbekannt";
  elements.safetyReason.textContent = model.tap?.safety_reason || "Die Anlage wurde sicher verriegelt.";
}

async function refreshContext(force = false) {
  const now = Date.now();
  if (!force && now - model.lastContextRefresh < 2000) return;
  model.lastContextRefresh = now;
  const authenticated = Boolean(model.tap?.user_id);
  try {
    model.options = await api("/api/tap/options");
    if (authenticated) {
      [model.consumption, model.keg] = await Promise.all([
        api("/api/consumption/current"),
        api("/api/keg/current"),
      ]);
    } else {
      model.consumption = null;
      model.keg = null;
    }
  } catch (error) {
    if (authenticated) elements.actionError.textContent = error.message;
  }
}

async function refresh() {
  if (model.refreshRunning) return;
  model.refreshRunning = true;
  try {
    const previousUser = model.tap?.user_id;
    const previousBooking = model.tap?.last_booking?.id;
    const now = Date.now();
    const requests = [api("/api/tap/status")];
    if (!model.health || now - model.lastHealthRefresh >= 3000) requests.push(api("/api/health"));
    if (!model.tap || model.tap.state === "idle") requests.push(api("/api/nfc/status"));
    const [tap, ...secondary] = await Promise.all(requests);
    model.tap = tap;
    for (const result of secondary) {
      if (result?.application === "zunder-zapfe") {
        if (model.health?.revision && model.health.revision !== result.revision) {
          window.location.reload();
          return;
        }
        model.health = result;
        model.lastHealthRefresh = now;
      }
      if (result?.state && "simulated" in result) model.nfc = result;
    }
    model.connected = true;
    const contextChanged = previousUser !== tap.user_id || previousBooking !== tap.last_booking?.id;
    await refreshContext(contextChanged);
  } catch (_error) {
    model.connected = false;
  } finally {
    model.refreshRunning = false;
    render();
  }
}

async function performAction(action, errorElement = elements.actionError) {
  if (model.actionPending) return;
  model.actionPending = true;
  errorElement.textContent = "";
  try {
    await action();
    await refresh();
  } catch (error) {
    errorElement.textContent = error.message;
  } finally {
    model.actionPending = false;
  }
}

function logout() {
  return performAction(() => api("/api/session/logout", { method: "POST" }));
}

async function requestManualStop() {
  if (model.manualStopPending) return;
  if (model.manualStartPending) {
    model.manualReleaseRequested = true;
    return;
  }
  if (model.tap?.state !== "manual_pouring") return;
  model.manualStopPending = true;
  try {
    await api("/api/tap/manual/stop", { method: "POST" });
  } catch (_error) {
    // The backend watchdog remains the independent safety fallback.
  } finally {
    await refresh();
    model.manualStopPending = false;
  }
}

function startManual(event) {
  if (event.pointerType === "mouse" && event.button !== 0) return;
  if (model.manualHeld || model.tap?.state !== "authenticated") return;
  model.manualHeld = true;
  model.manualReleaseRequested = false;
  elements.actionError.textContent = "";
  elements.manualButton.classList.add("is-holding");
  try {
    elements.manualButton.setPointerCapture(event.pointerId);
  } catch (_error) {
    // Pointer capture is an enhancement; global release handlers remain active.
  }

  const debounceMs = model.options?.manual_press_debounce_ms ?? 120;
  model.manualActivationTimer = window.setTimeout(async () => {
    model.manualActivationTimer = null;
    if (!model.manualHeld) return;
    model.manualStartPending = true;
    try {
      model.tap = await api("/api/tap/manual/start", { method: "POST" });
    } catch (error) {
      elements.actionError.textContent = error.message;
      model.manualHeld = false;
    } finally {
      model.manualStartPending = false;
    }
    if (model.manualReleaseRequested || !model.manualHeld) await requestManualStop();
    await refresh();
  }, debounceMs);
}

function releaseManual() {
  if (model.manualActivationTimer !== null) {
    window.clearTimeout(model.manualActivationTimer);
    model.manualActivationTimer = null;
  }
  const wasHeld = model.manualHeld;
  model.manualHeld = false;
  model.manualReleaseRequested = true;
  elements.manualButton.classList.remove("is-holding");
  if (wasHeld || model.manualStartPending || model.tap?.state === "manual_pouring") {
    requestManualStop();
  }
}

document.querySelector("#logout-button").addEventListener("click", logout);
document.querySelector("#reset-button").addEventListener("click", () =>
  performAction(
    () => api("/api/tap/safety/reset", { method: "POST" }),
    elements.resetError,
  ),
);
elements.manualButton.addEventListener("pointerdown", startManual);
elements.manualButton.addEventListener("pointerup", releaseManual);
elements.manualButton.addEventListener("pointercancel", releaseManual);
elements.manualButton.addEventListener("lostpointercapture", releaseManual);
window.addEventListener("pointerup", releaseManual);
window.addEventListener("blur", releaseManual);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) releaseManual();
});
document.addEventListener("contextmenu", (event) => event.preventDefault());

window.setInterval(() => {
  elements.clock.textContent = new Intl.DateTimeFormat("de-DE", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date());
}, 1000);

window.setInterval(() => {
  if (ACTIVE_POUR_STATES.has(model.tap?.state)) {
    api("/api/tap/heartbeat", { method: "POST" }).catch(() => {
      model.connected = false;
      render();
    });
  }
}, 650);

window.setInterval(refresh, 300);
refresh();
