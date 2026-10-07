#!/usr/bin/env python3
"""
Kapitel 22 – Hue-Lampen per REST (überarbeitete Fassung von leap_lights_oh.py).

  Zonen:  hinten (Z < 0): Küche | Bad | IoT       vorne (Z >= 0): Smart Home | Multimedia
  Höhe (Y)  = Helligkeit 0..100 %
  Tiefe (Z) = Farbton 0..360°
Gesendet wird HSB an <Raum>_Hue_Lampen_Farbe und ON/OFF an <Raum>_Hue_Lampen_Schalter.
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.mapping import Zone, ZoneSet, map_range, quantize  # noqa: E402
from leapsmarthome.rest import OpenHABSender  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402

ROOMS = ZoneSet([
    Zone("iKueche",     x=(-400, -131), z=(-300, -1)),
    Zone("iBad",        x=(-130, 129),  z=(-300, -1)),
    Zone("iIoT",        x=(130, 400),   z=(-300, -1)),
    Zone("iSmartHome",  x=(-400, -1),   z=(0, 300)),
    Zone("iMultimedia", x=(0, 400),     z=(0, 300)),
])
Y_MIN, Y_MAX = 80, 400


async def main():
    args = base_parser("Hue-Lampen per Leap Motion").parse_args()
    cfg = load(args)
    print("ASYNC HUE-CONTROLLER: Höhe = Helligkeit | Tiefe = Farbe")
    async with OpenHABSender.from_config(cfg.section("openhab")) as oh:
        oh.min_interval = 0.2            # Hue-Bridges sind träge
        with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
            last_room = None
            async for frame in mgr.aframes():
                hand = frame.hand()
                if hand is None:
                    live("Suche Hand ...")
                    continue
                x, y, z = hand.palm_position
                room = ROOMS.find(hand.palm_position)
                if room is None:
                    continue
                bri = quantize(map_range(y, Y_MIN, Y_MAX), 5)
                hue = quantize(map_range(z, -200, 200, 0, 360), 5) % 360
                live(f"RAUM: {room:12} | BRI: {bri:3}% | HUE: {hue:3}° | X:{x:4.0f} Z:{z:4.0f}")
                if room != last_room:
                    say(f"Raum gewechselt: {room}")
                    last_room = room
                if await oh.send(f"{room}_Hue_Lampen_Farbe", f"{hue},100,{bri}"):
                    await oh.send(f"{room}_Hue_Lampen_Schalter", "ON" if bri > 5 else "OFF")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBeendet.")
