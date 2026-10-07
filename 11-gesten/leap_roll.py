#!/usr/bin/env python3
"""
Kapitel 11 – Hand als Drehregler (Roll).

Pinch rastet den Regler ein (aktueller Winkel = Nullpunkt), Drehen der Hand
verändert den Wert, Loslassen beendet. So wird ein versehentliches Drehen ohne
Pinch ignoriert – Grundlage für „Roll = Lautstärke“ beim Samsung TV.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.gestures import PinchDetector, RollTracker  # noqa: E402
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402



def main():
    args = base_parser('Drehregler').parse_args()
    cfg = load(args, required=False)
    pinch, roll = PinchDetector(), RollTracker()
    value, start_value = 50.0, 50.0
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            for frame in mgr.frames():
                hand = frame.hand()
                if hand is None:
                    pinch.reset()
                    roll.release()
                    live("Suche Hand ...")
                    continue
                ev = pinch.update(hand)
                if ev == "PINCH":
                    roll.engage(hand)
                    start_value = value
                elif ev == "UNPINCH":
                    roll.release()
                    say(f"  Wert übernommen: {value:.0f} %")
                if roll.reference is not None:
                    value = max(0.0, min(100.0, start_value + roll.delta(hand) / 2))
                live(f"Roll: {hand.roll:6.1f}° | eingerastet: {'ja ' if roll.reference is not None else 'nein'} "
                     f"| Wert: {value:5.1f} %")
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
