#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Bitte als root ausfuehren: sudo $0 <desktop-benutzer>" >&2
  exit 1
fi

kiosk_user="${1:-}"
if [[ -z "${kiosk_user}" ]] || ! id "${kiosk_user}" >/dev/null 2>&1; then
  echo "Aufruf: sudo $0 <desktop-benutzer>" >&2
  echo "Der Desktop-Benutzer muss bereits existieren." >&2
  exit 1
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
app_dir="$(cd -- "${script_dir}/.." && pwd)"
model="$(tr -d '\0' </proc/device-tree/model 2>/dev/null || true)"

echo "Installiere Zunder Zapfe aus ${app_dir}"
echo "Zielsystem: ${model:-unbekannt}"

apt-get update
apt-get install --yes \
  python3-venv python3-dev build-essential \
  chromium curl \
  pcscd libccid libpcsclite-dev pcsc-tools swig \
  network-manager iw nginx-light

install -d -o "${kiosk_user}" -g "${kiosk_user}" /var/lib/zunder-zapfe /var/log/zunder-zapfe
install -d -m 0755 /etc/zunder-zapfe

if [[ ! -f /etc/zunder-zapfe/web.env ]]; then
  install -m 0644 "${app_dir}/config/web.env.example" /etc/zunder-zapfe/web.env
fi

# Repository-local Python files must remain writable by the checkout owner.
# Older installer versions created the venv and egg-info as root; repair only
# those generated paths before installing as the service user.
if [[ -d "${app_dir}/.venv" ]]; then
  chown -R "${kiosk_user}:${kiosk_user}" "${app_dir}/.venv"
fi
if [[ -d "${app_dir}/src/zunder_zapfe.egg-info" ]]; then
  chown -R "${kiosk_user}:${kiosk_user}" "${app_dir}/src/zunder_zapfe.egg-info"
fi

runuser -u "${kiosk_user}" -- python3 -m venv "${app_dir}/.venv"
runuser -u "${kiosk_user}" -- \
  "${app_dir}/.venv/bin/python" -m pip install --upgrade pip
runuser -u "${kiosk_user}" -- \
  "${app_dir}/.venv/bin/python" -m pip install --editable "${app_dir}[dev,debug]"

sed -e "s|@@APP_DIR@@|${app_dir}|g" \
  -e "s|@@SERVICE_USER@@|${kiosk_user}|g" \
  "${app_dir}/deploy/systemd/zunder-zapfe-web.service.in" \
  >/etc/systemd/system/zunder-zapfe-web.service

install -m 0755 "${app_dir}/deploy/kiosk/zunder-zapfe-kiosk" \
  /usr/local/bin/zunder-zapfe-kiosk
install -m 0755 "${app_dir}/scripts/install-admin-wifi.sh" \
  /usr/local/sbin/zunder-zapfe-admin-wifi
install -d -m 0755 /usr/local/share/zunder-zapfe
install -m 0644 "${app_dir}/deploy/nginx/zunder-zapfe-admin.conf" \
  /usr/local/share/zunder-zapfe/zunder-zapfe-admin.conf

kiosk_home="$(getent passwd "${kiosk_user}" | cut -d: -f6)"
autostart_dir="${kiosk_home}/.config/labwc"
autostart_file="${autostart_dir}/autostart"
install -d -o "${kiosk_user}" -g "${kiosk_user}" "${autostart_dir}"
touch "${autostart_file}"

autostart_command="/usr/local/bin/zunder-zapfe-kiosk &"
if ! grep --fixed-strings --quiet "${autostart_command}" "${autostart_file}"; then
  printf '\n# Zunder Zapfe kiosk\n%s\n' "${autostart_command}" >>"${autostart_file}"
fi
chown "${kiosk_user}:${kiosk_user}" "${autostart_file}"

systemctl daemon-reload
systemctl enable --now zunder-zapfe-web.service

echo
echo "Installation abgeschlossen."
echo "Backend: http://127.0.0.1:8000"
echo "Pruefung: ${app_dir}/scripts/pi-verify.sh"
echo "Admin-WLAN einmalig und bewusst: sudo zunder-zapfe-admin-wifi"
echo "Kioskstart erfolgt bei der naechsten grafischen Anmeldung oder nach einem Neustart."
