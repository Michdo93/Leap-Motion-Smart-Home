"""
runtime.py – gemeinsame Kleinigkeiten für alle Beispielprogramme:
Logging, Live-Zeile im Terminal, Kommandozeile (--config, --sensor), Sensorauswahl.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import List, Optional, Set

from .config import Config, load_config


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")


def live(text: str) -> None:
    """Eine Zeile im Terminal überschreiben (Live-Anzeige)."""
    sys.stdout.write("\r" + text.ljust(100)[:120])
    sys.stdout.flush()


def say(text: str) -> None:
    """Meldung in eigener Zeile, ohne die Live-Zeile zu zerstören."""
    sys.stdout.write("\r" + " " * 120 + "\r" + text + "\n")
    sys.stdout.flush()


def base_parser(description: str, sensor: bool = True) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--config", help="Pfad zur config.yaml")
    if sensor:
        ap.add_argument("--sensor", action="append",
                        help="Alias oder Seriennummer des Sensors (mehrfach möglich); "
                             "ohne Angabe: alle Sensoren")
    ap.add_argument("-v", "--verbose", action="store_true")
    return ap


def load(args: argparse.Namespace, required: bool = True) -> Optional[Config]:
    setup_logging(getattr(args, "verbose", False))
    try:
        return load_config(getattr(args, "config", None))
    except FileNotFoundError:
        if required:
            raise
        return None


def sensor_serials(cfg: Optional[Config], names: Optional[List[str]]) -> Optional[Set[str]]:
    """Aliase aus config.yaml (devices:) in Seriennummern übersetzen."""
    if not names:
        return None
    result = set()
    for n in names:
        serial = cfg.serial_for(n) if cfg else None
        result.add(serial or n)
    return result


def alias(cfg: Optional[Config], serial: str) -> str:
    return cfg.alias_for(serial) if cfg else serial
