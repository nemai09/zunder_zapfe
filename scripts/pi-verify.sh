#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Commit: $(git -C "${repo_dir}" rev-parse --short HEAD)"
echo "Modell: $(tr -d '\0' </proc/device-tree/model 2>/dev/null || echo unbekannt)"
echo "Python: $("${repo_dir}/.venv/bin/python" --version)"
echo

echo "1/7 Python-Tests"
env -u ZUNDER_ZAPFE_DATABASE_URL "${repo_dir}/.venv/bin/python" -m pytest

# Load the deployed configuration only after the isolated test suite. Otherwise
# Alembic would migrate the production database instead of each temporary test
# database selected by the tests.
if [[ -f /etc/zunder-zapfe/web.env ]]; then
  set -a
  # shellcheck disable=SC1091
  source /etc/zunder-zapfe/web.env
  set +a
fi
export ZUNDER_ZAPFE_DATABASE_URL="${ZUNDER_ZAPFE_DATABASE_URL:-sqlite:////var/lib/zunder-zapfe/zunder-zapfe.db}"

echo "2/7 Datenbankschema"
"${repo_dir}/.venv/bin/alembic" -c "${repo_dir}/alembic.ini" current --check-heads

echo "3/7 systemd-Dienst"
systemctl is-active --quiet zunder-zapfe-web.service
echo "zunder-zapfe-web.service: active"

echo "4/7 Health-Endpunkt"
curl --fail --silent --show-error http://127.0.0.1:8000/api/health
echo

echo "5/7 ACR122U"
nfc_status=""
for _attempt in $(seq 1 10); do
  nfc_status="$(curl --fail --silent --show-error http://127.0.0.1:8000/api/nfc/status)"
  if grep --extended-regexp --quiet '"state":"(ready|card)"' <<<"${nfc_status}"; then
    break
  fi
  sleep 1
done
echo "${nfc_status}"
grep --extended-regexp --quiet '"state":"(ready|card)"' <<<"${nfc_status}" || {
  echo "ACR122U ist nicht betriebsbereit." >&2
  exit 1
}

echo "6/7 Admin-WLAN"
if [[ -f /etc/zunder-zapfe/admin-wifi.configured ]]; then
  nmcli --terse --fields NAME connection show --active \
    | grep --fixed-strings --line-regexp --quiet "zunder-zapfe-ap"
  nmcli -g 802-11-wireless.ssid connection show "zunder-zapfe-ap" \
    | grep --fixed-strings --line-regexp --quiet "ZUNDER_ZAPFE"
  ip -4 address show dev wlan0 \
    | grep --fixed-strings --quiet "inet 10.42.0.1/24"
  echo "ZUNDER_ZAPFE: aktiv auf 10.42.0.1/24"
else
  echo "Noch nicht eingerichtet; einmalig sudo zunder-zapfe-admin-wifi ausfuehren."
fi

echo "7/7 Admin-Webzugang"
if [[ -f /etc/zunder-zapfe/admin-wifi.configured ]]; then
  curl --fail --silent --show-error http://10.42.0.1/api/health
  echo
else
  echo "Bis zur WLAN-Einrichtung uebersprungen."
fi

echo "Zielsystem-Verifikation erfolgreich."
