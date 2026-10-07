# Kapitel 25 – Hybrid A: Ereignis-Regeln (Python Scripting, openHAB 5)
from openhab import rule, Registry
from openhab.triggers import when

import scope


@rule()
@when("Channel mqtt:topic:mosquitto:leap_multimedia:gesture triggered")
def hybrid_a_gesten(module, input):
    e = str(input["event"].getEvent())
    schalter = Registry.getItem("iMultimedia_Hue_Lampen_Schalter")
    if e == "KEY_TAP":
        schalter.sendCommand(scope.OFF if schalter.getState() == scope.ON else scope.ON)
    elif e.startswith("FINGERS_"):
        Registry.getItem("iMultimedia_Hue_Lampen_Szene").sendCommand(f"Szene {e[8:]}")
        schalter.sendCommand(scope.ON)
    elif e in ("CIRCLE_CW", "CIRCLE_CCW"):
        ct = Registry.getItem("iMultimedia_Hue_Lampen_Farbtemperatur")
        try:
            aktuell = ct.getState().intValue()
        except AttributeError:
            aktuell = 50
        ct.sendCommand(max(0, min(100, aktuell + (10 if e == "CIRCLE_CW" else -10))))
