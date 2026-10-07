#!/usr/bin/env python3
"""
Kapitel 9 – Finger (entspricht Tutorial 6 „Finger and Bone Data“, Teil 1).

Für jeden Finger: ausgestreckt ja/nein, Position der Fingerspitze, Zeigerichtung.
Die Anzahl ausgestreckter Finger ersetzt das Ereignis fingersX_YYY des openHAB-Bindings.

Hinweis zu Tutorial 7 „Tool Data“: Werkzeug-Tracking (Stifte) gibt es in
Ultraleap Gemini nicht mehr.
"""

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import FINGER_NAMES, LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import base_parser, load, sensor_serials  # noqa: E402


def main():
    args = base_parser("Fingerdaten ausgeben").parse_args()
    cfg = load(args, required=False)
    last = 0.0
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            for frame in mgr.frames():
                h = frame.hand()
                if h is None or time.time() - last < 0.3:
                    continue
                last = time.time()
                print("\033[2J\033[H", end="")
                print(f"Hand {'links' if h.is_left else 'rechts'} – "
                      f"{h.extended_count} Finger ausgestreckt, Höhe {h.palm_position[1]:.0f} mm "
                      f"(Binding-Äquivalent: fingers{h.extended_count}_{int(h.palm_position[1])})\n")
                for name, f in zip(FINGER_NAMES, h.fingers):
                    t, d = f.tip, f.direction
                    print(f"  {name:15} {'gestreckt' if f.extended else 'gebeugt  '}  "
                          f"Spitze ({t[0]:6.0f},{t[1]:6.0f},{t[2]:6.0f})  "
                          f"Richtung ({d[0]:5.1f},{d[1]:5.1f},{d[2]:5.1f})")
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
