#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <PRIMARY_WIFI_NAME> <FALLBACK_WIFI_NAME>"
  exit 1
fi

PRIMARY="$1"
FALLBACK="$2"

nmcli connection modify "$PRIMARY" connection.autoconnect yes connection.autoconnect-priority 100
nmcli connection modify "$FALLBACK" connection.autoconnect yes connection.autoconnect-priority 10

echo "Updated priorities:"
nmcli -f NAME,AUTOCONNECT,AUTOCONNECT-PRIORITY connection show

