#!/usr/bin/env python3
"""
Kapitel 7 – Zum Vergleich: die High-Level-API von Ultraleap („import leap“).

Sie erinnert an den Listener aus dem alten SDK v2 (Tutorial 2): Man leitet von
leap.Listener ab und überschreibt on_tracking_event(). Die Abfrage-Schleife läuft
in einem eigenen Thread der Bibliothek.

Installation: pip install -e leapc-python-api  (siehe install_leap_python.sh)

Im restlichen Buch nutzen wir trotzdem LeapC direkt bzw. leapsmarthome.leapdevices,
weil wir volle Kontrolle über Polling, Multi-Device und asyncio brauchen.
"""

import time

import leap


class PalmListener(leap.Listener):
    def on_connection_event(self, event):
        print("Verbunden mit dem Ultraleap-Dienst")

    def on_device_event(self, event):
        try:
            with event.device.open():
                info = event.device.get_info()
        except leap.LeapCannotOpenDeviceError:
            info = event.device.get_info()
        print(f"Controller gefunden: {info.serial}")

    def on_tracking_event(self, event):
        for hand in event.hands:
            seite = "links" if str(hand.type) == "HandType.Left" else "rechts"
            p = hand.palm.position
            print(f"Frame {event.tracking_frame_id}: Hand {seite} "
                  f"X:{p.x:6.1f} Y:{p.y:6.1f} Z:{p.z:6.1f} mm")


def main():
    connection = leap.Connection()
    connection.add_listener(PalmListener())
    with connection.open():
        connection.set_tracking_mode(leap.TrackingMode.Desktop)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nBeendet.")


if __name__ == "__main__":
    main()
