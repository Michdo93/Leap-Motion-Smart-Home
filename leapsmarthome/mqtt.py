"""
mqtt.py – schlanker MQTT-Publisher (paho-mqtt >= 2.0) für Ansatz A.

* Last Will: <base>/gateway/status = offline (retained), nach dem Verbinden online
* publish_state(): retained, nur bei Änderung (Zustände wie Höhe, Zone, Hand)
* publish_event(): nicht retained (Gesten -> openHAB-Trigger-Channel)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt

log = logging.getLogger("leapmqtt")


class LeapMqtt:
    def __init__(self, host: str = "localhost", port: int = 1883,
                 username: Optional[str] = None, password: Optional[str] = None,
                 base_topic: str = "leap", client_id: str = "leap-gateway",
                 tls: bool = False):
        self.base = base_topic.rstrip("/")
        self._last: Dict[str, str] = {}
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        if username:
            self.client.username_pw_set(username, password)
        if tls:
            self.client.tls_set()
        self.status_topic = f"{self.base}/gateway/status"
        self.client.will_set(self.status_topic, "offline", qos=1, retain=True)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._host, self._port = host, port

    @classmethod
    def from_config(cls, cfg: Dict[str, Any], client_id: str = "leap-gateway") -> "LeapMqtt":
        return cls(host=cfg.get("host", "localhost"), port=int(cfg.get("port", 1883)),
                   username=cfg.get("username"), password=cfg.get("password"),
                   base_topic=cfg.get("base_topic", "leap"),
                   client_id=cfg.get("client_id", client_id), tls=bool(cfg.get("tls", False)))

    # -- Verbindung ----------------------------------------------------------
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            log.info("MQTT verbunden")
            client.publish(self.status_topic, "online", qos=1, retain=True)
            # Nach einem Reconnect alle Zustände erneut senden
            for topic, payload in self._last.items():
                client.publish(topic, payload, qos=0, retain=True)
        else:
            log.error("MQTT-Verbindung abgelehnt: %s", reason_code)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        log.warning("MQTT getrennt (%s) – automatischer Reconnect", reason_code)

    def start(self) -> "LeapMqtt":
        self.client.connect_async(self._host, self._port, keepalive=30)
        self.client.loop_start()
        return self

    def stop(self) -> None:
        self.client.publish(self.status_topic, "offline", qos=1, retain=True).wait_for_publish(2)
        self.client.loop_stop()
        self.client.disconnect()

    def __enter__(self) -> "LeapMqtt":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    # -- Senden --------------------------------------------------------------
    def topic(self, alias: str, *parts: str) -> str:
        return "/".join([self.base, alias, *parts])

    def publish_state(self, alias: str, name: str, value: Any, force: bool = False) -> bool:
        """Retained, nur bei Änderung. Liefert True, wenn gesendet wurde."""
        t = self.topic(alias, *name.split("/"))
        payload = str(value)
        if not force and self._last.get(t) == payload:
            return False
        self._last[t] = payload
        self.client.publish(t, payload, qos=0, retain=True)
        return True

    def publish_event(self, alias: str, name: str, value: Any) -> None:
        """Nicht retained – sonst würde openHAB alte Gesten beim Neustart erneut auslösen."""
        self.client.publish(self.topic(alias, *name.split("/")), str(value), qos=0, retain=False)
