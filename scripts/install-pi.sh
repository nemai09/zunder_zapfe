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
  chromium curl i2c-tools util-linux-extra \
  pcscd libccid libpcsclite-dev pcsc-tools swig \
  liblgpio-dev \
  network-manager iw nginx-light

install -d -o "${kiosk_user}" -g "${kiosk_user}" /var/lib/zunder-zapfe /var/log/zunder-zapfe
install -d -m 0700 -o "${kiosk_user}" -g "${kiosk_user}" /var/lib/zunder-zapfe/backups
install -d -m 0755 /etc/zunder-zapfe
if getent group gpio >/dev/null 2>&1; then
  usermod -a -G gpio "${kiosk_user}"
fi

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

if command -v raspi-config >/dev/null 2>&1; then
  raspi-config nonint do_i2c 0
fi

boot_config=""
if [[ -f /boot/firmware/config.txt ]]; then
  boot_config="/boot/firmware/config.txt"
elif [[ -f /boot/config.txt ]]; then
  boot_config="/boot/config.txt"
else
  echo "Raspberry-Pi-Bootkonfiguration nicht gefunden." >&2
  exit 1
fi

if ! grep --extended-regexp --quiet \
  '^[[:space:]]*dtparam=i2c_arm=on([[:space:]]|$)' "${boot_config}"; then
  printf '\n[all]\n# Zunder Zapfe I2C\ndtparam=i2c_arm=on\n' >>"${boot_config}"
fi
if ! grep --extended-regexp --quiet \
  '^[[:space:]]*dtoverlay=i2c-rtc,ds3231([[:space:]]|$)' "${boot_config}"; then
  printf '\n[all]\n# Zunder Zapfe DS3231 RTC\ndtoverlay=i2c-rtc,ds3231\n' >>"${boot_config}"
fi

# Apply the overlay immediately when supported. The config.txt entry remains
# authoritative and ensures that the RTC is available after every reboot.
if [[ ! -e /dev/rtc0 ]] && command -v dtoverlay >/dev/null 2>&1; then
  dtoverlay i2c-rtc ds3231 || true
  udevadm settle || true
fi

sed -e "s|@@APP_DIR@@|${app_dir}|g" \
  -e "s|@@SERVICE_USER@@|${kiosk_user}|g" \
  "${app_dir}/deploy/systemd/zunder-zapfe-web.service.in" \
  >/etc/systemd/system/zunder-zapfe-web.service

sed -e "s|@@APP_DIR@@|${app_dir}|g" \
  "${app_dir}/deploy/systemd/zunder-zapfe-rtc.service.in" \
  >/etc/systemd/system/zunder-zapfe-rtc.service

sed -e "s|@@APP_DIR@@|${app_dir}|g" \
  -e "s|@@SERVICE_USER@@|${kiosk_user}|g" \
  "${app_dir}/deploy/systemd/zunder-zapfe-backup.service.in" \
  >/etc/systemd/system/zunder-zapfe-backup.service
install -m 0644 "${app_dir}/deploy/systemd/zunder-zapfe-backup.timer" \
  /etc/systemd/system/zunder-zapfe-backup.timer

ln -sfn "${app_dir}/.venv/bin/zunder-zapfe-rtc" \
  /usr/local/sbin/zunder-zapfe-rtc

install -m 0755 "${app_dir}/deploy/kiosk/zunder-zapfe-kiosk" \
  /usr/local/bin/zunder-zapfe-kiosk
install -m 0755 "${app_dir}/scripts/install-admin-wifi.sh" \
  /usr/local/sbin/zunder-zapfe-admin-wifi
install -m 0755 "${app_dir}/scripts/wifi-mode.sh" \
  /usr/local/sbin/zunder-zapfe-wifi-mode
install -m 0755 "${app_dir}/scripts/system-power.sh" \
  /usr/local/sbin/zunder-zapfe-system-power
install -d -m 0755 /usr/local/share/zunder-zapfe
install -m 0644 "${app_dir}/deploy/nginx/zunder-zapfe-admin.conf" \
  /usr/local/share/zunder-zapfe/zunder-zapfe-admin.conf
install -d -m 0755 /etc/polkit-1/rules.d
sed -e "s|@@SERVICE_USER@@|${kiosk_user}|g" \
  "${app_dir}/deploy/polkit/zunder-zapfe-networkmanager.rules.in" \
  >/etc/polkit-1/rules.d/60-zunder-zapfe-networkmanager.rules
chmod 0644 /etc/polkit-1/rules.d/60-zunder-zapfe-networkmanager.rules
sed -e "s|@@SERVICE_USER@@|${kiosk_user}|g" \
  "${app_dir}/deploy/polkit/zunder-zapfe-power.rules.in" \
  >/etc/polkit-1/rules.d/61-zunder-zapfe-power.rules
chmod 0644 /etc/polkit-1/rules.d/61-zunder-zapfe-power.rules

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
systemctl enable zunder-zapfe-rtc.service
if [[ -e /dev/rtc0 ]] && [[ -f /var/lib/zunder-zapfe/rtc-initialized ]]; then
  rm -f /run/zunder-zapfe-rtc-action-required
  systemctl restart zunder-zapfe-rtc.service
elif [[ -e /dev/rtc0 ]]; then
  touch /run/zunder-zapfe-rtc-action-required
  echo "DS3231 ist noch nicht initialisiert. Jetzt sudo zunder-zapfe-rtc set ausfuehren."
else
  touch /run/zunder-zapfe-rtc-action-required
  echo "DS3231 wird nach dem erforderlichen Neustart als /dev/rtc0 erwartet."
fi
systemctl enable --now zunder-zapfe-web.service
systemctl enable --now zunder-zapfe-backup.timer
if ! systemctl start zunder-zapfe-backup.service; then
  echo "WARNUNG: Erste Datensicherung fehlgeschlagen; der Zapfdienst bleibt aktiv." >&2
fi

echo
echo "Installation abgeschlossen."
echo "Backend: http://127.0.0.1:8000"
echo "RTC: sudo zunder-zapfe-rtc status"
echo "Pruefung: ${app_dir}/scripts/pi-verify.sh"
echo "Admin-WLAN einmalig und bewusst: sudo zunder-zapfe-admin-wifi"
echo "Lokaler WLAN-Moduswechsel: blauer Admin-Button am Kiosk"
echo "Lokale Systemsteuerung: Systemseite im Low-Level-Menue"
echo "Datensicherung: alle 30 Minuten nach /var/lib/zunder-zapfe/backups"
echo "Kioskstart erfolgt bei der naechsten grafischen Anmeldung oder nach einem Neustart."
