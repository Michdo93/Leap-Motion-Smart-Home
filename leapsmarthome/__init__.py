"""
leapsmarthome – Begleitbibliothek zum Buch „Leap Motion im Smart Home“.

Module:
  leapc        LeapC-CFFI-Bindings laden (Raspberry Pi / Linux)
  leapdevices  Sensoren per Seriennummer verwalten, Frames kopieren
  mapping      Millimeter -> Prozent, Zonen, Hysterese, Änderungsfilter
  gestures     eigene Gestenerkennung (Swipe, Circle, Taps, Grab, Pinch, ...)
  config       config/config.yaml laden
  mqtt         Ansatz A: MQTT-Publisher (paho-mqtt)
  rest         Ansatz B: openHAB-REST (python-openhab-rest-client)
  runtime      Logging, Terminalausgabe, Kommandozeile

leapdevices/gestures importieren LeapC erst beim Import – mapping/config/mqtt/rest
lassen sich auch ohne installiertes Ultraleap-SDK verwenden.
"""

__version__ = "1.0.0"
