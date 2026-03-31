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
let timer = require("timer");

let screen = "menu";
let menuIndex = 0;
let menuScroll = 0;
let londonSelectedRow = 0; // 0 = first row, 1 = second row, -1 = off

// Destination marquee scrolling (front strip).
let scrollTick = 0;
let scrollTimer = null;
let SCROLL_INTERVAL_SECONDS = 0.25;
let SCROLL_GAP = "   ";

let CITIES = [
  {
    id: "london",
    menuLabel: "London",
    theme: "london",
    arrivals: [
      { lineName: "286", destinationName: "Sidcup, Queen Mary's Hospital", platformName: "", timeToStation: 180, lineColor: "#e8ba10" },
      { lineName: "286", destinationName: "Sidcup, Queen Mary's Hospital", platformName: "", timeToStation: 720, lineColor: "#e8ba10" },
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

function stopScrollTimer() {
  if (scrollTimer !== null && scrollTimer !== undefined) {
    timer.cancel(scrollTimer);
  }
  scrollTimer = null;
}

function startScrollTimer() {
  stopScrollTimer();
  scrollTick = 0;
  scrollTimer = timer.every(SCROLL_INTERVAL_SECONDS, function () {
    if (screen !== "city") return;
    scrollTick = scrollTick + 1;
    drawCity();
  });
}

function marqueeText(fullText, maxChars) {
  let s = toStr(fullText);
  if (maxChars <= 0) return "";
  if (s.length <= maxChars) return s;

  // Simple wrap-around marquee by character count (no text-width API in on-device JS).
  let loop = s + SCROLL_GAP;
  let i = scrollTick % loop.length;
  let out = "";
  let k;
  for (k = 0; k < maxChars; k++) {
    out = out + loop[(i + k) % loop.length];
  }
  return out;
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
    let minsColor = londonSelectedRow === 0 ? "#ffffff" : "#e8ba10";
    display.text(r.route, { x: 2, y: y, font: "small", color: c, align: "left" });
    display.text(marqueeText(r.dest, 10), { x: 17, y: y, font: "small", color: "#e8ba10", align: "left" });
    display.text(r.mins, { x: 59, y: y, font: "small", color: minsColor, align: "left" });
  }
  if (rows.length >= 2) {
    let r = rows[1];
    let y = 9;
    let c = r.lineColor || whiteGold;
    let minsColor = londonSelectedRow === 1 ? "#ffffff" : "#e8ba10";
    display.text(r.route, { x: 2, y: y, font: "small", color: c, align: "left" });
    display.text(marqueeText(r.dest, 10), { x: 17, y: y, font: "small", color: "#e8ba10", align: "left" });
    display.text(r.mins, { x: 59, y: y, font: "small", color: minsColor, align: "left" });
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
    display.text(marqueeText(r.dest, 11), { x: 21, y: y1, font: "small", color: white, align: "left" });
    display.text(r.mins, { x: 60, y: y1, font: "small", color: white, align: "left" });
  }
  if (rows.length >= 2) {
    let r = rows[1];
    let y2 = 9;
    display.text(r.route, { x: 3, y: y2, font: "small", color: white, align: "left" });
    display.text(marqueeText(r.dest, 11), { x: 21, y: y2, font: "small", color: white, align: "left" });
    display.text(r.mins, { x: 59, y: y2, font: "small", color: white, align: "left" });
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
    display.text(marqueeText(r.dest, 11), { x: 21, y: y1, font: "small", color: white, align: "left" });
    display.text(r.mins, { x: 59, y: y1, font: "small", color: white, align: "left" });
  }
  if (rows.length >= 2) {
    let r = rows[1];
    let y2 = 9;
    display.text(r.route, { x: 1, y: y2, font: "small", color: white, align: "left" });
    display.text(marqueeText(r.dest, 11), { x: 21, y: y2, font: "small", color: white, align: "left" });
    display.text(r.mins, { x: 59, y: y2, font: "small", color: white, align: "left" });
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

function currentCity() {
  return CITIES[menuIndex];
}

function isLondonCitySelected() {
  let city = currentCity();
  return !!city && city.theme === "london";
}

function adjustSelectedLondonMinutes(deltaMinutes) {
  if (screen !== "city") return;
  if (!isLondonCitySelected()) return;
  if (londonSelectedRow < 0) return;

  let city = currentCity();
  if (!city || !city.arrivals || city.arrivals.length <= londonSelectedRow) return;

  let row = city.arrivals[londonSelectedRow];
  let nowSeconds = row.timeToStation !== undefined ? row.timeToStation : 0;
  let nextSeconds = nowSeconds + deltaMinutes * 60;
  if (nextSeconds < 0) nextSeconds = 0;
  if (nextSeconds > 99 * 60) nextSeconds = 99 * 60;
  row.timeToStation = nextSeconds;
  drawCity();
}

input.on("up", "short", function () {
  if (screen === "menu") {
    if (menuIndex <= 0) return;
    menuIndex = menuIndex - 1;
    if (menuIndex === 0) {
      menuScroll = 0;
    }
    drawMenu();
    return;
  }
  if (screen === "city" && isLondonCitySelected()) {
    adjustSelectedLondonMinutes(1);
  }
});

input.on("down", "short", function () {
  if (screen === "menu") {
    if (menuIndex >= CITIES.length - 1) return;
    menuIndex = menuIndex + 1;
    if (menuIndex === 2) {
      menuScroll = 1;
    }
    drawMenu();
    return;
  }
  if (screen === "city" && isLondonCitySelected()) {
    adjustSelectedLondonMinutes(-1);
  }
});

function enterSelectedCity() {
  if (screen !== "menu") return;
  screen = "city";
  drawCity();
  startScrollTimer();
}

function goToSelectionFromCity() {
  if (screen !== "city") return;
  screen = "menu";
  stopScrollTimer();
  drawMenu();
}

input.on("ok", "short", function () {
  if (screen === "menu") {
    enterSelectedCity();
  } else if (screen === "city") {
    if (isLondonCitySelected()) {
      if (londonSelectedRow === 0) {
        londonSelectedRow = 1;
      } else if (londonSelectedRow === 1) {
        londonSelectedRow = -1;
      } else {
        londonSelectedRow = 0;
      }
      drawCity();
    } else {
      goToSelectionFromCity();
    }
  }
});

input.on("start", "short", function () {
  if (screen === "menu") {
    enterSelectedCity();
  } else if (screen === "city") {
    goToSelectionFromCity();
  }
});

// Some firmware/builds map the wheel to left/right events.
input.on("right", "short", function () {
  adjustSelectedLondonMinutes(1);
});
input.on("left", "short", function () {
  adjustSelectedLondonMinutes(-1);
});
input.on("right", "repeat", function () {
  adjustSelectedLondonMinutes(1);
});
input.on("left", "repeat", function () {
  adjustSelectedLondonMinutes(-1);
});

drawMenu();

__runLoop();
