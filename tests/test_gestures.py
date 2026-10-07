import math

import _leapc_cffi as fake

from leapsmarthome.gestures import CircleDetector, FingerCountDetector, GrabDetector, SwipeDetector
from leapsmarthome.leapdevices import _copy_hand


def H(**kw):
    return _copy_hand(fake.hand(**kw))


def test_swipe_directions_and_rearm():
    s = SwipeDetector()
    assert s.update(H(vx=1200), now=1.0) == "SWIPE_RIGHT"
    assert s.update(H(vx=1200), now=2.0) is None          # erst nach Re-Arm
    s.update(H(vx=0), now=3.0)
    assert s.update(H(vy=-1500), now=4.0) == "SWIPE_DOWN"


def test_circle_clockwise():
    c = CircleDetector()
    events = []
    for i in range(120):
        a = math.radians(i * 12)        # +X -> +Z: von oben im Uhrzeigersinn
        ev = c.update(H(x=50 * math.cos(a), z=50 * math.sin(a)), now=i * 0.02)
        if ev:
            events.append(ev)
    assert events and set(events) == {"CIRCLE_CW"}


def test_grab_and_fist_tap():
    g = GrabDetector()
    assert g.update(H(grab=0.9), now=0.0) == "GRAB"
    assert g.update(H(grab=0.1), now=0.3) == "FIST_TAP"
    assert g.update(H(grab=0.9), now=1.0) == "GRAB"
    assert g.update(H(grab=0.1), now=3.0) == "RELEASE"


def test_finger_count_stable():
    f = FingerCountDetector()
    assert f.update(H(extended=3), now=0.0) is None
    assert f.update(H(extended=3), now=0.5) == "FINGERS_3"
    assert f.update(H(extended=3), now=1.0) is None
