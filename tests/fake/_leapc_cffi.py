"""
Minimale Attrappe der LeapC-CFFI-Bindings für Tests ohne Hardware/SDK.
Simuliert Geräte-, Verlust- und Tracking-Ereignisse über die Warteschlange QUEUE.
"""
from types import SimpleNamespace as N


class _Ptr(list):
    def __getattr__(self, k):
        return getattr(self[0], k)

    def __setattr__(self, k, v):
        setattr(self[0], k, v)


class _FFI:
    NULL = None

    def new(self, t, *a):
        if t.startswith("char[]"):
            return N(val=b"")
        if t == "uint32_t *":
            return [0]
        return _Ptr([N()])

    def sizeof(self, t):
        return 1

    def string(self, b):
        return b.val


ffi = _FFI()


def V(x, y, z):
    return N(x=x, y=y, z=z)


def hand(x=0.0, y=200.0, z=0.0, vx=0.0, vy=0.0, vz=0.0, grab=0.0, extended=5):
    def bone(i):
        return N(prev_joint=V(x, y, z - 10 * i), next_joint=V(x, y, z - 10 * (i + 1)), width=10.0)
    return N(id=1, type=0, confidence=1.0, visible_time=1000, grab_strength=grab,
             pinch_strength=0.0, pinch_distance=40.0,
             palm=N(position=V(x, y, z), velocity=V(vx, vy, vz), normal=V(0, -1, 0),
                    direction=V(0, 0, -1), width=80.0),
             digits=[N(is_extended=i < extended, bones=[bone(j) for j in range(4)]) for i in range(5)],
             arm=N(prev_joint=V(x, y - 50, z + 250), next_joint=V(x, y, z + 50), width=60.0))


DEVICES = {}   # Laufzeit-ID -> Seriennummer
QUEUE = []


def device_event(i):
    return N(type=1, device_event=N(device=N(id=i)), device_id=0)


def lost_event(i):
    return N(type=2, device_event=N(device=N(id=i)), device_id=0)


def tracking_event(i, *hands):
    return N(type=3, device_id=i,
             tracking_event=N(tracking_frame_id=1, info=N(timestamp=1), framerate=110.0,
                              nHands=len(hands), pHands=list(hands)))


class _Lib:
    eLeapRS_Success = 0
    eLeapEventType_Device = 1
    eLeapEventType_DeviceLost = 2
    eLeapEventType_Tracking = 3
    eLeapEventType_ConnectionLost = 4
    eLeapConnectionConfig_MultiDeviceAware = 1
    eLeapHandType_Left = 0
    eLeapDevicePID_Peripheral = 3
    subscribed = []

    def LeapCreateConnection(self, c, p):
        p[0] = "conn"
        return 0

    def LeapOpenConnection(self, c):
        return 0

    def LeapCloseConnection(self, c):
        pass

    def LeapDestroyConnection(self, c):
        pass

    def LeapOpenDevice(self, ref, h):
        h[0] = ref.id
        return 0

    def LeapCloseDevice(self, h):
        pass

    def LeapGetDeviceInfo(self, h, info):
        info.serial_length, info.pid, info.status = 14, 3, 0
        info.baseline, info.h_fov, info.v_fov, info.range = 40000, 2.4, 2.4, 600000
        if info.serial is not None:
            info.serial.val = DEVICES[h].encode()
        return 0

    def LeapSubscribeEvents(self, c, h):
        self.subscribed.append(h)
        return 0

    def LeapPollConnection(self, c, t, msg):
        if not QUEUE:
            return 0xE2000004   # Timeout
        msg[0] = QUEUE.pop(0)
        return 0


lib = _Lib()
