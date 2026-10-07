#!/usr/bin/env python3
"""
Kapitel 6 – Discovery: alle angeschlossenen Controller finden.

Unterschied Seriennummer vs. Laufzeit-ID:
  * Seriennummer (z. B. LP19566274693): fest im Gerät – STABILER Schlüssel
  * Laufzeit-ID (device_ref.id):         vergibt der Dienst – kann sich nach
                                          Neustecken oder USB/IP-Reconnect ändern

Am Ende wird ein fertiger devices:-Block für config/config.yaml ausgegeben.
Die robuste Variante für Anwendungen ist leapsmarthome.leapdevices (Kapitel 12).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import base_parser, load  # noqa: E402


def main():
    ap = base_parser("Leap Motion Controller finden", sensor=False)
    ap.add_argument("--timeout", type=float, default=5.0)
    args = ap.parse_args()
    cfg = load(args, required=False)

    print("=" * 70)
    print(" SCANNE AKTIVE LEAP MOTION CONTROLLER (USB / USB-IP)")
    print("=" * 70)
    with LeapDeviceManager() as mgr:
        found = mgr.wait_for_devices(args.timeout)

    if not found:
        print("\nKeine Geräte gefunden. Prüfe USB, USB/IP (Kapitel 16) und den Ultraleap-Dienst.")
        return 1

    for n, info in enumerate(found.values(), 1):
        alias = cfg.alias_for(info.serial) if cfg else "-"
        print(f"\n[GERÄT {n}]")
        print(f"  SERIENNUMMER : {info.serial}")
        print(f"  ALIAS        : {alias if alias != info.serial else '(noch nicht in config.yaml)'}")
        print(f"  LAUFZEIT-ID  : {info.device_id}")
        print(f"  PRODUKT      : {info.product}")
        print("-" * 45)

    print("\nVorschlag für config/config.yaml:\n\ndevices:")
    for n, info in enumerate(found.values(), 1):
        print(f"  {info.serial}: {cfg.alias_for(info.serial) if cfg and info.serial in cfg.devices else f'sensor{n}'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
