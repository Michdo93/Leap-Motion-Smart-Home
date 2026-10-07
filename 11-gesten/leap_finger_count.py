#!/usr/bin/env python3
"""
Kapitel 11 – Finger zählen (Ersatz für fingersX_YYY des openHAB-Bindings).

Ein Ereignis FINGERS_n kommt erst, wenn die Anzahl 0,4 s stabil ist. Typische
Anwendung: Szene 1–5 auswählen.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.gestures import FingerCountDetector  # noqa: E402
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402



def main():
    args = base_parser('Finger zählen').parse_args()
    cfg = load(args, required=False)
    fingers = FingerCountDetector()
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            for frame in mgr.frames():
                hand = frame.hand()
                if hand is None:
                    fingers.reset()
                    live("Suche Hand ...")
                    continue
                ev = fingers.update(hand)
                live(f"Aktuell ausgestreckt: {hand.extended_count}")
                if ev:
                    say(f"  >>> {ev} (Höhe {hand.palm_position[1]:.0f} mm)")
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
