#!/usr/bin/env python3
"""
Kapitel 11 – Kreis-Geste (entspricht Tutorial 8 „Circle Gesture“, Port aus leap_gestures.py).

Die Handfläche beschreibt einen Kreis (Ø ca. 4–16 cm) über dem Sensor.
Von oben betrachtet: im Uhrzeigersinn = CIRCLE_CW, gegen = CIRCLE_CCW.
Wie in leap_gestures.py wird ein Winkel (z. B. für den Hologram-Fan) gedreht.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.gestures import CircleDetector  # noqa: E402
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402



def main():
    args = base_parser('Kreis-Geste').parse_args()
    cfg = load(args, required=False)
    circle = CircleDetector()
    angle, step = 0.0, 10.0
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            for frame in mgr.frames():
                hand = frame.hand()
                if hand is None:
                    circle.reset()
                    live("Suche Hand ...")
                    continue
                ev = circle.update(hand)
                if ev:
                    angle = (angle + (step if ev == "CIRCLE_CW" else -step)) % 360
                    say(f"  {'↻' if ev == 'CIRCLE_CW' else '↺'}  {ev} -> {angle:.0f}°")
                live(f"Kreis aktiv: {'ja ' if circle.is_active() else 'nein'} | Winkel {angle:5.1f}°")
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
