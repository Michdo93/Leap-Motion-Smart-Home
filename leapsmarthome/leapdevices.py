#!/usr/bin/env python3
"""
leapdevices.py – Geräteverwaltung für einen oder mehrere Leap Motion Controller
                 über LeapC (Ultraleap Gemini) auf dem Raspberry Pi / Linux.

Kernidee
--------
* Die Seriennummer (z. B. "LP19566274693") ist der STABILE Schlüssel eines Sensors.
* Die LeapC-Device-ID (device_ref.id bzw. msg.device_id) ist nur LAUFZEIT-Information
  und kann sich nach Neustecken, Neustart des Dienstes oder USB/IP-Reconnect ändern.
* Die Verbindung wird "multi device aware" geöffnet. Jeder gewünschte Sensor wird
  per LeapSubscribeEvents abonniert. Jedes Tracking-Event trägt msg.device_id und wird
  über eine Tabelle device_id -> Seriennummer zugeordnet.
* Frame-Daten werden sofort in Python-Objekte kopiert, weil der Speicher hinter
  msg.tracking_event beim nächsten LeapPollConnection überschrieben wird.

Benutzung
---------
    python3 -m leapsmarthome.leapdevices               # 5 s scannen, Geräte auflisten
    python3 -m leapsmarthome.leapdevices --track       # Live-Daten pro Seriennummer

    from leapsmarthome.leapdevices import LeapDeviceManager
    with LeapDeviceManager(serials={"LP19566274693"}) as mgr:
        for frame in mgr.frames():
            for hand in frame.hands:
                print(frame.serial, hand.palm_position)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from typing import AsyncIterator, Callable, Dict, Iterable, Iterator, Optional, Set, Tuple

from .leapc import const, ffi, libleapc

log = logging.getLogger("leapdevices")

RS_SUCCESS = const("eLeapRS_Success", 0)
EV_DEVICE = const("eLeapEventType_Device")
EV_DEVICE_LOST = const("eLeapEventType_DeviceLost")
EV_TRACKING = const("eLeapEventType_Tracking")
EV_CONNECTION_LOST = const("eLeapEventType_ConnectionLost")
CFG_MULTI_DEVICE = const("eLeapConnectionConfig_MultiDeviceAware", 0x00000001)
HAND_LEFT = const("eLeapHandType_Left", 0)

# PID-Werte -> lesbare Namen (eLeapDevicePID_Peripheral = Leap Motion Controller 1 / LM-010)
_PID_NAMES = {
    getattr(libleapc, n): n.replace("eLeapDevicePID_", "")
    for n in dir(libleapc)
    if n.startswith("eLeapDevicePID_")
}

from .model import (FINGER_NAMES, BONE_NAMES, Arm, Bone, DeviceInfo, Finger, Frame,  # noqa: F401
                    Hand, Vec3, _v)


def _copy_bone(b) -> Bone:
    return Bone(_v(b.prev_joint), _v(b.next_joint), float(b.width))


def _copy_hand(h) -> Hand:
    fingers = [
        Finger(extended=bool(h.digits[i].is_extended),
               bones=[_copy_bone(h.digits[i].bones[j]) for j in range(4)])
        for i in range(5)
    ]
    return Hand(
        id=int(h.id),
        is_left=(h.type == HAND_LEFT),
        confidence=float(h.confidence),
        visible_time_us=int(h.visible_time),
        palm_position=_v(h.palm.position),
        palm_velocity=_v(h.palm.velocity),
        palm_normal=_v(h.palm.normal),
        palm_direction=_v(h.palm.direction),
        palm_width=float(h.palm.width),
        grab_strength=float(h.grab_strength),
        pinch_strength=float(h.pinch_strength),
        pinch_distance=float(h.pinch_distance),
        fingers=fingers,
        arm=Arm(_v(h.arm.prev_joint), _v(h.arm.next_joint), float(h.arm.width)),
    )


# --- Geräteverwaltung -------------------------------------------------------
class LeapDeviceManager:
    """
    Öffnet EINE LeapC-Verbindung (multi device aware) und verwaltet alle Sensoren.

    serials:  Menge erlaubter Seriennummern. None = alle gefundenen Sensoren.
              Damit kann jede Anwendung (Rollladen, Licht, ...) gezielt "ihren"
              Sensor abonnieren – auch in getrennten Prozessen.
    on_device_added / on_device_removed: optionale Callbacks mit DeviceInfo.
    """

    def __init__(
        self,
        serials: Optional[Iterable[str]] = None,
        on_device_added: Optional[Callable[[DeviceInfo], None]] = None,
        on_device_removed: Optional[Callable[[DeviceInfo], None]] = None,
    ) -> None:
        self.allowed: Optional[Set[str]] = set(serials) if serials else None
        self.on_device_added = on_device_added
        self.on_device_removed = on_device_removed
        self.devices: Dict[str, DeviceInfo] = {}      # serial -> info
        self._id_to_serial: Dict[int, str] = {}      # device_id -> serial
        self._conn = None
        self._msg = ffi.new("LEAP_CONNECTION_MESSAGE *")

    # -- Verbindung ----------------------------------------------------------
    def open(self) -> "LeapDeviceManager":
        cfg = ffi.new("LEAP_CONNECTION_CONFIG *")
        cfg.size = ffi.sizeof("LEAP_CONNECTION_CONFIG")
        cfg.flags = CFG_MULTI_DEVICE
        cfg.server_namespace = ffi.NULL

        conn_ptr = ffi.new("LEAP_CONNECTION *")
        res = libleapc.LeapCreateConnection(cfg, conn_ptr)
        if res != RS_SUCCESS:
            raise RuntimeError(f"LeapCreateConnection fehlgeschlagen (Code {res:#x})")
        res = libleapc.LeapOpenConnection(conn_ptr[0])
        if res != RS_SUCCESS:
            libleapc.LeapDestroyConnection(conn_ptr[0])
            raise RuntimeError(f"LeapOpenConnection fehlgeschlagen (Code {res:#x}) – "
                               "läuft der Ultraleap-Dienst?")
        self._conn = conn_ptr[0]
        return self

    def close(self) -> None:
        if self._conn is not None:
            libleapc.LeapCloseConnection(self._conn)
            libleapc.LeapDestroyConnection(self._conn)
            self._conn = None

    def __enter__(self) -> "LeapDeviceManager":
        return self.open()

    def __exit__(self, *exc) -> None:
        self.close()

    # -- Ereignisse ----------------------------------------------------------
    def _read_info(self, device_ref) -> Optional[DeviceInfo]:
        """Gerät kurz öffnen, Info + Seriennummer lesen, ggf. abonnieren."""
        h_dev = ffi.new("LEAP_DEVICE *")
        if libleapc.LeapOpenDevice(device_ref, h_dev) != RS_SUCCESS:
            log.warning("Gerät id=%s ließ sich nicht öffnen", device_ref.id)
            return None
        try:
            info = ffi.new("LEAP_DEVICE_INFO *")
            info.size = ffi.sizeof("LEAP_DEVICE_INFO")
            info.serial = ffi.NULL
            # 1. Aufruf liefert die benötigte Länge, 2. Aufruf die Seriennummer
            libleapc.LeapGetDeviceInfo(h_dev[0], info)
            length = max(int(info.serial_length), 1)
            buf = ffi.new("char[]", length)
            info.serial = buf
            info.serial_length = length
            if libleapc.LeapGetDeviceInfo(h_dev[0], info) != RS_SUCCESS:
                log.warning("Geräteinfo für id=%s nicht lesbar", device_ref.id)
                return None
            serial = ffi.string(info.serial).decode("utf-8", "replace")

            if self.allowed is not None and serial not in self.allowed:
                log.info("Ignoriere Sensor %s (nicht in serials)", serial)
                return None

            res = libleapc.LeapSubscribeEvents(self._conn, h_dev[0])
            if res != RS_SUCCESS:
                log.warning("LeapSubscribeEvents für %s fehlgeschlagen (Code %#x)", serial, res)

            return DeviceInfo(
                serial=serial,
                device_id=int(device_ref.id),
                pid=int(info.pid),
                product=_PID_NAMES.get(int(info.pid), f"PID {int(info.pid):#x}"),
                status=int(info.status),
                baseline_um=int(info.baseline),
                h_fov_rad=float(info.h_fov),
                v_fov_rad=float(info.v_fov),
                range_um=int(info.range),
            )
        finally:
            libleapc.LeapCloseDevice(h_dev[0])

    def _device_added(self, device_ref) -> None:
        info = self._read_info(device_ref)
        if info is None:
            return
        old = self.devices.get(info.serial)
        if old is not None and old.device_id != info.device_id:
            # Gleicher Sensor, neue Laufzeit-ID (z. B. nach USB/IP-Reconnect)
            self._id_to_serial.pop(old.device_id, None)
        self.devices[info.serial] = info
        self._id_to_serial[info.device_id] = info.serial
        log.info("Sensor verbunden: %s (%s, id=%d)", info.serial, info.product, info.device_id)
        if self.on_device_added:
            self.on_device_added(info)

    def _device_lost(self, device_id: int) -> None:
        serial = self._id_to_serial.pop(device_id, None)
        if serial is None:
            return
        info = self.devices.pop(serial, None)
        log.warning("Sensor getrennt: %s (id=%d)", serial, device_id)
        if info and self.on_device_removed:
            self.on_device_removed(info)

    def _connection_lost(self) -> None:
        log.error("Verbindung zum Ultraleap-Dienst verloren – warte auf Wiederverbindung")
        for device_id in list(self._id_to_serial):
            self._device_lost(device_id)

    # -- Polling -------------------------------------------------------------
    def poll(self, timeout_ms: int = 100) -> Optional[Frame]:
        """
        Ein Ereignis abholen. Liefert ein Frame (nur von abonnierten, bekannten
        Sensoren) oder None. Geräte-Ereignisse werden intern verarbeitet.
        """
        return self._poll_once(timeout_ms)[1]

    def _poll_once(self, timeout_ms: int) -> Tuple[bool, Optional[Frame]]:
        """(ok, frame): ok=False bei Timeout/Fehler, d. h. Puffer leer."""
        if self._conn is None:
            raise RuntimeError("Verbindung nicht geöffnet")
        res = libleapc.LeapPollConnection(self._conn, timeout_ms, self._msg)
        if res != RS_SUCCESS:
            return False, None  # Timeout oder Dienst nicht erreichbar – LeapC verbindet selbst neu
        return True, self._handle_message()

    def _handle_message(self) -> Optional[Frame]:
        msg = self._msg
        if msg.type == EV_DEVICE:
            self._device_added(msg.device_event.device)
        elif EV_DEVICE_LOST is not None and msg.type == EV_DEVICE_LOST:
            self._device_lost(int(msg.device_event.device.id))
        elif EV_CONNECTION_LOST is not None and msg.type == EV_CONNECTION_LOST:
            self._connection_lost()
        elif msg.type == EV_TRACKING:
            serial = self._id_to_serial.get(int(msg.device_id))
            if serial is None:
                return None  # nicht abonniert / noch nicht identifiziert
            ev = msg.tracking_event
            return Frame(
                serial=serial,
                device_id=int(msg.device_id),
                frame_id=int(ev.tracking_frame_id),
                timestamp_us=int(ev.info.timestamp),
                fps=float(ev.framerate),
                hands=[_copy_hand(ev.pHands[i]) for i in range(int(ev.nHands))],
            )
        return None

    def poll_latest(self, timeout_ms: int = 10) -> Dict[str, Frame]:
        """
        Puffer leeren und nur das jeweils NEUESTE Frame pro Sensor liefern
        (Echtzeit-Garantie wie in leap_pepper.py – kein Rückstau bei langsamer Verarbeitung).
        """
        latest: Dict[str, Frame] = {}
        ok, frame = self._poll_once(timeout_ms)
        while ok:
            if frame is not None:
                latest[frame.serial] = frame
            ok, frame = self._poll_once(0)   # sofort weiter, bis der Puffer leer ist
        return latest

    def frames(self, timeout_ms: int = 100) -> Iterator[Frame]:
        """Endlos-Generator über alle Frames aller (erlaubten) Sensoren."""
        while True:
            frame = self.poll(timeout_ms)
            if frame is not None:
                yield frame

    async def aframes(self, timeout_ms: int = 20) -> AsyncIterator[Frame]:
        """Async-Variante für asyncio-Programme (z. B. mit python-openhab-rest-client)."""
        while True:
            frame = await asyncio.to_thread(self.poll, timeout_ms)
            if frame is not None:
                yield frame

    def wait_for_devices(self, timeout_s: float = 5.0, count: Optional[int] = None) -> Dict[str, DeviceInfo]:
        """
        Bis zu timeout_s Sekunden auf Geräte-Ereignisse warten.
        count: vorzeitig abbrechen, sobald so viele Sensoren bekannt sind.
               Bei gesetztem serials-Filter standardmäßig dessen Größe.
        """
        if count is None and self.allowed is not None:
            count = len(self.allowed)
        end = time.time() + timeout_s
        while time.time() < end:
            self.poll(100)
            if count is not None and len(self.devices) >= count:
                break
        return dict(self.devices)


# --- Kommandozeile ----------------------------------------------------------
def _main() -> int:
    ap = argparse.ArgumentParser(description="Leap Motion Controller finden und überwachen")
    ap.add_argument("--serial", action="append", help="nur diese Seriennummer(n) verwenden")
    ap.add_argument("--timeout", type=float, default=5.0, help="Scan-Dauer in Sekunden")
    ap.add_argument("--track", action="store_true", help="Live-Handdaten pro Sensor ausgeben")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(message)s")

    with LeapDeviceManager(serials=args.serial) as mgr:
        print(f"Scanne {args.timeout:.0f} s nach Leap Motion Controllern ...")
        found = mgr.wait_for_devices(args.timeout)
        if not found:
            print("Keine Sensoren gefunden. Dienst, USB-Verbindung bzw. USB/IP prüfen.")
            return 1
        for n, info in enumerate(found.values(), 1):
            print(f"[{n}] Seriennummer {info.serial} | {info.product} | "
                  f"Laufzeit-ID {info.device_id} | Reichweite {info.range_um / 1000:.0f} mm")

        if not args.track:
            return 0

        print("\nLive-Tracking (Strg+C beendet) ...")
        last: Dict[str, str] = {}
        try:
            for frame in mgr.frames():
                h = frame.hand()
                if h:
                    x, y, z = h.palm_position
                    line = (f"{'L' if h.is_left else 'R'} X:{x:6.1f} Y:{y:6.1f} Z:{z:6.1f} "
                            f"Finger:{h.extended_count} Grab:{h.grab_strength:.2f} "
                            f"@ {frame.fps:4.0f} fps")
                else:
                    line = "keine Hand"
                last[frame.serial] = line
                sys.stdout.write("\r" + " | ".join(f"{s}: {l}" for s, l in sorted(last.items())) + "   ")
                sys.stdout.flush()
        except KeyboardInterrupt:
            print("\nBeendet.")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
