#!/usr/bin/env python3
"""
Kapitel 22 – Somfy-Rollläden per REST (überarbeitete Fassung von leap_rollladen_oh.py,
jetzt mit dem richtigen Import über leapsmarthome.rest / openhab.AsyncClient).

  Zone 1..4 entlang X: Multimedia | Konferenz 2 | Konferenz 1 | Smart Home
  Höhe: oben (>= 450 mm) = 0 % offen, unten (<= 100 mm) = 100 % zu
  Schneller Wisch hoch/runter = ganz auf/zu (danach 2 s Höhensperre)
"""

import asyncio
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.gestures import SwipeDetector  # noqa: E402
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.mapping import ZoneSet, height_percent  # noqa: E402
from leapsmarthome.rest import OpenHABSender  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402

SHUTTER_ITEMS = {
    "1": "iMultimedia_Somfy_Rollladen_Steuerung_Prozent",
    "2": "iKonferenz_Somfy_Rollladen2_Steuerung_Prozent",
    "3": "iKonferenz_Somfy_Rollladen1_Steuerung_Prozent",
    "4": "iSmartHome_Somfy_Rollladen_Steuerung_Prozent",
}
ZONES = ZoneSet.columns(list(SHUTTER_ITEMS), boundaries=[-150, 0, 150])


async def main():
    args = base_parser("Rollläden per Leap Motion").parse_args()
    cfg = load(args)
    swipe = SwipeDetector()
    swipe.AXES = "y"
    swipe.THRESHOLD = 600
    lock_until = 0.0
    async with OpenHABSender.from_config(cfg.section("openhab")) as oh:
        with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
            async for frame in mgr.aframes():
                hand = frame.hand()
                if hand is None:
                    swipe.reset()
                    live("Suche Hand ...")
                    continue
                x, y, _ = hand.palm_position
                zone = ZONES.find(hand.palm_position)
                if zone is None:
                    continue
                item = SHUTTER_ITEMS[zone]
                ev = swipe.update(hand)
                if ev in ("SWIPE_UP", "SWIPE_DOWN"):
                    pct = 0 if ev == "SWIPE_UP" else 100
                    await oh.send(item, pct, force=True)
                    say(f"{ev} -> Rollladen {zone} auf {pct}%")
                    lock_until = time.monotonic() + 2.0
                    continue
                if time.monotonic() < lock_until:
                    continue
                pct = height_percent(y, 100, 450, invert=True)
                live(f"LIVE: X:{x:4.0f} Y:{y:4.0f} | Z{zone} | Ziel: {pct:3}%")
                if await oh.send(item, pct):
                    say(f"POS -> Rollladen {zone} auf {pct}%")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBeendet.")
