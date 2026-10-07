#!/usr/bin/env python3
"""
Kapitel 12 – Ein Prozess, mehrere Sensoren, verschiedene Aufgaben.

Jeder Sensor (Alias aus config.yaml) bekommt eine Rolle. Der Router verteilt die
Frames anhand der Seriennummer an die passende Logik – mit eigenem Zustand pro
Sensor. Das ist die Grundlage für „ein Sensor pro Gerät“ (Kapitel 15).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.gestures import GestureEngine  # noqa: E402
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.mapping import ChangeFilter, height_percent  # noqa: E402
from leapsmarthome.runtime import alias, base_parser, load, say  # noqa: E402

# Alias -> Rolle (anpassen)
ROLES = {
    "multimedia": "rollladen",
    "konferenz": "licht",
    "kueche": "webradio",
    "tv": "fernseher",
}


class Role:
    def __init__(self, name):
        self.name = name
        self.engine = GestureEngine({"swipe", "grab", "circle"})
        self.filter = ChangeFilter(min_interval=0.1)

    def handle(self, who, hand):
        events = self.engine.update(hand)
        if hand is None:
            return
        pct = height_percent(hand.palm_position[1])
        if self.filter.changed("pct", pct):
            say(f"[{who}/{self.name}] Höhe -> {pct}%")
        for ev in events:
            say(f"[{who}/{self.name}] Geste {ev}")


def main():
    args = base_parser("Sensoren nach Rollen verteilen", sensor=False).parse_args()
    cfg = load(args)
    roles = {}
    with LeapDeviceManager(serials=set(cfg.devices) or None) as mgr:
        try:
            for frame in mgr.frames():
                who = alias(cfg, frame.serial)
                role = roles.get(frame.serial)
                if role is None:
                    role = roles[frame.serial] = Role(ROLES.get(who, "unbekannt"))
                    say(f"Sensor {who} ({frame.serial}) -> Rolle {role.name}")
                role.handle(who, frame.hand())
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
