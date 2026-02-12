#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="marrabbio.service"
SERVICE_DST="/etc/systemd/system/${SERVICE_NAME}"
SERVICE_USER="${SERVICE_USER:-licia}"
SUDOERS_FILE="/etc/sudoers.d/marrabbio-power"
REPO_URL="https://github.com/leandromacrini/Marrabbio.git"
REPO_REMOTE="remote"
REPO_BRANCH="master"

echo "[1/9] Checking required binaries"
command -v python3 >/dev/null
command -v systemctl >/dev/null
command -v git >/dev/null
SYSTEMCTL_BIN="$(command -v systemctl)"

echo "[2/9] Installing Python runtime dependencies"
sudo apt-get update
sudo apt-get install -y git python3-gpiozero mpg123

echo "[3/9] Configuring git remote (${REPO_REMOTE}/${REPO_BRANCH})"
if ! git -C "${PROJECT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "${PROJECT_DIR}" init
fi
if git -C "${PROJECT_DIR}" remote get-url "${REPO_REMOTE}" >/dev/null 2>&1; then
  git -C "${PROJECT_DIR}" remote set-url "${REPO_REMOTE}" "${REPO_URL}"
else
  git -C "${PROJECT_DIR}" remote add "${REPO_REMOTE}" "${REPO_URL}"
fi
git -C "${PROJECT_DIR}" fetch --prune "${REPO_REMOTE}" || true
git -C "${PROJECT_DIR}" branch --set-upstream-to="${REPO_REMOTE}/${REPO_BRANCH}" "${REPO_BRANCH}" >/dev/null 2>&1 || true

echo "[4/9] Updating project from git"
bash "${PROJECT_DIR}/scripts/update_from_git.sh" || true

echo "[5/9] Installing systemd service"
sudo cp "${PROJECT_DIR}/systemd/${SERVICE_NAME}" "${SERVICE_DST}"

echo "[6/9] Configuring sudoers for reboot/poweroff secret codes"
cat <<EOF | sudo tee "${SUDOERS_FILE}" >/dev/null
${SERVICE_USER} ALL=(root) NOPASSWD: ${SYSTEMCTL_BIN} reboot, ${SYSTEMCTL_BIN} poweroff
EOF
sudo chmod 440 "${SUDOERS_FILE}"
sudo visudo -cf "${SUDOERS_FILE}"

echo "[7/9] Reloading systemd"
sudo systemctl daemon-reload

echo "[8/9] Enabling service"
sudo systemctl enable "${SERVICE_NAME}"

echo "[9/9] Starting service"
sudo systemctl restart "${SERVICE_NAME}"

echo
echo "Service status:"
sudo systemctl --no-pager --full status "${SERVICE_NAME}" || true
