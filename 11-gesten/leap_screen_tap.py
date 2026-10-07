#!/usr/bin/env python3
"""
Kapitel 11 – Screen-Tap (entspricht Tutorial 11 „Screen Tap Gesture“).

Mit ausgestrecktem Zeigefinger (übrige Finger gebeugt) kurz nach vorne Richtung
Bildschirm stoßen und zurückziehen – wie ein Tippen auf einen Touchscreen.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.gestures import ScreenTapDetector  # noqa: E402
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402



def main():
    args = base_parser('Screen-Tap').parse_args()
    cfg = load(args, required=False)
    tap = ScreenTapDetector()
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            for frame in mgr.frames():
                hand = frame.hand()
                if hand is None:
                    tap.reset()
                    live("Suche Hand ...")
                    continue
                ev = tap.update(hand)
                pointing = hand.fingers[1].extended and hand.extended_count <= 2
                live(f"Zeigehaltung: {'ja ' if pointing else 'nein'} | Spitze Z: {hand.fingers[1].tip[2]:6.1f} mm")
                if ev:
                    say("  SCREEN_TAP")
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
