#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Commit: $(git -C "${repo_dir}" rev-parse --short HEAD)"
echo "Modell: $(tr -d '\0' </proc/device-tree/model 2>/dev/null || echo unbekannt)"
echo "Python: $("${repo_dir}/.venv/bin/python" --version)"
echo

echo "1/4 Python-Tests"
"${repo_dir}/.venv/bin/python" -m pytest

echo "2/4 systemd-Dienst"
systemctl is-active --quiet zunder-zapfe-web.service
echo "zunder-zapfe-web.service: active"

echo "3/4 Health-Endpunkt"
curl --fail --silent --show-error http://127.0.0.1:8000/api/health
echo

echo "4/4 ACR122U"
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

echo "Zielsystem-Verifikation erfolgreich."
