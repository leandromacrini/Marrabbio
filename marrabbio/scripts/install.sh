#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="marrabbio.service"
SERVICE_DST="/etc/systemd/system/${SERVICE_NAME}"

echo "[1/7] Checking required binaries"
command -v python3 >/dev/null
command -v systemctl >/dev/null
command -v nmcli >/dev/null || true

echo "[2/7] Installing Python runtime dependencies"
sudo apt-get update
sudo apt-get install -y python3-gpiozero mpg123

echo "[3/7] Installing systemd service"
sudo cp "${PROJECT_DIR}/systemd/${SERVICE_NAME}" "${SERVICE_DST}"

echo "[4/7] Reloading systemd"
sudo systemctl daemon-reload

echo "[5/7] Enabling service"
sudo systemctl enable "${SERVICE_NAME}"

echo "[6/7] Starting service"
sudo systemctl restart "${SERVICE_NAME}"

echo "[7/7] Optional Wi-Fi priority"
if [[ -n "${WIFI_PRIMARY:-}" && -n "${WIFI_FALLBACK:-}" ]]; then
  bash "${PROJECT_DIR}/scripts/set_wifi_priority.sh" "${WIFI_PRIMARY}" "${WIFI_FALLBACK}"
else
  echo "Skip Wi-Fi priority (set WIFI_PRIMARY and WIFI_FALLBACK env vars to enable)."
fi

echo
echo "Service status:"
sudo systemctl --no-pager --full status "${SERVICE_NAME}" || true
