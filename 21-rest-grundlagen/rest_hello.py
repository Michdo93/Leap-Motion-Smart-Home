#!/usr/bin/env python3
"""
Kapitel 21 – Erste Schritte mit python-openhab-rest-client (ohne Leap Motion).

  1. Verbindung mit API-Token aus config.yaml
  2. Zustand eines Items lesen
  3. Befehl senden (sendCommand) – das Gerät soll etwas tun
  4. Zustand setzen (updateItemState / postUpdate) – nur Anzeige, kein Befehl
  5. Zustand erneut lesen

Richtige Imports (asynchrone Variante):
    from openhab.AsyncClient import AsyncOpenHABClient
    from openhab.AsyncItems import AsyncItems
"""

import asyncio
import pathlib
import sys

from openhab.AsyncClient import AsyncOpenHABClient
from openhab.AsyncItems import AsyncItems

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.runtime import base_parser, load  # noqa: E402

ITEM = "iMultimedia_Hue_Lampen_Helligkeit"


async def main():
    args = base_parser("REST-Grundlagen", sensor=False).parse_args()
    oh = load(args).section("openhab")

    async with AsyncOpenHABClient(url=oh["url"], token=oh.get("token"),
                                  username=oh.get("username"), password=oh.get("password")) as client:
        if not client.isLoggedIn:
            sys.exit(f"openHAB unter {oh['url']} nicht erreichbar oder Token ungültig")
        items = AsyncItems(client)

        print(f"1) Zustand {ITEM}:", await items.getItemState(ITEM))
        print("2) sendCommand 40 ->", await items.sendCommand(ITEM, "40"))
        await asyncio.sleep(0.5)
        print("   Zustand jetzt:", await items.getItemState(ITEM))
        print("3) updateItemState 60 ->", await items.updateItemState(ITEM, "60"))
        print("   Zustand jetzt:", await items.getItemState(ITEM))

        info = await items.getItem(ITEM)
        if isinstance(info, dict):
            print(f"4) Typ: {info.get('type')} | Label: {info.get('label')} | Tags: {info.get('tags')}")


if __name__ == "__main__":
    asyncio.run(main())
