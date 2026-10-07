#!/usr/bin/env python3
"""
Kapitel 8 – Handdaten (entspricht Tutorial 4 „Hand Data“).

Pro Hand:
  * links/rechts, Konfidenz, Sichtbarkeitsdauer
  * Position, Geschwindigkeit, Normale und Richtung der Handfläche
  * Pitch / Yaw / Roll in Grad (berechnet wie im alten SDK v2)
  * grab_strength (0 = offen, 1 = Faust), pinch_strength, pinch_distance
"""

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import base_parser, load, sensor_serials  # noqa: E402


def fmt(v):
    return "(" + ", ".join(f"{c:7.1f}" for c in v) + ")"


def main():
    ap = base_parser("Alle Handdaten ausgeben")
    ap.add_argument("--interval", type=float, default=0.5, help="Ausgabeintervall in s")
    args = ap.parse_args()
    cfg = load(args, required=False)

    last = 0.0
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            for frame in mgr.frames():
                if time.time() - last < args.interval:
                    continue
                last = time.time()
                print("\033[2J\033[H", end="")   # Bildschirm leeren
                print(f"Sensor {frame.serial} | Frame {frame.frame_id} | {frame.fps:.0f} fps | "
                      f"{len(frame.hands)} Hand/Hände\n")
                for h in frame.hands:
                    print(f"Hand {h.id} ({'links' if h.is_left else 'rechts'}), "
                          f"Konfidenz {h.confidence:.2f}, sichtbar seit {h.visible_time_us / 1e6:.1f} s")
                    print(f"  Position      {fmt(h.palm_position)} mm")
                    print(f"  Geschwindigk. {fmt(h.palm_velocity)} mm/s")
                    print(f"  Normale       {fmt(h.palm_normal)}")
                    print(f"  Richtung      {fmt(h.palm_direction)}")
                    print(f"  Pitch {h.pitch:6.1f}°  Yaw {h.yaw:6.1f}°  Roll {h.roll:6.1f}°")
                    print(f"  Grab {h.grab_strength:.2f}  Pinch {h.pinch_strength:.2f} "
                          f"({h.pinch_distance:.0f} mm)  Handbreite {h.palm_width:.0f} mm\n")
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
