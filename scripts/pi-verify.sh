#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Commit: $(git -C "${repo_dir}" rev-parse --short HEAD)"
echo "Modell: $(tr -d '\0' </proc/device-tree/model 2>/dev/null || echo unbekannt)"
echo "Python: $("${repo_dir}/.venv/bin/python" --version)"
echo

echo "1/3 Python-Tests"
"${repo_dir}/.venv/bin/python" -m pytest

echo "2/3 systemd-Dienst"
systemctl is-active --quiet zunder-zapfe-web.service
echo "zunder-zapfe-web.service: active"

echo "3/3 Health-Endpunkt"
curl --fail --silent --show-error http://127.0.0.1:8000/api/health
echo
echo "Zielsystem-Verifikation erfolgreich."
