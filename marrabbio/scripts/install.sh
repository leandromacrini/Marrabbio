#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="marrabbio.service"
SERVICE_DST="/etc/systemd/system/${SERVICE_NAME}"
SERVICE_USER="${SERVICE_USER:-licia}"
SUDOERS_FILE="/etc/sudoers.d/marrabbio-power"

echo "[1/8] Checking required binaries"
command -v python3 >/dev/null
command -v systemctl >/dev/null
command -v nmcli >/dev/null || true
SYSTEMCTL_BIN="$(command -v systemctl)"

echo "[2/8] Installing Python runtime dependencies"
sudo apt-get update
sudo apt-get install -y git python3-gpiozero mpg123

echo "[3/8] Installing systemd service"
sudo cp "${PROJECT_DIR}/systemd/${SERVICE_NAME}" "${SERVICE_DST}"

echo "[4/8] Configuring sudoers for reboot/poweroff secret codes"
cat <<EOF | sudo tee "${SUDOERS_FILE}" >/dev/null
${SERVICE_USER} ALL=(root) NOPASSWD: ${SYSTEMCTL_BIN} reboot, ${SYSTEMCTL_BIN} poweroff
EOF
sudo chmod 440 "${SUDOERS_FILE}"
sudo visudo -cf "${SUDOERS_FILE}"

echo "[5/8] Reloading systemd"
sudo systemctl daemon-reload

echo "[6/8] Enabling service"
sudo systemctl enable "${SERVICE_NAME}"

echo "[7/8] Starting service"
sudo systemctl restart "${SERVICE_NAME}"

echo "[8/8] Optional Wi-Fi priority"
if [[ -n "${WIFI_PRIMARY:-}" && -n "${WIFI_FALLBACK:-}" ]]; then
  bash "${PROJECT_DIR}/scripts/set_wifi_priority.sh" "${WIFI_PRIMARY}" "${WIFI_FALLBACK}"
else
  echo "Skip Wi-Fi priority (set WIFI_PRIMARY and WIFI_FALLBACK env vars to enable)."
fi

echo
echo "Service status:"
sudo systemctl --no-pager --full status "${SERVICE_NAME}" || true
