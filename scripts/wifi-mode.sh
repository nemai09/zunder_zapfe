#!/usr/bin/env bash
set -euo pipefail

action="${1:-status}"
ap_profile="zunder-zapfe-ap"
wifi_interface="wlan0"

case "${action}" in
  status|ap|client) ;;
  *)
    echo "Aufruf: zunder-zapfe-wifi-mode {status|ap|client}" >&2
    exit 2
    ;;
esac

command -v nmcli >/dev/null 2>&1 || {
  echo "NetworkManager-Werkzeug nmcli ist nicht installiert." >&2
  exit 1
}
nmcli --terse --fields RUNNING general \
  | grep --fixed-strings --line-regexp --quiet "running" || {
  echo "NetworkManager ist nicht aktiv." >&2
  exit 1
}

known_client_profile() {
  local candidate connection_type wifi_mode autoconnect priority
  local selected="" selected_priority=-1000000
  while IFS= read -r candidate; do
    [[ -n "${candidate}" ]] || continue
    [[ "${candidate}" != "${ap_profile}" ]] || continue
    connection_type="$(nmcli -g connection.type connection show id "${candidate}" 2>/dev/null || true)"
    [[ "${connection_type}" == "802-11-wireless" ]] || continue
    wifi_mode="$(nmcli -g 802-11-wireless.mode connection show id "${candidate}" 2>/dev/null || true)"
    [[ "${wifi_mode}" != "ap" ]] || continue
    autoconnect="$(nmcli -g connection.autoconnect connection show id "${candidate}" 2>/dev/null || true)"
    [[ "${autoconnect}" == "yes" ]] || continue
    priority="$(nmcli -g connection.autoconnect-priority connection show id "${candidate}" 2>/dev/null || echo 0)"
    [[ "${priority}" =~ ^-?[0-9]+$ ]] || priority=0
    if (( priority > selected_priority )); then
      selected="${candidate}"
      selected_priority="${priority}"
    fi
  done < <(nmcli -g NAME connection show)
  printf '%s' "${selected}"
}

print_status() {
  local active_connection connection_type wifi_mode mode ssid ip_address client_profile
  active_connection="$(nmcli -g GENERAL.CONNECTION device show "${wifi_interface}" 2>/dev/null || true)"
  [[ "${active_connection}" != "--" ]] || active_connection=""
  mode="disconnected"
  ssid=""
  if [[ -n "${active_connection}" ]]; then
    connection_type="$(
      nmcli -g connection.type connection show id "${active_connection}" 2>/dev/null || true
    )"
    wifi_mode="$(
      nmcli -g 802-11-wireless.mode connection show id "${active_connection}" 2>/dev/null || true
    )"
    if [[ "${active_connection}" == "${ap_profile}" ]] || [[ "${wifi_mode}" == "ap" ]]; then
      mode="ap"
    elif [[ "${connection_type}" == "802-11-wireless" ]]; then
      mode="client"
    else
      mode="unknown"
    fi
    ssid="$(
      nmcli -g 802-11-wireless.ssid connection show id "${active_connection}" 2>/dev/null || true
    )"
  fi
  ip_address="$(
    nmcli -g IP4.ADDRESS device show "${wifi_interface}" 2>/dev/null \
      | head -n 1 \
      | cut -d/ -f1
  )"
  client_profile="$(known_client_profile)"

  printf 'mode=%s\n' "${mode}"
  printf 'active_connection=%s\n' "${active_connection}"
  printf 'ssid=%s\n' "${ssid}"
  printf 'ip_address=%s\n' "${ip_address}"
  if [[ -n "${client_profile}" ]]; then
    printf 'client_profile_available=true\n'
  else
    printf 'client_profile_available=false\n'
  fi
}

if [[ "${action}" == "ap" ]]; then
  nmcli -g NAME connection show \
    | grep --fixed-strings --line-regexp --quiet "${ap_profile}" || {
    echo "Der Access Point ist noch nicht eingerichtet." >&2
    echo "Einmalig sudo zunder-zapfe-admin-wifi ausführen." >&2
    exit 1
  }
  nmcli connection modify id "${ap_profile}" connection.autoconnect yes
  nmcli --wait 20 connection up id "${ap_profile}" ifname "${wifi_interface}" >/dev/null
elif [[ "${action}" == "client" ]]; then
  client_profile="$(known_client_profile)"
  [[ -n "${client_profile}" ]] || {
    echo "Es ist kein automatisch verbindbares WLAN-Clientprofil gespeichert." >&2
    exit 1
  }
  nmcli connection modify id "${ap_profile}" connection.autoconnect no
  if ! nmcli --wait 20 connection up id "${client_profile}" ifname "${wifi_interface}" >/dev/null; then
    nmcli connection modify id "${ap_profile}" connection.autoconnect yes
    nmcli --wait 20 connection up id "${ap_profile}" ifname "${wifi_interface}" >/dev/null || true
    echo "Das bekannte WLAN war nicht erreichbar; Access Point wurde wieder aktiviert." >&2
    exit 1
  fi
fi

print_status
