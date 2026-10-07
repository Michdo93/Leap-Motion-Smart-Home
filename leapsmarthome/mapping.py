"""
mapping.py – vom Millimeter zum Smart-Home-Wert.

Koordinatensystem des Leap Motion Controllers (Desktop-Modus, Sensor liegt flach):
  X: links (-) / rechts (+)        in mm
  Y: Höhe über dem Sensor (+)      in mm
  Z: zum Bildschirm/hinten (-) / zum Körper/vorne (+)   in mm

Bausteine:
  clamp / map_range / quantize   – Wertebereiche abbilden und runden
  Zone / ZoneSet                 – benannte Bereiche im Raum (1D, 2D oder 3D)
  Hysteresis                     – Schwellwert mit Ein-/Ausschaltpunkt
  ChangeFilter                   – nur bei Änderung und höchstens alle n Sekunden senden
  Cooldown                       – Sperrzeit nach einer Aktion
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def map_range(value: float, in_min: float, in_max: float,
              out_min: float = 0.0, out_max: float = 100.0,
              invert: bool = False) -> float:
    """Linear abbilden und begrenzen. invert=True: in_min -> out_max."""
    if in_max == in_min:
        return out_min
    t = clamp((value - in_min) / (in_max - in_min), 0.0, 1.0)
    if invert:
        t = 1.0 - t
    return out_min + t * (out_max - out_min)


def quantize(value: float, step: float = 5.0) -> int:
    """Auf Raster runden (z. B. 5-%-Schritte) – reduziert Befehlsflut und Zittern."""
    return int(round(value / step) * step)


def height_percent(y: float, y_min: float = 100, y_max: float = 450,
                   step: float = 5, invert: bool = False) -> int:
    """Handhöhe -> 0..100 %. invert=True: oben = 0 % (z. B. Rollladen offen)."""
    return quantize(map_range(y, y_min, y_max, 0, 100, invert), step)


# --- Zonen ------------------------------------------------------------------
Range = Optional[Tuple[float, float]]


@dataclass
class Zone:
    """Benannter Quader. Fehlende Achse (None) = unbegrenzt."""
    name: str
    x: Range = None
    y: Range = None
    z: Range = None

    def contains(self, pos: Sequence[float]) -> bool:
        for rng, v in ((self.x, pos[0]), (self.y, pos[1]), (self.z, pos[2])):
            if rng is not None and not (rng[0] <= v <= rng[1]):
                return False
        return True


class ZoneSet:
    """Liste von Zonen; die erste passende gewinnt."""

    def __init__(self, zones: Iterable[Zone]):
        self.zones: List[Zone] = list(zones)

    def find(self, pos: Sequence[float]) -> Optional[str]:
        for z in self.zones:
            if z.contains(pos):
                return z.name
        return None

    @classmethod
    def from_config(cls, items: Iterable[Dict[str, Any]]) -> "ZoneSet":
        def rng(v):
            return tuple(v) if v is not None else None
        return cls(Zone(d["name"], rng(d.get("x")), rng(d.get("y")), rng(d.get("z"))) for d in items)

    @classmethod
    def columns(cls, names: Sequence[str], boundaries: Sequence[float],
                lo: float = -400, hi: float = 400) -> "ZoneSet":
        """Spalten entlang X, z. B. names=[Z1..Z4], boundaries=[-150, 0, 150]."""
        edges = [lo, *boundaries, hi]
        return cls(Zone(n, x=(edges[i], edges[i + 1])) for i, n in enumerate(names))


# --- Zeitverhalten ----------------------------------------------------------
class Hysteresis:
    """
    Schaltet bei >= on ein und erst bei <= off wieder aus.
    Verhindert Flattern z. B. bei grab_strength um 0,8.
    """

    def __init__(self, on: float, off: float):
        assert off < on
        self.on, self.off, self.state = on, off, False

    def update(self, value: float) -> Optional[bool]:
        """Liefert True/False bei Zustandswechsel, sonst None."""
        if not self.state and value >= self.on:
            self.state = True
            return True
        if self.state and value <= self.off:
            self.state = False
            return False
        return None


class ChangeFilter:
    """Gibt einen Wert nur weiter, wenn er sich geändert hat und min_interval vorbei ist."""

    def __init__(self, min_interval: float = 0.0):
        self.min_interval = min_interval
        self._last: Dict[str, Any] = {}
        self._time: Dict[str, float] = {}

    def changed(self, key: str, value: Any) -> bool:
        now = time.monotonic()
        if self._last.get(key, object()) == value:
            return False
        if now - self._time.get(key, 0.0) < self.min_interval:
            return False
        self._last[key] = value
        self._time[key] = now
        return True

    def forget(self, key: Optional[str] = None) -> None:
        if key is None:
            self._last.clear()
            self._time.clear()
        else:
            self._last.pop(key, None)
            self._time.pop(key, None)


class Cooldown:
    def __init__(self, seconds: float):
        self.seconds, self._until = seconds, 0.0

    def ready(self) -> bool:
        return time.monotonic() >= self._until

    def trigger(self) -> None:
        self._until = time.monotonic() + self.seconds
