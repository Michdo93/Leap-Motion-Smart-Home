# Leap Motion im Smart Home – Begleit-Repository

Codes zum Buch über **Leap Motion, Python 3, openHAB 5 und ROS 2**.
Zielplattform ist ein **Raspberry Pi** mit einem **Leap Motion Controller der 1. Generation (LM-010)**.

> Alle Smart-Home-Geräte sind **virtuell**: Items ohne Thing/Channel, orientiert an den
> jeweiligen Bindings (Somfy TaHoma, HomeMatic, Hue, Sonos, Samsung TV). Things gibt es nur
> für das **Leap-Motion-Binding** und das **MQTT-Binding**. Dank `autoupdate` übernehmen die
> virtuellen Items jeden Befehl als Zustand – alles lässt sich ohne echte Geräte testen.

## Aufbau

| Ordner | Kapitel | Inhalt |
|---|---|---|
| `leapsmarthome/` | – | Begleitbibliothek: LeapC laden, Sensoren per Seriennummer, Zonen, Gesten, MQTT, REST |
| `config/` | 5 | `config.example.yaml` → `config.yaml` (steht in `.gitignore`) |
| `00-virtuelle-geraete/` | alle | Semantisches Modell, virtuelle Items, Test-Sitemap |
| `03-leapmotion-binding/` | 3 | Thing, Items mit Profilen, Regeln (DSL/JS/Python) – ohne eigene Programmierung |
| `05-installation/` | 5 | Installationsskript (venv, `leapc_cffi` bauen), Installationsprüfung |
| `06-hardware-discovery/` | 6 | Hardware-Check, Discovery (Seriennummer vs. Laufzeit-ID) |
| `07-frames/` | 7 | Event-Schleife von LeapC, High-Level-API zum Vergleich |
| `08-handdaten/` | 8 | Koordinaten, Handdaten (Pitch/Yaw/Roll, Grab, Pinch) |
| `09-finger-knochen-arm/` | 9 | Finger, Knochen, Arm |
| `10-zonen-raster/` | 10 | Zonen entlang X, Höhe in %, 2x2- und 3x3-Raster |
| `11-gesten/` | 11 | Swipe, Kreis, Key-Tap, Screen-Tap, Grab/Pinch, Finger zählen, Drehregler, Cursor, Kombination |
| `12-mehrere-controller/` | 12 | Mehrere Sensoren, Rollladen pro Seriennummer, Rollen-Router |
| `13-robuster-code/` | 13 | Vorlage für den Dauerbetrieb, systemd-Unit |
| `16-usbip/` | 16 | USB/IP: Pi als Server, Ubuntu-VM als Client, Watchdog |
| `17-mosquitto/` | 17 | Broker-Konfiguration mit Benutzern und ACL |
| `18-mqtt-things/` | 18 | Broker-Thing, Generic-MQTT-Things und Items, MQTT-Monitor |
| `19-mqtt-gateway/` | 19 | Ansatz A: Leap-MQTT-Gateway (Zustände + Gesten-Ereignisse) |
| `20-mqtt-rules/` | 20 | Ansatz A: Rollladen, Jalousie, Licht, Webradio als Regeln (DSL/JS/Python) |
| `21-rest-grundlagen/` | 21 | Ansatz B: python-openhab-rest-client, kleinstes Leap-REST-Programm |
| `22-rest-beispiele/` | 22 | Ansatz B: Licht, Jalousie, Rollladen, Webradio (überarbeitete `*_oh.py`) |
| `23-samsung-tv/` | 23 | Samsung TV per Gesten (ein Sensor = ein Gerät) |
| `24-rueckkanal-sse/` | 24 | Item-Änderungen per SSE, relative Lautstärke mit Rückkanal |
| `25-hybrid/` | 25 | A: Gesten per MQTT + Dimmen per REST · B: Zeigen auf Geräte (REST-Kontext) + Gesten per MQTT |
| `26-robotik/` | 26 | Twist-Vorschau, ROS-2-Paket (`cmd_vel`, Totmann, Freigabe), Brücke ROS 2 ↔ MQTT ↔ openHAB |
| `tests/` | – | Tests mit LeapC-Attrappe – laufen ohne Hardware und ohne SDK |

Kapitel ohne Code (Einleitung, Hardware, Grenzen des Bindings, Architekturfragen, Ausblick)
haben keinen eigenen Ordner.

## Schnellstart auf dem Raspberry Pi

```bash
git clone https://github.com/Michdo93/<repo>.git Leap-Motion-Smart-Home
cd Leap-Motion-Smart-Home
bash 05-installation/install_leap_python.sh     # Gemini (ARM64) muss bereits installiert sein
source .venv/bin/activate
python3 05-installation/check_installation.py
python3 06-hardware-discovery/leap_discovery.py  # Seriennummern -> config/config.yaml
```

`config/config.yaml` enthält Token und Passwörter und wird **nie eingecheckt**.
Alle Programme verstehen `--config <pfad>`, `--sensor <alias|seriennummer>` und `-v`.

## openHAB-Dateien einspielen

Die Unterordner `openhab/` spiegeln `$OPENHAB_CONF` (`things/`, `items/`, `rules/`,
`sitemaps/`, `automation/js/`, `automation/python/`).

1. **Immer:** `00-virtuelle-geraete/openhab/*`
2. **Kapitel 3:** `03-leapmotion-binding/openhab/*` (nur macOS/Intel – das Binding läuft nicht auf dem Pi)
3. **Ansatz A:** `18-mqtt-things/openhab/*` + `20-mqtt-rules/openhab/*` – Passwort im Broker-Thing eintragen
4. **Hybrid:** zusätzlich `25-hybrid/*/openhab/*` (die Regeln aus Kapitel 20 dann deaktivieren)
5. **Robotik:** `26-robotik/openhab/*`

Regeln liegen jeweils in **drei Varianten** vor: Rules DSL (`rules/*.rules`),
JavaScript Scripting (`automation/js/*.js`) und Python Scripting (`automation/python/*.py`).
**Pro Kapitel nur eine Variante aktivieren**, sonst feuern die Regeln mehrfach.

Benötigte Add-ons: MQTT-Binding, ggf. JavaScript Scripting bzw. Python Scripting,
Basic UI für die Test-Sitemap.

## Namensschema

| Präfix | Bedeutung |
|---|---|
| `i<Raum>_<Gerät>_<Funktion>` | virtuelle Geräte, z. B. `iMultimedia_Somfy_Rollladen_Steuerung_Prozent` |
| `Leap_<Alias>_<Wert>` | Leap-Daten per MQTT, z. B. `Leap_Multimedia_Hoehe` |
| `leap/<alias>/...` | MQTT-Topics des Gateways, `<alias>` aus `config.yaml` |

## Tests ohne Hardware

```bash
pip install pytest pyyaml paho-mqtt aiohttp
python3 -m pytest -q tests
```

`tests/fake/_leapc_cffi.py` simuliert Geräte-, Verlust- und Tracking-Ereignisse.

## Hinweise

* **Seriennummer statt Laufzeit-ID:** Die Laufzeit-ID ändert sich beim Neustecken oder nach einem
  USB/IP-Reconnect, die Seriennummer (`LP…`) nicht. `leapsmarthome.leapdevices` ordnet beides zu.
* **Mehrere Controller / Verlängerungen:** Der LM-010 braucht viel USB-2.0-Bandbreite – aktive Hubs
  bzw. aktive Verlängerungen verwenden.
* **Gesten-API:** Circle/Swipe/Tap aus dem alten SDK v2 gibt es in Gemini nicht mehr; `leapsmarthome.gestures`
  ersetzt sie. Die Parameter sind Startwerte und als Klassenattribute anpassbar.
* **SSE:** `AsyncEvents` aus python-openhab-rest-client ruft intern eine private Methode auf;
  `OpenHABSender.watch_states()` nutzt deshalb die aiohttp-Session direkt.
