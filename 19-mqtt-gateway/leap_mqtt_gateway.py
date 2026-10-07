#!/usr/bin/env python3
"""
Kapitel 19 – Ansatz A: Leap-MQTT-Gateway.

Das Gateway kennt KEINE Smart-Home-Geräte. Es übersetzt Sensordaten in Topics –
welches Gerät reagiert, entscheiden die openHAB-Regeln (Kapitel 20).

Für jeden Sensor (Alias aus config.yaml) wird veröffentlicht:
  Zustände (retained, nur bei Änderung, gedrosselt auf interaction.rate_hz):
    status, hand, side, palm/x|y|z, hoehe, tiefe, finger, grab, pinch, roll, fps,
    zone/<satz> für jeden Zonen-Satz aus zone_sets
  Ereignisse (nicht retained):
    gesture = SWIPE_*, CIRCLE_*, KEY_TAP, SCREEN_TAP, GRAB, RELEASE, FIST_TAP,
              PINCH, UNPINCH, FINGERS_n, HOLD_FLAT

Start:  python3 19-mqtt-gateway/leap_mqtt_gateway.py [--sensor multimedia]
Dienst: siehe 13-robuster-code/systemd/leap-app@.service
"""

import logging
import pathlib
import signal
import sys
import time
from typing import Any, Dict, Optional

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.gestures import GestureEngine  # noqa: E402
from leapsmarthome.leapdevices import DeviceInfo, Frame, LeapDeviceManager  # noqa: E402
from leapsmarthome.mapping import ZoneSet, map_range, quantize  # noqa: E402
from leapsmarthome.mqtt import LeapMqtt  # noqa: E402
from leapsmarthome.runtime import base_parser, load, sensor_serials  # noqa: E402

log = logging.getLogger("leap-gateway")


class Throttle:
    """
    Pro Topic höchstens alle `interval` Sekunden senden – aber den LETZTEN Wert
    nie verlieren: Er wird nachgereicht, sobald das Intervall abgelaufen ist.
    """

    def __init__(self, interval: float):
        self.interval = interval
        self.sent: Dict[str, Any] = {}
        self.time: Dict[str, float] = {}
        self.pending: Dict[str, Any] = {}

    def offer(self, key: str, value: Any) -> Optional[Any]:
        if self.sent.get(key) == value:
            self.pending.pop(key, None)
            return None
        now = time.monotonic()
        if now - self.time.get(key, 0.0) >= self.interval:
            self.sent[key], self.time[key] = value, now
            self.pending.pop(key, None)
            return value
        self.pending[key] = value
        return None

    def due(self):
        now = time.monotonic()
        for key, value in list(self.pending.items()):
            if now - self.time.get(key, 0.0) >= self.interval:
                del self.pending[key]
                self.sent[key], self.time[key] = value, now
                yield key, value


class SensorState:
    def __init__(self, alias: str, gestures, interval: float):
        self.alias = alias
        self.engine = GestureEngine(gestures)
        self.throttle = Throttle(interval)
        self.hand_present: Optional[bool] = None
        self.last_fps = 0.0


class Gateway:
    def __init__(self, cfg, serials):
        self.cfg = cfg
        ia = cfg.section("interaction")
        self.y_min, self.y_max = ia.get("y_min", 100), ia.get("y_max", 450)
        self.z_min, self.z_max = ia.get("z_min", -200), ia.get("z_max", 200)
        self.step = ia.get("step", 5)
        self.res = ia.get("palm_resolution", 5)
        self.interval = 1.0 / float(ia.get("rate_hz", 10))
        self.gestures = cfg.get("gestures")
        self.zone_sets = {name: ZoneSet.from_config(z) for name, z in (cfg.get("zone_sets") or {}).items()}
        self.mqtt = LeapMqtt.from_config(cfg.section("mqtt"))
        self.serials = serials
        self.sensors: Dict[str, SensorState] = {}
        self.running = True

    def state_for(self, serial: str) -> SensorState:
        st = self.sensors.get(serial)
        if st is None:
            st = self.sensors[serial] = SensorState(self.cfg.alias_for(serial), self.gestures, self.interval)
        return st

    # --- Geräte -------------------------------------------------------------
    def on_added(self, info: DeviceInfo) -> None:
        st = self.state_for(info.serial)
        log.info("Sensor %s (%s) online", st.alias, info.serial)
        self.mqtt.publish_state(st.alias, "status", "online", force=True)
        self.mqtt.publish_state(st.alias, "serial", info.serial, force=True)

    def on_removed(self, info: DeviceInfo) -> None:
        st = self.state_for(info.serial)
        log.warning("Sensor %s offline", st.alias)
        self.mqtt.publish_state(st.alias, "status", "offline", force=True)
        self.mqtt.publish_state(st.alias, "hand", "OFF")
        st.hand_present = False
        st.engine.reset()

    # --- Frames -------------------------------------------------------------
    def publish(self, st: SensorState, name: str, value: Any) -> None:
        v = st.throttle.offer(name, value)
        if v is not None:
            self.mqtt.publish_state(st.alias, name, v)

    def on_frame(self, frame: Frame) -> None:
        st = self.state_for(frame.serial)
        hand = frame.hand()

        present = hand is not None
        if present != st.hand_present:
            st.hand_present = present
            self.mqtt.publish_state(st.alias, "hand", "ON" if present else "OFF")
            if not present:
                for name in self.zone_sets:
                    self.mqtt.publish_state(st.alias, f"zone/{name}", "NONE")

        for ev in st.engine.update(hand):
            log.info("%s: %s", st.alias, ev)
            self.mqtt.publish_event(st.alias, "gesture", ev)

        if frame.timestamp_us and time.monotonic() - st.last_fps > 1.0:
            st.last_fps = time.monotonic()
            self.mqtt.publish_state(st.alias, "fps", round(frame.fps))

        if hand is not None:
            x, y, z = hand.palm_position
            self.publish(st, "side", "LEFT" if hand.is_left else "RIGHT")
            self.publish(st, "palm/x", quantize(x, self.res))
            self.publish(st, "palm/y", quantize(y, self.res))
            self.publish(st, "palm/z", quantize(z, self.res))
            self.publish(st, "hoehe", quantize(map_range(y, self.y_min, self.y_max), self.step))
            self.publish(st, "tiefe", quantize(map_range(z, self.z_min, self.z_max), self.step))
            self.publish(st, "finger", hand.extended_count)
            self.publish(st, "grab", quantize(hand.grab_strength * 100, self.step))
            self.publish(st, "pinch", quantize(hand.pinch_strength * 100, self.step))
            self.publish(st, "roll", quantize(hand.roll, 5))
            for name, zs in self.zone_sets.items():
                # Zonen ungedrosselt: ein Zonenwechsel soll sofort ankommen
                self.mqtt.publish_state(st.alias, f"zone/{name}", zs.find(hand.palm_position) or "NONE")

        for key, value in st.throttle.due():
            self.mqtt.publish_state(st.alias, key, value)

    # --- Hauptschleife ------------------------------------------------------
    def stop(self, *_):
        self.running = False

    def run(self) -> int:
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        self.mqtt.start()
        try:
            while self.running:
                try:
                    with LeapDeviceManager(serials=self.serials, on_device_added=self.on_added,
                                           on_device_removed=self.on_removed) as mgr:
                        while self.running:
                            frame = mgr.poll(50)
                            if frame is not None:
                                self.on_frame(frame)
                            else:
                                for st in self.sensors.values():
                                    for key, value in st.throttle.due():
                                        self.mqtt.publish_state(st.alias, key, value)
                except RuntimeError as exc:
                    log.error("%s – neuer Versuch in 5 s", exc)
                    time.sleep(5)
        finally:
            for st in self.sensors.values():
                self.mqtt.publish_state(st.alias, "status", "offline", force=True)
            self.mqtt.stop()
        return 0


def main():
    args = base_parser("Leap-MQTT-Gateway").parse_args()
    cfg = load(args)
    serials = sensor_serials(cfg, args.sensor) or (set(cfg.devices) or None)
    return Gateway(cfg, serials).run()


if __name__ == "__main__":
    sys.exit(main())
