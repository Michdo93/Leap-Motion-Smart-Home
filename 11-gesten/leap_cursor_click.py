#!/usr/bin/env python3
"""
Kapitel 11 – Zeigefinger als Cursor, Daumen als Klick
(Idee aus der YouTube-Serie „Leap Motion and Raspberry Pi“, Tutorial 3).

  * Die Zeigefingerspitze (X/Y) wird auf ein virtuelles Raster 0..100 % abgebildet
  * Klick, wenn der Daumen eingeklappt wird (war ausgestreckt -> nicht mehr)
  * Kreis im/gegen den Uhrzeigersinn = Scrollen runter/hoch (Tutorial 4)

Statt einen Desktop-Mauszeiger zu bewegen, zeigen wir den Cursor im Terminal –
in Kapitel 22 wird daraus die Auswahl von Geräten.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.gestures import CircleDetector  # noqa: E402
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.mapping import map_range  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402

X_RANGE = (-150, 150)
Y_RANGE = (120, 350)


def main():
    args = base_parser("Cursor und Klick").parse_args()
    cfg = load(args, required=False)
    circle = CircleDetector()
    thumb_was_extended = True
    scroll = 0
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
        try:
            for frame in mgr.frames():
                hand = frame.hand()
                if hand is None:
                    circle.reset()
                    live("Suche Hand ...")
                    continue
                tx, ty, _ = hand.fingers[1].tip
                cx = map_range(tx, *X_RANGE)
                cy = map_range(ty, *Y_RANGE, invert=True)   # oben = 0 %

                thumb = hand.fingers[0].extended
                if thumb_was_extended and not thumb:
                    say(f"  KLICK bei ({cx:3.0f} %, {cy:3.0f} %)")
                thumb_was_extended = thumb

                ev = circle.update(hand)
                if ev:
                    scroll += 1 if ev == "CIRCLE_CW" else -1
                    say(f"  SCROLL {'runter' if ev == 'CIRCLE_CW' else 'hoch'} -> {scroll}")

                bar = ["."] * 40
                bar[min(39, int(cx / 2.5))] = "+"
                live(f"[{''.join(bar)}] Y {cy:3.0f} % | Daumen {'offen ' if thumb else 'zu    '}")
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
