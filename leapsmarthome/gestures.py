"""
gestures.py – eigene Gestenerkennung auf Basis der LeapC-Rohdaten.

Das alte Leap SDK v2 (YouTube-Serie „Leap Motion and Python“, Tutorial 8–12) hatte ein
eingebautes Gesture-API: Circle, Swipe, Screen Tap, Key Tap. In Ultraleap Gemini/LeapC
gibt es dieses API NICHT mehr – wir erkennen die Gesten deshalb selbst.

Alle Detektoren arbeiten auf leapsmarthome.leapdevices.Hand und liefern bei Erkennung
einen Ereignis-String (oder None):

  SwipeDetector        SWIPE_LEFT / SWIPE_RIGHT / SWIPE_UP / SWIPE_DOWN / SWIPE_FORWARD / SWIPE_BACK
  CircleDetector       CIRCLE_CW / CIRCLE_CCW              (Blick von oben auf den Sensor)
  KeyTapDetector       KEY_TAP     (Zeigefinger tippt isoliert nach unten, wie eine Taste)
  ScreenTapDetector    SCREEN_TAP  (Zeigefinger stößt nach vorne, wie auf einen Bildschirm)
  GrabDetector         GRAB / RELEASE / FIST_TAP (kurz Faust ballen und öffnen)
  PinchDetector        PINCH / UNPINCH
  FingerCountDetector  FINGERS_1 ... FINGERS_5 (stabil gehaltene Fingeranzahl)
  HoldDetector         HOLD_FLAT   (flache, offene Hand ruhig halten)
  RollTracker          kontinuierlicher Drehwinkel (Drehregler), kein Ereignis

GestureEngine kombiniert alles und verhindert über GestureMode, dass sich Gesten
gegenseitig auslösen (z. B. Kreis wird nicht zusätzlich als Swipe erkannt).

Die Parameter sind Startwerte aus dem Labor (LM-010, Desktop-Modus) und als
Klassenattribute bewusst leicht anpassbar.
"""

from __future__ import annotations

import math
import time
from collections import deque
from typing import Deque, Iterable, List, Optional, Set, Tuple

from .model import Hand
from .mapping import Hysteresis


def _now(now: Optional[float]) -> float:
    return time.monotonic() if now is None else now


def _speed(v: Tuple[float, float, float]) -> float:
    return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


# ── Gegenseitiger Ausschluss ────────────────────────────────────────────────
class GestureMode:
    """Mutex: Solange eine Geste "läuft", sind andere gesperrt."""

    def __init__(self):
        self.mode = "idle"

    def set(self, mode: str) -> None:
        self.mode = mode

    def free(self, detector: str) -> bool:
        return self.mode in ("idle", detector)

    def release(self, detector: str) -> None:
        if self.mode == detector:
            self.mode = "idle"


# ── Swipe ───────────────────────────────────────────────────────────────────
class SwipeDetector:
    """
    Wischen über die Handflächengeschwindigkeit (mm/s).
    Die dominante Achse bestimmt die Richtung („Determine Gesture Direction“, Tutorial 10).
    Nach einem Swipe muss die Hand erst wieder langsamer werden (Re-Arm), sonst würde
    eine einzige Bewegung mehrfach zählen.
    """
    THRESHOLD = 800.0       # mm/s
    REARM = 300.0           # mm/s – darunter wieder scharf
    DOMINANCE = 1.6         # Hauptachse muss X-mal schneller sein als die anderen
    COOLDOWN = 0.6          # s
    AXES = "xy"             # welche Achsen ausgewertet werden ("xyz" für vor/zurück)

    _NAMES = {("x", 1): "SWIPE_RIGHT", ("x", -1): "SWIPE_LEFT",
              ("y", 1): "SWIPE_UP", ("y", -1): "SWIPE_DOWN",
              ("z", -1): "SWIPE_FORWARD", ("z", 1): "SWIPE_BACK"}

    def __init__(self):
        self._armed = True
        self._last = 0.0

    def update(self, hand: Hand, now: Optional[float] = None) -> Optional[str]:
        now = _now(now)
        vx, vy, vz = hand.palm_velocity
        comp = {"x": vx, "y": vy, "z": vz}
        if not self._armed:
            if _speed(hand.palm_velocity) < self.REARM:
                self._armed = True
            return None
        if now - self._last < self.COOLDOWN:
            return None
        axis = max(self.AXES, key=lambda a: abs(comp[a]))
        main = abs(comp[axis])
        others = [abs(comp[a]) for a in "xyz" if a != axis]
        if main >= self.THRESHOLD and main >= self.DOMINANCE * max(others):
            self._armed = False
            self._last = now
            return self._NAMES[(axis, 1 if comp[axis] > 0 else -1)]
        return None

    def reset(self) -> None:
        self._armed = True


# ── Kreis ───────────────────────────────────────────────────────────────────
class CircleDetector:
    """
    Kreisbewegung der Handfläche in der X/Z-Ebene (Port aus leap_gestures.py).
    Mittelpunkt und Radius werden aus einem Fenster der letzten Punkte geschätzt,
    die Winkeländerungen werden aufsummiert. Je ARC_THRESHOLD Grad ein Ereignis.
    """
    WINDOW = 20
    MIN_RADIUS = 20         # mm
    MAX_RADIUS = 80         # mm
    RADIUS_TOL = 0.55       # zulässige Streuung der Radien (relativ)
    ARC_THRESHOLD = 300     # Grad pro Ereignis (≈ ein Kreis; 90 = Viertelkreis für feinere Schritte)
    DIR_CONSISTENCY = 0.65  # Anteil gleichsinniger Winkeländerungen
    COOLDOWN = 0.3          # s

    def __init__(self):
        self._pts: Deque[Tuple[float, float]] = deque(maxlen=self.WINDOW)
        self._accum = 0.0
        self._last_trigger = 0.0
        self._is_active = False

    def is_active(self) -> bool:
        return self._is_active

    def _fail(self) -> None:
        self._is_active = False
        self._accum = 0.0

    def update(self, hand: Hand, now: Optional[float] = None) -> Optional[str]:
        now = _now(now)
        x, _, z = hand.palm_position
        self._pts.append((x, z))
        if len(self._pts) < self.WINDOW:
            self._is_active = False
            return None

        pts = list(self._pts)
        cx = sum(p[0] for p in pts) / len(pts)
        cz = sum(p[1] for p in pts) / len(pts)
        radii = [math.hypot(p[0] - cx, p[1] - cz) for p in pts]
        r_mean = sum(radii) / len(radii)

        if not (self.MIN_RADIUS <= r_mean <= self.MAX_RADIUS):
            self._fail()
            return None
        if (max(radii) - min(radii)) / r_mean > 2 * self.RADIUS_TOL:
            self._fail()
            return None

        angles = [math.degrees(math.atan2(p[1] - cz, p[0] - cx)) for p in pts]
        deltas = []
        for i in range(1, len(angles)):
            d = angles[i] - angles[i - 1]
            if d > 180:
                d -= 360
            if d < -180:
                d += 360
            deltas.append(d)

        total = len(deltas)
        pos = sum(1 for d in deltas if d > 0)
        neg = sum(1 for d in deltas if d < 0)
        if pos / total >= self.DIR_CONSISTENCY:
            direction = +1
        elif neg / total >= self.DIR_CONSISTENCY:
            direction = -1
        else:
            self._fail()
            return None

        # Alle Kriterien erfüllt → Mutex früh sperren
        self._is_active = True
        if (now - self._last_trigger) < self.COOLDOWN:
            return None

        # Nur die Änderung des letzten Schritts aufsummieren (nicht das ganze Fenster)
        self._accum += abs(deltas[-1])
        if self._accum >= self.ARC_THRESHOLD:
            self._accum = 0.0
            self._last_trigger = now
            # atan2(z, x) steigt von +X (rechts) nach +Z (zum Körper):
            # von oben betrachtet ist das im Uhrzeigersinn.
            return "CIRCLE_CW" if direction > 0 else "CIRCLE_CCW"
        return None

    def reset(self) -> None:
        self._pts.clear()
        self._accum = 0.0
        self._is_active = False


# ── Tipp-Gesten ─────────────────────────────────────────────────────────────
class KeyTapDetector:
    """
    Zeigefinger tippt isoliert nach unten (Port des ClickDetector aus leap_gestures.py).
    Der Zeigefinger muss deutlich mehr Y-Ausschlag haben als Mittel-, Ring- und
    kleiner Finger – sonst ist es eine allgemeine Handbewegung.
    """
    BASELINE_FRAMES = 12
    DIP_DEPTH = 14.0        # mm
    RETURN_FRAC = 0.4
    MAX_DUR = 0.45          # s
    PALM_STILL_VY = 80.0    # mm/s
    COOLDOWN = 0.6          # s
    FINGER_ISOLATION = 1.8
    AXIS = 1                # 1 = Y (nach unten tippen)
    DIRECTION = -1          # Finger bewegt sich in negative Achsenrichtung
    REQUIRE_POINTING = False

    def __init__(self):
        self._buf: Deque[float] = deque(maxlen=self.BASELINE_FRAMES)
        self._cmp: Deque[float] = deque(maxlen=self.BASELINE_FRAMES)
        self._baseline: Optional[float] = None
        self._baseline_cmp: Optional[float] = None
        self._phase = "idle"
        self._down_time = 0.0
        self._last = 0.0
        self.last_position: Optional[Tuple[float, float, float]] = None

    def is_active(self) -> bool:
        return self._phase == "down"

    def _clear(self) -> None:
        self._buf.clear()
        self._cmp.clear()

    def update(self, hand: Hand, now: Optional[float] = None) -> Optional[str]:
        now = _now(now)
        a = self.AXIS
        tip = hand.fingers[1].tip[a] * -self.DIRECTION     # positiv = "zurück"
        cmp_mean = sum(hand.fingers[i].tip[a] for i in (2, 3, 4)) / 3 * -self.DIRECTION
        palm_v = abs(hand.palm_velocity[a])

        if self.REQUIRE_POINTING and not (hand.fingers[1].extended and
                                          not any(hand.fingers[i].extended for i in (2, 3, 4))):
            self._phase = "idle"
            self._clear()
            return None

        if now - self._last < self.COOLDOWN:
            self._buf.append(tip)
            self._cmp.append(cmp_mean)
            self._phase = "idle"
            return None

        if self._phase == "idle":
            if palm_v < self.PALM_STILL_VY:
                self._buf.append(tip)
                self._cmp.append(cmp_mean)
            if len(self._buf) >= self.BASELINE_FRAMES:
                self._baseline = sum(self._buf) / len(self._buf)
                self._baseline_cmp = sum(self._cmp) / len(self._cmp)
                index_dip = self._baseline - tip
                other_dip = self._baseline_cmp - cmp_mean
                isolated = index_dip > self.DIP_DEPTH and (
                    other_dip < 0 or index_dip / max(abs(other_dip), 1.0) >= self.FINGER_ISOLATION)
                if isolated:
                    self._phase = "down"
                    self._down_time = now
                    self.last_position = hand.palm_position
        elif self._phase == "down":
            if now - self._down_time > self.MAX_DUR:
                self._phase = "idle"
                self._clear()
            elif tip > self._baseline - self.DIP_DEPTH * self.RETURN_FRAC:
                self._phase = "idle"
                self._last = now
                self._clear()
                return "KEY_TAP"
        return None

    def reset(self) -> None:
        self._phase = "idle"
        self._clear()
        self._baseline = self._baseline_cmp = None


class ScreenTapDetector(KeyTapDetector):
    """
    Zeigefinger stößt nach vorne (Richtung Bildschirm = -Z) und kehrt zurück.
    Gleiche Zustandsmaschine wie KeyTap, nur auf der Z-Achse und mit Zeigehaltung.
    """
    AXIS = 2
    DIRECTION = -1
    DIP_DEPTH = 18.0
    PALM_STILL_VY = 150.0
    REQUIRE_POINTING = True

    def update(self, hand: Hand, now: Optional[float] = None) -> Optional[str]:
        ev = super().update(hand, now)
        return "SCREEN_TAP" if ev else None


# ── Greifen / Pinch ─────────────────────────────────────────────────────────
class GrabDetector:
    """
    Faust mit Hysterese. GRAB beim Schließen; beim Öffnen FIST_TAP (kurz gehalten,
    „Zurück“-Geste aus leap_gestures.py) oder RELEASE (länger gehalten).
    """
    GRAB_ON = 0.85
    GRAB_OFF = 0.35
    TAP_MIN = 0.08          # s
    TAP_MAX = 1.2           # s

    def __init__(self):
        self._h = Hysteresis(self.GRAB_ON, self.GRAB_OFF)
        self._since = 0.0

    @property
    def closed(self) -> bool:
        return self._h.state

    def is_active(self) -> bool:
        return self._h.state

    def update(self, hand: Hand, now: Optional[float] = None) -> Optional[str]:
        now = _now(now)
        change = self._h.update(hand.grab_strength)
        if change is True:
            self._since = now
            return "GRAB"
        if change is False:
            held = now - self._since
            return "FIST_TAP" if self.TAP_MIN <= held <= self.TAP_MAX else "RELEASE"
        return None

    def reset(self) -> None:
        self._h.state = False


class PinchDetector:
    PINCH_ON = 0.8
    PINCH_OFF = 0.4

    def __init__(self):
        self._h = Hysteresis(self.PINCH_ON, self.PINCH_OFF)

    def is_active(self) -> bool:
        return self._h.state

    def update(self, hand: Hand, now: Optional[float] = None) -> Optional[str]:
        change = self._h.update(hand.pinch_strength)
        if change is True:
            return "PINCH"
        if change is False:
            return "UNPINCH"
        return None

    def reset(self) -> None:
        self._h.state = False


# ── Finger zählen / Halten ──────────────────────────────────────────────────
class FingerCountDetector:
    """Ersatz für fingersX_YYY des openHAB-Bindings: Anzahl muss STABLE s stabil sein."""
    STABLE = 0.4  # s

    def __init__(self):
        self._candidate = -1
        self._since = 0.0
        self._reported = -1

    def update(self, hand: Hand, now: Optional[float] = None) -> Optional[str]:
        now = _now(now)
        n = hand.extended_count
        if n != self._candidate:
            self._candidate, self._since = n, now
            return None
        if n != self._reported and now - self._since >= self.STABLE:
            self._reported = n
            if n > 0:
                return f"FINGERS_{n}"
        return None

    def reset(self) -> None:
        self._candidate = self._reported = -1


class HoldDetector:
    """Offene, flache Hand ruhig halten (z. B. „Mute“ beim Samsung TV)."""
    HOLD_TIME = 1.0         # s
    MAX_SPEED = 60.0        # mm/s
    MIN_FINGERS = 4
    MAX_GRAB = 0.2

    def __init__(self):
        self._since: Optional[float] = None
        self._fired = False

    def update(self, hand: Hand, now: Optional[float] = None) -> Optional[str]:
        now = _now(now)
        still = (_speed(hand.palm_velocity) < self.MAX_SPEED
                 and hand.extended_count >= self.MIN_FINGERS
                 and hand.grab_strength <= self.MAX_GRAB)
        if not still:
            self._since, self._fired = None, False
            return None
        if self._since is None:
            self._since = now
        if not self._fired and now - self._since >= self.HOLD_TIME:
            self._fired = True
            return "HOLD_FLAT"
        return None

    def reset(self) -> None:
        self._since, self._fired = None, False


class RollTracker:
    """
    Hand als Drehregler: liefert die Roll-Änderung (Grad) seit dem Einrasten.
    engage() merkt sich den aktuellen Winkel als Nullpunkt (z. B. bei PINCH).
    """
    DEADBAND = 8.0  # Grad

    def __init__(self):
        self.reference: Optional[float] = None

    def engage(self, hand: Hand) -> None:
        self.reference = hand.roll

    def release(self) -> None:
        self.reference = None

    def delta(self, hand: Hand) -> float:
        if self.reference is None:
            return 0.0
        d = (hand.roll - self.reference + 180) % 360 - 180
        return 0.0 if abs(d) < self.DEADBAND else d


# ── Kombination ─────────────────────────────────────────────────────────────
ALL_GESTURES = {"swipe", "circle", "key_tap", "screen_tap", "grab", "pinch", "fingers", "hold"}


class GestureEngine:
    """
    Wertet alle aktivierten Detektoren pro Frame aus und liefert eine Liste von Ereignissen.
    Prioritäten: Kreis sperrt Swipe/Taps; Faust sperrt Taps; Taps sperren sich gegenseitig.
    """

    def __init__(self, enabled: Optional[Iterable[str]] = None):
        self.enabled: Set[str] = set(enabled) if enabled else set(ALL_GESTURES)
        self.mode = GestureMode()
        self.swipe = SwipeDetector()
        self.circle = CircleDetector()
        self.key_tap = KeyTapDetector()
        self.screen_tap = ScreenTapDetector()
        self.grab = GrabDetector()
        self.pinch = PinchDetector()
        self.fingers = FingerCountDetector()
        self.hold = HoldDetector()

    def _gated(self, name: str, det, hand: Hand, now: float) -> Optional[str]:
        if name not in self.enabled:
            return None
        if not self.mode.free(name):
            det.reset()
            return None
        ev = det.update(hand, now)
        if hasattr(det, "is_active"):
            if det.is_active():
                self.mode.set(name)
            else:
                self.mode.release(name)
        return ev

    def update(self, hand: Optional[Hand], now: Optional[float] = None) -> List[str]:
        if hand is None:
            self.reset()
            return []
        now = _now(now)
        events: List[str] = []

        def add(ev):
            if ev:
                events.append(ev)

        add(self._gated("circle", self.circle, hand, now))
        add(self._gated("grab", self.grab, hand, now))
        if "pinch" in self.enabled:
            add(self.pinch.update(hand, now))
        if self.mode.free("swipe") and "swipe" in self.enabled:
            add(self.swipe.update(hand, now))
        add(self._gated("key_tap", self.key_tap, hand, now))
        add(self._gated("screen_tap", self.screen_tap, hand, now))
        if "fingers" in self.enabled:
            add(self.fingers.update(hand, now))
        if "hold" in self.enabled:
            add(self.hold.update(hand, now))
        return events

    def reset(self) -> None:
        self.mode.set("idle")
        for det in (self.swipe, self.circle, self.key_tap, self.screen_tap,
                    self.grab, self.pinch, self.fingers, self.hold):
            det.reset()
