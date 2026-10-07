#!/usr/bin/env python3
"""
Kapitel 22 – Jalousien per REST, 2x2-Matrix (überarbeitete Fassung von leap_jalousie_oh.py).

    [Küche hinten] [Bad hinten]
    [Küche vorne ] [Bad vorne ]
Höhe: oben = offen (0 %), unten = geschlossen (100 %).
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.mapping import height_percent  # noqa: E402
from leapsmarthome.rest import OpenHABSender  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402

JALOUSIE_MAP = {
    "HINTEN_LINKS":  "iKueche_Jalousie_Hinten_Steuerung_Prozent",
    "HINTEN_RECHTS": "iBad_Jalousie_Hinten_Steuerung_Prozent",
    "VORNE_LINKS":   "iKueche_Jalousie_Vorne_Steuerung_Prozent",
    "VORNE_RECHTS":  "iBad_Jalousie_Vorne_Steuerung_Prozent",
}
Y_MIN, Y_MAX = 100, 450


async def main():
    args = base_parser("Jalousien per Leap Motion").parse_args()
    cfg = load(args)
    async with OpenHABSender.from_config(cfg.section("openhab")) as oh:
        with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
            async for frame in mgr.aframes():
                hand = frame.hand()
                if hand is None:
                    live("Suche Hand ...")
                    continue
                x, y, z = hand.palm_position
                key = f"{'HINTEN' if z < 0 else 'VORNE'}_{'LINKS' if x < 0 else 'RECHTS'}"
                item = JALOUSIE_MAP[key]
                pct = height_percent(y, Y_MIN, Y_MAX, invert=True)
                live(f"QUADRANT: {key:14} | {pct:3}%")
                if await oh.send(item, pct):
                    say(f"AKTION: {item} -> {pct}%")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBeendet.")
