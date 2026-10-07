#!/usr/bin/env python3
"""
Kapitel 11 – Swipe-Geste (entspricht Tutorial 9 „Swipe Gesture“ und 10 „Determine Gesture
Direction“).

Wischen wird über die Geschwindigkeit der Handfläche erkannt. Die schnellste Achse
bestimmt die Richtung: links/rechts (X), hoch/runter (Y), optional vor/zurück (Z).
--xyz aktiviert auch vor/zurück.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.gestures import SwipeDetector  # noqa: E402
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402



def main():
    ap = base_parser('Swipe-Geste')
    ap.add_argument("--xyz", action="store_true", help="auch vor/zurück (Z) erkennen")
    args = ap.parse_args()
    cfg = load(args, required=False)
    swipe = SwipeDetector()
    if args.xyz:
        swipe.AXES = 'xyz'
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            for frame in mgr.frames():
                hand = frame.hand()
                if hand is None:
                    swipe.reset()
                    live("Suche Hand ...")
                    continue
                ev = swipe.update(hand)
                vx, vy, vz = hand.palm_velocity
                live(f"vX:{vx:6.0f} vY:{vy:6.0f} vZ:{vz:6.0f} mm/s  (Schwelle {swipe.THRESHOLD:.0f})")
                if ev:
                    say(f"  >>> {ev}")
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
