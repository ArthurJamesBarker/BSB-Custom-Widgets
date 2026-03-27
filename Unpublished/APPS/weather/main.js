let display = require("display");
let input = require("input");
let timer = require("timer");
let settings = require("settings");
let sys = require("./system");
let block1 = require("./block1");
let block2 = require("./block2");
let block3 = require("./block3");

let blocks = [block1, block2, block3];
let currentBlock = 0;
let inSettings = false;

function draw() {
  if (inSettings) return;
  display.clear();

  if (sys.loading && sys.currentTemp === null) {
    display.text("Loading...", {
      font: "small",
      align: "center",
      color: sys.COLOR_WHITE,
    });
    display.text("Loading weather...", {
      font: "medium",
      align: "center",
      display: "back",
      color: sys.COLOR_WHITE,
    });
    display.show();
    return;
  }

  if (sys.noInternet && sys.currentTemp === null) {
    display.text("No data", {
      font: "small",
      align: "center",
      color: sys.COLOR_WHITE,
    });
    display.text("Waiting for weather", {
      font: "medium",
      align: "center",
      y: 20,
      display: "back",
      color: sys.COLOR_WHITE,
    });
    display.text("retry every 10s", {
      font: "small",
      align: "center",
      y: 36,
      display: "back",
      color: sys.COLOR_GRAY,
    });
    display.show();
    return;
  }

  blocks[currentBlock].drawFront(0);
  blocks[currentBlock].drawBack();
  display.show();
}

sys.draw = draw;

sys.loadConfig();
block1.update();
sys.fetchWeather();

timer.every(0.1, function() {
  sys.refreshCurrent();
  blocks[currentBlock].update();
  draw();
});

timer.every(1800, function() {
  sys.fetchWeather();
});

input.on("start", "short", function() {
  currentBlock = (currentBlock + 1) % blocks.length;
});

input.on("ok", "short", function() {
  inSettings = true;
  display.clear();
  display.show();
  let names = [];
  for (let i = 0; i < sys.cities.length; i++) names.push(sys.cities[i].name);
  settings.show([
    { label: "City", options: names, value: sys.config.city }
  ], function(values) {
    inSettings = false;
    let newCity = values[0];
    if (newCity !== sys.config.city) {
      sys.config.city = newCity;
      sys.saveConfig();
      sys.currentTemp = null;
      sys.currentCode = null;
      sys.hourlyTemps = [];
      sys.fetchWeather();
    }
  });
});

input.on("up", "short", function() {
  let b = blocks[currentBlock];
  if (b.onUp) b.onUp();
});

input.on("down", "short", function() {
  let b = blocks[currentBlock];
  if (b.onDown) b.onDown();
});

__runLoop();
