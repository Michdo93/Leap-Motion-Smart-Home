#!/usr/bin/env python3
"""
Kapitel 7 – Die Event-Schleife von LeapC (entspricht Tutorial 2 und 3 der Serie
„Leap Motion and Python“: Listener und Frame Data).

Statt eines Listeners mit on_frame() (SDK v2) fragen wir in LeapC selbst ab:
    LeapPollConnection(connection, timeout_ms, message)
Jede Nachricht hat einen Typ (Connection, Device, Tracking, Policy, ...).
Das Programm zählt alle Ereignistypen und zeigt die Frame-Kopfdaten.
"""

import collections
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapc import ffi, libleapc  # noqa: E402

EVENT_NAMES = {getattr(libleapc, n): n.replace("eLeapEventType_", "")
               for n in dir(libleapc) if n.startswith("eLeapEventType_")}


def main():
    conn = ffi.new("LEAP_CONNECTION *")
    if libleapc.LeapCreateConnection(ffi.NULL, conn) != libleapc.eLeapRS_Success:
        sys.exit("LeapCreateConnection fehlgeschlagen")
    if libleapc.LeapOpenConnection(conn[0]) != libleapc.eLeapRS_Success:
        sys.exit("LeapOpenConnection fehlgeschlagen")

    msg = ffi.new("LEAP_CONNECTION_MESSAGE *")
    counter = collections.Counter()
    last_print = time.time()

    print("Ereignisse werden gezählt (Strg+C beendet) ...\n")
    try:
        while True:
            res = libleapc.LeapPollConnection(conn[0], 100, msg)
            if res != libleapc.eLeapRS_Success:
                continue                       # Timeout: einfach weiter warten
            name = EVENT_NAMES.get(msg.type, str(msg.type))
            counter[name] += 1

            if msg.type == libleapc.eLeapEventType_Tracking:
                ev = msg.tracking_event
                if time.time() - last_print > 0.5:
                    last_print = time.time()
                    print(f"Frame {ev.tracking_frame_id:8d} | Zeitstempel {ev.info.timestamp} µs | "
                          f"{ev.framerate:5.1f} fps | Hände: {ev.nHands} | "
                          f"Ereignisse: {dict(counter)}")
            elif msg.type != libleapc.eLeapEventType_Tracking:
                print(f"-> {name}")
    except KeyboardInterrupt:
        print(f"\nBeendet. Summe: {dict(counter)}")
    finally:
        libleapc.LeapCloseConnection(conn[0])
        libleapc.LeapDestroyConnection(conn[0])


if __name__ == "__main__":
    main()
