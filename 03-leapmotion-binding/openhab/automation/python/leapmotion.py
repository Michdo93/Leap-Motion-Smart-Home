# ============================================================================
# Kapitel 3 – Regeln für das Leap-Motion-Binding (Python Scripting, openHAB 5)
# Datei: $OPENHAB_CONF/automation/python/leapmotion.py
# Hinweis: Nur EINE Sprachvariante aktivieren, sonst feuern die Regeln doppelt.
# ============================================================================

from openhab import rule, Registry
from openhab.triggers import when

import scope


@rule()
@when("Channel leapmotion:controller:1:gesture triggered")
def leap_binding_rohereignis(module, input):
    ereignis = str(input["event"].getEvent())
    Registry.getItem("Leap_Binding_Ereignis").postUpdate(ereignis)

    if ereignis == "clockwise":
        Registry.getItem("iMultimedia_Sonos_Lautsprecher_Steuerung").sendCommand(scope.NEXT)
    elif ereignis == "anticlockwise":
        Registry.getItem("iMultimedia_Sonos_Lautsprecher_Steuerung").sendCommand(scope.PREVIOUS)
    elif ereignis.startswith("fingers"):
        finger, hoehe = (int(v) for v in ereignis[7:].split("_"))
        leap_binding_rohereignis.logger.debug(f"Finger: {finger} | Höhe: {hoehe} mm")


@rule()
@when("Item Leap_Binding_Schalter changed")
def leap_binding_tap_licht(module, input):
    Registry.getItem("iMultimedia_Hue_Lampen_Schalter").sendCommand(input["event"].getItemState())


@rule()
@when("Item Leap_Binding_Finger changed")
def leap_binding_finger_licht(module, input):
    Registry.getItem("iMultimedia_Hue_Lampen_Helligkeit").sendCommand(input["event"].getItemState())


@rule()
@when("Item Leap_Binding_Hoehe changed")
def leap_binding_hoehe_rollladen(module, input):
    prozent = 100 - input["event"].getItemState().intValue()
    Registry.getItem("iMultimedia_Somfy_Rollladen_Steuerung_Prozent").sendCommand(prozent)


@rule()
@when("Item Leap_Binding_Farbe changed")
def leap_binding_farbe(module, input):
    Registry.getItem("iMultimedia_Hue_Lampen_Farbe").sendCommand(input["event"].getItemState())
