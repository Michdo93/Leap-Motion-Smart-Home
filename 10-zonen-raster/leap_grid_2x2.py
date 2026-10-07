#!/usr/bin/env python3
"""
Kapitel 10 – 2x2-Matrix aus X und Z (Grundlage von leap_jalousie_oh.py).

    [HINTEN_LINKS] [HINTEN_RECHTS]     Z < 0 (Richtung Bildschirm)
    [VORNE_LINKS ] [VORNE_RECHTS ]     Z >= 0 (Richtung Körper)
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.mapping import height_percent  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402


def quadrant(x, z, x_center=0, z_center=0):
    reihe = "HINTEN" if z < z_center else "VORNE"
    spalte = "LINKS" if x < x_center else "RECHTS"
    return f"{reihe}_{spalte}"


def main():
    args = base_parser("2x2-Matrix").parse_args()
    cfg = load(args, required=False)
    last = None
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            for frame in mgr.frames():
                hand = frame.hand()
                if hand is None:
                    live("Suche Hand ...")
                    continue
                x, y, z = hand.palm_position
                q = quadrant(x, z)
                pct = height_percent(y, 100, 450, invert=True)
                live(f"QUADRANT: {q:14} | {pct:3}% | X:{x:5.0f} Z:{z:5.0f}")
                if (q, pct) != last:
                    say(f"AKTION: Jalousie {q} -> {pct}%")
                    last = (q, pct)
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
