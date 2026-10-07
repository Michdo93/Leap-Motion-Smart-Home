#!/usr/bin/env python3
"""
Kapitel 11 – Alle Gesten kombiniert (Weiterentwicklung von leap_gestures.py).

GestureEngine wertet pro Frame alle Detektoren aus. Über GestureMode sperrt eine
laufende Geste die anderen: Während eines Kreises gibt es keine Swipes, während
einer Faust keine Taps. Mit --only lassen sich Gesten gezielt aktivieren:

    python3 leap_gesture_engine.py --only swipe --only circle
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.gestures import ALL_GESTURES, GestureEngine  # noqa: E402
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402


def main():
    ap = base_parser("Alle Gesten")
    ap.add_argument("--only", action="append", choices=sorted(ALL_GESTURES))
    args = ap.parse_args()
    cfg = load(args, required=False)

    engines = {}   # pro Sensor eine eigene Engine (Zustand je Sensor!)
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            for frame in mgr.frames():
                engine = engines.setdefault(frame.serial, GestureEngine(args.only))
                hand = frame.hand()
                for ev in engine.update(hand):
                    say(f"[{cfg.alias_for(frame.serial) if cfg else frame.serial}] {ev}")
                live(f"Modus: {engine.mode.mode:10} | Hand: {'ja' if hand else 'nein'}")
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
