#!/usr/bin/env python3
"""
Kapitel 11 – Greifen und Pinch.

  GRAB / RELEASE  Faust schließen / öffnen (Hysterese 0,85 / 0,35)
  FIST_TAP        Faust nur kurz ballen – „Zurück“-Geste aus leap_gestures.py
  PINCH / UNPINCH Daumen und Zeigefinger zusammenführen
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.gestures import GrabDetector, PinchDetector  # noqa: E402
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402



def main():
    args = base_parser('Greifen und Pinch').parse_args()
    cfg = load(args, required=False)
    grab, pinch = GrabDetector(), PinchDetector()
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            for frame in mgr.frames():
                hand = frame.hand()
                if hand is None:
                    grab.reset()
                    pinch.reset()
                    live("Suche Hand ...")
                    continue
                for ev in (grab.update(hand), pinch.update(hand)):
                    if ev:
                        say(f"  >>> {ev}")
                live(f"Grab: {hand.grab_strength:.2f} {'[FAUST]' if grab.closed else '       '} | "
                     f"Pinch: {hand.pinch_strength:.2f} ({hand.pinch_distance:4.0f} mm)")
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
