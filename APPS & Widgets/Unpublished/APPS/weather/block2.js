let sys = require("./system");
let display = require("display");
let time = require("time");

let cursorX = 0;
let CURSOR_STEP = 3;
let CURSOR_MAX = 69;

let cachedWindow = null;

function getWindow() {
  let pts = sys.hourlyTemps;
  if (!pts || pts.length < 2 || sys.initUnix === 0) return null;

  let nowSec = time.now();
  let elapsed = (nowSec - sys.initUnix) / 3600;

  let lastPastIdx = -1;
  for (let i = 0; i < pts.length; i++) {
    if (pts[i].timepoint < elapsed) lastPastIdx = i;
  }
  let startIdx = lastPastIdx >= 0 ? lastPastIdx : 0;

  let filtered = [];
  for (let i = startIdx; i < pts.length; i++) {
    let tp = pts[i].timepoint;
    if (tp > elapsed + 30) break;
    filtered.push(pts[i]);
  }

  if (filtered.length < 2) return null;

  let minT = filtered[0].temp;
  let maxT = filtered[0].temp;
  for (let i = 1; i < filtered.length; i++) {
    if (filtered[i].temp < minT) minT = filtered[i].temp;
    if (filtered[i].temp > maxT) maxT = filtered[i].temp;
  }
  let range = maxT - minT;
  if (range < 1) range = 1;

  let values = [];
  for (let i = 0; i < filtered.length; i++) {
    values.push((filtered[i].temp - minT) / range);
  }

  cachedWindow = {
    values: values,
    pts: filtered,
    startTp: filtered[0].timepoint,
    minT: minT,
    maxT: maxT,
  };
  return cachedWindow;
}

function getCursorTime() {
  let w = cachedWindow;
  if (!w || w.pts.length < 2) return "--:--";

  let frac = cursorX / 71;
  let startTp = w.pts[0].timepoint;
  let endTp = w.pts[w.pts.length - 1].timepoint;
  let tp = startTp + frac * (endTp - startTp);
  let cursorUnix = sys.initUnix + tp * 3600;
  let t = sys.unixToLocal(cursorUnix);
  return str(t.day) + " " + sys.months[t.month - 1] + " " + sys.pad2(t.hour) + ":00";
}

function formatTempValue(celsius) {
  let v = Math.floor(celsius + 0.5);
  let sign = v > 0 ? "+" : "";
  return sign + str(v);
}

function getCursorTemp() {
  let w = cachedWindow;
  if (!w || w.pts.length < 2) return "--";

  let frac = cursorX / 71;
  let pos = frac * (w.pts.length - 1);
  let idx = Math.floor(pos);
  let f = pos - idx;
  if (idx >= w.pts.length - 1) return formatTempValue(w.pts[w.pts.length - 1].temp);
  let temp = w.pts[idx].temp * (1 - f) + w.pts[idx + 1].temp * f;
  return formatTempValue(temp);
}

function getCursorCode() {
  let w = cachedWindow;
  if (!w || w.pts.length < 2) return "";

  let frac = cursorX / 71;
  let idx = Math.floor(frac * (w.pts.length - 1));
  if (idx >= w.pts.length) idx = w.pts.length - 1;
  return w.pts[idx].code;
}

function drawFront(yOffset) {
  let data = getWindow();

  let timeStr = getCursorTime();
  display.text(timeStr, {
    font: "small",
    x: 1,
    y: 0 + yOffset,
    align: "left",
    color: sys.COLOR_DATE,
  });

  let tempStr = getCursorTemp() + "C";
  display.text(tempStr, {
    font: "small",
    x: 1,
    y: 0 + yOffset,
    align: "right",
    color: sys.COLOR_WHITE,
  });

  if (data) {
    display.graph(data.values, {
      x: 0,
      y: 6 + yOffset,
      width: 72,
      height: 10,
      tempMin: data.minT,
      tempMax: data.maxT,
      cursorX: cursorX,
      cursorColor: "#ffffff",
      minCurveY: 8,
      z: 0,
    });
  }
}

function drawBack() {
  display.text("24h Forecast", {
    font: "medium",
    align: "center",
    y: 2,
    display: "back",
    color: sys.COLOR_WHITE,
  });

  let w = cachedWindow;
  if (w) {
    display.text(sys.formatTemp(w.minT) + "- " + sys.formatTemp(w.maxT), {
      font: "small",
      align: "center",
      y: 20,
      display: "back",
      color: sys.COLOR_GRAY,
    });
  }
}

let block2 = {
  drawFront: drawFront,
  drawBack: drawBack,
  update: function() {},
  onUp: function() {
    if (cursorX < CURSOR_MAX) cursorX = cursorX + CURSOR_STEP;
    if (cursorX > CURSOR_MAX) cursorX = CURSOR_MAX;
  },
  onDown: function() {
    if (cursorX > 0) cursorX = cursorX - CURSOR_STEP;
    if (cursorX < 0) cursorX = 0;
  },
};

block2;
