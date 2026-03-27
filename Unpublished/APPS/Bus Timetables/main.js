/**
 * Buses v2 — city picker + per-city demo boards (JerryScript).
 * Menu: two lines on the 16px-tall strip at y=1 and y=9 (Bus Selection.json) so both fit;
 * larger y on row 2 clips text. Page1 London+NY; dial down → page2 NY+Toronto.
 * From a city board, **OK** returns to bus selection; **Start** only opens a city from
 * the menu (same as OK on menu). Hardware Back may still exit the app.
 * Menu/city text is drawn in code only. Do not use JSON "composited" PNGs as full-frame
 * backgrounds — those previews usually include the same text, so it would draw twice.
 */

let display = require("display");
let input = require("input");

let screen = "menu";
let menuIndex = 0;
let menuScroll = 0;

let CITIES = [
  {
    id: "london",
    menuLabel: "London",
    theme: "london",
    arrivals: [
      { lineName: "8", destinationName: "Oxford St", platformName: "", timeToStation: 180, lineColor: "#e8ba11" },
      { lineName: "25", destinationName: "Ilford", platformName: "", timeToStation: 480, lineColor: "#e8ba10" },
    ],
  },
  {
    id: "newyork",
    menuLabel: "New York",
    theme: "ny",
    arrivals: [
      { lineName: "M1", destinationName: "E Harlem", platformName: "", timeToStation: 60 },
      { lineName: "M2", destinationName: "Fort George", platformName: "", timeToStation: 300 },
    ],
  },
  {
    id: "toronto",
    menuLabel: "Toronto",
    theme: "toronto",
    arrivals: [
      { lineName: "510", destinationName: "Spadina Stn", platformName: "", timeToStation: 180 },
      { lineName: "504", destinationName: "Distillery Lp", platformName: "", timeToStation: 480 },
    ],
  },
];

let MENU_X = 1;
let MENU_LINE_Y = [1, 9];

function toStr(x) {
  if (x == null) return "";
  return str(x);
}

function sortArrivals(list) {
  if (!list || typeof list.length !== "number") {
    return [];
  }
  let arr = [];
  let k;
  for (k = 0; k < list.length; k++) {
    arr.push(list[k]);
  }
  arr.sort(function (a, b) {
    let ta = a.timeToStation !== undefined ? a.timeToStation : 1e9;
    let tb = b.timeToStation !== undefined ? b.timeToStation : 1e9;
    return ta - tb;
  });
  return arr;
}

function formatMins(seconds) {
  let s = Math.max(0, seconds);
  if (s < 30) return "due";
  return toStr(Math.min(99, Math.ceil(s / 60))) + "m";
}

function buildRows(arrivals) {
  let sorted = sortArrivals(arrivals);
  let rows = [];
  let idx;
  for (idx = 0; idx < sorted.length && idx < 2; idx++) {
    let a = sorted[idx];
    let route = toStr(a.lineName);
    let dest = toStr(a.destinationName) || "??";
    let secs = a.timeToStation !== undefined ? a.timeToStation : 0;
    let mins = formatMins(secs);
    let lineColor = a.lineColor ? a.lineColor : "#ffffff";
    rows.push({ route: route, dest: dest, mins: mins, lineColor: lineColor });
  }
  return rows;
}

function syncMenuScrollToSelection() {
  if (menuIndex === 0) {
    menuScroll = 0;
  }
  if (menuIndex === 2) {
    menuScroll = 1;
  }
}

function drawMenu() {
  let i;
  syncMenuScrollToSelection();
  display.clear();
  for (i = 0; i < 2; i++) {
    let cityIdx = menuScroll + i;
    let city = CITIES[cityIdx];
    if (!city) continue;
    let sel = menuIndex === cityIdx;
    let color = sel ? "#e8ba10" : "#ffffff";
    display.text(city.menuLabel, {
      x: MENU_X,
      y: MENU_LINE_Y[i],
      font: "small",
      color: color,
      align: "left",
    });
  }
  display.show();
}

function drawLondon(arrivals) {
  let rows = buildRows(arrivals);
  let whiteGold = "#e8ba10";
  display.clear();
  if (rows.length >= 1) {
    let r = rows[0];
    let y = 2;
    let c = r.lineColor || whiteGold;
    display.text(r.route, { x: 2, y: y, font: "small", color: c, align: "left" });
    display.text(r.dest, { x: 13, y: y, font: "small", color: "#e8ba10", align: "left" });
    display.text(r.mins, { x: 62, y: y, font: "small", color: "#e8ba10", align: "left" });
  }
  if (rows.length >= 2) {
    let r = rows[1];
    let y = 9;
    let c = r.lineColor || whiteGold;
    display.text(r.route, { x: 2, y: y, font: "small", color: c, align: "left" });
    display.text(r.dest, { x: 13, y: y, font: "small", color: "#e8ba10", align: "left" });
    display.text(r.mins, { x: 62, y: y, font: "small", color: "#e8ba10", align: "left" });
  }
  display.show();
}

function drawNY(arrivals) {
  let rows = buildRows(arrivals);
  let white = "#ffffff";
  display.clear();
  try {
    display.image("BlueSign.png", { x: 0, y: 0 });
    display.image("BlueSign.png", { x: 0, y: 9 });
  } catch (e) {
    print("BlueSign missing", e);
  }
  if (rows.length >= 1) {
    let r = rows[0];
    let y1 = 0;
    display.text(r.route, { x: 3, y: y1, font: "small", color: white, align: "left" });
    display.text(r.dest, { x: 17, y: y1, font: "small", color: white, align: "left" });
    display.text(r.mins, { x: 63, y: y1, font: "small", color: white, align: "left" });
  }
  if (rows.length >= 2) {
    let r = rows[1];
    let y2 = 9;
    display.text(r.route, { x: 3, y: y2, font: "small", color: white, align: "left" });
    display.text(r.dest, { x: 17, y: y2, font: "small", color: white, align: "left" });
    display.text(r.mins, { x: 62, y: y2, font: "small", color: white, align: "left" });
  }
  display.show();
}

function drawToronto(arrivals) {
  let rows = buildRows(arrivals);
  let white = "#ffffff";
  display.clear();
  try {
    display.image("RedSign.png", { x: 0, y: 0 });
    display.image("RedSign.png", { x: 0, y: 9 });
  } catch (e) {
    print("RedSign missing", e);
  }
  if (rows.length >= 1) {
    let r = rows[0];
    let y1 = 0;
    display.text(r.route, { x: 2, y: y1, font: "small", color: white, align: "left" });
    display.text(r.dest, { x: 17, y: y1, font: "small", color: white, align: "left" });
    display.text(r.mins, { x: 62, y: y1, font: "small", color: white, align: "left" });
  }
  if (rows.length >= 2) {
    let r = rows[1];
    let y2 = 9;
    display.text(r.route, { x: 1, y: y2, font: "small", color: white, align: "left" });
    display.text(r.dest, { x: 17, y: y2, font: "small", color: white, align: "left" });
    display.text(r.mins, { x: 62, y: y2, font: "small", color: white, align: "left" });
  }
  display.show();
}

function drawCity() {
  let city = CITIES[menuIndex];
  if (!city) return;
  if (city.theme === "london") {
    drawLondon(city.arrivals);
  } else if (city.theme === "ny") {
    drawNY(city.arrivals);
  } else if (city.theme === "toronto") {
    drawToronto(city.arrivals);
  }
}

input.on("up", "short", function () {
  if (screen !== "menu") return;
  if (menuIndex <= 0) return;
  menuIndex = menuIndex - 1;
  if (menuIndex === 0) {
    menuScroll = 0;
  }
  drawMenu();
});

input.on("down", "short", function () {
  if (screen !== "menu") return;
  if (menuIndex >= CITIES.length - 1) return;
  menuIndex = menuIndex + 1;
  if (menuIndex === 2) {
    menuScroll = 1;
  }
  drawMenu();
});

function enterSelectedCity() {
  if (screen !== "menu") return;
  screen = "city";
  drawCity();
}

function goToSelectionFromCity() {
  if (screen !== "city") return;
  screen = "menu";
  drawMenu();
}

input.on("ok", "short", function () {
  if (screen === "menu") {
    enterSelectedCity();
  } else if (screen === "city") {
    goToSelectionFromCity();
  }
});

input.on("start", "short", function () {
  if (screen === "menu") {
    enterSelectedCity();
  }
});

drawMenu();

__runLoop();
