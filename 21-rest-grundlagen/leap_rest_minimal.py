#!/usr/bin/env python3
"""
Kapitel 21 – Kleinstes Leap-REST-Programm: Handhöhe = Helligkeit einer Lampe.

Zeigt das Grundmuster von Ansatz B:
  * Frames asynchron lesen (mgr.aframes) – die asyncio-Schleife blockiert nicht
  * Wert berechnen und quantisieren
  * OpenHABSender.send() sendet nur bei Änderung und höchstens alle 0,1 s
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.mapping import height_percent  # noqa: E402
from leapsmarthome.rest import OpenHABSender  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, sensor_serials  # noqa: E402

ITEM = "iMultimedia_Hue_Lampen_Helligkeit"


async def main():
    args = base_parser("Höhe -> Helligkeit per REST").parse_args()
    cfg = load(args)
    async with OpenHABSender.from_config(cfg.section("openhab")) as oh:
        with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
            async for frame in mgr.aframes():
                hand = frame.hand()
                if hand is None:
                    live("Suche Hand ...")
                    continue
                pct = height_percent(hand.palm_position[1])
                sent = await oh.send(ITEM, pct)
                live(f"Höhe {hand.palm_position[1]:5.0f} mm -> {pct:3}% {'(gesendet)' if sent else ''}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBeendet.")
