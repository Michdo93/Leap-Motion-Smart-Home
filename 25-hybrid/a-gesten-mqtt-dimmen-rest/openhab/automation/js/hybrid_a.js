// Kapitel 25 – Hybrid A: Ereignis-Regeln (JavaScript Scripting)
const GESTE = "mqtt:topic:mosquitto:leap_multimedia:gesture";

rules.when().channel(GESTE).triggered().then((event) => {
  const e = event.receivedEvent;
  if (e === "KEY_TAP") {
    const sw = items.iMultimedia_Hue_Lampen_Schalter;
    sw.sendCommand(sw.state === "ON" ? "OFF" : "ON");
  } else if (e.startsWith("FINGERS_")) {
    items.iMultimedia_Hue_Lampen_Szene.sendCommand(`Szene ${e.substring(8)}`);
    items.iMultimedia_Hue_Lampen_Schalter.sendCommand("ON");
  } else if (e === "CIRCLE_CW" || e === "CIRCLE_CCW") {
    const ct = items.iMultimedia_Hue_Lampen_Farbtemperatur;
    const aktuell = ct.numericState ?? 50;
    ct.sendCommand(Math.max(0, Math.min(100, aktuell + (e === "CIRCLE_CW" ? 10 : -10))));
  }
}).build("Hybrid A: Gesten (JS)");
