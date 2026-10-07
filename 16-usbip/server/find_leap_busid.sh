#!/usr/bin/env bash
# Kapitel 16 – Bus-ID(s) aller Leap Motion Controller finden (Vendor-ID f182)
# Ausgabe z. B.:  1-1.2   (Leap Motion Controller, f182:0003)
set -euo pipefail
sudo modprobe usbip_host
usbip list -l | awk '/busid/ {id=$3} /f182/ {print id "\t" $0}'
