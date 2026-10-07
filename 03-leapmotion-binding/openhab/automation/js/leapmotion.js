// ============================================================================
// Kapitel 3 – Regeln für das Leap-Motion-Binding (JavaScript Scripting, openhab-js)
// Datei: $OPENHAB_CONF/automation/js/leapmotion.js
// Hinweis: Nur EINE Sprachvariante aktivieren, sonst feuern die Regeln doppelt.
// ============================================================================

rules.when().channel("leapmotion:controller:1:gesture").triggered().then((event) => {
  const ereignis = event.receivedEvent;
  items.Leap_Binding_Ereignis.postUpdate(ereignis);

  if (ereignis === "clockwise") {
    items.iMultimedia_Sonos_Lautsprecher_Steuerung.sendCommand("NEXT");
  } else if (ereignis === "anticlockwise") {
    items.iMultimedia_Sonos_Lautsprecher_Steuerung.sendCommand("PREVIOUS");
  } else if (ereignis.startsWith("fingers")) {
    const [finger, hoehe] = ereignis.substring(7).split("_").map(Number);
    console.debug(`Finger: ${finger} | Höhe: ${hoehe} mm`);
  }
}).build("Leap Binding: Rohereignis (JS)");

rules.when().item("Leap_Binding_Schalter").changed().then((event) => {
  items.iMultimedia_Hue_Lampen_Schalter.sendCommand(event.newState);
}).build("Leap Binding: Tap schaltet Licht (JS)");

rules.when().item("Leap_Binding_Finger").changed().then((event) => {
  items.iMultimedia_Hue_Lampen_Helligkeit.sendCommand(event.newState);
}).build("Leap Binding: Finger dimmen Licht (JS)");

rules.when().item("Leap_Binding_Hoehe").changed().then((event) => {
  const prozent = 100 - Math.round(Number(event.newState));
  items.iMultimedia_Somfy_Rollladen_Steuerung_Prozent.sendCommand(prozent);
}).build("Leap Binding: Höhe steuert Rollladen (JS)");

rules.when().item("Leap_Binding_Farbe").changed().then((event) => {
  items.iMultimedia_Hue_Lampen_Farbe.sendCommand(event.newState);
}).build("Leap Binding: Farbe an Hue (JS)");
