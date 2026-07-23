#!/usr/bin/env bash
set -euo pipefail

profile_name="zunder-zapfe-ap"
profile_path="/etc/NetworkManager/system-connections/${profile_name}.nmconnection"
wifi_interface="wlan0"
wifi_ssid="ZUNDER_ZAPFE"
wifi_address="10.42.0.1/24"
marker_path="/etc/zunder-zapfe/admin-wifi.configured"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Bitte als root ausfuehren: sudo $0" >&2
  exit 1
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
app_dir="$(cd -- "${script_dir}/.." && pwd)"
repository_nginx_source="${app_dir}/deploy/nginx/zunder-zapfe-admin.conf"
installed_nginx_source="/usr/local/share/zunder-zapfe/zunder-zapfe-admin.conf"
nginx_available="/etc/nginx/sites-available/zunder-zapfe-admin"
nginx_enabled="/etc/nginx/sites-enabled/zunder-zapfe-admin"

if [[ -f "${repository_nginx_source}" ]]; then
  nginx_source="${repository_nginx_source}"
elif [[ -f "${installed_nginx_source}" ]]; then
  nginx_source="${installed_nginx_source}"
else
  echo "Die nginx-Konfiguration wurde nicht gefunden." >&2
  echo "Bitte zuerst install-pi.sh ausfuehren." >&2
  exit 1
fi

for command_name in nmcli iw nginx curl; do
  command -v "${command_name}" >/dev/null 2>&1 || {
    echo "Fehlendes Werkzeug: ${command_name}. Zuerst install-pi.sh ausfuehren." >&2
    exit 1
  }
done

systemctl is-active --quiet NetworkManager || {
  echo "NetworkManager ist nicht aktiv." >&2
  exit 1
}

nmcli -g GENERAL.TYPE device show "${wifi_interface}" 2>/dev/null \
  | grep --fixed-strings --quiet "wifi" || {
  echo "${wifi_interface} ist kein verfuegbares WLAN-Geraet." >&2
  exit 1
}

nmcli -g WIFI-PROPERTIES.AP device show "${wifi_interface}" 2>/dev/null \
  | grep --ignore-case --extended-regexp --quiet "^(yes|ja)$" || {
  echo "${wifi_interface} meldet keine Access-Point-Unterstuetzung." >&2
  exit 1
}

wifi_country="$(
  iw reg get \
    | sed -n 's/^[[:space:]]*country \([A-Z][A-Z]\):.*/\1/p' \
    | grep --invert-match --fixed-strings "00" \
    | head -n 1
)"
if [[ -z "${wifi_country}" ]]; then
  echo "Das WLAN-Land ist nicht gesetzt." >&2
  echo "Bitte zuerst beispielsweise 'sudo raspi-config nonint do_wifi_country DE' ausfuehren." >&2
  exit 1
fi

active_connection="$(
  nmcli -g GENERAL.CONNECTION device show "${wifi_interface}" 2>/dev/null || true
)"
if [[ -n "${active_connection}" ]] \
  && [[ "${active_connection}" != "--" ]] \
  && [[ "${active_connection}" != "${profile_name}" ]]; then
  echo
  echo "WARNUNG: ${wifi_interface} verwendet aktuell '${active_connection}'."
  echo "Die Aktivierung von ${wifi_ssid} trennt diese WLAN-Verbindung und kann SSH beenden."
  if [[ ! -t 0 ]]; then
    echo "Abbruch: Bestaetigung erfordert ein interaktives Terminal." >&2
    exit 1
  fi
  read -r -p "Zum Fortfahren exakt ZUNDER_ZAPFE eingeben: " confirmation
  [[ "${confirmation}" == "ZUNDER_ZAPFE" ]] || {
    echo "Abgebrochen."
    exit 1
  }
fi

if nmcli --terse --fields NAME connection show \
  | grep --fixed-strings --line-regexp --quiet "${profile_name}"; then
  echo "Vorhandenes Profil ${profile_name} wird ohne Schluesselaenderung aktualisiert."
else
  [[ -t 0 ]] || {
    echo "Die erstmalige Einrichtung erfordert ein interaktives Terminal." >&2
    exit 1
  }
  read -r -s -p "Neuer WPA-Schluessel fuer ${wifi_ssid}: " wifi_psk
  echo
  read -r -s -p "WPA-Schluessel wiederholen: " wifi_psk_confirmation
  echo
  [[ "${wifi_psk}" == "${wifi_psk_confirmation}" ]] || {
    echo "Die WPA-Schluessel stimmen nicht ueberein." >&2
    exit 1
  }
  if (( ${#wifi_psk} < 12 || ${#wifi_psk} > 63 )) \
    || [[ ! "${wifi_psk}" =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "Der WPA-Schluessel muss 12 bis 63 Zeichen aus A-Z, a-z, 0-9, Punkt," >&2
    echo "Unterstrich oder Bindestrich enthalten." >&2
    exit 1
  fi

  profile_uuid="$(tr -d '\n' </proc/sys/kernel/random/uuid)"
  temporary_profile="$(mktemp)"
  trap 'rm -f -- "${temporary_profile:-}"' EXIT
  chmod 0600 "${temporary_profile}"
  {
    printf '%s\n' \
      "[connection]" \
      "id=${profile_name}" \
      "uuid=${profile_uuid}" \
      "type=wifi" \
      "interface-name=${wifi_interface}" \
      "autoconnect=true" \
      "autoconnect-priority=100" \
      "" \
      "[wifi]" \
      "band=bg" \
      "mode=ap" \
      "ssid=${wifi_ssid}" \
      "" \
      "[wifi-security]" \
      "key-mgmt=wpa-psk" \
      "proto=rsn;" \
      "psk=${wifi_psk}" \
      "" \
      "[ipv4]" \
      "address1=${wifi_address}" \
      "method=shared" \
      "never-default=true" \
      "" \
      "[ipv6]" \
      "method=disabled"
  } >"${temporary_profile}"
  install -m 0600 "${temporary_profile}" "${profile_path}"
  nmcli connection load "${profile_path}" >/dev/null
  unset wifi_psk wifi_psk_confirmation
fi

nmcli connection modify "${profile_name}" \
  connection.interface-name "${wifi_interface}" \
  connection.autoconnect yes \
  connection.autoconnect-priority 100 \
  802-11-wireless.mode ap \
  802-11-wireless.ssid "${wifi_ssid}" \
  802-11-wireless.band bg \
  802-11-wireless-security.key-mgmt wpa-psk \
  802-11-wireless-security.proto rsn \
  ipv4.method shared \
  ipv4.addresses "${wifi_address}" \
  ipv4.never-default yes \
  ipv6.method disabled

install -m 0644 "${nginx_source}" "${nginx_available}"
ln -sfn "${nginx_available}" "${nginx_enabled}"
if [[ -L /etc/nginx/sites-enabled/default ]]; then
  rm -- /etc/nginx/sites-enabled/default
fi
nginx -t
systemctl enable nginx >/dev/null

echo "Aktiviere ${wifi_ssid} auf ${wifi_interface}."
nmcli connection up "${profile_name}" ifname "${wifi_interface}" >/dev/null
systemctl restart nginx

nmcli --terse --fields NAME connection show --active \
  | grep --fixed-strings --line-regexp --quiet "${profile_name}"
ip -4 address show dev "${wifi_interface}" \
  | grep --fixed-strings --quiet "inet ${wifi_address}"
curl --fail --silent --show-error http://10.42.0.1/api/health >/dev/null

install -d -m 0755 /etc/zunder-zapfe
touch "${marker_path}"
chmod 0644 "${marker_path}"

echo
echo "Admin-WLAN ist eingerichtet."
echo "SSID: ${wifi_ssid}"
echo "Admin-URL: http://10.42.0.1/admin"
echo "Der WPA-Schluessel wurde nicht ausgegeben oder im Repository gespeichert."
