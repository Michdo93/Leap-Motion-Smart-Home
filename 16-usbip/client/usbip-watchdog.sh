#!/bin/bash
# Kapitel 16 – Watchdog: hängt das Gerät nicht mehr am vhci-Port, Client neu starten.
# Datei: /usr/local/bin/usbip-watchdog.sh
# Bus-IDs in /etc/default/usbip-client:  USBIP_BUSIDS="1-1.2 1-1.3"
# Hinweis Ubuntu: usbip liegt unter /usr/bin statt /usr/sbin (linux-tools)

source /etc/default/usbip-client
USBIP="$(command -v usbip || echo /usr/sbin/usbip)"
rc=0
for BUS_ID in ${USBIP_BUSIDS}; do
    if ! "${USBIP}" port | grep -q "/${BUS_ID}"; then
        echo "WATCHDOG: USB/IP-Gerät ${BUS_ID} nicht gefunden – Neustart des Clients"
        systemctl restart "usbip-client@${BUS_ID}.service"
        rc=1
    fi
done
exit $rc
