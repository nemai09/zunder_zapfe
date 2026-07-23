"use strict";

const model = {
  session: null,
  users: [],
  events: [],
  beverages: [],
  kegs: [],
  bookings: [],
  statistics: null,
  auditEntries: [],
  technicalEvents: [],
  selectedUserId: null,
  cards: [],
  captureActive: false,
  captureTimer: null,
  toastTimer: null,
};

const elements = {
  loginScreen: document.querySelector("#login-screen"),
  loginForm: document.querySelector("#login-form"),
  loginUser: document.querySelector("#login-user"),
  loginPassword: document.querySelector("#login-password"),
  loginMessage: document.querySelector("#login-message"),
  app: document.querySelector("#admin-app"),
  sessionName: document.querySelector("#session-name"),
  welcomeName: document.querySelector("#welcome-name"),
  userCount: document.querySelector("#user-count"),
  cardCount: document.querySelector("#card-count"),
  activeEventName: document.querySelector("#active-event-name"),
  activeKegName: document.querySelector("#active-keg-name"),
  activeKegRemaining: document.querySelector("#active-keg-remaining"),
  backendStatus: document.querySelector("#backend-status"),
  buildVersion: document.querySelector("#build-version"),
  views: [...document.querySelectorAll("[data-view]")],
  navButtons: [...document.querySelectorAll("[data-nav-view]")],
  userSearch: document.querySelector("#user-search"),
  userFilter: document.querySelector("#user-filter"),
  userResultCount: document.querySelector("#user-result-count"),
  userList: document.querySelector("#user-list"),
  userEmpty: document.querySelector("#user-empty"),
  userSheet: document.querySelector("#user-sheet"),
  editorTitle: document.querySelector("#editor-title"),
  userForm: document.querySelector("#user-form"),
  userId: document.querySelector("#user-id"),
  firstName: document.querySelector("#first-name"),
  lastName: document.querySelector("#last-name"),
  userNote: document.querySelector("#user-note"),
  userIsAdmin: document.querySelector("#user-is-admin"),
  userActive: document.querySelector("#user-active"),
  userMessage: document.querySelector("#user-message"),
  deleteUserSection: document.querySelector("#delete-user-section"),
  deleteUserButton: document.querySelector("#delete-user-button"),
  passwordSection: document.querySelector("#password-section"),
  passwordState: document.querySelector("#password-state"),
  resetPasswordForm: document.querySelector("#reset-password-form"),
  resetPassword: document.querySelector("#reset-password"),
  cardsSection: document.querySelector("#cards-section"),
  cardList: document.querySelector("#card-list"),
  eventForm: document.querySelector("#event-form"),
  eventId: document.querySelector("#event-id"),
  eventName: document.querySelector("#event-name"),
  eventYear: document.querySelector("#event-year"),
  eventActive: document.querySelector("#event-active"),
  eventList: document.querySelector("#event-list"),
  beverageForm: document.querySelector("#beverage-form"),
  beverageId: document.querySelector("#beverage-id"),
  beverageName: document.querySelector("#beverage-name"),
  beverageKegLiters: document.querySelector("#beverage-keg-liters"),
  beveragePriceEuros: document.querySelector("#beverage-price-euros"),
  beverageActive: document.querySelector("#beverage-active"),
  beverageList: document.querySelector("#beverage-list"),
  kegSwitchForm: document.querySelector("#keg-switch-form"),
  kegBeverage: document.querySelector("#keg-beverage"),
  kegVolumeLiters: document.querySelector("#keg-volume-liters"),
  kegVolumeHint: document.querySelector("#keg-volume-hint"),
  kegDetachButton: document.querySelector("#keg-detach-button"),
  kegList: document.querySelector("#keg-list"),
  operationsActiveKeg: document.querySelector("#operations-active-keg"),
  operationsActiveKegDetail: document.querySelector("#operations-active-keg-detail"),
  reportEvent: document.querySelector("#report-event"),
  reportBookingCount: document.querySelector("#report-booking-count"),
  reportVolume: document.querySelector("#report-volume"),
  reportAmount: document.querySelector("#report-amount"),
  reportMaintenance: document.querySelector("#report-maintenance"),
  billingUserList: document.querySelector("#billing-user-list"),
  bookingFilterForm: document.querySelector("#booking-filter-form"),
  bookingUserFilter: document.querySelector("#booking-user-filter"),
  bookingKegFilter: document.querySelector("#booking-keg-filter"),
  bookingKindFilter: document.querySelector("#booking-kind-filter"),
  bookingCompletionFilter: document.querySelector("#booking-completion-filter"),
  bookingFromFilter: document.querySelector("#booking-from-filter"),
  bookingToFilter: document.querySelector("#booking-to-filter"),
  bookingResultCount: document.querySelector("#booking-result-count"),
  bookingList: document.querySelector("#booking-list"),
  auditList: document.querySelector("#audit-list"),
  technicalEventList: document.querySelector("#technical-event-list"),
  captureDialog: document.querySelector("#capture-dialog"),
  captureInstruction: document.querySelector("#capture-instruction"),
  ownPasswordForm: document.querySelector("#own-password-form"),
  currentPassword: document.querySelector("#current-password"),
  newOwnPassword: document.querySelector("#new-own-password"),
  confirmOwnPassword: document.querySelector("#confirm-own-password"),
  accountMessage: document.querySelector("#account-message"),
  toast: document.querySelector("#toast"),
};

function csrfToken() {
  const prefix = "zz_admin_csrf=";
  const cookie = document.cookie.split("; ").find((item) => item.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : "";
}

async function api(path, options = {}) {
  const method = options.method || "GET";
  const headers = new Headers(options.headers || {});
  if (options.body) headers.set("Content-Type", "application/json");
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    headers.set("X-CSRF-Token", csrfToken());
  }
  const response = await fetch(path, { cache: "no-store", ...options, method, headers });
  if (!response.ok) {
    if (response.status === 401 && path !== "/api/web-auth/login") showLogin();
    let detail = `HTTP ${response.status}`;
    try {
      detail = (await response.json()).detail || detail;
    } catch (_error) {
      // HTTP status remains useful when no JSON error body exists.
    }
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

function showToast(message, isError = false) {
  elements.toast.textContent = message;
  elements.toast.classList.toggle("is-error", isError);
  elements.toast.classList.add("is-visible");
  if (model.toastTimer !== null) window.clearTimeout(model.toastTimer);
  model.toastTimer = window.setTimeout(
    () => elements.toast.classList.remove("is-visible"),
    3200,
  );
}

function showLogin() {
  stopCapture(false);
  model.session = null;
  elements.app.hidden = true;
  elements.loginScreen.hidden = false;
  elements.loginPassword.value = "";
  loadLoginOptions();
}

function showApp() {
  elements.loginScreen.hidden = true;
  elements.app.hidden = false;
  elements.sessionName.textContent = model.session.display_name;
  elements.welcomeName.textContent = model.session.display_name;
}

function showView(name) {
  for (const view of elements.views) {
    view.classList.toggle("is-active", view.dataset.view === name);
  }
  for (const button of elements.navButtons) {
    button.classList.toggle("is-active", button.dataset.navView === name);
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (name === "data") loadReporting();
}

async function loadLoginOptions() {
  try {
    const admins = await api("/api/web-auth/admins");
    elements.loginUser.replaceChildren();
    if (!admins.length) {
      elements.loginUser.add(new Option("Kein Adminpasswort eingerichtet", ""));
      elements.loginMessage.textContent =
        "Zuerst am Raspberry Pi ein persönliches Adminpasswort setzen.";
      return;
    }
    elements.loginUser.add(new Option("Admin auswählen", ""));
    for (const admin of admins) {
      elements.loginUser.add(new Option(admin.display_name, String(admin.id)));
    }
    elements.loginMessage.textContent = "";
  } catch (error) {
    elements.loginMessage.textContent = error.message;
  }
}

async function login(event) {
  event.preventDefault();
  elements.loginMessage.textContent = "";
  try {
    model.session = await api("/api/web-auth/login", {
      method: "POST",
      body: JSON.stringify({
        user_id: Number(elements.loginUser.value),
        password: elements.loginPassword.value,
      }),
    });
    elements.loginPassword.value = "";
    showApp();
    await loadWorkspace();
    resetEventForm();
    resetBeverageForm();
  } catch (error) {
    elements.loginMessage.textContent =
      error.message === "Invalid admin credentials"
        ? "Admin oder Passwort ist nicht korrekt."
        : error.message;
  }
}

async function logout() {
  try {
    await api("/api/web-auth/logout", { method: "POST" });
  } catch (_error) {
    // A missing or expired session has the same local result.
  }
  showLogin();
}

async function loadWorkspace() {
  try {
    const [users, events, beverages, kegs, health] = await Promise.all([
      api("/api/web-admin/users"),
      api("/api/web-admin/events"),
      api("/api/web-admin/beverages"),
      api("/api/web-admin/kegs"),
      api("/api/health"),
    ]);
    model.users = users;
    model.events = events;
    model.beverages = beverages;
    model.kegs = kegs;
    elements.backendStatus.textContent = "Bereit";
    elements.buildVersion.textContent = health.build;
    renderUsers();
    renderSettings();
    renderKegs();
    renderReportingOptions();
    renderMetrics();
  } catch (error) {
    showToast(error.message, true);
  }
}

function renderMetrics() {
  elements.userCount.textContent = String(model.users.length);
  elements.cardCount.textContent = String(
    model.users.reduce((total, user) => total + user.active_nfc_card_count, 0),
  );
  const activeEvent = model.events.find((event) => event.active);
  const activeKeg = model.kegs.find((keg) => keg.active);
  elements.activeEventName.textContent = activeEvent?.name || "Nicht gewählt";
  elements.activeKegName.textContent = activeKeg?.beverage_name || "Keines";
  elements.activeKegRemaining.textContent = activeKeg
    ? `${formatLiters(activeKeg.remaining_volume_ml)} L rechnerisch übrig`
    : "";
}

function filteredUsers() {
  const query = elements.userSearch.value.trim().toLocaleLowerCase("de-DE");
  const filter = elements.userFilter.value;
  return model.users.filter((user) => {
    const matchesQuery = !query || [user.display_name, user.note]
      .filter(Boolean)
      .some((value) => value.toLocaleLowerCase("de-DE").includes(query));
    const matchesFilter =
      filter === "all"
      || (filter === "active" && user.active)
      || (filter === "blocked" && !user.active)
      || (filter === "admin" && user.is_admin);
    return matchesQuery && matchesFilter;
  });
}

function badge(text, className = "") {
  const item = document.createElement("span");
  item.className = `badge ${className}`.trim();
  item.textContent = text;
  return item;
}

function renderUsers() {
  const users = filteredUsers();
  elements.userList.replaceChildren();
  elements.userResultCount.textContent = `${users.length} von ${model.users.length} Benutzern`;
  elements.userEmpty.hidden = users.length !== 0;
  for (const user of users) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "user-card";
    button.classList.toggle("is-blocked", !user.active);
    const details = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = user.display_name;
    const summary = document.createElement("small");
    summary.textContent = `${user.active_nfc_card_count} aktive von ${user.nfc_card_count} Armbändern`;
    details.append(name, summary);
    const badges = document.createElement("div");
    badges.className = "badges";
    if (user.is_admin) badges.append(badge("Admin", "admin"));
    if (!user.active) badges.append(badge("Gesperrt", "blocked"));
    button.append(details, badges);
    button.addEventListener("click", () => openUser(user.id));
    elements.userList.append(button);
  }
}

function selectedUser() {
  return model.users.find((user) => user.id === model.selectedUserId) || null;
}

async function openUser(userId = null) {
  model.selectedUserId = userId;
  const user = selectedUser();
  elements.editorTitle.textContent = user ? "Benutzer bearbeiten" : "Benutzer anlegen";
  elements.userId.value = user ? String(user.id) : "";
  elements.firstName.value = user?.first_name || "";
  elements.lastName.value = user?.last_name || "";
  elements.userNote.value = user?.note || "";
  elements.userIsAdmin.checked = Boolean(user?.is_admin);
  elements.userActive.checked = user ? user.active : true;
  elements.userActive.disabled = !user;
  elements.userMessage.textContent = "";
  elements.deleteUserSection.hidden = !user;
  elements.deleteUserButton.disabled = user?.id === model.session?.user_id;
  elements.deleteUserButton.title =
    user?.id === model.session?.user_id
      ? "Der aktuell angemeldete Admin kann sich nicht selbst löschen."
      : "";
  elements.passwordSection.hidden = !user?.is_admin;
  elements.cardsSection.hidden = !user;
  elements.passwordState.textContent = user?.has_password
    ? "Ein persönliches Passwort ist gesetzt."
    : "Noch kein persönliches Passwort gesetzt.";
  elements.resetPassword.value = "";
  elements.userSheet.hidden = false;
  if (user) await loadCards();
}

function closeUser() {
  elements.userSheet.hidden = true;
  elements.userMessage.textContent = "";
}

async function saveUser(event) {
  event.preventDefault();
  const userId = Number(elements.userId.value) || null;
  const payload = {
    first_name: elements.firstName.value.trim(),
    last_name: elements.lastName.value.trim() || null,
    note: elements.userNote.value.trim() || null,
    is_admin: elements.userIsAdmin.checked,
  };
  if (userId !== null) payload.active = elements.userActive.checked;
  try {
    const saved = await api(
      userId === null ? "/api/web-admin/users" : `/api/web-admin/users/${userId}`,
      {
        method: userId === null ? "POST" : "PATCH",
        body: JSON.stringify(payload),
      },
    );
    await loadWorkspace();
    model.selectedUserId = saved.id;
    await openUser(saved.id);
    elements.userMessage.textContent = "Gespeichert.";
    showToast(userId === null ? "Benutzer angelegt." : "Änderungen gespeichert.");
  } catch (error) {
    elements.userMessage.textContent = error.message;
    elements.userMessage.classList.add("error");
  }
}

async function loadCards() {
  const user = selectedUser();
  if (!user) return;
  try {
    model.cards = await api(`/api/web-admin/users/${user.id}/nfc-cards`);
    renderCards();
  } catch (error) {
    elements.userMessage.textContent = error.message;
  }
}

async function deleteUser() {
  const user = selectedUser();
  if (!user || user.id === model.session?.user_id) return;
  const confirmed = window.confirm(
    `${user.display_name} wirklich löschen?\n\n`
      + "Armbandzuordnungen und Zugänge werden entfernt. "
      + "Vorhandene Buchungen bleiben erhalten.",
  );
  if (!confirmed) return;
  try {
    await api(`/api/web-admin/users/${user.id}`, { method: "DELETE" });
    closeUser();
    model.selectedUserId = null;
    await loadWorkspace();
    showToast("Benutzer gelöscht. Vorhandene Buchungen bleiben erhalten.");
  } catch (error) {
    showToast(error.message, true);
  }
}

function renderCards() {
  elements.cardList.replaceChildren();
  if (!model.cards.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "Noch kein Armband zugewiesen.";
    elements.cardList.append(empty);
    return;
  }
  for (const card of model.cards) {
    const row = document.createElement("div");
    row.className = "nfc-card";
    const label = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = `Armband ${card.uid_hint}`;
    const status = document.createElement("small");
    status.textContent = card.active ? "aktiv" : "gesperrt";
    label.append(strong, status);
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = `button button-small ${card.active ? "button-danger" : "button-secondary"}`;
    toggle.textContent = card.active ? "Sperren" : "Aktivieren";
    toggle.addEventListener("click", () => setCardActive(card.id, !card.active));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "button button-small button-quiet";
    remove.textContent = "Löschen";
    remove.addEventListener("click", () => removeCard(card.id));
    row.append(label, toggle, remove);
    elements.cardList.append(row);
  }
}

async function setCardActive(cardId, active) {
  try {
    await api(`/api/web-admin/nfc-cards/${cardId}`, {
      method: "PATCH",
      body: JSON.stringify({ active }),
    });
    await loadCards();
    await loadWorkspace();
    showToast(active ? "Armband aktiviert." : "Armband gesperrt.");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function removeCard(cardId) {
  if (!window.confirm("Diese Armbandzuordnung wirklich löschen?")) return;
  try {
    await api(`/api/web-admin/nfc-cards/${cardId}`, { method: "DELETE" });
    await loadCards();
    await loadWorkspace();
    showToast("Armbandzuordnung gelöscht.");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function resetPassword(event) {
  event.preventDefault();
  const user = selectedUser();
  if (!user) return;
  try {
    await api(`/api/web-admin/users/${user.id}/password`, {
      method: "PUT",
      body: JSON.stringify({ new_password: elements.resetPassword.value }),
    });
    elements.resetPassword.value = "";
    await loadWorkspace();
    await openUser(user.id);
    showToast("Adminpasswort gesetzt. Bestehende Sitzungen wurden beendet.");
  } catch (error) {
    showToast(error.message, true);
  }
}

function beginCapture() {
  if (!selectedUser() || model.captureActive) return;
  model.captureActive = true;
  elements.captureDialog.hidden = false;
  elements.captureInstruction.textContent = "NFC-Leser wird vorbereitet …";
  pollCapture();
}

async function pollCapture() {
  const user = selectedUser();
  if (!model.captureActive || !user) return;
  try {
    const result = await api(
      `/api/web-admin/users/${user.id}/nfc-cards/capture`,
      { method: "POST" },
    );
    const instructions = {
      remove_card: "Vorhandenes Armband vom Leser entfernen.",
      waiting: "Neues Veranstaltungsarmband kurz auflegen.",
      reader_unavailable: "NFC-Leser ist momentan nicht verfügbar.",
      assigned: "Armband wurde erfolgreich zugewiesen.",
      timed_out: "Zeit abgelaufen. Bitte erneut starten.",
    };
    elements.captureInstruction.textContent = instructions[result.state] || result.state;
    if (result.state === "assigned") {
      model.captureActive = false;
      await loadCards();
      await loadWorkspace();
      model.captureTimer = window.setTimeout(() => {
        elements.captureDialog.hidden = true;
      }, 700);
      return;
    }
    if (result.state === "timed_out") {
      model.captureActive = false;
      model.captureTimer = window.setTimeout(() => {
        elements.captureDialog.hidden = true;
      }, 1200);
      return;
    }
  } catch (error) {
    elements.captureInstruction.textContent = error.message;
    model.captureActive = false;
    return;
  }
  model.captureTimer = window.setTimeout(pollCapture, 500);
}

function stopCapture(notifyBackend = true) {
  model.captureActive = false;
  if (model.captureTimer !== null) window.clearTimeout(model.captureTimer);
  model.captureTimer = null;
  elements.captureDialog.hidden = true;
  if (notifyBackend && model.session) {
    api("/api/web-admin/nfc-capture", { method: "DELETE" }).catch(() => {});
  }
}

function formatLiters(volumeMl) {
  return (volumeMl / 1000).toLocaleString("de-DE", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  });
}

function formatEuros(amountCents) {
  return (amountCents / 100).toLocaleString("de-DE", {
    style: "currency",
    currency: "EUR",
  });
}

function formatDateTime(value) {
  if (!value) return "–";
  return new Intl.DateTimeFormat("de-DE", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function recordRow(title, detail, buttonLabel, onClick, inactive = false) {
  const row = document.createElement("article");
  row.className = "record-row";
  row.classList.toggle("is-inactive", inactive);
  const text = document.createElement("div");
  const strong = document.createElement("strong");
  strong.textContent = title;
  const small = document.createElement("small");
  small.textContent = detail;
  text.append(strong, small);
  row.append(text);
  if (buttonLabel) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "button button-quiet button-small";
    button.textContent = buttonLabel;
    button.addEventListener("click", onClick);
    row.append(button);
  }
  return row;
}

function renderSettings() {
  renderEvents();
  renderBeverages();
}

function renderReportingOptions() {
  const selectedEventId = Number(elements.reportEvent.value);
  elements.reportEvent.replaceChildren(new Option("Veranstaltung wählen", ""));
  for (const event of model.events) {
    elements.reportEvent.add(new Option(`${event.name} (${event.year})`, String(event.id)));
  }
  const activeEvent = model.events.find((event) => event.active);
  elements.reportEvent.value = String(
    model.events.some((event) => event.id === selectedEventId)
      ? selectedEventId
      : activeEvent?.id || model.events[0]?.id || "",
  );

  const selectedUserId = elements.bookingUserFilter.value;
  elements.bookingUserFilter.replaceChildren(new Option("Alle Benutzer", ""));
  for (const user of model.users) {
    elements.bookingUserFilter.add(new Option(user.display_name, String(user.id)));
  }
  elements.bookingUserFilter.value = selectedUserId;

  const selectedKegId = elements.bookingKegFilter.value;
  elements.bookingKegFilter.replaceChildren(new Option("Alle Fässer", ""));
  const eventId = Number(elements.reportEvent.value);
  for (const keg of model.kegs.filter((item) => item.event_id === eventId)) {
    elements.bookingKegFilter.add(
      new Option(
        `#${keg.id} · ${keg.beverage_name} · ${formatDateTime(keg.opened_at)}`,
        String(keg.id),
      ),
    );
  }
  elements.bookingKegFilter.value = selectedKegId;
}

function dateFilterValue(input) {
  return input.value ? new Date(input.value).toISOString() : "";
}

async function loadReporting() {
  const eventId = Number(elements.reportEvent.value);
  if (!eventId) {
    model.statistics = null;
    model.bookings = [];
    model.auditEntries = [];
    model.technicalEvents = [];
    renderReporting();
    return;
  }
  const params = new URLSearchParams({ event_id: String(eventId), limit: "100" });
  const optionalFilters = {
    user_id: elements.bookingUserFilter.value,
    keg_id: elements.bookingKegFilter.value,
    kind: elements.bookingKindFilter.value,
    completion: elements.bookingCompletionFilter.value,
    occurred_from: dateFilterValue(elements.bookingFromFilter),
    occurred_to: dateFilterValue(elements.bookingToFilter),
  };
  for (const [key, value] of Object.entries(optionalFilters)) {
    if (value) params.set(key, value);
  }
  try {
    const [statistics, bookings, auditEntries, technicalEvents] = await Promise.all([
      api(`/api/web-admin/statistics?event_id=${eventId}`),
      api(`/api/web-admin/booking-sessions?${params.toString()}`),
      api("/api/web-admin/audit?limit=50"),
      api("/api/web-admin/technical-events?limit=50"),
    ]);
    model.statistics = statistics;
    model.bookings = bookings;
    model.auditEntries = auditEntries;
    model.technicalEvents = technicalEvents;
    renderReporting();
  } catch (error) {
    showToast(error.message, true);
  }
}

function dataRow(title, detail, badges = []) {
  const row = recordRow(title, detail);
  if (badges.length) {
    const meta = document.createElement("div");
    meta.className = "record-meta";
    for (const item of badges) meta.append(badge(item.text, item.className || ""));
    row.firstElementChild.append(meta);
  }
  return row;
}

function compactJson(value) {
  if (value === null || value === undefined) return "keine Werte";
  const text = JSON.stringify(value);
  return text.length > 160 ? `${text.slice(0, 157)}…` : text;
}

function renderReporting() {
  const statistics = model.statistics;
  elements.reportBookingCount.textContent = statistics
    ? String(statistics.booking_count)
    : "–";
  elements.reportVolume.textContent = statistics
    ? formatLiters(statistics.chargeable_volume_ml)
    : "–";
  elements.reportAmount.textContent = statistics
    ? formatEuros(statistics.amount_cents)
    : "–";
  elements.reportMaintenance.textContent = statistics
    ? formatLiters(statistics.maintenance_volume_ml)
    : "–";

  elements.billingUserList.replaceChildren();
  if (!statistics?.users.length) {
    elements.billingUserList.append(
      recordRow("Noch keine kostenpflichtigen Buchungen", "Für diese Veranstaltung."),
    );
  } else {
    for (const summary of statistics.users) {
      elements.billingUserList.append(
        dataRow(
          summary.user_display_name,
          `${summary.booking_count} Buchungen · `
            + `${formatLiters(summary.measured_volume_ml)} L`,
          [{ text: formatEuros(summary.amount_cents), className: "admin" }],
        ),
      );
    }
  }

  elements.bookingResultCount.textContent =
    `${model.bookings.length} Buchungen angezeigt`;
  elements.bookingList.replaceChildren();
  if (!model.bookings.length) {
    elements.bookingList.append(recordRow("Keine Buchungen", "Filter gegebenenfalls ändern."));
  }
  const kindLabels = {
    manual: "Manuell",
    portion: "Portion",
    top_up: "Nachfüllen",
    maintenance: "Wartung",
    free_admin: "Adminfrei",
  };
  const completionLabels = {
    target_reached: "Ziel erreicht",
    released: "Losgelassen",
    limit_reached: "Zeitlimit",
    user_abort: "Abgebrochen",
    fault: "Fehler",
    shutdown: "Shutdown",
  };
  for (const booking of model.bookings) {
    const timeRange = booking.started_at === booking.ended_at
      ? formatDateTime(booking.started_at)
      : `${formatDateTime(booking.started_at)} bis ${formatDateTime(booking.ended_at)}`;
    const beverages = booking.beverage_names.join(", ");
    const kegs = booking.keg_ids.map((kegId) => `#${kegId}`).join(", ");
    elements.bookingList.append(
      dataRow(
        `${booking.user_display_name} · ${formatLiters(booking.measured_volume_ml)} L`,
        `${timeRange}\n${booking.pour_count} Zapfung${booking.pour_count === 1 ? "" : "en"}`
          + ` · ${beverages} · Fass ${kegs}`,
        [
          {
            text: booking.kinds.map((kind) => kindLabels[kind] || kind).join(", "),
          },
          {
            text: booking.completions
              .map((completion) => completionLabels[completion] || completion)
              .join(", "),
          },
          {
            text: booking.chargeable ? formatEuros(booking.amount_cents) : "kostenfrei",
            className: booking.chargeable ? "admin" : "",
          },
        ],
      ),
    );
  }

  elements.auditList.replaceChildren();
  if (!model.auditEntries.length) {
    elements.auditList.append(recordRow("Keine Auditaktionen", "Noch keine Einträge."));
  }
  for (const entry of model.auditEntries) {
    const values = entry.new_values ?? entry.old_values;
    elements.auditList.append(
      dataRow(
        entry.action,
        `${formatDateTime(entry.occurred_at)} · ${entry.admin_display_name}\n`
          + `${entry.entity_type}${entry.entity_id ? ` #${entry.entity_id}` : ""}\n`
          + compactJson(values),
      ),
    );
  }

  elements.technicalEventList.replaceChildren();
  if (!model.technicalEvents.length) {
    elements.technicalEventList.append(
      recordRow("Keine technischen Ereignisse", "Derzeit liegen keine Einträge vor."),
    );
  }
  for (const entry of model.technicalEvents) {
    elements.technicalEventList.append(
      dataRow(
        entry.message,
        `${formatDateTime(entry.occurred_at)}\n${entry.event_type}`,
        [{ text: entry.severity, className: entry.severity.toLowerCase() }],
      ),
    );
  }
}

function renderEvents() {
  elements.eventList.replaceChildren();
  if (!model.events.length) {
    elements.eventList.append(recordRow("Noch keine Veranstaltung", "Bitte zuerst anlegen."));
  }
  for (const event of model.events) {
    const state = event.active ? "aktiv" : "inaktiv";
    elements.eventList.append(
      recordRow(
        event.name,
        `${event.year} · ${state}`,
        "Bearbeiten",
        () => editEvent(event.id),
        !event.active,
      ),
    );
  }
}

function resetEventForm() {
  elements.eventForm.reset();
  elements.eventId.value = "";
  elements.eventYear.value = String(new Date().getFullYear());
  elements.eventActive.checked = model.events.length === 0;
}

function editEvent(eventId) {
  const event = model.events.find((item) => item.id === eventId);
  if (!event) return;
  elements.eventId.value = String(event.id);
  elements.eventName.value = event.name;
  elements.eventYear.value = String(event.year);
  elements.eventActive.checked = event.active;
  elements.eventName.focus();
}

async function saveEvent(event) {
  event.preventDefault();
  const eventId = Number(elements.eventId.value) || null;
  const existing = model.events.find((item) => item.id === eventId);
  const payload = {
    name: elements.eventName.value.trim(),
    year: Number(elements.eventYear.value),
    starts_at: existing?.starts_at || null,
    ends_at: existing?.ends_at || null,
    active: elements.eventActive.checked,
  };
  try {
    await api(
      eventId === null ? "/api/web-admin/events" : `/api/web-admin/events/${eventId}`,
      {
        method: eventId === null ? "POST" : "PATCH",
        body: JSON.stringify(payload),
      },
    );
    await loadWorkspace();
    resetEventForm();
    showToast(eventId === null ? "Veranstaltung angelegt." : "Veranstaltung gespeichert.");
  } catch (error) {
    showToast(error.message, true);
  }
}

function renderBeverages() {
  elements.beverageList.replaceChildren();
  if (!model.beverages.length) {
    elements.beverageList.append(recordRow("Noch kein Getränk", "Bitte zuerst anlegen."));
  }
  for (const beverage of model.beverages) {
    elements.beverageList.append(
      recordRow(
        beverage.name,
        `${formatLiters(beverage.default_keg_size_ml)} L · `
          + `${formatEuros(beverage.price_per_liter_cents)} / L`,
        "Bearbeiten",
        () => editBeverage(beverage.id),
        !beverage.active,
      ),
    );
  }
  const currentId = Number(elements.kegBeverage.value);
  elements.kegBeverage.replaceChildren(new Option("Getränk wählen", ""));
  for (const beverage of model.beverages.filter((item) => item.active)) {
    elements.kegBeverage.add(new Option(beverage.name, String(beverage.id)));
  }
  if (model.beverages.some((beverage) => beverage.id === currentId && beverage.active)) {
    elements.kegBeverage.value = String(currentId);
  }
  applyBeverageDefaultVolume();
}

function resetBeverageForm() {
  elements.beverageForm.reset();
  elements.beverageId.value = "";
  elements.beverageActive.checked = true;
}

function editBeverage(beverageId) {
  const beverage = model.beverages.find((item) => item.id === beverageId);
  if (!beverage) return;
  elements.beverageId.value = String(beverage.id);
  elements.beverageName.value = beverage.name;
  elements.beverageKegLiters.value = String(beverage.default_keg_size_ml / 1000);
  elements.beveragePriceEuros.value = (beverage.price_per_liter_cents / 100).toFixed(2);
  elements.beverageActive.checked = beverage.active;
  elements.beverageName.focus();
}

async function saveBeverage(event) {
  event.preventDefault();
  const beverageId = Number(elements.beverageId.value) || null;
  const payload = {
    name: elements.beverageName.value.trim(),
    default_keg_size_ml: Math.round(Number(elements.beverageKegLiters.value) * 1000),
    price_per_liter_cents: Math.round(Number(elements.beveragePriceEuros.value) * 100),
  };
  if (beverageId !== null) payload.active = elements.beverageActive.checked;
  try {
    await api(
      beverageId === null
        ? "/api/web-admin/beverages"
        : `/api/web-admin/beverages/${beverageId}`,
      {
        method: beverageId === null ? "POST" : "PATCH",
        body: JSON.stringify(payload),
      },
    );
    await loadWorkspace();
    resetBeverageForm();
    showToast(beverageId === null ? "Getränk angelegt." : "Getränk gespeichert.");
  } catch (error) {
    showToast(error.message, true);
  }
}

function renderKegs() {
  elements.kegList.replaceChildren();
  const activeKeg = model.kegs.find((keg) => keg.active);
  elements.operationsActiveKeg.textContent = activeKeg
    ? activeKeg.beverage_name
    : "Kein aktives Fass";
  elements.operationsActiveKegDetail.textContent = activeKeg
    ? `${formatLiters(activeKeg.remaining_volume_ml)} von `
      + `${formatLiters(activeKeg.initial_volume_ml)} L rechnerisch übrig`
    : "Vor dem Zapfen ein Fass aktivieren.";
  elements.kegDetachButton.disabled = !activeKeg;
  if (!model.kegs.length) {
    elements.kegList.append(recordRow("Noch keine Fasshistorie", "Der erste Wechsel legt sie an."));
  }
  for (const keg of model.kegs.slice(0, 12)) {
    elements.kegList.append(
      recordRow(
        `${keg.beverage_name} · ${formatLiters(keg.initial_volume_ml)} L`,
        `${keg.active ? "AKTIV · " : ""}${keg.event_name} · `
          + `geöffnet ${formatDateTime(keg.opened_at)} · `
          + `${formatLiters(keg.remaining_volume_ml)} L übrig`,
        "",
        () => {},
        !keg.active,
      ),
    );
  }
}

function applyBeverageDefaultVolume() {
  const beverageId = Number(elements.kegBeverage.value);
  const beverage = model.beverages.find((item) => item.id === beverageId);
  if (beverage) {
    const liters = formatLiters(beverage.default_keg_size_ml);
    elements.kegVolumeLiters.placeholder = `${liters} L (voll)`;
    elements.kegVolumeHint.textContent =
      `Leer lassen für ein volles Standardfass mit ${liters} L.`;
  } else {
    elements.kegVolumeLiters.placeholder = "Standardfass voll";
    elements.kegVolumeHint.textContent = "Leer lassen für den Standardfüllstand.";
  }
}

async function switchKeg(event) {
  event.preventDefault();
  const activeKeg = model.kegs.find((keg) => keg.active);
  const beverage = model.beverages.find(
    (item) => item.id === Number(elements.kegBeverage.value),
  );
  const confirmation = activeKeg
    ? `${activeKeg.beverage_name} abzapfen und ${beverage?.name || "das neue Fass"} anzapfen? `
      + "Ein rechnerischer Restbestand wird nicht übertragen."
    : `${beverage?.name || "Dieses Fass"} jetzt anzapfen?`;
  if (!window.confirm(confirmation)) return;
  try {
    await api("/api/web-admin/kegs/switch", {
      method: "POST",
      body: JSON.stringify({
        beverage_id: Number(elements.kegBeverage.value),
        initial_volume_ml: elements.kegVolumeLiters.value
          ? Math.round(Number(elements.kegVolumeLiters.value) * 1000)
          : null,
      }),
    });
    await loadWorkspace();
    elements.kegVolumeLiters.value = "";
    showToast("Fass ist angezapft und aktiv.");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function detachKeg() {
  const activeKeg = model.kegs.find((keg) => keg.active);
  if (!activeKeg) return;
  if (
    !window.confirm(
      `${activeKeg.beverage_name} wirklich abzapfen? Danach ist kein Getränk aktiv.`,
    )
  ) return;
  try {
    await api("/api/web-admin/kegs/detach", { method: "POST" });
    await loadWorkspace();
    showToast("Fass wurde abgezapft. Der Hahn ist jetzt ohne aktives Getränk.");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function changeOwnPassword(event) {
  event.preventDefault();
  elements.accountMessage.classList.remove("error");
  if (elements.newOwnPassword.value !== elements.confirmOwnPassword.value) {
    elements.accountMessage.textContent = "Die neuen Passwörter stimmen nicht überein.";
    elements.accountMessage.classList.add("error");
    return;
  }
  try {
    await api("/api/web-auth/password", {
      method: "POST",
      body: JSON.stringify({
        current_password: elements.currentPassword.value,
        new_password: elements.newOwnPassword.value,
      }),
    });
    showToast("Passwort geändert. Bitte erneut anmelden.");
    elements.ownPasswordForm.reset();
    showLogin();
  } catch (error) {
    elements.accountMessage.textContent = error.message;
    elements.accountMessage.classList.add("error");
  }
}

async function initialize() {
  try {
    model.session = await api("/api/web-auth/session");
    showApp();
    await loadWorkspace();
    resetEventForm();
    resetBeverageForm();
  } catch (_error) {
    showLogin();
  }
}

elements.loginForm.addEventListener("submit", login);
document.querySelector("#logout-button").addEventListener("click", logout);
document.querySelector("#new-user-button").addEventListener("click", () => openUser());
document.querySelector("#close-user-sheet").addEventListener("click", closeUser);
elements.userForm.addEventListener("submit", saveUser);
elements.deleteUserButton.addEventListener("click", deleteUser);
elements.resetPasswordForm.addEventListener("submit", resetPassword);
elements.userSearch.addEventListener("input", renderUsers);
elements.userFilter.addEventListener("change", renderUsers);
elements.eventForm.addEventListener("submit", saveEvent);
document.querySelector("#reset-event-button").addEventListener("click", resetEventForm);
elements.beverageForm.addEventListener("submit", saveBeverage);
document.querySelector("#reset-beverage-button").addEventListener("click", resetBeverageForm);
elements.kegBeverage.addEventListener("change", applyBeverageDefaultVolume);
elements.kegSwitchForm.addEventListener("submit", switchKeg);
elements.kegDetachButton.addEventListener("click", detachKeg);
elements.reportEvent.addEventListener("change", () => {
  renderReportingOptions();
  loadReporting();
});
elements.bookingFilterForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loadReporting();
});
document.querySelector("#refresh-reporting-button").addEventListener("click", loadReporting);
document.querySelector("#capture-card-button").addEventListener("click", beginCapture);
document.querySelector("#cancel-capture-button").addEventListener("click", () => stopCapture());
elements.ownPasswordForm.addEventListener("submit", changeOwnPassword);
for (const button of elements.navButtons) {
  button.addEventListener("click", () => showView(button.dataset.navView));
}
for (const button of document.querySelectorAll("[data-open-view]")) {
  button.addEventListener("click", () => showView(button.dataset.openView));
}
elements.userSheet.addEventListener("click", (event) => {
  if (event.target === elements.userSheet) closeUser();
});
window.addEventListener("pagehide", () => stopCapture());

initialize();
