#!/usr/bin/env python3
"""
Kapitel 24 – Relative Lautstärke mit Rückkanal.

Problem ohne Rückkanal: Ändert jemand die Lautstärke per App, kennt das Python-
Programm den neuen Wert nicht – die nächste Geste springt auf den alten Wert.
Lösung: Ein SSE-Task hält den aktuellen Zustand aktuell; die Geste ändert relativ.

  Pinch + Hand heben/senken   Lautstärke relativ ±
  Wischen hoch / runter       ±10 %
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.gestures import PinchDetector, SwipeDetector  # noqa: E402
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.mapping import clamp  # noqa: E402
from leapsmarthome.rest import OpenHABSender  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402

ITEM = "iMultimedia_Sonos_Lautsprecher_Lautstaerke"
MM_PER_PERCENT = 3.0


async def main():
    args = base_parser("Relative Lautstärke mit SSE-Rückkanal").parse_args()
    cfg = load(args)
    state = {"volume": 20.0}

    async with OpenHABSender.from_config(cfg.section("openhab")) as oh:
        initial = await oh.state(ITEM)
        try:
            state["volume"] = float(initial)
        except (TypeError, ValueError):
            pass

        async def follow():
            async for item, value in oh.watch_states([ITEM]):
                try:
                    v = float(value)
                except ValueError:
                    continue
                if abs(v - state["volume"]) >= 1:
                    say(f"[Rückkanal] {item} extern geändert -> {v:.0f}%")
                    state["volume"] = v
                    oh.forget(ITEM)

        watcher = asyncio.create_task(follow())
        pinch, swipe = PinchDetector(), SwipeDetector()
        swipe.AXES = "y"
        anchor_y, anchor_vol = None, 0.0
        try:
            with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
                async for frame in mgr.aframes():
                    hand = frame.hand()
                    if hand is None:
                        pinch.reset()
                        swipe.reset()
                        anchor_y = None
                        live(f"Lautstärke {state['volume']:3.0f}% | Suche Hand ...")
                        continue
                    y = hand.palm_position[1]
                    ev = pinch.update(hand)
                    if ev == "PINCH":
                        anchor_y, anchor_vol = y, state["volume"]
                    elif ev == "UNPINCH":
                        anchor_y = None
                    if anchor_y is not None:
                        state["volume"] = clamp(anchor_vol + (y - anchor_y) / MM_PER_PERCENT, 0, 100)
                        await oh.send(ITEM, round(state["volume"]))
                    else:
                        sw = swipe.update(hand)
                        if sw in ("SWIPE_UP", "SWIPE_DOWN"):
                            state["volume"] = clamp(state["volume"] + (10 if sw == "SWIPE_UP" else -10), 0, 100)
                            await oh.send(ITEM, round(state["volume"]), force=True)
                            say(f"{sw} -> {state['volume']:.0f}%")
                    live(f"Lautstärke {state['volume']:3.0f}% | Pinch {'aktiv' if anchor_y is not None else '-'}")
        finally:
            watcher.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBeendet.")
