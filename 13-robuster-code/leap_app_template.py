#!/usr/bin/env python3
"""
Kapitel 13 – Vorlage für eine robuste Leap-Anwendung (Dauerbetrieb als Dienst).

Enthält alles, was die einfachen Beispiele weglassen:
  * Konfiguration aus config/config.yaml, keine Zugangsdaten im Code
  * Logging statt print (journalctl -u leap-app@... zeigt die Ausgabe)
  * Warten auf den Sensor, ohne abzubrechen (Sensor kann später kommen)
  * An-/Abstecken und Dienst-Neustarts werden überstanden
  * sauberes Beenden bei SIGTERM (systemctl stop) und Strg+C
  * Watchdog: Warnung, wenn länger keine Frames kommen

Eigene Logik gehört in on_frame().
"""

import logging
import pathlib
import signal
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # Repo-Wurzel
from leapsmarthome.leapdevices import Frame, LeapDeviceManager  # noqa: E402
from leapsmarthome.runtime import alias, base_parser, load, sensor_serials  # noqa: E402

log = logging.getLogger("leap-app")
FRAME_TIMEOUT = 10.0   # s ohne Frames -> Warnung


class App:
    def __init__(self, cfg, serials):
        self.cfg = cfg
        self.serials = serials
        self.running = True
        self.last_frame = time.monotonic()
        self.warned = False

    def stop(self, *_):
        log.info("Beende ...")
        self.running = False

    # --- eigene Logik ------------------------------------------------------
    def on_frame(self, frame: Frame) -> None:
        hand = frame.hand()
        if hand:
            log.debug("%s: Y=%.0f", alias(self.cfg, frame.serial), hand.palm_position[1])

    # --- Rahmen -------------------------------------------------------------
    def run(self) -> int:
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        while self.running:
            try:
                with LeapDeviceManager(
                        serials=self.serials,
                        on_device_added=lambda i: log.info("Sensor %s verbunden", alias(self.cfg, i.serial)),
                        on_device_removed=lambda i: log.warning("Sensor %s getrennt", alias(self.cfg, i.serial)),
                ) as mgr:
                    log.info("Verbindung zum Ultraleap-Dienst geöffnet")
                    while self.running:
                        frame = mgr.poll(100)
                        now = time.monotonic()
                        if frame is not None:
                            self.last_frame, self.warned = now, False
                            try:
                                self.on_frame(frame)
                            except Exception:            # Fehler in der Logik dürfen
                                log.exception("Fehler in on_frame")  # den Dienst nicht beenden
                        elif not self.warned and now - self.last_frame > FRAME_TIMEOUT:
                            log.warning("Seit %.0f s keine Frames (Sensor getrennt? USB/IP?)", FRAME_TIMEOUT)
                            self.warned = True
            except RuntimeError as exc:
                log.error("%s – neuer Versuch in 5 s", exc)
                for _ in range(50):
                    if not self.running:
                        break
                    time.sleep(0.1)
        log.info("Beendet")
        return 0


def main():
    args = base_parser("Robuste Leap-Anwendung").parse_args()
    cfg = load(args, required=False)
    return App(cfg, sensor_serials(cfg, args.sensor)).run()


if __name__ == "__main__":
    sys.exit(main())
