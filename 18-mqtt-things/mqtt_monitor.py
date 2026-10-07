#!/usr/bin/env python3
"""
Kapitel 18 – Alle Leap-Topics mitlesen (Python-Pendant zu mosquitto_sub -t 'leap/#' -v).
Hilft beim Abgleich: Kommt an, was die Channels in leap_mqtt.things erwarten?
"""

import pathlib
import sys

import paho.mqtt.client as mqtt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.runtime import base_parser, load  # noqa: E402


def main():
    args = base_parser("MQTT-Monitor für leap/#", sensor=False).parse_args()
    m = load(args).section("mqtt")
    base = m.get("base_topic", "leap")

    def on_connect(client, userdata, flags, reason_code, properties):
        print(f"Verbunden ({reason_code}) – abonniere {base}/#")
        client.subscribe(f"{base}/#")

    def on_message(client, userdata, msg):
        flag = "R" if msg.retain else " "
        print(f"{flag} {msg.topic:40} {msg.payload.decode(errors='replace')}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="leap-monitor")
    if m.get("username"):
        client.username_pw_set(m["username"], m.get("password"))
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(m.get("host", "localhost"), int(m.get("port", 1883)))
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")


if __name__ == "__main__":
    main()
