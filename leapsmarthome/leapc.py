"""
leapc.py – lädt die LeapC-CFFI-Bindings (ffi, libleapc) robust unter Linux.

Es gibt drei verbreitete Varianten, wie das CFFI-Modul installiert ist:
  1. ultraleap/leapc-python-bindings:  from leapc_cffi import ffi, libleapc
  2. Paketstruktur wie im ROS2-Paket:  from leapc_cffi._leapc_cffi import ffi, lib
  3. Selbst gebautes Einzelmodul:      from _leapc_cffi import ffi, lib

Zusätzlich wird libLeapC.so vorab global geladen, falls das Modul die
Bibliothek sonst nicht findet. Suchpfade:
  - $LEAPSDK_INSTALL_LOCATION
  - /opt/ultraleap/LeapSDK                    (Linux ARM, Raspberry Pi)
  - /usr/lib/ultraleap-hand-tracking-service  (Linux x64)

Windows wird in diesem Buch bewusst nicht unterstützt (kein DLL-Workaround).
"""

import ctypes
import os
import sys

_SDK_CANDIDATES = [
    os.environ.get("LEAPSDK_INSTALL_LOCATION", ""),
    "/opt/ultraleap/LeapSDK",
    "/usr/lib/ultraleap-hand-tracking-service",
]


def _preload_libleapc() -> None:
    for base in filter(None, _SDK_CANDIDATES):
        for sub in ("lib", "lib/aarch64", "lib/arm64", "lib/x64", ""):
            path = os.path.join(base, sub, "libLeapC.so")
            if os.path.exists(path):
                try:
                    ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    continue
                # Verzeichnis zusätzlich für das CFFI-Modul durchsuchbar machen
                for p in (base, os.path.join(base, "leapc_cffi")):
                    if os.path.isdir(p) and p not in sys.path:
                        sys.path.append(p)
                return


_preload_libleapc()

try:
    from leapc_cffi import ffi, libleapc  # type: ignore  # Variante 1
except ImportError:
    try:
        from leapc_cffi._leapc_cffi import ffi, lib as libleapc  # type: ignore  # Variante 2
    except ImportError:
        try:
            from _leapc_cffi import ffi, lib as libleapc  # type: ignore  # Variante 3
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "LeapC-CFFI-Modul nicht gefunden. Ist Ultraleap Gemini installiert und "
                "leapc_cffi gebaut? Siehe Kapitel 5 (05-installation)."
            ) from exc

__all__ = ["ffi", "libleapc", "const"]


def const(name: str, default=None):
    """LeapC-Konstante tolerant auslesen (Namen variieren leicht zwischen SDK-Versionen)."""
    return getattr(libleapc, name, default)
