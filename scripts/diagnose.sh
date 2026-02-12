#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="marrabbio.service"

echo "== System =="
uname -a
echo

echo "== Python =="
python3 --version
echo

echo "== gpiozero backends =="
python3 - <<'PY'
import importlib
mods = ["gpiozero", "lgpio", "RPi.GPIO", "pigpio"]
for mod in mods:
    try:
        m = importlib.import_module(mod)
        print(f"{mod}: OK ({getattr(m, '__version__', 'n/a')})")
    except Exception as e:
        print(f"{mod}: MISSING ({e})")
PY
echo

echo "== Runtime pin factory =="
python3 - <<'PY'
from gpiozero import Device
print(Device.pin_factory)
PY
echo

echo "== Service status =="
sudo systemctl --no-pager --full status "${SERVICE_NAME}" || true
echo

echo "== Last logs =="
journalctl -u "${SERVICE_NAME}" -n 80 --no-pager || true

