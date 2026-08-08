#!/usr/bin/env bash
set -euo pipefail

action="${1:-}"

case "${action}" in
  reboot|poweroff)
    ;;
  *)
    echo "Aufruf: zunder-zapfe-system-power {reboot|poweroff}" >&2
    exit 2
    ;;
esac

command -v systemctl >/dev/null 2>&1 || {
  echo "systemctl ist nicht verfügbar." >&2
  exit 1
}

# Polkit authorizes exactly the two login1 actions for the service user. The
# non-blocking request lets the HTTP response reach the local kiosk first.
exec systemctl --no-block "${action}"
