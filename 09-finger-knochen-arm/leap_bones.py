#!/usr/bin/env python3
"""
Kapitel 9 – Knochen (entspricht Tutorial 6 „Finger and Bone Data“, Teil 2).

Jeder Finger besteht aus vier Knochen: Mittelhand, Grundglied, Mittelglied, Endglied.
Der Daumen hat anatomisch keinen Mittelhandknochen im Modell – LeapC liefert
dort einen Knochen der Länge 0.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import BONE_NAMES, FINGER_NAMES, LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import base_parser, load, sensor_serials  # noqa: E402


def main():
    args = base_parser("Knochen einer Hand einmalig vermessen").parse_args()
    cfg = load(args, required=False)
    print("Hand ruhig und gespreizt über den Sensor halten ...")
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        for frame in mgr.frames():
            h = frame.hand()
            if h is None or h.confidence < 0.8:
                continue
            print(f"\nHand {'links' if h.is_left else 'rechts'} (Konfidenz {h.confidence:.2f})\n")
            print(f"{'Finger':15}" + "".join(f"{b:>14}" for b in BONE_NAMES))
            for name, f in zip(FINGER_NAMES, h.fingers):
                print(f"{name:15}" + "".join(f"{bone.length:11.1f} mm" for bone in f.bones))
            break


if __name__ == "__main__":
    main()
