import importlib.util
import pathlib

import _leapc_cffi as fake

from leapsmarthome.config import Config

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gw", ROOT / "19-mqtt-gateway" / "leap_mqtt_gateway.py")
gw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gw)


class FakeClient:
    def __init__(self):
        self.sent = []

    def publish(self, topic, payload, qos=0, retain=False):
        self.sent.append((topic, payload, retain))


def make_gateway():
    cfg = Config({
        "mqtt": {"base_topic": "leap"},
        "devices": {"LP111": "multimedia"},
        "interaction": {"rate_hz": 1000},
        "zone_sets": {"rollladen": [{"name": "Z1", "x": [-400, 0]}, {"name": "Z2", "x": [1, 400]}]},
        "gestures": ["swipe"],
    })
    g = gw.Gateway(cfg, None)
    g.mqtt.client = FakeClient()
    return g


def frame(serial, **kw):
    from leapsmarthome.leapdevices import Frame, _copy_hand
    return Frame(serial, 7, 1, 1, 110.0, [_copy_hand(fake.hand(**kw))])


def test_gateway_topics():
    g = make_gateway()
    g.on_frame(frame("LP111", x=-100, y=450, z=0))
    g.on_frame(frame("LP111", x=-100, y=450, z=0, vx=1500))
    sent = {t: p for t, p, _ in g.mqtt.client.sent}
    assert sent["leap/multimedia/hand"] == "ON"
    assert sent["leap/multimedia/hoehe"] == "100"
    assert sent["leap/multimedia/zone/rollladen"] == "Z1"
    events = [(t, p, r) for t, p, r in g.mqtt.client.sent if t.endswith("/gesture")]
    assert events == [("leap/multimedia/gesture", "SWIPE_RIGHT", False)]
