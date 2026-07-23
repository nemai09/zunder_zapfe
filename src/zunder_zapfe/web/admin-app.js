"use strict";

const model = {
  session: null,
  users: [],
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
  passwordSection: document.querySelector("#password-section"),
  passwordState: document.querySelector("#password-state"),
  resetPasswordForm: document.querySelector("#reset-password-form"),
  resetPassword: document.querySelector("#reset-password"),
  cardsSection: document.querySelector("#cards-section"),
  cardList: document.querySelector("#card-list"),
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
    const [users, health] = await Promise.all([
      api("/api/web-admin/users"),
      api("/api/health"),
    ]);
    model.users = users;
    elements.backendStatus.textContent = "Bereit";
    elements.buildVersion.textContent = health.build;
    renderUsers();
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
  } catch (_error) {
    showLogin();
  }
}

elements.loginForm.addEventListener("submit", login);
document.querySelector("#logout-button").addEventListener("click", logout);
document.querySelector("#new-user-button").addEventListener("click", () => openUser());
document.querySelector("#close-user-sheet").addEventListener("click", closeUser);
elements.userForm.addEventListener("submit", saveUser);
elements.resetPasswordForm.addEventListener("submit", resetPassword);
elements.userSearch.addEventListener("input", renderUsers);
elements.userFilter.addEventListener("change", renderUsers);
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
