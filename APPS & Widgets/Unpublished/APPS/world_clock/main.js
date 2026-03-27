let display = require("display");
let timer = require("timer");
let time = require("time");

let colonVisible = true;

function pad2(value) {
  if (value < 10) return "0" + str(value);
  return str(value);
}

function getTimeInTimezone(timestamp, offsetHours) {
  let adjustedTime = timestamp + offsetHours * 3600;
  let totalHours = Math.floor(adjustedTime / 3600);
  let hours = totalHours % 24;
  if (hours < 0) hours += 24;
  let remainingSeconds = adjustedTime - totalHours * 3600;
  let minutes = Math.floor(remainingSeconds / 60) % 60;

  return {
    hours: hours,
    minutes: minutes,
  };
}

function drawClockColumn(title, titleColor, x, hourX, colonX, minuteX, value) {
  display.text(title, {
    x: x,
    y: -1,
    align: "left",
    font: "small",
    color: titleColor,
  });

  display.text(pad2(value.hours), {
    x: hourX,
    y: 6,
    align: "left",
    font: "medium",
    color: "#ffffff",
  });

  if (colonVisible) {
    display.text(":", {
      x: colonX,
      y: 6,
      align: "left",
      font: "medium",
      color: "#ffffff",
    });
  }

  display.text(pad2(value.minutes), {
    x: minuteX,
    y: 6,
    align: "left",
    font: "medium",
    color: "#ffffff",
  });
}

function render() {
  let now = time.now();
  let london = getTimeInTimezone(now, 0);
  let moscow = getTimeInTimezone(now, 3);

  display.clear();
  drawClockColumn("LONDON", "#4487e0", 1, 1, 13, 15, london);
  drawClockColumn("MOSCOW", "#f32424", 38, 38, 50, 52, moscow);
  display.show();
}

render();

timer.every(1, function() {
  colonVisible = !colonVisible;
  render();
});

__runLoop();
