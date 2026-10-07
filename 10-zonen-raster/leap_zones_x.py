#!/usr/bin/env python3
"""
Kapitel 10 – Zonen entlang der X-Achse (Port von leap_rollladen.py).

Vier Spalten über dem Sensor, z. B. für vier Rollläden:
  Z1: -400..-151 | Z2: -150..-1 | Z3: 0..149 | Z4: 150..400   (mm)
Ein Ereignis wird nur beim WECHSEL der Zone ausgelöst.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.mapping import ZoneSet  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402

ZONES = ZoneSet.columns(["Z1", "Z2", "Z3", "Z4"], boundaries=[-150, 0, 150])


def main():
    args = base_parser("Zonen entlang X").parse_args()
    cfg = load(args, required=False)
    last_zone = None
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            for frame in mgr.frames():
                hand = frame.hand()
                if hand is None:
                    live("Suche Hand ...")
                    last_zone = None
                    continue
                x, y, z = hand.palm_position
                zone = ZONES.find(hand.palm_position)
                live(f"LIVE -> X:{x:5.0f} Y:{y:5.0f} Z:{z:5.0f} | {zone or 'AUSSERHALB'}")
                if zone and zone != last_zone:
                    say(f"AKTION: Trigger Rollladen {zone} bei X={x:.0f}")
                last_zone = zone
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
