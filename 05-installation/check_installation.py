#!/usr/bin/env python3
"""
Kapitel 5 – Installation prüfen.

Prüft Schritt für Schritt:
  1. Python-Version (vorkompilierte leapc_cffi-Module gibt es für ARM bis 3.11)
  2. Ultraleap-SDK und libLeapC.so
  3. systemd-Dienst des Ultraleap Hand Tracking Service
  4. Import der LeapC-Bindings
  5. Verbindung zum Dienst und Anzahl erkannter Controller
  6. Zusatzbibliotheken (yaml, paho-mqtt, python-openhab-rest-client)
"""

import glob
import importlib
import os
import pathlib
import platform
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel

OK, FAIL, WARN = "  [ OK ]", "  [FAIL]", "  [WARN]"


def step(title):
    print(f"\n{title}")


def main() -> int:
    errors = 0

    step("1. Python")
    v = sys.version_info
    print(f"{OK} Python {platform.python_version()} auf {platform.machine()} ({platform.system()})")
    if platform.machine() in ("aarch64", "arm64") and v >= (3, 12):
        print(f"{WARN} Für Python >= 3.12 auf ARM muss leapc_cffi selbst gebaut werden "
              "(install_leap_python.sh erledigt das).")

    step("2. Ultraleap SDK")
    candidates = [os.environ.get("LEAPSDK_INSTALL_LOCATION", ""), "/opt/ultraleap/LeapSDK",
                  "/usr/lib/ultraleap-hand-tracking-service"]
    libs = [p for c in filter(None, candidates) for p in glob.glob(f"{c}/**/libLeapC.so*", recursive=True)]
    if libs:
        print(f"{OK} libLeapC.so: {libs[0]}")
    else:
        print(f"{FAIL} libLeapC.so nicht gefunden")
        errors += 1

    step("3. Dienst")
    for unit in ("ultraleap-hand-tracking-service", "ultraleap-hand-tracking"):
        try:
            state = subprocess.run(["systemctl", "is-active", unit], capture_output=True,
                                   text=True, timeout=5).stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            state = "unbekannt"
        if state == "active":
            print(f"{OK} {unit}.service läuft")
            break
    else:
        print(f"{WARN} Kein aktiver Ultraleap-Dienst gefunden (systemctl status ultraleap-hand-tracking-service)")

    step("4. LeapC-Bindings")
    try:
        from leapsmarthome.leapc import ffi, libleapc  # noqa: F401
        print(f"{OK} leapc_cffi importiert")
    except ImportError as exc:
        print(f"{FAIL} {exc}")
        return errors + 1

    step("5. Verbindung zum Dienst")
    conn = ffi.new("LEAP_CONNECTION *")
    if libleapc.LeapCreateConnection(ffi.NULL, conn) != libleapc.eLeapRS_Success:
        print(f"{FAIL} LeapCreateConnection")
        return errors + 1
    libleapc.LeapOpenConnection(conn[0])
    msg = ffi.new("LEAP_CONNECTION_MESSAGE *")
    connected = False
    end = time.time() + 3
    while time.time() < end:
        if libleapc.LeapPollConnection(conn[0], 200, msg) == libleapc.eLeapRS_Success:
            if msg.type == libleapc.eLeapEventType_Connection:
                connected = True
            if connected and msg.type == libleapc.eLeapEventType_Device:
                break
    count = ffi.new("uint32_t *")
    libleapc.LeapGetDeviceList(conn[0], ffi.NULL, count)
    libleapc.LeapCloseConnection(conn[0])
    libleapc.LeapDestroyConnection(conn[0])
    if connected:
        print(f"{OK} Verbunden mit dem Ultraleap-Dienst")
    else:
        print(f"{FAIL} Keine Verbindung zum Dienst")
        errors += 1
    if count[0]:
        print(f"{OK} {count[0]} Controller erkannt")
    else:
        print(f"{WARN} Kein Controller erkannt (USB, Kabel, USB/IP prüfen: lsusb | grep -i leap)")

    step("6. Zusatzbibliotheken")
    for mod, name in (("yaml", "PyYAML"), ("paho.mqtt.client", "paho-mqtt"),
                      ("openhab.AsyncClient", "python-openhab-rest-client")):
        try:
            importlib.import_module(mod)
            print(f"{OK} {name}")
        except ImportError:
            print(f"{WARN} {name} fehlt (pip install -r requirements.txt)")

    print("\nErgebnis:", "alles bereit" if errors == 0 else f"{errors} Fehler")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
