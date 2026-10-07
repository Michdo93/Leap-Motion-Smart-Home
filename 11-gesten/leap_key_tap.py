#!/usr/bin/env python3
"""
Kapitel 11 – Key-Tap (entspricht Tutorial 12 „Key Tap Gesture“, Port des ClickDetector).

Zeigefinger tippt isoliert nach unten, als würde man eine Taste drücken.
Die anderen Finger und die Handfläche bleiben ruhig – sonst wird nichts ausgelöst.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.gestures import KeyTapDetector  # noqa: E402
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402



def main():
    args = base_parser('Key-Tap').parse_args()
    cfg = load(args, required=False)
    tap = KeyTapDetector()
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            for frame in mgr.frames():
                hand = frame.hand()
                if hand is None:
                    tap.reset()
                    live("Suche Hand ...")
                    continue
                ev = tap.update(hand)
                live(f"Zeigefinger Y: {hand.fingers[1].tip[1]:6.1f} mm | Phase: {tap._phase}")
                if ev:
                    x, _, z = tap.last_position
                    say(f"  KEY_TAP bei X={x:+.0f} mm Z={z:+.0f} mm")
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
