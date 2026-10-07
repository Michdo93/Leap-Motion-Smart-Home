#!/usr/bin/env python3
"""
Kapitel 8 – Koordinaten der Handfläche (Port von leap_coordinates.py / README).

Koordinatensystem (Desktop-Modus, Sensor liegt flach, Kabel zeigt nach hinten):
  X  links (-) / rechts (+)
  Y  Höhe über dem Sensor
  Z  hinten/Bildschirm (-) / vorne/Körper (+)
Alle Werte in Millimetern.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, sensor_serials  # noqa: E402


def main():
    args = base_parser("Koordinaten der Handfläche").parse_args()
    cfg = load(args, required=False)
    print("Lege die Hand über den Sensor (Strg+C beendet).\n")
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            for frame in mgr.frames():
                hand = frame.hand()
                if hand is None:
                    live("Warte auf Hand ...")
                    continue
                x, y, z = hand.palm_position
                live(f"X: {x:6.1f} mm | Y: {y:6.1f} mm | Z: {z:6.1f} mm")
        except KeyboardInterrupt:
            print("\nProgramm wird beendet.")


if __name__ == "__main__":
    main()
