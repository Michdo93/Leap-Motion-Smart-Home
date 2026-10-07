#!/usr/bin/env bash
# ============================================================================
# Kapitel 5 – Python-3-Umgebung für Leap Motion auf dem Raspberry Pi
#
# Voraussetzung (manuell, siehe Buch):
#   * Raspberry Pi 4/5, Raspberry Pi OS 64 Bit (Bookworm) bzw. Ubuntu arm64
#   * Ultraleap Gemini für Linux ARM64 installiert, Dienst läuft
#     (Standardpfad des SDK: /opt/ultraleap/LeapSDK)
#   * Leap Motion Controller (LM-010) per USB angeschlossen
#
# Dieses Skript:
#   1. installiert Build-Abhängigkeiten
#   2. legt ein venv im Repo an
#   3. baut leapc_cffi aus ultraleap/leapc-python-bindings gegen das lokale SDK
#   4. installiert die Begleitbibliothek leapsmarthome + Abhängigkeiten
#
# Aufruf aus der Repo-Wurzel:  bash 05-installation/install_leap_python.sh
# ============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SDK="${LEAPSDK_INSTALL_LOCATION:-/opt/ultraleap/LeapSDK}"
BUILD_DIR="${REPO}/.build"

echo "== 1/5 Prüfe Ultraleap SDK unter ${SDK}"
if [[ ! -d "${SDK}" ]]; then
    for alt in /usr/lib/ultraleap-hand-tracking-service /opt/ultraleap/LeapSDK; do
        [[ -d "${alt}" ]] && SDK="${alt}" && break
    done
fi
if ! find "${SDK}" -name 'libLeapC.so*' 2>/dev/null | grep -q .; then
    echo "FEHLER: libLeapC.so nicht gefunden. Ist Ultraleap Gemini (ARM64) installiert?"
    echo "        Pfad per LEAPSDK_INSTALL_LOCATION=/pfad/zum/LeapSDK setzen."
    exit 1
fi
echo "   SDK gefunden: ${SDK}"
export LEAPSDK_INSTALL_LOCATION="${SDK}"

echo "== 2/5 Systempakete"
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev python3-yaml build-essential libffi-dev git

echo "== 3/5 Python-venv"
python3 -m venv --system-site-packages "${REPO}/.venv"
# shellcheck disable=SC1091
source "${REPO}/.venv/bin/activate"
pip install --upgrade pip build cffi

echo "== 4/5 leapc_cffi bauen (Python $(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))'))"
mkdir -p "${BUILD_DIR}"
if [[ ! -d "${BUILD_DIR}/leapc-python-bindings" ]]; then
    git clone --depth 1 https://github.com/ultraleap/leapc-python-bindings.git "${BUILD_DIR}/leapc-python-bindings"
fi
pushd "${BUILD_DIR}/leapc-python-bindings" >/dev/null
python3 -m build leapc-cffi
pip install leapc-cffi/dist/leapc_cffi-*.tar.gz
pip install -e leapc-python-api      # High-Level-API "import leap" (Kapitel 7)
popd >/dev/null

echo "== 5/5 Begleitbibliothek"
pip install -r "${REPO}/requirements.txt"
pip install -e "${REPO}"

if [[ ! -f "${REPO}/config/config.yaml" ]]; then
    cp "${REPO}/config/config.example.yaml" "${REPO}/config/config.yaml"
    echo "   config/config.yaml aus Vorlage angelegt – bitte anpassen."
fi

echo
echo "Fertig. Test:"
echo "  source .venv/bin/activate"
echo "  python3 05-installation/check_installation.py"
