#!/usr/bin/env python3
"""
Kapitel 23 – Samsung TV per Gesten (Ansatz B, ein Sensor = ein Gerät).

  Swipe rechts / links      Programm + / -        (Kanal-Item und keyCode KEY_CHUP/KEY_CHDOWN)
  Pinch + Hand drehen       Lautstärke (Roll wie ein Drehknopf, relativ zum Startwert)
  Flache Hand 1 s halten    Mute umschalten       (TV aus: einschalten)
  Faust 1 s halten          Standby (Power OFF)

Konfliktvermeidung:
  * Während Pinch (Lautstärke) sind Swipes gesperrt – Drehen erzeugt Seitwärtsbewegung
  * Mute braucht offene Hand, Standby eine Faust – die Gesten schließen sich aus
  * Nach jeder Aktion kurze Sperrzeit (Cooldown)
"""

import asyncio
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.gestures import HoldDetector, PinchDetector, RollTracker, SwipeDetector  # noqa: E402
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.mapping import Cooldown, clamp, quantize  # noqa: E402
from leapsmarthome.rest import OpenHABSender  # noqa: E402
from leapsmarthome.runtime import base_parser, live, load, say, sensor_serials  # noqa: E402

TV = "iMultimedia_Samsung_TV"
POWER, VOLUME, MUTE = f"{TV}_Power", f"{TV}_Lautstaerke", f"{TV}_Stumm"
CHANNEL, KEY = f"{TV}_Kanal", f"{TV}_Taste"

FIST_HOLD = 1.0           # s
DEGREES_PER_PERCENT = 2   # 2° Drehung = 1 % Lautstärke


def as_int(value, default):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


async def main():
    args = base_parser("Samsung TV per Leap Motion").parse_args()
    cfg = load(args)
    swipe, pinch, roll, hold = SwipeDetector(), PinchDetector(), RollTracker(), HoldDetector()
    swipe.AXES = "x"
    cooldown = Cooldown(0.8)
    fist_since = None
    volume_start = 0

    async with OpenHABSender.from_config(cfg.section("openhab")) as oh:
        with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
            print("Samsung-TV-Steuerung aktiv (Strg+C beendet)")
            async for frame in mgr.aframes():
                hand = frame.hand()
                if hand is None:
                    swipe.reset()
                    pinch.reset()
                    hold.reset()
                    roll.release()
                    fist_since = None
                    live("Suche Hand ...")
                    continue
                now = time.monotonic()

                # --- Standby: Faust halten -----------------------------------
                if hand.grab_strength > 0.85:
                    fist_since = fist_since or now
                    if now - fist_since >= FIST_HOLD and cooldown.ready():
                        await oh.send(POWER, "OFF", force=True)
                        say("FAUST -> Standby")
                        cooldown.trigger()
                    live(f"Faust {now - fist_since:3.1f} s")
                    continue
                fist_since = None

                # --- Lautstärke: Pinch + Drehen -------------------------------
                ev = pinch.update(hand)
                if ev == "PINCH":
                    roll.engage(hand)
                    volume_start = as_int(await oh.state(VOLUME), 20)
                    say(f"Lautstärke-Regler eingerastet bei {volume_start}%")
                elif ev == "UNPINCH":
                    roll.release()
                if roll.reference is not None:
                    # Drehung im Uhrzeigersinn (Daumen nach unten) = lauter
                    vol = int(clamp(volume_start - roll.delta(hand) / DEGREES_PER_PERCENT, 0, 100))
                    await oh.send(VOLUME, quantize(vol, 2))
                    live(f"Lautstärke {vol:3}% (Roll {roll.delta(hand):+5.0f}°)")
                    continue

                # --- Programm: Swipe -------------------------------------------
                sw = swipe.update(hand)
                if sw in ("SWIPE_LEFT", "SWIPE_RIGHT") and cooldown.ready():
                    step = 1 if sw == "SWIPE_RIGHT" else -1
                    current = as_int(await oh.state(CHANNEL), 1)
                    new = max(1, current + step)
                    await oh.send(CHANNEL, new, force=True)
                    await oh.send(KEY, "KEY_CHUP" if step > 0 else "KEY_CHDOWN", force=True)
                    say(f"{sw} -> Programm {new}")
                    cooldown.trigger()

                # --- Mute / Einschalten: flache Hand halten --------------------
                if hold.update(hand) == "HOLD_FLAT" and cooldown.ready():
                    if await oh.state(POWER) != "ON":
                        await oh.send(POWER, "ON", force=True)
                        say("FLACHE HAND -> TV ein")
                    else:
                        muted = await oh.state(MUTE) == "ON"
                        await oh.send(MUTE, "OFF" if muted else "ON", force=True)
                        say(f"FLACHE HAND -> Mute {'aus' if muted else 'an'}")
                    cooldown.trigger()

                live(f"bereit | Finger {hand.extended_count} | Roll {hand.roll:5.0f}°")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBeendet.")
