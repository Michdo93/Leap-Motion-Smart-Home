#!/usr/bin/env bash
# Kapitel 16 – USB/IP-Server auf dem Raspberry Pi einrichten
#   sudo bash setup_server.sh 1-1.2 [1-1.3 ...]
set -euo pipefail
[[ $# -ge 1 ]] || { echo "Aufruf: $0 <bus-id> [<bus-id> ...]  (Bus-ID: find_leap_busid.sh)"; exit 1; }
DIR="$(cd "$(dirname "$0")" && pwd)"

apt-get install -y usbip
grep -qx usbip_host /etc/modules || echo usbip_host >> /etc/modules
cp "$DIR/usbipd.service" "$DIR/usbip-server-bind@.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now usbipd.service      # (im Original-README fälschlich usbip.service)
for id in "$@"; do
    systemctl enable --now "usbip-server-bind@${id}.service"
done
usbip list -r localhost || true
