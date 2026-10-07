#!/usr/bin/env python3
"""
Kapitel 24 – Rückkanal: Zustandsänderungen von Items per Server-Sent Events (SSE).

openHAB meldet Änderungen unter /rest/events?topics=openhab/items/<Item>/statechanged.
Hinweis: AsyncEvents aus python-openhab-rest-client ruft intern eine private
Methode auf; deshalb liest OpenHABSender.watch_states() den Stream direkt über die
aiohttp-Session des Clients – inklusive automatischem Reconnect.
"""

import asyncio
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.rest import OpenHABSender  # noqa: E402
from leapsmarthome.runtime import base_parser, load  # noqa: E402

DEFAULT_ITEMS = [
    "iMultimedia_Sonos_Lautsprecher_Lautstaerke",
    "iMultimedia_Samsung_TV_Lautstaerke",
    "iMultimedia_Hue_Lampen_Farbe",
]


async def main():
    ap = base_parser("Item-Änderungen live verfolgen", sensor=False)
    ap.add_argument("items", nargs="*", default=DEFAULT_ITEMS)
    args = ap.parse_args()
    cfg = load(args)
    async with OpenHABSender.from_config(cfg.section("openhab")) as oh:
        print("Beobachte:", ", ".join(args.items))
        async for item, state in oh.watch_states(args.items):
            print(f"{time.strftime('%H:%M:%S')}  {item:45} -> {state}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBeendet.")
