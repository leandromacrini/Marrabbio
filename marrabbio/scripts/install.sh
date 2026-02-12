#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="marrabbio.service"
SERVICE_DST="/etc/systemd/system/${SERVICE_NAME}"
SERVICE_USER="${SERVICE_USER:-licia}"
SUDOERS_FILE="/etc/sudoers.d/marrabbio-power"

echo "[1/7] Checking required binaries"
command -v python3 >/dev/null
command -v systemctl >/dev/null
SYSTEMCTL_BIN="$(command -v systemctl)"

echo "[2/7] Installing Python runtime dependencies"
sudo apt-get update
sudo apt-get install -y git python3-gpiozero mpg123

echo "[3/7] Installing systemd service"
sudo cp "${PROJECT_DIR}/systemd/${SERVICE_NAME}" "${SERVICE_DST}"

echo "[4/7] Configuring sudoers for reboot/poweroff secret codes"
cat <<EOF | sudo tee "${SUDOERS_FILE}" >/dev/null
${SERVICE_USER} ALL=(root) NOPASSWD: ${SYSTEMCTL_BIN} reboot, ${SYSTEMCTL_BIN} poweroff
EOF
sudo chmod 440 "${SUDOERS_FILE}"
sudo visudo -cf "${SUDOERS_FILE}"

echo "[5/7] Reloading systemd"
sudo systemctl daemon-reload

echo "[6/7] Enabling service"
sudo systemctl enable "${SERVICE_NAME}"

echo "[7/7] Starting service"
sudo systemctl restart "${SERVICE_NAME}"

echo
echo "Service status:"
sudo systemctl --no-pager --full status "${SERVICE_NAME}" || true
