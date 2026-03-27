let audio = require("audio");
let display = require("display");
let input = require("input");

let volume = audio.getVolume();
let track = "platina-bassok.snd";

function clamp(value, min, max) {
  if(value < min) return min;
  if(value > max) return max;
  return value;
}

function render(message) {
  display.clear();
  display.text("Audio Demo", {
    x: 2,
    y: 0,
    align: "left",
    font: "small",
    color: "#ffffff",
  });
  display.text("vol: " + str(Math.floor(volume * 100)), {
    x: 2,
    y: 5,
    align: "left",
    font: "small",
    color: "#00ff88",
  });
  display.text(message, {
    x: 2,
    y: 10,
    align: "left",
    font: "small",
    color: "#ffaa00",
  });
  display.show();
}

render("OK play / START stop");

input.on("ok", "short", function() {
  let ok = audio.play(track);
  print("audio play:", ok, track);
  render(ok ? "playing bassok" : "play failed");
});

input.on("start", "short", function() {
  audio.stop();
  render("stopped");
});

input.on("up", "short", function() {
  volume = clamp(volume + 0.1, 0, 1);
  audio.setVolume(volume);
  render("volume up");
});

input.on("down", "short", function() {
  volume = clamp(volume - 0.1, 0, 1);
  audio.setVolume(volume);
  render("volume down");
});

__runLoop();
