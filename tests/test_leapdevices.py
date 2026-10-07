import _leapc_cffi as fake

from leapsmarthome.leapdevices import LeapDeviceManager


def setup_function():
    fake.QUEUE.clear()
    fake.lib.subscribed.clear()
    fake.DEVICES.clear()
    fake.DEVICES.update({7: "LP111", 9: "LP222", 12: "LP111"})


def test_serial_filter_and_mapping():
    fake.QUEUE.extend([fake.device_event(7), fake.device_event(9),
                       fake.tracking_event(7, fake.hand(x=-100)),
                       fake.tracking_event(9, fake.hand(x=50)),
                       fake.tracking_event(42, fake.hand())])
    with LeapDeviceManager(serials={"LP111"}) as mgr:
        frames = [mgr.poll() for _ in range(5)]
        got = [(f.serial, f.hands[0].palm_position[0]) for f in frames if f]
        assert got == [("LP111", -100.0)]          # LP222 und unbekannte ID gefiltert
        assert set(mgr.devices) == {"LP111"}
        assert fake.lib.subscribed == [7]


def test_reconnect_with_new_runtime_id():
    fake.QUEUE.extend([fake.device_event(7), fake.lost_event(7),
                       fake.device_event(12), fake.tracking_event(12, fake.hand())])
    removed = []
    with LeapDeviceManager(on_device_removed=removed.append) as mgr:
        frames = [mgr.poll() for _ in range(4)]
        assert [r.serial for r in removed] == ["LP111"]
        assert frames[-1].serial == "LP111" and frames[-1].device_id == 12


def test_poll_latest_keeps_newest_per_sensor():
    fake.QUEUE.extend([fake.device_event(7), fake.device_event(9),
                       fake.tracking_event(7, fake.hand(x=1)), fake.tracking_event(7, fake.hand(x=2)),
                       fake.tracking_event(9, fake.hand(x=3))])
    with LeapDeviceManager() as mgr:
        latest = mgr.poll_latest()
        assert latest["LP111"].hands[0].palm_position[0] == 2
        assert latest["LP222"].hands[0].palm_position[0] == 3
