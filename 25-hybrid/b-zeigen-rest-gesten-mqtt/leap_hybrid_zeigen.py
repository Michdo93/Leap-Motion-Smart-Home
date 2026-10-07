#!/usr/bin/env python3
"""
Kapitel 25 – Hybrid B: Auf Geräte zeigen.

Python wertet aus, WOHIN der Zeigefinger zeigt, und setzt das Kontext-Item
Leap_Multimedia_Ziel per REST (postUpdate). Die Gesten selbst gehen per MQTT an
openHAB; dort entscheidet eine Regel anhand des Ziels, welches Gerät reagiert.

Rückkopplung: Das Item Leap_Multimedia_Freigabe (Switch) wird per SSE gelesen.
Ist es OFF (z. B. nachts oder per Regel bei Abwesenheit), veröffentlicht das
Programm keine Gesten – openHAB steuert also das Verhalten des Python-Programms.

Zeigen = Zeigefinger gestreckt, Mittel-/Ring-/kleiner Finger gebeugt, 0,5 s ruhig.
Richtung = Gierwinkel (Yaw) des Zeigefinger-Endglieds, 0° = geradeaus zum Bildschirm.
"""

import asyncio
import math
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # Repo-Wurzel
from leapsmarthome.gestures import GestureEngine  # noqa: E402
from leapsmarthome.leapdevices import Hand, LeapDeviceManager  # noqa: E402
from leapsmarthome.mqtt import LeapMqtt  # noqa: E402
from leapsmarthome.rest import OpenHABSender  # noqa: E402
from leapsmarthome.runtime import alias, base_parser, live, load, say, sensor_serials  # noqa: E402

# Sektoren in Grad (an die Aufstellung der Geräte im Raum anpassen)
TARGETS = {
    "ROLLLADEN": (-75, -30),
    "LICHT":     (-30, 0),
    "TV":        (0, 30),
    "RADIO":     (30, 75),
}
TARGET_ITEM = "Leap_Multimedia_Ziel"
ENABLE_ITEM = "Leap_Multimedia_Freigabe"
POINT_STABLE = 0.5   # s


def pointing(hand: Hand) -> bool:
    f = hand.fingers
    return f[1].extended and not (f[2].extended or f[3].extended or f[4].extended)


def pointing_yaw(hand: Hand) -> float:
    dx, _, dz = hand.fingers[1].direction
    return math.degrees(math.atan2(dx, -dz))


def target_for(yaw: float):
    for name, (lo, hi) in TARGETS.items():
        if lo <= yaw < hi:
            return name
    return None


async def main():
    args = base_parser("Hybrid B: Zeigen per REST, Gesten per MQTT").parse_args()
    cfg = load(args)
    engine = GestureEngine({"swipe", "key_tap", "circle", "grab"})
    mqtt = LeapMqtt.from_config(cfg.section("mqtt"), client_id="leap-hybrid-b").start()
    enabled = {"on": True}

    try:
        async with OpenHABSender.from_config(cfg.section("openhab")) as oh:
            enabled["on"] = (await oh.state(ENABLE_ITEM)) != "OFF"

            async def follow_enable():
                async for _, value in oh.watch_states([ENABLE_ITEM]):
                    enabled["on"] = value != "OFF"
                    say(f"[openHAB] Freigabe {'AN' if enabled['on'] else 'AUS'}")

            watcher = asyncio.create_task(follow_enable())
            candidate, since, current = None, 0.0, None
            try:
                with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
                    async for frame in mgr.aframes():
                        who = alias(cfg, frame.serial)
                        hand = frame.hand()
                        events = engine.update(hand)
                        if hand is None:
                            live(f"Ziel: {current or '-'} | Suche Hand ...")
                            continue

                        # 1) Zielauswahl durch Zeigen (Kontext per REST)
                        if pointing(hand):
                            yaw = pointing_yaw(hand)
                            t = target_for(yaw)
                            if t != candidate:
                                candidate, since = t, time.monotonic()
                            elif t and t != current and time.monotonic() - since >= POINT_STABLE:
                                current = t
                                await oh.update(TARGET_ITEM, t)
                                say(f"REST  {TARGET_ITEM} = {t} (Yaw {yaw:+.0f}°)")
                            live(f"Zeigen: Yaw {yaw:+5.0f}° -> {t or '-':9} | Ziel: {current or '-'}")
                            continue   # beim Zeigen keine Gesten auslösen

                        # 2) Gesten per MQTT – nur mit Freigabe aus openHAB
                        for ev in events:
                            if enabled["on"]:
                                mqtt.publish_event(who, "gesture", ev)
                                say(f"MQTT  {who}/gesture = {ev} (Ziel {current or '-'})")
                        live(f"Ziel: {current or '-'} | Freigabe: {'an' if enabled['on'] else 'aus'}")
            finally:
                watcher.cancel()
    finally:
        mqtt.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBeendet.")
