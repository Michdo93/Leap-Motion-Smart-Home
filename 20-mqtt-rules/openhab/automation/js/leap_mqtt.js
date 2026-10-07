// ============================================================================
// Kapitel 20 – Ansatz A: Gerätesteuerung über openHAB-Regeln (JavaScript Scripting)
// Datei: $OPENHAB_CONF/automation/js/leap_mqtt.js
// Nur EINE Sprachvariante (DSL, JS oder Python) gleichzeitig aktivieren!
// ============================================================================

const GESTE = "mqtt:topic:mosquitto:leap_multimedia:gesture";
const MODI = ["ROLLLADEN", "JALOUSIE", "LICHT", "WEBRADIO"];

const ROLLLADEN = {
  Z1: "iMultimedia_Somfy_Rollladen_Steuerung_Prozent",
  Z2: "iKonferenz_Somfy_Rollladen2_Steuerung_Prozent",
  Z3: "iKonferenz_Somfy_Rollladen1_Steuerung_Prozent",
  Z4: "iSmartHome_Somfy_Rollladen_Steuerung_Prozent",
};
const JALOUSIE = {
  HINTEN_LINKS: "iKueche_Jalousie_Hinten_Steuerung_Prozent",
  HINTEN_RECHTS: "iBad_Jalousie_Hinten_Steuerung_Prozent",
  VORNE_LINKS: "iKueche_Jalousie_Vorne_Steuerung_Prozent",
  VORNE_RECHTS: "iBad_Jalousie_Vorne_Steuerung_Prozent",
};
const LICHT = {
  HINTEN_LINKS: "iKueche", HINTEN_MITTE: "iBad", HINTEN_RECHTS: "iIoT",
  VORNE_LINKS: "iSmartHome", VORNE_RECHTS: "iMultimedia",
};
const SENDER = ["SWR3", "bigFM_BW", "Energy_Stuttgart", "Radio_Regenbogen", "Antenne1", "DASDING"];

const modus = () => items.Leap_Multimedia_Modus.state;
const handDa = () => items.Leap_Multimedia_Hand.state === "ON";
const zahl = (name) => items.getItem(name).numericState;   // null bei NULL/UNDEF

// --- Start -----------------------------------------------------------------
rules.when().system().startLevel(100).then(() => {
  if (items.Leap_Multimedia_Modus.isUninitialized) items.Leap_Multimedia_Modus.postUpdate("ROLLLADEN");
  if (items.Leap_Multimedia_Webradio_Sender.isUninitialized) items.Leap_Multimedia_Webradio_Sender.postUpdate("SWR3");
}).build("Leap MQTT: Start (JS)");

// --- Modus -----------------------------------------------------------------
rules.when().channel(GESTE).triggered("CIRCLE_CW").or().channel(GESTE).triggered("CIRCLE_CCW").then((event) => {
  let idx = Math.max(0, MODI.indexOf(modus()));
  idx = event.receivedEvent === "CIRCLE_CW" ? (idx + 1) % MODI.length : (idx + MODI.length - 1) % MODI.length;
  items.Leap_Multimedia_Modus.postUpdate(MODI[idx]);
  console.info(`Modus: ${MODI[idx]}`);
}).build("Leap MQTT: Modus per Kreis (JS)");

// --- Rollladen / Jalousie --------------------------------------------------
rules.when()
  .item("Leap_Multimedia_Hoehe").changed()
  .or().item("Leap_Multimedia_Zone_Rollladen").changed()
  .or().item("Leap_Multimedia_Zone_Jalousie").changed()
  .then(() => {
    const m = modus();
    if ((m !== "ROLLLADEN" && m !== "JALOUSIE") || !handDa()) return;
    if (Date.now() < (cache.private.get("swipeSperreBis") || 0)) return;
    const hoehe = zahl("Leap_Multimedia_Hoehe");
    if (hoehe === null) return;
    const item = m === "ROLLLADEN"
      ? ROLLLADEN[items.Leap_Multimedia_Zone_Rollladen.state]
      : JALOUSIE[items.Leap_Multimedia_Zone_Jalousie.state];
    if (!item) return;
    items.getItem(item).sendCommand(100 - Math.round(hoehe));   // Hand oben = offen
  }).build("Leap MQTT: Rollladen/Jalousie per Höhe (JS)");

rules.when().channel(GESTE).triggered("SWIPE_UP").or().channel(GESTE).triggered("SWIPE_DOWN").then((event) => {
  const m = modus();
  const item = m === "ROLLLADEN" ? ROLLLADEN[items.Leap_Multimedia_Zone_Rollladen.state]
    : m === "JALOUSIE" ? JALOUSIE[items.Leap_Multimedia_Zone_Jalousie.state] : undefined;
  if (!item) return;
  items.getItem(item).sendCommand(event.receivedEvent === "SWIPE_UP" ? 0 : 100);
  cache.private.put("swipeSperreBis", Date.now() + 2000);
}).build("Leap MQTT: Rollladen/Jalousie per Swipe (JS)");

// --- Licht -----------------------------------------------------------------
rules.when()
  .item("Leap_Multimedia_Hoehe").changed()
  .or().item("Leap_Multimedia_Tiefe").changed()
  .or().item("Leap_Multimedia_Zone_Licht").changed()
  .then(() => {
    if (modus() !== "LICHT" || !handDa()) return;
    const raum = LICHT[items.Leap_Multimedia_Zone_Licht.state];
    const hell = zahl("Leap_Multimedia_Hoehe");
    const tiefe = zahl("Leap_Multimedia_Tiefe");
    if (!raum || hell === null || tiefe === null) return;
    const farbton = (Math.round((tiefe * 3.6) / 5) * 5) % 360;
    items.getItem(`${raum}_Hue_Lampen_Farbe`).sendCommand(`${farbton},100,${Math.round(hell)}`);
    items.getItem(`${raum}_Hue_Lampen_Schalter`).sendCommand(hell > 5 ? "ON" : "OFF");
  }).build("Leap MQTT: Licht (JS)");

// --- Webradio --------------------------------------------------------------
rules.when().item("Leap_Multimedia_Hoehe").changed().then(() => {
  if (modus() !== "WEBRADIO" || !handDa()) return;
  const grab = zahl("Leap_Multimedia_Grab");
  if (grab !== null && grab >= 80) return;
  const hoehe = zahl("Leap_Multimedia_Hoehe");
  if (hoehe !== null) items.iMultimedia_Sonos_Lautsprecher_Lautstaerke.sendCommand(Math.round(hoehe));
}).build("Leap MQTT: Webradio-Lautstärke (JS)");

rules.when().channel(GESTE).triggered().then((event) => {
  if (modus() !== "WEBRADIO") return;
  let sender = items.Leap_Multimedia_Webradio_Sender.state;
  if (!SENDER.includes(sender)) sender = SENDER[0];
  const e = event.receivedEvent;
  if (e === "GRAB") {
    items.getItem(`iMultimedia_Webradio_${sender}`).sendCommand("OFF");
  } else if (e === "RELEASE" || e === "FIST_TAP") {
    items.getItem(`iMultimedia_Webradio_${sender}`).sendCommand("ON");
  } else if (e === "SWIPE_LEFT" || e === "SWIPE_RIGHT") {
    const dir = e === "SWIPE_RIGHT" ? 1 : -1;
    const neu = SENDER[(SENDER.indexOf(sender) + dir + SENDER.length) % SENDER.length];
    items.getItem(`iMultimedia_Webradio_${sender}`).sendCommand("OFF");
    items.getItem(`iMultimedia_Webradio_${neu}`).sendCommand("ON");
    items.Leap_Multimedia_Webradio_Sender.postUpdate(neu);
    console.info(`Sender: ${neu}`);
  }
}).build("Leap MQTT: Webradio per Geste (JS)");
