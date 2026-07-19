"use strict";

const ACTIVE_POUR_STATES = new Set([
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
  topUpHeld: false,
  topUpStopPending: false,
  refreshRunning: false,
  lastContextRefresh: 0,
  lastHealthRefresh: 0,
};

const elements = {
  screens: [...document.querySelectorAll("[data-screen]")],
  connection: document.querySelector("#connection"),
  connectionLabel: document.querySelector("#connection-label"),
  readerStatus: document.querySelector("#reader-status"),
  readerLabel: document.querySelector("#reader-label"),
  buildVersion: document.querySelector("#build-version"),
  clock: document.querySelector("#clock"),
  userName: document.querySelector("#user-name"),
  portionGrid: document.querySelector("#portion-grid"),
  actionError: document.querySelector("#action-error"),
  beverageName: document.querySelector("#beverage-name"),
  beverageDetail: document.querySelector("#beverage-detail"),
  consumptionVolume: document.querySelector("#consumption-volume"),
  consumptionAmount: document.querySelector("#consumption-amount"),
  measuredVolume: document.querySelector("#measured-volume"),
  targetVolume: document.querySelector("#target-volume"),
  progressRing: document.querySelector("#progress-ring"),
  topUpButton: document.querySelector("#top-up-button"),
  topUpCountdown: document.querySelector("#top-up-countdown"),
  topUpLabel: document.querySelector("#top-up-label"),
  topUpUnit: document.querySelector("#top-up-unit"),
  topUpInstruction: document.querySelector("#top-up-instruction"),
  topUpLogout: document.querySelector("#top-up-logout"),
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
  if (state === "portion_pouring") return "pouring";
  if (["top_up_available", "top_up_pouring"].includes(state)) return "top-up";
  if (["authenticated", "maintenance", "maintenance_pouring"].includes(state)) {
    return "authenticated";
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

function renderPortions() {
  const portions = model.options?.standard_portions_ml || [];
  const special = model.options?.special_portion_ml;
  const signature = JSON.stringify([portions, special]);
  if (elements.portionGrid.dataset.signature === signature) return;
  elements.portionGrid.dataset.signature = signature;
  elements.portionGrid.replaceChildren();

  const choices = portions.map((volume) => ({ volume, special: false }));
  if (special !== null && special !== undefined) {
    choices.push({ volume: special, special: true });
  }
  for (const choice of choices) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `portion-button${choice.special ? " is-special" : ""}`;
    button.innerHTML = `<strong>${choice.volume}</strong><span>${choice.special ? "Deine Sondergröße" : "Milliliter"}</span>`;
    button.addEventListener("click", () => startPortion(choice.volume));
    elements.portionGrid.append(button);
  }
}

function render() {
  setScreen(currentScreen());
  elements.connection.className = `connection ${model.connected ? "is-online" : "is-offline"}`;
  elements.connectionLabel.textContent = model.connected ? "Steuerung bereit" : "Keine Verbindung";
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
  renderPortions();
  elements.beverageName.textContent = model.keg?.beverage_name || "Kein aktives Getränk";
  elements.beverageDetail.textContent = model.keg
    ? `${formatMoney(model.keg.price_per_liter_cents)} / Liter · ${formatVolume(model.keg.remaining_volume_ml)} im Fass`
    : "Fassdaten sind noch nicht verfügbar.";
  elements.consumptionVolume.textContent = formatVolume(model.consumption?.measured_volume_ml);
  elements.consumptionAmount.textContent = formatMoney(model.consumption?.amount_cents);

  const measured = model.tap?.measured_volume_ml || 0;
  const target = model.tap?.target_volume_ml || 0;
  elements.measuredVolume.textContent = String(measured);
  elements.targetVolume.textContent = String(target);
  const progress = target > 0 ? Math.min(1, measured / target) : 0;
  elements.progressRing.style.setProperty("--progress", `${progress * 360}deg`);

  const topUpPouring = model.tap?.state === "top_up_pouring";
  const remainingMs = model.tap?.top_up_remaining_ms;
  elements.topUpCountdown.textContent = topUpPouring
    ? String(model.tap?.measured_volume_ml || 0)
    : String(Math.max(0, Math.ceil((remainingMs || 0) / 1000)));
  elements.topUpLabel.textContent = topUpPouring ? "Nachfüllen läuft" : "Gedrückt halten";
  elements.topUpUnit.textContent = topUpPouring ? "Milliliter" : "zum Nachfüllen";
  elements.topUpInstruction.textContent = topUpPouring
    ? "Weiter gedrückt halten. Loslassen stoppt sofort."
    : "Button gedrückt halten. Loslassen stoppt sofort.";
  elements.topUpButton.classList.toggle("is-holding", topUpPouring || model.topUpHeld);
  elements.topUpLogout.disabled = topUpPouring;

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
    if (!model.health || now - model.lastHealthRefresh >= 3000) {
      requests.push(api("/api/health"));
    }
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
    const contextChanged =
      previousUser !== model.tap.user_id || previousBooking !== model.tap.last_booking?.id;
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

function startPortion(volumeMl) {
  return performAction(() =>
    api("/api/tap/portion", {
      method: "POST",
      body: JSON.stringify({ target_volume_ml: volumeMl }),
    }),
  );
}

function logout() {
  return performAction(() => api("/api/session/logout", { method: "POST" }));
}

async function startTopUp(event) {
  if (model.topUpHeld || model.tap?.state !== "top_up_available") return;
  model.topUpHeld = true;
  elements.topUpButton.classList.add("is-holding");
  try {
    elements.topUpButton.setPointerCapture(event.pointerId);
  } catch (_error) {
    // Pointer capture is an enhancement; global release handlers remain active.
  }
  try {
    await api("/api/tap/top-up/start", { method: "POST" });
    await refresh();
  } catch (error) {
    model.topUpHeld = false;
    elements.actionError.textContent = error.message;
    render();
  }
}

async function stopTopUp() {
  if (model.topUpStopPending) return;
  if (!model.topUpHeld && model.tap?.state !== "top_up_pouring") return;
  model.topUpStopPending = true;
  model.topUpHeld = false;
  elements.topUpButton.classList.remove("is-holding");
  try {
    await api("/api/tap/top-up/stop", { method: "POST" });
  } catch (_error) {
    // The backend watchdog remains the independent safety fallback.
  }
  await refresh();
  model.topUpStopPending = false;
}

document.querySelector("#logout-button").addEventListener("click", logout);
elements.topUpLogout.addEventListener("click", logout);
document.querySelector("#abort-button").addEventListener("click", () =>
  performAction(() => api("/api/tap/portion/abort", { method: "POST" })),
);
document.querySelector("#reset-button").addEventListener("click", () =>
  performAction(
    () => api("/api/tap/safety/reset", { method: "POST" }),
    elements.resetError,
  ),
);
elements.topUpButton.addEventListener("pointerdown", startTopUp);
elements.topUpButton.addEventListener("pointerup", stopTopUp);
elements.topUpButton.addEventListener("pointercancel", stopTopUp);
elements.topUpButton.addEventListener("lostpointercapture", stopTopUp);
window.addEventListener("blur", stopTopUp);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopTopUp();
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
