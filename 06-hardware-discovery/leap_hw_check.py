#!/usr/bin/env python3
"""
Kapitel 6 – Hardware-Check: alle Felder von LEAP_DEVICE_INFO je Controller ausgeben.

Überarbeitete Fassung von leap_hw_check.py (ohne Windows-DLL-Workaround):
  * Seriennummer in zwei Schritten lesen (1. Aufruf liefert die Länge)
  * Produkt (PID) im Klartext
  * Sichtfeld in Grad, Reichweite und Kamera-Basisabstand in mm
"""

import math
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapc import ffi, libleapc  # noqa: E402

PID_NAMES = {getattr(libleapc, n): n.replace("eLeapDevicePID_", "")
             for n in dir(libleapc) if n.startswith("eLeapDevicePID_")}


def read_device_info(device_ref):
    h_dev = ffi.new("LEAP_DEVICE *")
    if libleapc.LeapOpenDevice(device_ref, h_dev) != libleapc.eLeapRS_Success:
        return None
    try:
        info = ffi.new("LEAP_DEVICE_INFO *")
        info.size = ffi.sizeof("LEAP_DEVICE_INFO")
        info.serial = ffi.NULL
        libleapc.LeapGetDeviceInfo(h_dev[0], info)        # Länge ermitteln
        buf = ffi.new("char[]", max(info.serial_length, 1))
        info.serial = buf
        if libleapc.LeapGetDeviceInfo(h_dev[0], info) != libleapc.eLeapRS_Success:
            return None
        return {
            "serial": ffi.string(info.serial).decode("utf-8", "replace"),
            "device_id": device_ref.id,
            "produkt": PID_NAMES.get(info.pid, hex(info.pid)),
            "status": hex(info.status),
            "caps": hex(info.caps),
            "basisabstand": f"{info.baseline / 1000:.1f} mm",
            "sichtfeld_h": f"{math.degrees(info.h_fov):.0f}°",
            "sichtfeld_v": f"{math.degrees(info.v_fov):.0f}°",
            "reichweite": f"{info.range / 1000:.0f} mm",
        }
    finally:
        libleapc.LeapCloseDevice(h_dev[0])


def main():
    conn = ffi.new("LEAP_CONNECTION *")
    libleapc.LeapCreateConnection(ffi.NULL, conn)
    libleapc.LeapOpenConnection(conn[0])
    msg = ffi.new("LEAP_CONNECTION_MESSAGE *")
    print("Warte 5 Sekunden auf Geräte-Ereignisse ...")

    seen = set()
    end = time.time() + 5
    try:
        while time.time() < end:
            if libleapc.LeapPollConnection(conn[0], 200, msg) != libleapc.eLeapRS_Success:
                continue
            if msg.type != libleapc.eLeapEventType_Device:
                continue
            info = read_device_info(msg.device_event.device)
            if not info or info["serial"] in seen:
                continue
            seen.add(info["serial"])
            print("\n" + "=" * 50)
            for key, value in info.items():
                print(f"{key:15}: {value}")
    finally:
        libleapc.LeapCloseConnection(conn[0])
        libleapc.LeapDestroyConnection(conn[0])

    if not seen:
        print("Kein Controller gefunden.")


if __name__ == "__main__":
    main()
