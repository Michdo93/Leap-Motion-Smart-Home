#!/usr/bin/env python3
"""
Kapitel 10 – 3x3-Raster mit Totzone in der Mitte (Grundlage von leap_pepper.py).

Mittelfeld ±LIMIT mm = STOPP. Nur das jeweils neueste Frame wird verarbeitet
(poll_latest), damit bei langsamer Ausgabe kein Rückstau entsteht.
"""

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import base_parser, load, sensor_serials  # noqa: E402

LIMIT = 25.0          # mm – halbe Breite der Mittelzone
SAMPLE_DELAY = 0.3    # s


def cell(x, z, limit=LIMIT):
    """(row, col) mit -1/0/1. row -1 = vorne (Körper), col -1 = links."""
    col = -1 if x < -limit else (1 if x > limit else 0)
    row = -1 if z > limit else (1 if z < -limit else 0)
    return row, col


def main():
    args = base_parser("3x3-Raster").parse_args()
    cfg = load(args, required=False)
    print("\033[2J", end="")
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            while True:
                frames = mgr.poll_latest()
                frame = next(iter(frames.values()), None)
                hand = frame.hand() if frame else None
                grid = [[" "] * 3 for _ in range(3)]
                if hand:
                    row, col = cell(hand.palm_position[0], hand.palm_position[2])
                    grid[row + 1][col + 1] = "X"
                print("\033[H3x3-RASTER (vorne = zum Körper)\n")
                for i, label in enumerate(("VORNE", "MITTE", "HINTEN")):
                    print("  +---+---+---+")
                    print(f"  | {' | '.join(grid[i])} |  {label}")
                print("  +---+---+---+")
                time.sleep(SAMPLE_DELAY)
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
