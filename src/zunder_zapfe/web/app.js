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
  lastActivitySentAt: 0,
  adminUsers: [],
  adminCards: [],
  adminSettings: null,
  adminSelectedUserId: null,
  adminLoaded: false,
  captureActive: false,
  captureTimer: null,
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
  logoutButton: document.querySelector("#logout-button"),
  sessionActions: document.querySelector(".session-actions"),
  adminButton: document.querySelector("#admin-button"),
  adminBackButton: document.querySelector("#admin-back-button"),
  adminLogoutButton: document.querySelector("#admin-logout-button"),
  actionError: document.querySelector("#action-error"),
  beverageName: document.querySelector("#beverage-name"),
  beverageDetail: document.querySelector("#beverage-detail"),
  consumptionVolume: document.querySelector("#consumption-volume"),
  consumptionAmount: document.querySelector("#consumption-amount"),
  manualButton: document.querySelector("#manual-button"),
  manualVolume: document.querySelector("#manual-volume"),
  manualLabel: document.querySelector("#manual-label"),
  manualHint: document.querySelector("#manual-hint"),
  sessionTimeout: document.querySelector("#session-timeout"),
  sessionTimeoutFill: document.querySelector("#session-timeout-fill"),
  legacyState: document.querySelector("#legacy-state"),
  safetyReason: document.querySelector("#safety-reason"),
  resetError: document.querySelector("#reset-error"),
  adminPanels: [...document.querySelectorAll("[data-admin-panel]")],
  adminNavButtons: [...document.querySelectorAll("[data-admin-section]")],
  userList: document.querySelector("#user-list"),
  userForm: document.querySelector("#user-form"),
  userId: document.querySelector("#user-id"),
  firstName: document.querySelector("#first-name"),
  lastName: document.querySelector("#last-name"),
  userNote: document.querySelector("#user-note"),
  userIsAdmin: document.querySelector("#user-is-admin"),
  userActive: document.querySelector("#user-active"),
  captureCardButton: document.querySelector("#capture-card-button"),
  cardList: document.querySelector("#card-list"),
  userMessage: document.querySelector("#user-message"),
  captureDialog: document.querySelector("#capture-dialog"),
  captureInstruction: document.querySelector("#capture-instruction"),
  adminSettingsForm: document.querySelector("#admin-settings-form"),
  adminTimeoutInput: document.querySelector("#admin-timeout-input"),
  settingsMessage: document.querySelector("#settings-message"),
  adminBackendState: document.querySelector("#admin-backend-state"),
  adminReaderState: document.querySelector("#admin-reader-state"),
  adminValveState: document.querySelector("#admin-valve-state"),
  diagnosticConnection: document.querySelector("#diagnostic-connection"),
  diagnosticNfc: document.querySelector("#diagnostic-nfc"),
  diagnosticValve: document.querySelector("#diagnostic-valve"),
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
  if (state === "admin") return "admin";
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
      ? "ml · Loslassen stoppt sofort"
      : "zum Zapfen";
  elements.manualButton.classList.toggle("is-holding", holding);
  elements.manualButton.setAttribute("aria-pressed", String(holding));
  elements.manualButton.disabled = !["authenticated", "manual_pouring"].includes(
    model.tap?.state,
  );
  elements.logoutButton.disabled = manualPouring;
  const adminEntryVisible = Boolean(
    model.tap?.is_admin && model.tap?.state === "authenticated",
  );
  elements.adminButton.hidden = !adminEntryVisible;
  elements.sessionActions.classList.toggle("has-admin", adminEntryVisible);
  elements.adminButton.disabled = manualPouring;

  const sessionRemainingMs = model.tap?.session_remaining_ms;
  const sessionTimeoutSeconds = model.tap?.state === "admin"
    ? model.adminSettings?.admin_session_timeout_seconds
      ?? model.options?.admin_session_timeout_seconds
      ?? 30
    : model.options?.session_timeout_seconds ?? 15;
  const sessionTimeoutMs = sessionTimeoutSeconds * 1000;
  const sessionBarActive = Boolean(model.tap?.user_id) && Number.isFinite(sessionRemainingMs);
  const sessionProgress = sessionBarActive
    ? Math.max(0, Math.min(1, sessionRemainingMs / sessionTimeoutMs))
    : 0;
  elements.sessionTimeout.classList.toggle("is-active", sessionBarActive);
  elements.sessionTimeoutFill.style.width = `${sessionProgress * 100}%`;

  elements.legacyState.textContent = model.tap?.state || "unbekannt";
  elements.safetyReason.textContent = model.tap?.safety_reason || "Die Anlage wurde sicher verriegelt.";

  const readerState = model.nfc?.state || "unbekannt";
  const valveState = valveOpen ? "OFFEN" : "geschlossen";
  elements.adminBackendState.textContent = model.connected ? "bereit" : "offline";
  elements.adminReaderState.textContent = readerState;
  elements.adminValveState.textContent = valveState;
  elements.diagnosticConnection.textContent = model.connected ? "bereit" : "offline";
  elements.diagnosticNfc.textContent = readerState;
  elements.diagnosticValve.textContent = valveState;
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
    if (tap.state !== "admin") model.adminLoaded = false;
    const contextChanged = previousUser !== tap.user_id || previousBooking !== tap.last_booking?.id;
    await refreshContext(contextChanged);
    if (tap.state === "admin" && !model.adminLoaded) await loadAdminData();
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
  stopCapture(false);
  return performAction(() => api("/api/session/logout", { method: "POST" }));
}

function registerActivity() {
  if (!["authenticated", "admin", "manual_pouring"].includes(model.tap?.state)) return;
  const now = Date.now();
  if (now - model.lastActivitySentAt < 500) return;
  model.lastActivitySentAt = now;
  if (Number.isFinite(model.tap?.session_remaining_ms)) {
    const timeoutSeconds = model.tap?.state === "admin"
      ? model.adminSettings?.admin_session_timeout_seconds
        ?? model.options?.admin_session_timeout_seconds
        ?? 30
      : model.options?.session_timeout_seconds ?? 15;
    model.tap.session_remaining_ms = timeoutSeconds * 1000;
    render();
  }
  api("/api/session/activity", { method: "POST" }).catch(() => {
    // The regular status refresh remains the source of truth.
  });
}

function showAdminSection(section) {
  for (const button of elements.adminNavButtons) {
    button.classList.toggle("is-active", button.dataset.adminSection === section);
  }
  for (const panel of elements.adminPanels) {
    panel.classList.toggle("is-active", panel.dataset.adminPanel === section);
  }
}

async function enterAdmin() {
  if (model.actionPending) return;
  model.actionPending = true;
  elements.actionError.textContent = "";
  try {
    model.tap = await api("/api/admin/session/enter", { method: "POST" });
    model.adminLoaded = false;
    await loadAdminData();
  } catch (error) {
    elements.actionError.textContent = error.message;
  } finally {
    model.actionPending = false;
    render();
  }
}

async function exitAdmin() {
  stopCapture(false);
  await performAction(async () => {
    model.tap = await api("/api/admin/session/exit", { method: "POST" });
    model.adminLoaded = false;
  }, elements.userMessage);
}

async function loadAdminData() {
  if (model.tap?.state !== "admin") return;
  try {
    [model.adminUsers, model.adminSettings] = await Promise.all([
      api("/api/admin/users"),
      api("/api/admin/settings"),
    ]);
    elements.adminTimeoutInput.value = String(
      model.adminSettings.admin_session_timeout_seconds,
    );
    if (
      model.adminSelectedUserId !== null
      && !model.adminUsers.some((user) => user.id === model.adminSelectedUserId)
    ) {
      model.adminSelectedUserId = null;
    }
    if (model.adminSelectedUserId === null && model.adminUsers.length) {
      model.adminSelectedUserId = model.adminUsers[0].id;
    }
    renderAdminUsers();
    await loadAdminCards();
    model.adminLoaded = true;
  } catch (error) {
    elements.userMessage.textContent = error.message;
  }
}

function selectedAdminUser() {
  return model.adminUsers.find((user) => user.id === model.adminSelectedUserId) || null;
}

function renderAdminUsers() {
  elements.userList.replaceChildren();
  for (const user of model.adminUsers) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "user-list-item";
    button.classList.toggle("is-selected", user.id === model.adminSelectedUserId);
    button.classList.toggle("is-inactive", !user.active);
    const name = document.createElement("strong");
    name.textContent = user.display_name;
    const meta = document.createElement("span");
    const role = user.is_admin ? "Admin" : "Benutzer";
    meta.textContent = `${role} · ${user.active_nfc_card_count} Armband`;
    button.append(name, meta);
    button.addEventListener("click", async () => {
      model.adminSelectedUserId = user.id;
      fillUserForm(user);
      renderAdminUsers();
      await loadAdminCards();
    });
    elements.userList.append(button);
  }
  const user = selectedAdminUser();
  if (user) fillUserForm(user);
}

function fillUserForm(user) {
  elements.userId.value = String(user.id);
  elements.firstName.value = user.first_name;
  elements.lastName.value = user.last_name || "";
  elements.userNote.value = user.note || "";
  elements.userIsAdmin.checked = user.is_admin;
  elements.userActive.checked = user.active;
  elements.captureCardButton.disabled = false;
  elements.userMessage.textContent = "";
}

function newUser() {
  model.adminSelectedUserId = null;
  elements.userId.value = "";
  elements.firstName.value = "";
  elements.lastName.value = "";
  elements.userNote.value = "";
  elements.userIsAdmin.checked = false;
  elements.userActive.checked = true;
  elements.captureCardButton.disabled = true;
  elements.cardList.replaceChildren();
  elements.userMessage.textContent = "Neuen Benutzer speichern, danach Armband zuweisen.";
  renderAdminUsers();
  elements.firstName.focus();
}

async function saveUser(event) {
  event.preventDefault();
  const existingId = Number(elements.userId.value) || null;
  const payload = {
    first_name: elements.firstName.value,
    last_name: elements.lastName.value || null,
    note: elements.userNote.value || null,
    is_admin: elements.userIsAdmin.checked,
  };
  if (existingId !== null) payload.active = elements.userActive.checked;
  elements.userMessage.textContent = "";
  try {
    const user = await api(
      existingId === null ? "/api/admin/users" : `/api/admin/users/${existingId}`,
      {
        method: existingId === null ? "POST" : "PATCH",
        body: JSON.stringify(payload),
      },
    );
    model.adminSelectedUserId = user.id;
    elements.userMessage.textContent = "Gespeichert.";
    await loadAdminData();
  } catch (error) {
    elements.userMessage.textContent = error.message;
  }
}

async function loadAdminCards() {
  if (model.adminSelectedUserId === null || model.tap?.state !== "admin") {
    model.adminCards = [];
    renderAdminCards();
    return;
  }
  try {
    model.adminCards = await api(
      `/api/admin/users/${model.adminSelectedUserId}/nfc-cards`,
    );
    renderAdminCards();
  } catch (error) {
    elements.userMessage.textContent = error.message;
  }
}

function renderAdminCards() {
  elements.cardList.replaceChildren();
  for (const card of model.adminCards) {
    const row = document.createElement("div");
    row.className = "card-list-item";
    const label = document.createElement("span");
    label.textContent = `Armband ${card.uid_hint}`;
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = `card-status ${card.active ? "is-active" : ""}`;
    toggle.textContent = card.active ? "Aktiv" : "Gesperrt";
    toggle.addEventListener("click", async () => {
      try {
        await api(`/api/admin/nfc-cards/${card.id}`, {
          method: "PATCH",
          body: JSON.stringify({ active: !card.active }),
        });
        await loadAdminData();
      } catch (error) {
        elements.userMessage.textContent = error.message;
      }
    });
    row.append(label, toggle);
    elements.cardList.append(row);
  }
}

function beginCapture() {
  if (model.adminSelectedUserId === null || model.captureActive) return;
  model.captureActive = true;
  elements.captureDialog.hidden = false;
  elements.captureInstruction.textContent = "Admin-Armband vom Leser entfernen.";
  pollCapture();
}

async function pollCapture() {
  if (!model.captureActive || model.adminSelectedUserId === null) return;
  try {
    const result = await api(
      `/api/admin/users/${model.adminSelectedUserId}/nfc-cards/capture`,
      { method: "POST" },
    );
    const instructions = {
      remove_card: "Admin-Armband vom Leser entfernen.",
      waiting: "Neues Veranstaltungsarmband kurz auflegen.",
      reader_unavailable: "NFC-Leser ist momentan nicht verfügbar.",
      assigned: "Armband wurde erfolgreich zugewiesen.",
    };
    elements.captureInstruction.textContent = instructions[result.state] || result.state;
    if (result.state === "assigned") {
      model.captureActive = false;
      await loadAdminData();
      model.captureTimer = window.setTimeout(() => {
        elements.captureDialog.hidden = true;
      }, 650);
      return;
    }
  } catch (error) {
    elements.captureInstruction.textContent = error.message;
    model.captureActive = false;
    return;
  }
  model.captureTimer = window.setTimeout(pollCapture, 350);
}

function stopCapture(notifyBackend = true) {
  model.captureActive = false;
  if (model.captureTimer !== null) window.clearTimeout(model.captureTimer);
  model.captureTimer = null;
  elements.captureDialog.hidden = true;
  if (notifyBackend && model.tap?.state === "admin") {
    api("/api/admin/nfc-capture", { method: "DELETE" }).catch(() => {});
  }
}

async function saveAdminSettings(event) {
  event.preventDefault();
  elements.settingsMessage.textContent = "";
  try {
    model.adminSettings = await api("/api/admin/settings", {
      method: "PATCH",
      body: JSON.stringify({
        admin_session_timeout_seconds: Number(elements.adminTimeoutInput.value),
      }),
    });
    elements.settingsMessage.textContent = "Timeout übernommen.";
    render();
  } catch (error) {
    elements.settingsMessage.textContent = error.message;
  }
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

elements.logoutButton.addEventListener("click", logout);
elements.adminButton.addEventListener("click", enterAdmin);
elements.adminBackButton.addEventListener("click", exitAdmin);
elements.adminLogoutButton.addEventListener("click", logout);
document.querySelector("#new-user-button").addEventListener("click", newUser);
elements.userForm.addEventListener("submit", saveUser);
elements.captureCardButton.addEventListener("click", beginCapture);
document.querySelector("#cancel-capture-button").addEventListener("click", () => stopCapture());
elements.adminSettingsForm.addEventListener("submit", saveAdminSettings);
for (const button of elements.adminNavButtons) {
  button.addEventListener("click", () => showAdminSection(button.dataset.adminSection));
}
document.addEventListener("pointerdown", registerActivity, { capture: true });
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
