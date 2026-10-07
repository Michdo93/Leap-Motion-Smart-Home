// Kapitel 25 – Hybrid B: Gesten nach Zeige-Ziel verteilen (JavaScript Scripting)
const GESTE = "mqtt:topic:mosquitto:leap_multimedia:gesture";
const toggle = (item, a, b) => item.sendCommand(item.state === a ? b : a);

rules.when().system().startLevel(100).then(() => {
  if (items.Leap_Multimedia_Freigabe.isUninitialized) items.Leap_Multimedia_Freigabe.postUpdate("ON");
}).build("Hybrid B: Start (JS)");

rules.when().cron("0 0 23 * * ?").then(() => {
  items.Leap_Multimedia_Freigabe.sendCommand("OFF");
}).build("Hybrid B: Freigabe nachts entziehen (JS)");

rules.when().channel(GESTE).triggered().then((event) => {
  const e = event.receivedEvent;
  switch (items.Leap_Multimedia_Ziel.state) {
    case "TV": {
      const kanal = items.iMultimedia_Samsung_TV_Kanal.numericState ?? 1;
      if (e === "SWIPE_RIGHT") items.iMultimedia_Samsung_TV_Kanal.sendCommand(kanal + 1);
      if (e === "SWIPE_LEFT" && kanal > 1) items.iMultimedia_Samsung_TV_Kanal.sendCommand(kanal - 1);
      if (e === "KEY_TAP") toggle(items.iMultimedia_Samsung_TV_Stumm, "ON", "OFF");
      if (e === "GRAB") items.iMultimedia_Samsung_TV_Power.sendCommand("OFF");
      break;
    }
    case "LICHT": {
      const hell = items.iMultimedia_Hue_Lampen_Helligkeit.numericState ?? 0;
      if (e === "SWIPE_UP") items.iMultimedia_Hue_Lampen_Helligkeit.sendCommand(Math.min(100, hell + 20));
      if (e === "SWIPE_DOWN") items.iMultimedia_Hue_Lampen_Helligkeit.sendCommand(Math.max(0, hell - 20));
      if (e === "KEY_TAP") toggle(items.iMultimedia_Hue_Lampen_Schalter, "ON", "OFF");
      break;
    }
    case "ROLLLADEN":
      if (e === "SWIPE_UP") items.iMultimedia_Somfy_Rollladen_Steuerung_Prozent.sendCommand(0);
      if (e === "SWIPE_DOWN") items.iMultimedia_Somfy_Rollladen_Steuerung_Prozent.sendCommand(100);
      break;
    case "RADIO":
      if (e === "KEY_TAP") toggle(items.iMultimedia_Sonos_Lautsprecher_Steuerung, "PLAY", "PAUSE");
      if (e === "SWIPE_RIGHT") items.iMultimedia_Sonos_Lautsprecher_Steuerung.sendCommand("NEXT");
      if (e === "SWIPE_LEFT") items.iMultimedia_Sonos_Lautsprecher_Steuerung.sendCommand("PREVIOUS");
      break;
  }
}).build("Hybrid B: Gesten verteilen (JS)");
