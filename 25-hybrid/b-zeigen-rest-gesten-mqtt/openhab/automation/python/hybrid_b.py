# Kapitel 25 – Hybrid B: Gesten nach Zeige-Ziel verteilen (Python Scripting, openHAB 5)
from openhab import rule, Registry
from openhab.triggers import when

import scope


def _int(name, default):
    try:
        return Registry.getItemState(name).intValue()
    except AttributeError:
        return default


def _toggle(name, a, b):
    item = Registry.getItem(name)
    item.sendCommand(b if item.getState() == a else a)


@rule()
@when("System started")
def hybrid_b_start(module, input):
    if str(Registry.getItemState("Leap_Multimedia_Freigabe")) == "NULL":
        Registry.getItem("Leap_Multimedia_Freigabe").postUpdate(scope.ON)


@rule()
@when("Time cron 0 0 23 * * ?")
def hybrid_b_nachts(module, input):
    Registry.getItem("Leap_Multimedia_Freigabe").sendCommand(scope.OFF)


@rule()
@when("Channel mqtt:topic:mosquitto:leap_multimedia:gesture triggered")
def hybrid_b_gesten(module, input):
    e = str(input["event"].getEvent())
    ziel = str(Registry.getItemState("Leap_Multimedia_Ziel"))
    cmd = lambda name, v: Registry.getItem(name).sendCommand(v)  # noqa: E731

    if ziel == "TV":
        kanal = _int("iMultimedia_Samsung_TV_Kanal", 1)
        if e == "SWIPE_RIGHT":
            cmd("iMultimedia_Samsung_TV_Kanal", kanal + 1)
        elif e == "SWIPE_LEFT" and kanal > 1:
            cmd("iMultimedia_Samsung_TV_Kanal", kanal - 1)
        elif e == "KEY_TAP":
            _toggle("iMultimedia_Samsung_TV_Stumm", scope.ON, scope.OFF)
        elif e == "GRAB":
            cmd("iMultimedia_Samsung_TV_Power", scope.OFF)
    elif ziel == "LICHT":
        hell = _int("iMultimedia_Hue_Lampen_Helligkeit", 0)
        if e == "SWIPE_UP":
            cmd("iMultimedia_Hue_Lampen_Helligkeit", min(100, hell + 20))
        elif e == "SWIPE_DOWN":
            cmd("iMultimedia_Hue_Lampen_Helligkeit", max(0, hell - 20))
        elif e == "KEY_TAP":
            _toggle("iMultimedia_Hue_Lampen_Schalter", scope.ON, scope.OFF)
    elif ziel == "ROLLLADEN":
        if e in ("SWIPE_UP", "SWIPE_DOWN"):
            cmd("iMultimedia_Somfy_Rollladen_Steuerung_Prozent", 0 if e == "SWIPE_UP" else 100)
    elif ziel == "RADIO":
        if e == "KEY_TAP":
            _toggle("iMultimedia_Sonos_Lautsprecher_Steuerung", scope.PLAY, scope.PAUSE)
        elif e == "SWIPE_RIGHT":
            cmd("iMultimedia_Sonos_Lautsprecher_Steuerung", scope.NEXT)
        elif e == "SWIPE_LEFT":
            cmd("iMultimedia_Sonos_Lautsprecher_Steuerung", scope.PREVIOUS)
