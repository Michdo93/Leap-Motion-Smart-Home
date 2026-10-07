#!/usr/bin/env python3
"""
Kapitel 22 – Sonos/Webradio per REST (überarbeitete Fassung von leap_webradio_oh.py).

  Höhe (Y)          = Lautstärke (nur bei offener Hand)
  Faust             = aktueller Sender AUS, Hand öffnen = wieder AN
  Wischen links/re. = vorheriger/nächster Sender
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.gestures import GrabDetector, SwipeDetector  # noqa: E402
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.mapping import height_percent  # noqa: E402
from leapsmarthome.rest import OpenHABSender  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402

ROOM = "iMultimedia"
VOL_ITEM = f"{ROOM}_Sonos_Lautsprecher_Lautstaerke"
STATIONS = ["SWR3", "bigFM_BW", "Energy_Stuttgart", "Radio_Regenbogen", "Antenne1", "DASDING"]


def station_item(idx):
    return f"{ROOM}_Webradio_{STATIONS[idx]}"


async def main():
    args = base_parser("Webradio per Leap Motion").parse_args()
    cfg = load(args)
    grab, swipe = GrabDetector(), SwipeDetector()
    swipe.AXES, swipe.THRESHOLD, swipe.COOLDOWN = "x", 800, 1.2
    idx = 0
    async with OpenHABSender.from_config(cfg.section("openhab")) as oh:
        with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
            async for frame in mgr.aframes():
                hand = frame.hand()
                if hand is None:
                    swipe.reset()
                    live("Suche Hand ...")
                    continue

                ev = grab.update(hand)
                if ev == "GRAB":
                    await oh.send(station_item(idx), "OFF", force=True)
                    say("[AKTION] Faust -> STOP")
                elif ev in ("RELEASE", "FIST_TAP"):
                    await oh.send(station_item(idx), "ON", force=True)
                    say("[AKTION] Hand offen -> START")

                if not grab.closed:
                    await oh.send(VOL_ITEM, height_percent(hand.palm_position[1], 100, 400))
                    sw = swipe.update(hand)
                    if sw in ("SWIPE_LEFT", "SWIPE_RIGHT"):
                        await oh.send(station_item(idx), "OFF", force=True)
                        idx = (idx + (1 if sw == "SWIPE_RIGHT" else -1)) % len(STATIONS)
                        await oh.send(station_item(idx), "ON", force=True)
                        say(f"[SENDER] Wechsel zu: {STATIONS[idx]}")

                live(f"Y: {hand.palm_position[1]:3.0f} | Grab: {hand.grab_strength:.2f} | Sender: {STATIONS[idx]}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBeendet.")
