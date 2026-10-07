#!/usr/bin/env python3
"""
Kapitel 25 – Hybrid A: Ereignisse über MQTT, kontinuierliche Werte über REST.

Warum hybrid?
  * Diskrete Gesten (Tap, Finger zählen, Kreis) sind Ereignisse. Über MQTT +
    Trigger-Channel landen sie in openHAB-Regeln – dort ist die Logik für alle
    sichtbar und ohne Python änderbar (Szenen, Zeitpläne, Bedingungen).
  * Die Helligkeit beim Dimmen ist ein schneller, kontinuierlicher Wert. Ihn als
    Item -> Regel -> Item zu routen, kostet Latenz und erzeugt viele Regelaufrufe.
    Direkt per REST ist es flüssiger.

Bedienung (Raum Multimedia):
  Pinch halten + Hand heben/senken   Helligkeit (REST, direkt)
  KEY_TAP                            Licht an/aus           (MQTT -> Regel)
  FINGERS_1..5                       Szene 1..5             (MQTT -> Regel)
  CIRCLE_CW / CIRCLE_CCW             Farbtemperatur ±10 %   (MQTT -> Regel)

Läuft anstelle des Gateways aus Kapitel 19 (gleiche Topics leap/<alias>/gesture).
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # Repo-Wurzel
from leapsmarthome.gestures import GestureEngine  # noqa: E402
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.mapping import height_percent  # noqa: E402
from leapsmarthome.mqtt import LeapMqtt  # noqa: E402
from leapsmarthome.rest import OpenHABSender  # noqa: E402
from leapsmarthome.runtime import alias, base_parser, live, load, say, sensor_serials  # noqa: E402

DIMMER = "iMultimedia_Hue_Lampen_Helligkeit"


async def main():
    args = base_parser("Hybrid A: Gesten per MQTT, Dimmen per REST").parse_args()
    cfg = load(args)
    engine = GestureEngine({"key_tap", "fingers", "circle", "pinch"})
    mqtt = LeapMqtt.from_config(cfg.section("mqtt"), client_id="leap-hybrid-a").start()
    try:
        async with OpenHABSender.from_config(cfg.section("openhab")) as oh:
            with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor)) as mgr:
                dimming = False
                async for frame in mgr.aframes():
                    who = alias(cfg, frame.serial)
                    hand = frame.hand()
                    mqtt.publish_state(who, "hand", "ON" if hand else "OFF")
                    for ev in engine.update(hand):
                        if ev in ("PINCH", "UNPINCH"):
                            dimming = ev == "PINCH"       # Pinch steuert nur lokal das Dimmen
                            continue
                        if dimming and ev.startswith("FINGERS_"):
                            continue                      # beim Dimmen keine Szenen auslösen
                        mqtt.publish_event(who, "gesture", ev)
                        say(f"MQTT  {who}/gesture = {ev}")
                    if hand and dimming:
                        pct = height_percent(hand.palm_position[1])
                        if await oh.send(DIMMER, pct):
                            live(f"REST  {DIMMER} = {pct}%")
                    elif not hand:
                        dimming = False
    finally:
        mqtt.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBeendet.")
