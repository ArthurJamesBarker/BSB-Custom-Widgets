let sys = require("./system");
let display = require("display");

let b1DateHH = "";
let b1DateMM = "";
let b1DatePart = "";
let b1WeekdayPart = "";
let b1DateStr = "";
let b1DateColonVisible = true;

let b1ShowDate = true;
let b1DateToggleTick = 0;

function b1UpdateDateTime() {
  let t = sys.cityTime();
  b1DateHH = sys.pad2(t.hour);
  b1DateMM = sys.pad2(t.minute);
  b1DatePart = str(t.day) + " " + sys.months[t.month - 1];
  b1WeekdayPart = sys.weekdays[t.weekday];
  b1DateStr = b1DateHH + ":" + b1DateMM + " " + b1DatePart + " " + b1WeekdayPart;
  b1DateColonVisible = (t.second % 2 === 0);
}

function b1UpdateDateToggle() {
  b1DateToggleTick++;
  if (b1DateToggleTick >= 30) {
    b1DateToggleTick = 0;
    b1ShowDate = !b1ShowDate;
  }
}

// Front display (72x16), block 1. Layers:
// weather icon (background) + temperature text + date/time text
function drawFront(yOffset) {
  let code = sys.currentCode || "clear";
  let animFile = sys.conditionAnims[code] || "w_rain.anim";
  display.anim(animFile, { x: 0, y: yOffset });

  let tempStr = sys.currentTemp !== null ? sys.formatTemp(sys.currentTemp) : "--\u00B0C ";
  display.text(tempStr, {
    font: "bold_7",
    x: 20,
    y: -1 + yOffset,
    align: "left",
    color: sys.COLOR_WHITE,
  });

  let colonStr = b1DateColonVisible ? ":" : " ";
  let dayPart = b1ShowDate ? b1DatePart : b1WeekdayPart;
  let dateTimeStr = b1DateHH + colonStr + b1DateMM + ", " + dayPart;
  display.text(dateTimeStr, {
    font: "small",
    x: 20,
    y: 9 + yOffset,
    align: "left",
    color: sys.COLOR_DATE,
  });
}

// Back display (160x80): city name, temperature, condition, date
function drawBack() {
  let cityName = sys.cities[sys.config.city - 1].name;
  let code = sys.currentCode || "clear";
  let tempStr = sys.currentTemp !== null ? sys.formatTemp(sys.currentTemp) : "--\u00B0C ";

  display.text(cityName + " Weather", {
    font: "medium",
    align: "center",
    y: 2,
    display: "back",
    color: sys.COLOR_WHITE,
  });
  display.text(tempStr, {
    font: "bold_10",
    align: "center",
    y: 18,
    display: "back",
    color: sys.COLOR_WHITE,
  });
  display.text(sys.getCondition(code), {
    font: "medium",
    align: "center",
    y: 34,
    display: "back",
    color: sys.COLOR_CONDITION,
  });
  display.text(b1DateStr, {
    font: "small",
    align: "center",
    y: 50,
    display: "back",
    color: sys.COLOR_GRAY,
  });
}

let block1 = {
  drawFront: drawFront,
  drawBack: drawBack,
  update: function() {
    b1UpdateDateTime();
    b1UpdateDateToggle();
  },
};

block1;
