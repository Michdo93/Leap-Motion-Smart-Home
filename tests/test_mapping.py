from leapsmarthome.mapping import ChangeFilter, Hysteresis, ZoneSet, height_percent, map_range, quantize


def test_map_and_quantize():
    assert map_range(100, 100, 450) == 0
    assert map_range(450, 100, 450) == 100
    assert map_range(1000, 100, 450) == 100
    assert quantize(47.4, 5) == 45
    assert height_percent(450, invert=True) == 0
    assert height_percent(100, invert=True) == 100


def test_zones():
    z = ZoneSet.columns(["Z1", "Z2", "Z3", "Z4"], [-150, 0, 150])
    assert z.find((-200, 0, 0)) == "Z1"
    assert z.find((10, 0, 0)) == "Z3"
    assert z.find((999, 0, 0)) is None
    q = ZoneSet.from_config([{"name": "HL", "x": [-400, -1], "z": [-300, -1]}])
    assert q.find((-10, 200, -10)) == "HL"
    assert q.find((-10, 200, 10)) is None


def test_hysteresis_and_filter():
    h = Hysteresis(0.8, 0.4)
    assert [h.update(v) for v in (0.5, 0.85, 0.7, 0.3)] == [None, True, None, False]
    f = ChangeFilter()
    assert f.changed("a", 1) and not f.changed("a", 1) and f.changed("a", 2)
