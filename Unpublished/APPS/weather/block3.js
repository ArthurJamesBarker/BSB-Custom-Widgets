let sys = require("./system");
let display = require("display");

function drawFront(yOffset) {
  display.image("block3.png", { x: 0, y: yOffset, background: true });
}

function drawBack() {
  display.text("Details", {
    font: "medium",
    align: "center",
    y: 2,
    display: "back",
    color: sys.COLOR_WHITE,
  });
  display.text("Coming soon", {
    font: "small",
    align: "center",
    y: 20,
    display: "back",
    color: sys.COLOR_GRAY,
  });
}

let block3 = {
  drawFront: drawFront,
  drawBack: drawBack,
  update: function() {},
};

block3;
