"""
model.py – Datenklassen für Sensor, Hand, Finger, Knochen und Arm.

Bewusst ohne LeapC-Abhängigkeit: Gestenerkennung, Tests und Simulationen
funktionieren damit auch auf einem Rechner ohne Ultraleap-SDK.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

FINGER_NAMES = ("Daumen", "Zeigefinger", "Mittelfinger", "Ringfinger", "Kleiner Finger")
BONE_NAMES = ("Mittelhand", "Grundglied", "Mittelglied", "Endglied")

Vec3 = Tuple[float, float, float]


def _v(vec) -> Vec3:
    return (float(vec.x), float(vec.y), float(vec.z))


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


@dataclass
class DeviceInfo:
    serial: str
    device_id: int
    pid: int
    product: str
    status: int
    baseline_um: int
    h_fov_rad: float
    v_fov_rad: float
    range_um: int
    connected_since: float = field(default_factory=time.time)


@dataclass
class Bone:
    prev_joint: Vec3
    next_joint: Vec3
    width: float

    @property
    def length(self) -> float:
        return math.dist(self.prev_joint, self.next_joint)


@dataclass
class Finger:
    extended: bool
    bones: List[Bone]  # 0=Mittelhand, 1=Grundglied, 2=Mittelglied, 3=Endglied

    @property
    def tip(self) -> Vec3:
        return self.bones[3].next_joint

    @property
    def direction(self) -> Vec3:
        """Richtung des Endglieds (unnormiert) – z. B. zum Zeigen auf Geräte."""
        return _sub(self.bones[3].next_joint, self.bones[3].prev_joint)


@dataclass
class Arm:
    elbow: Vec3     # prev_joint
    wrist: Vec3     # next_joint
    width: float

    @property
    def length(self) -> float:
        return math.dist(self.elbow, self.wrist)


@dataclass
class Hand:
    id: int
    is_left: bool
    confidence: float
    visible_time_us: int
    palm_position: Vec3
    palm_velocity: Vec3
    palm_normal: Vec3
    palm_direction: Vec3
    palm_width: float
    grab_strength: float
    pinch_strength: float
    pinch_distance: float
    fingers: List[Finger]  # 0=Daumen, 1=Zeige, 2=Mittel, 3=Ring, 4=kleiner Finger
    arm: Arm

    @property
    def extended_count(self) -> int:
        return sum(1 for f in self.fingers if f.extended)

    # Winkel wie im alten SDK v2 (Hand.direction / Hand.palmNormal), in Grad
    @property
    def pitch(self) -> float:
        d = self.palm_direction
        return math.degrees(math.atan2(d[1], -d[2]))

    @property
    def yaw(self) -> float:
        d = self.palm_direction
        return math.degrees(math.atan2(d[0], -d[2]))

    @property
    def roll(self) -> float:
        n = self.palm_normal
        return math.degrees(math.atan2(n[0], -n[1]))


@dataclass
class Frame:
    serial: str
    device_id: int
    frame_id: int
    timestamp_us: int
    fps: float
    hands: List[Hand]

    def hand(self, left: Optional[bool] = None) -> Optional[Hand]:
        """Erste Hand (oder gezielt linke/rechte) – None, wenn keine passende Hand."""
        for h in self.hands:
            if left is None or h.is_left == left:
                return h
        return None


