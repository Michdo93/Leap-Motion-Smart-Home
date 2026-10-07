#!/usr/bin/env python3
"""
Kapitel 26 – Vorschau der Robotersteuerung ohne ROS (Port von leap_pepper.py).

3x3-Raster über dem Sensor -> geometry_msgs/Twist-Werte für eine holonome Basis
wie Pepper. Totmann-Prinzip: Ohne Hand oder in der Mitte steht der Roboter.

    VORNE:   links drehen | vorwärts  | rechts drehen
    MITTE:   links gleiten| STOPP     | rechts gleiten
    HINTEN:  links drehen | rückwärts | rechts drehen
"""

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import base_parser, load, sensor_serials  # noqa: E402

LIMIT = 25.0          # mm – halbe Breite der Mittelzone
SAMPLE_DELAY = 0.1    # s


def twist_for(x: float, z: float, limit: float = LIMIT):
    """Liefert (lin_x, lin_y, ang_z, zone, row, col)."""
    col = -1 if x < -limit else (1 if x > limit else 0)
    row = -1 if z > limit else (1 if z < -limit else 0)     # row -1 = vorne (zum Körper)
    lx = ly = az = 0.0
    if row == -1:
        lx = 0.5
        if col == -1:
            az, zone = 0.8, "VORNE LINKS DREHEN"
        elif col == 1:
            az, zone = -0.8, "VORNE RECHTS DREHEN"
        else:
            zone = "VORWÄRTS"
    elif row == 1:
        lx = -0.4
        if col == -1:
            az, zone = 0.8, "HINTEN LINKS DREHEN"
        elif col == 1:
            az, zone = -0.8, "HINTEN RECHTS DREHEN"
        else:
            zone = "RÜCKWÄRTS"
    else:
        if col == -1:
            ly, zone = 0.4, "LINKS GLEITEN"
        elif col == 1:
            ly, zone = -0.4, "RECHTS GLEITEN"
        else:
            zone = "STOPP (ZENTRUM)"
    return lx, ly, az, zone, row, col


def main():
    args = base_parser("Twist-Vorschau").parse_args()
    cfg = load(args, required=False)
    print("\033[2J", end="")
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            while True:
                frame = next(iter(mgr.poll_latest().values()), None)
                hand = frame.hand() if frame else None
                grid = [[" "] * 3 for _ in range(3)]
                if hand:
                    x, _, z = hand.palm_position
                    lx, ly, az, zone, row, col = twist_for(x, z)
                    grid[row + 1][col + 1] = "X"
                else:
                    x = z = lx = ly = az = 0.0
                    zone = "KEINE HAND -> STOPP"
                print("\033[H" + "=" * 65)
                print(" ZIEL: /cmd_vel  |  geometry_msgs/Twist")
                print("=" * 65)
                print(f"\n  AKTIVE ZONE: {zone:25}  X: {x:6.1f}  Z: {z:6.1f}\n")
                for i, label in enumerate(("VORNE", "MITTE", "HINTEN")):
                    print("  +---+---+---+")
                    print(f"  | {' | '.join(grid[i])} |  {label}")
                print("  +---+---+---+")
                print(f"\n  linear:  {{x: {lx:4.2f}, y: {ly:4.2f}, z: 0.00}}")
                print(f"  angular: {{x: 0.00, y: 0.00, z: {az:4.2f}}}")
                time.sleep(SAMPLE_DELAY)
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
