#!/usr/bin/env python3
"""
Kapitel 12 – Mehrere Controller an einem Raspberry Pi.

Eine LeapC-Verbindung (multi device aware), alle Sensoren abonniert. Jede Zeile
zeigt einen Sensor – identifiziert über die Seriennummer bzw. den Alias aus
config.yaml. Ab-/Anstecken wird gemeldet; nach dem Wiederanstecken landet der
Sensor wieder in derselben Zeile, auch wenn sich die Laufzeit-ID geändert hat.

Hardware-Hinweis: Der LM-010 braucht viel USB-2.0-Bandbreite. Für mehrere
Controller oder Verlängerungen > 2 m aktive Hubs/Repeaterkabel verwenden.
"""

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import alias, base_parser, load, sensor_serials  # noqa: E402


def main():
    args = base_parser("Mehrere Controller live anzeigen").parse_args()
    cfg = load(args, required=False)
    rows = {}
    events = []

    def added(info):
        events.append(f"{time.strftime('%H:%M:%S')} + {alias(cfg, info.serial)} ({info.serial}, ID {info.device_id})")

    def removed(info):
        events.append(f"{time.strftime('%H:%M:%S')} - {alias(cfg, info.serial)} getrennt")
        rows[info.serial] = "GETRENNT"

    last = 0.0
    print("\033[2J", end="")
    with LeapDeviceManager(serials=sensor_serials(cfg, args.sensor),
                           on_device_added=added, on_device_removed=removed) as mgr:
        try:
            for frame in mgr.frames(timeout_ms=50):
                h = frame.hand()
                if h:
                    x, y, z = h.palm_position
                    rows[frame.serial] = (f"{frame.fps:4.0f} fps | {'L' if h.is_left else 'R'} "
                                          f"X:{x:6.0f} Y:{y:6.0f} Z:{z:6.0f} | Finger {h.extended_count}")
                else:
                    rows[frame.serial] = f"{frame.fps:4.0f} fps | keine Hand"
                if time.time() - last < 0.1:
                    continue
                last = time.time()
                print("\033[H" + f"{'Alias':12} {'Seriennummer':16} Daten")
                print("-" * 80)
                for serial in sorted(set(rows) | set(mgr.devices)):
                    print(f"{alias(cfg, serial):12} {serial:16} {rows.get(serial, '...'):50}")
                print("\nEreignisse:")
                for e in events[-5:]:
                    print(f"  {e:70}")
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
