#!/usr/bin/env python3
"""
Kapitel 10 – Zone (X) + Höhe (Y) + schneller Wisch (vY) (Port von leap_rollladen2.py).

  * X wählt den Rollladen
  * Y bestimmt die Position: oben (>= Y_MAX) = 0 % offen, unten (<= Y_MIN) = 100 % zu
  * Quantisierung auf 5-%-Schritte verhindert Befehlsflut
  * schneller Wisch nach oben/unten = ganz auf/ganz zu (hat Vorrang)
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.mapping import ZoneSet, height_percent  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402

ZONES = ZoneSet.columns(["1", "2", "3", "4"], boundaries=[-150, 0, 150])
Y_MIN, Y_MAX = 100, 450
SWIPE_THRESHOLD = 600  # mm/s


def main():
    args = base_parser("Zonen mit Höhe und Wisch").parse_args()
    cfg = load(args, required=False)
    last = (None, None)
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            for frame in mgr.frames():
                hand = frame.hand()
                if hand is None:
                    live("Suche Hand ...")
                    continue
                x, y, _ = hand.palm_position
                vy = hand.palm_velocity[1]
                zone = ZONES.find(hand.palm_position)
                pct = height_percent(y, Y_MIN, Y_MAX, invert=True)
                action = f"POS -> Rollladen {zone} auf {pct}%"
                if vy > SWIPE_THRESHOLD:
                    pct, action = 0, f"SWIPE HOCH -> Rollladen {zone} auf 0%"
                elif vy < -SWIPE_THRESHOLD:
                    pct, action = 100, f"SWIPE RUNTER -> Rollladen {zone} auf 100%"
                live(f"LIVE: X:{x:4.0f} Y:{y:4.0f} | Z{zone or '-'} | Ziel: {pct:3}% | vY: {vy:5.0f}")
                if zone and (zone, pct) != last:
                    say(f"AKTION: {action}")
                    last = (zone, pct)
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
