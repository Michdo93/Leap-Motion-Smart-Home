#!/usr/bin/env python3
"""
Kapitel 12 – Rollladen-Steuerung für GENAU EINEN Sensor (korrigierte Fassung von
leap_rollladen3.py).

In leap_rollladen3.py wurde die Seriennummer zwar gefunden, die Frames aber nicht
gefiltert (der Vergleich mit tracking_event.info.reserved endete in "pass").
Hier abonniert LeapDeviceManager nur den gewünschten Sensor – Frames anderer
Controller kommen gar nicht erst an. Mehrere Instanzen (je Sensor ein Prozess)
laufen so problemlos parallel:

    python3 leap_rollladen_serial.py --sensor LP19566274693
    python3 leap_rollladen_serial.py --sensor konferenz        # Alias aus config.yaml
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.mapping import ZoneSet, height_percent  # noqa: E402
from leapsmarthome.runtime import alias, base_parser, live, load, say, sensor_serials  # noqa: E402

ZONES = ZoneSet.columns(["1", "2", "3", "4"], boundaries=[-150, 0, 150])
SWIPE_THRESHOLD = 600


def main():
    args = base_parser("Rollladen für einen bestimmten Sensor").parse_args()
    if not args.sensor or len(args.sensor) != 1:
        sys.exit("Bitte genau einen Sensor angeben: --sensor <Seriennummer|Alias>")
    cfg = load(args, required=False)
    serials = sensor_serials(cfg, args.sensor)
    target = next(iter(serials))
    name = alias(cfg, target)

    with LeapDeviceManager(serials=serials) as mgr:
        print(f"--- ROLLLADEN-STEUERUNG ({name}) ---\nSuche nach Sensor {target} ...")
        while not mgr.wait_for_devices(5.0):
            print("  noch nicht gefunden – warte weiter (USB/USB-IP prüfen)")
        print("Sensor gefunden.\n")

        last = (None, None)
        try:
            for frame in mgr.frames(timeout_ms=20):
                hand = frame.hand()
                if hand is None:
                    live("Suche Hand ...")
                    continue
                x, y, _ = hand.palm_position
                vy = hand.palm_velocity[1]
                zone = ZONES.find(hand.palm_position)
                pct = height_percent(y, 100, 450, invert=True)
                if vy > SWIPE_THRESHOLD:
                    pct = 0
                elif vy < -SWIPE_THRESHOLD:
                    pct = 100
                live(f"[{name}] X:{x:4.0f} Y:{y:4.0f} | Z{zone or '-'} | Ziel: {pct:3}%")
                if zone and (zone, pct) != last:
                    say(f"[{name}] Rollladen {zone} -> {pct}%")
                    last = (zone, pct)
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
