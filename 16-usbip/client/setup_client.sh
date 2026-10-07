#!/usr/bin/env bash
# Kapitel 16 – USB/IP-Client (Ubuntu-VM) einrichten
#   sudo bash setup_client.sh <server-ip> <bus-id> [<bus-id> ...]
set -euo pipefail
[[ $# -ge 2 ]] || { echo "Aufruf: $0 <server-ip> <bus-id> [<bus-id> ...]"; exit 1; }
DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER="$1"; shift

apt-get install -y "linux-tools-$(uname -r)" || apt-get install -y linux-tools-generic
grep -qx vhci-hcd /etc/modules || echo vhci-hcd >> /etc/modules

# Ubuntu: usbip unter /usr/bin -> Pfade in den Units anpassen
USBIP="$(command -v usbip)"
sed "s#/usr/sbin/usbip#${USBIP}#g" "$DIR/usbip-client@.service" > /etc/systemd/system/usbip-client@.service
cp "$DIR/usbip-watchdog.service" "$DIR/usbip-watchdog.timer" /etc/systemd/system/
install -m 755 "$DIR/usbip-watchdog.sh" /usr/local/bin/usbip-watchdog.sh
printf 'USBIP_SERVER=%s\nUSBIP_BUSIDS="%s"\n' "$SERVER" "$*" > /etc/default/usbip-client

systemctl daemon-reload
for id in "$@"; do
    systemctl enable --now "usbip-client@${id}.service"
done
systemctl enable --now usbip-watchdog.timer
"${USBIP}" port
