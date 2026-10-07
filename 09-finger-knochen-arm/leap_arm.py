#!/usr/bin/env python3
"""
Kapitel 9 – Armdaten (entspricht Tutorial 5 „Arm Data“).

LeapC liefert den Unterarm als Knochen: prev_joint = Ellbogen, next_joint = Handgelenk.
Der Ellbogen liegt oft außerhalb des Sichtfelds und wird dann geschätzt.
"""

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, sensor_serials  # noqa: E402


def main():
    args = base_parser("Armdaten ausgeben").parse_args()
    cfg = load(args, required=False)
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            last = 0.0
            for frame in mgr.frames():
                h = frame.hand()
                if h is None or time.time() - last < 0.2:
                    continue
                last = time.time()
                e, w = h.arm.elbow, h.arm.wrist
                live(f"{'L' if h.is_left else 'R'} Ellbogen ({e[0]:6.0f},{e[1]:6.0f},{e[2]:6.0f}) "
                     f"Handgelenk ({w[0]:6.0f},{w[1]:6.0f},{w[2]:6.0f}) "
                     f"Länge {h.arm.length:5.0f} mm Breite {h.arm.width:4.0f} mm")
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
