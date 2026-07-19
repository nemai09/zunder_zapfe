#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Bitte als root ausfuehren: sudo $0 [desktop-benutzer]" >&2
  exit 1
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "${script_dir}/.." && pwd)"
repo_user="$(stat -c '%U' "${repo_dir}")"
kiosk_user="${1:-${SUDO_USER:-}}"

if [[ -z "${kiosk_user}" ]] || [[ "${kiosk_user}" == "root" ]] || ! id "${kiosk_user}" >/dev/null 2>&1; then
  echo "Aufruf: sudo $0 <desktop-benutzer>" >&2
  exit 1
fi

git_as_owner() {
  runuser -u "${repo_user}" -- git -C "${repo_dir}" "$@"
}

if [[ -n "$(git_as_owner status --porcelain --untracked-files=no)" ]]; then
  echo "Deployment abgebrochen: Der Checkout enthaelt lokale Aenderungen." >&2
  git_as_owner status --short --untracked-files=no >&2
  exit 1
fi

branch="$(git_as_owner symbolic-ref --quiet --short HEAD)" || {
  echo "Deployment abgebrochen: Der Checkout befindet sich nicht auf einem Branch." >&2
  exit 1
}

old_revision="$(git_as_owner rev-parse HEAD)"
echo "Aktualisiere ${branch} aus origin"
git_as_owner fetch origin "${branch}"
git_as_owner merge --ff-only "origin/${branch}"
new_revision="$(git_as_owner rev-parse HEAD)"

echo "Installiere Commit $(git_as_owner rev-parse --short HEAD)"
needs_full_install=false
if [[ ! -x "${repo_dir}/.venv/bin/python" ]] \
  || ! "${repo_dir}/.venv/bin/python" -c "import smartcard" >/dev/null 2>&1 \
  || ! command -v pcsc_scan >/dev/null 2>&1; then
  needs_full_install=true
elif [[ "${old_revision}" != "${new_revision}" ]] && ! git_as_owner diff --quiet \
  "${old_revision}" "${new_revision}" -- \
  pyproject.toml scripts/install-pi.sh deploy/systemd deploy/kiosk config/web.env.example; then
  needs_full_install=true
fi

if [[ "${needs_full_install}" == true ]]; then
  echo "System- oder Abhaengigkeitsaenderung erkannt: vollstaendige Installation"
  "${repo_dir}/scripts/install-pi.sh" "${kiosk_user}"
else
  echo "Keine Systemabhaengigkeiten geaendert"
fi

echo "Starte Webdienst mit dem neuen Stand neu"
systemctl restart zunder-zapfe-web.service
"${repo_dir}/scripts/pi-verify.sh"

echo "Deployment erfolgreich. Ein Neustart des Raspberry Pi ist nicht erforderlich."
