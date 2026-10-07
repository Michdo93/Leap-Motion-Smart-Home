# ============================================================================
# Kapitel 20 – Ansatz A: Gerätesteuerung über openHAB-Regeln (Python Scripting, openHAB 5)
# Datei: $OPENHAB_CONF/automation/python/leap_mqtt.py
# Nur EINE Sprachvariante (DSL, JS oder Python) gleichzeitig aktivieren!
# ============================================================================

import time

from openhab import rule, Registry
from openhab.triggers import when

import scope

GESTE = "mqtt:topic:mosquitto:leap_multimedia:gesture"
MODI = ["ROLLLADEN", "JALOUSIE", "LICHT", "WEBRADIO"]

ROLLLADEN = {
    "Z1": "iMultimedia_Somfy_Rollladen_Steuerung_Prozent",
    "Z2": "iKonferenz_Somfy_Rollladen2_Steuerung_Prozent",
    "Z3": "iKonferenz_Somfy_Rollladen1_Steuerung_Prozent",
    "Z4": "iSmartHome_Somfy_Rollladen_Steuerung_Prozent",
}
JALOUSIE = {
    "HINTEN_LINKS": "iKueche_Jalousie_Hinten_Steuerung_Prozent",
    "HINTEN_RECHTS": "iBad_Jalousie_Hinten_Steuerung_Prozent",
    "VORNE_LINKS": "iKueche_Jalousie_Vorne_Steuerung_Prozent",
    "VORNE_RECHTS": "iBad_Jalousie_Vorne_Steuerung_Prozent",
}
LICHT = {
    "HINTEN_LINKS": "iKueche", "HINTEN_MITTE": "iBad", "HINTEN_RECHTS": "iIoT",
    "VORNE_LINKS": "iSmartHome", "VORNE_RECHTS": "iMultimedia",
}
SENDER = ["SWR3", "bigFM_BW", "Energy_Stuttgart", "Radio_Regenbogen", "Antenne1", "DASDING"]

_swipe_sperre_bis = 0.0


def _text(name):
    return str(Registry.getItemState(name))


def _zahl(name):
    """Zahlenwert eines Items oder None (NULL/UNDEF)."""
    state = Registry.getItemState(name)
    try:
        return float(state.floatValue())
    except AttributeError:
        return None


def _hand_da():
    return Registry.getItemState("Leap_Multimedia_Hand") == scope.ON


def _cmd(name, value):
    Registry.getItem(name).sendCommand(value)


@rule()
@when("System started")
def leap_start(module, input):
    if _text("Leap_Multimedia_Modus") in ("NULL", "UNDEF"):
        Registry.getItem("Leap_Multimedia_Modus").postUpdate("ROLLLADEN")
    if _text("Leap_Multimedia_Webradio_Sender") in ("NULL", "UNDEF"):
        Registry.getItem("Leap_Multimedia_Webradio_Sender").postUpdate("SWR3")


@rule()
@when(f"Channel {GESTE} triggered CIRCLE_CW")
@when(f"Channel {GESTE} triggered CIRCLE_CCW")
def leap_modus(module, input):
    modus = _text("Leap_Multimedia_Modus")
    idx = MODI.index(modus) if modus in MODI else 0
    step = 1 if str(input["event"].getEvent()) == "CIRCLE_CW" else -1
    neu = MODI[(idx + step) % len(MODI)]
    Registry.getItem("Leap_Multimedia_Modus").postUpdate(neu)
    leap_modus.logger.info(f"Modus: {neu}")


@rule()
@when("Item Leap_Multimedia_Hoehe changed")
@when("Item Leap_Multimedia_Zone_Rollladen changed")
@when("Item Leap_Multimedia_Zone_Jalousie changed")
def leap_rollladen_hoehe(module, input):
    modus = _text("Leap_Multimedia_Modus")
    if modus not in ("ROLLLADEN", "JALOUSIE") or not _hand_da():
        return
    if time.time() < _swipe_sperre_bis:
        return
    hoehe = _zahl("Leap_Multimedia_Hoehe")
    if hoehe is None:
        return
    if modus == "ROLLLADEN":
        item = ROLLLADEN.get(_text("Leap_Multimedia_Zone_Rollladen"))
    else:
        item = JALOUSIE.get(_text("Leap_Multimedia_Zone_Jalousie"))
    if item:
        _cmd(item, 100 - round(hoehe))   # Hand oben = offen


@rule()
@when(f"Channel {GESTE} triggered SWIPE_UP")
@when(f"Channel {GESTE} triggered SWIPE_DOWN")
def leap_rollladen_swipe(module, input):
    global _swipe_sperre_bis
    modus = _text("Leap_Multimedia_Modus")
    if modus == "ROLLLADEN":
        item = ROLLLADEN.get(_text("Leap_Multimedia_Zone_Rollladen"))
    elif modus == "JALOUSIE":
        item = JALOUSIE.get(_text("Leap_Multimedia_Zone_Jalousie"))
    else:
        return
    if item:
        _cmd(item, 0 if str(input["event"].getEvent()) == "SWIPE_UP" else 100)
        _swipe_sperre_bis = time.time() + 2.0


@rule()
@when("Item Leap_Multimedia_Hoehe changed")
@when("Item Leap_Multimedia_Tiefe changed")
@when("Item Leap_Multimedia_Zone_Licht changed")
def leap_licht(module, input):
    if _text("Leap_Multimedia_Modus") != "LICHT" or not _hand_da():
        return
    raum = LICHT.get(_text("Leap_Multimedia_Zone_Licht"))
    hell, tiefe = _zahl("Leap_Multimedia_Hoehe"), _zahl("Leap_Multimedia_Tiefe")
    if raum is None or hell is None or tiefe is None:
        return
    farbton = int(round(tiefe * 3.6 / 5) * 5) % 360
    _cmd(f"{raum}_Hue_Lampen_Farbe", f"{farbton},100,{round(hell)}")
    _cmd(f"{raum}_Hue_Lampen_Schalter", "ON" if hell > 5 else "OFF")


@rule()
@when("Item Leap_Multimedia_Hoehe changed")
def leap_webradio_lautstaerke(module, input):
    if _text("Leap_Multimedia_Modus") != "WEBRADIO" or not _hand_da():
        return
    grab = _zahl("Leap_Multimedia_Grab")
    if grab is not None and grab >= 80:
        return
    hoehe = _zahl("Leap_Multimedia_Hoehe")
    if hoehe is not None:
        _cmd("iMultimedia_Sonos_Lautsprecher_Lautstaerke", round(hoehe))


@rule()
@when(f"Channel {GESTE} triggered")
def leap_webradio_geste(module, input):
    if _text("Leap_Multimedia_Modus") != "WEBRADIO":
        return
    sender = _text("Leap_Multimedia_Webradio_Sender")
    if sender not in SENDER:
        sender = SENDER[0]
    ev = str(input["event"].getEvent())
    if ev == "GRAB":
        _cmd(f"iMultimedia_Webradio_{sender}", "OFF")
    elif ev in ("RELEASE", "FIST_TAP"):
        _cmd(f"iMultimedia_Webradio_{sender}", "ON")
    elif ev in ("SWIPE_LEFT", "SWIPE_RIGHT"):
        step = 1 if ev == "SWIPE_RIGHT" else -1
        neu = SENDER[(SENDER.index(sender) + step) % len(SENDER)]
        _cmd(f"iMultimedia_Webradio_{sender}", "OFF")
        _cmd(f"iMultimedia_Webradio_{neu}", "ON")
        Registry.getItem("Leap_Multimedia_Webradio_Sender").postUpdate(neu)
        leap_webradio_geste.logger.info(f"Sender: {neu}")
