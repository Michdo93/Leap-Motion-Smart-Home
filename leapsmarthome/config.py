"""
config.py – lädt config/config.yaml (wird NICHT eingecheckt, siehe .gitignore).

Suchreihenfolge:
  1. Pfad aus Umgebungsvariable LEAP_CONFIG
  2. ./config.yaml im aktuellen Verzeichnis
  3. <Repo>/config/config.yaml

Vorlage: config/config.example.yaml  ->  cp config/config.example.yaml config/config.yaml
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


class Config(dict):
    """Dictionary mit ein paar Komfortfunktionen."""

    path: Optional[Path] = None

    # -- Sensoren --------------------------------------------------------------
    @property
    def devices(self) -> Dict[str, str]:
        """Seriennummer -> Alias (z. B. 'LP19566274693' -> 'multimedia')."""
        return {str(k): str(v) for k, v in (self.get("devices") or {}).items()}

    def alias_for(self, serial: str) -> str:
        return self.devices.get(serial, serial)

    def serial_for(self, alias: str) -> Optional[str]:
        for serial, name in self.devices.items():
            if name == alias:
                return serial
        return None

    # -- Abschnitte ----------------------------------------------------------
    def section(self, name: str) -> Dict[str, Any]:
        return dict(self.get(name) or {})


def find_config_path(explicit: Optional[str] = None) -> Path:
    candidates = [explicit, os.environ.get("LEAP_CONFIG"), "config.yaml",
                  str(REPO_ROOT / "config" / "config.yaml")]
    for c in candidates:
        if c and Path(c).is_file():
            return Path(c)
    raise FileNotFoundError(
        "Keine config.yaml gefunden. Bitte zuerst anlegen:\n"
        f"  cp {REPO_ROOT / 'config' / 'config.example.yaml'} {REPO_ROOT / 'config' / 'config.yaml'}"
    )


def load_config(path: Optional[str] = None) -> Config:
    p = find_config_path(path)
    with open(p, encoding="utf-8") as fh:
        cfg = Config(yaml.safe_load(fh) or {})
    cfg.path = p
    return cfg
