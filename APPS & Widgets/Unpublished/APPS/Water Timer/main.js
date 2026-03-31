// Water Timer — JerryScript (js_runner). Legacy Lua used busy.*; this uses require() modules.
// Fill animation: gui.close + gui.anim matches old busy.gui (see BSB-AI Lessons/Unofficial/12).

let display = require("display");
let input = require("input");
let timer = require("timer");
let gui = require("gui");

let START_PHOTO_PATH = "Starting Photo.png";
let START_IMAGE_PATH = "STArT.png";
let DRINK_IMAGE_PATH = "Drink.png";
let WATER_IMAGE_PATH = "WATER.png";

let DOWN_FRAMES_DIR = "Water 3";
let DOWN_FRAME_PREFIX = "Water 3_";
// New asset set includes frames 00000..00030 (31 frames total).
let DOWN_FRAME_COUNT = 31;

let ANIM_UP_PATH = "Water 2.anim";
/** Seconds to show cup_2.anim fill before countdown (tune to match .anim length on device). */
let FILL_INTRO_SECONDS = 4;

/** Front strip (72×16): timer / prompts (MM:SS, DRINK WATER, etc.). */
/** BUSY-style bold 10px — same id as weather `bold_10` (not HTTP `big`). */
let TIMER_FONT = "bold_10";
/** MM:SS timer text only — independent of PNG label column below. */
let TIME_TEXT_X = 28;
let TIME_TEXT_Y = -1;

/** PNG column: `STArT.png`; Drink/WATER prompt (alternates) — not tied to `TIME_TEXT_*`. */
let LABEL_IMAGE_X = 26;
let LABEL_IMAGE_Y = 2;

/** Cup offsets (shared by start photo, PNG frames, and .anim). */
/**
 * Layout notes:
 * - `Starting Photo.png` is full-frame (72×16), so it should stay at (0,0).
 * - `Water 3/*.png` are 16×16 sprites and need their own offset.
 * - `.anim` is positioned separately as well.
 */
let START_PHOTO_X = 7;
let START_PHOTO_Y = 0;
/** One knob to keep PNG + anim perfectly aligned. */
let CUP_CONTENT_X = 10;
let CUP_CONTENT_Y = 0;
let CUP_PNG_X = CUP_CONTENT_X;
let CUP_PNG_Y = CUP_CONTENT_Y;
let CUP_ANIM_X = CUP_CONTENT_X;
let CUP_ANIM_Y = CUP_CONTENT_Y;

let DEFAULT_DURATION_SECONDS = 30 * 60;
let STEP_SECONDS = 60;
let MIN_SECONDS = 60;
let MAX_SECONDS = 30 * 60;

let state = "start";
let durationSeconds = DEFAULT_DURATION_SECONDS;

let tickTimer = null;
let flashTimer = null;
/** `waiting_refill`: toggles between `Drink.png` and `WATER.png`. */
let flashOn = false;

let downTotalSeconds = 0;
let downElapsedSeconds = 0;

let COLOR_WHITE = "#ffffff";
let COLOR_RED = "#ff0000";
let COLOR_BG = "#223847"; // subtle but more blue

// Countdown last-3-seconds flash
let downFlashTimer = null;
let downFlashOn = false;

// Hold OK to fast-forward the timer (one-second steps, faster tick rate).
let fastForward = false;
let fastHoldLevel = 0;
let fastHoldTimer = null;
let FAST_HOLD_STEP_SECONDS = 0.25; // how often "speed" increases while holding OK
let FAST_MIN_INTERVAL_SECONDS = 0.08; // cap max speed (lower is faster)
let STOP_FAST_AT_REMAINING_SECONDS = 3; // must stop fast-forward at 3s remaining
let FAST_FORWARD_STEP_SECONDS = 60; // while held: move countdown by minutes (60s steps)
let fastHoldElapsed = 0;
let fastMinuteMode = false; // switches to minute steps once we "round down" to a whole minute
let fastSecondsIntervalCarry = 0.12; // remembered fast seconds interval to reuse under 1 minute

let FAST_STEP_10S = 10;
let SLOWDOWN_START_SECONDS = 5;
let SLOWDOWN_END_SECONDS = 4;

function stopFastHoldTimer() {
  if (fastHoldTimer !== null && fastHoldTimer !== undefined) {
    timer.cancel(fastHoldTimer);
  }
  fastHoldTimer = null;
}

/** Must clear when leaving `down` (e.g. countdown finished while OK held) or new fill/down looks wrong. */
function resetFastForwardState() {
  fastForward = false;
  fastHoldLevel = 0;
  fastHoldElapsed = 0;
  fastMinuteMode = false;
  stopFastHoldTimer();
}

function currentTickIntervalSeconds() {
  if (!fastForward) return 1;
  // Default fast interval (speeds up while held).
  let interval = 0.6 / (1 + fastHoldLevel * 1.6);
  return Math.max(FAST_MIN_INTERVAL_SECONDS, interval);
}

function fastConfigForRemaining(remainingSeconds) {
  // Above 1 minute: start with 1-second steps (ramping faster) until we "round down"
  // to a whole minute, then use minute-jumps down to 1:00.
  if (remainingSeconds > 60) {
    // Stage within each minute:
    // - mm:59 .. mm:31  -> step by seconds (down to mm:30)
    // - mm:30 .. mm:01  -> step by 10s (down to mm:00)
    // - mm:00 .. 01:00  -> step by minutes (60s)
    let secInMinute = remainingSeconds % 60;
    let interval = currentTickIntervalSeconds();
    fastSecondsIntervalCarry = interval;

    if (secInMinute > 30) {
      return { step: 1, interval: interval };
    }
    if (secInMinute > 0) {
      return { step: FAST_STEP_10S, interval: interval };
    }
    // Exactly on the minute boundary.
    return { step: FAST_FORWARD_STEP_SECONDS, interval: interval };
  }

  // Under 1 minute: return to seconds at the speed we last reached in seconds-mode,
  // then step by 10s down to 0:30, then seconds down to 0:05, then slow down near the end.
  // Stop fast-forward at 3 seconds (handled elsewhere).
  let interval = currentTickIntervalSeconds();
  if (remainingSeconds > 30) {
    return { step: FAST_STEP_10S, interval: interval };
  }
  if (remainingSeconds > SLOWDOWN_START_SECONDS) {
    // Seconds from 0:30 down to 0:05.
    return { step: 1, interval: interval };
  }

  // <= 5 seconds: keep stepping by seconds but slow down slightly as we approach 3.
  interval = fastSecondsIntervalCarry;
  let denom = (SLOWDOWN_START_SECONDS - SLOWDOWN_END_SECONDS);
  let t = denom > 0 ? (SLOWDOWN_START_SECONDS - remainingSeconds) / denom : 1;
  if (t < 0) t = 0;
  if (t > 1) t = 1;
  interval = interval + (1.0 - interval) * t;
  interval = Math.max(FAST_MIN_INTERVAL_SECONDS, Math.min(1.0, interval));
  return { step: 1, interval: interval };
}

function clamp(n, lo, hi) {
  if (n < lo) return lo;
  if (n > hi) return hi;
  return n;
}

function downFrameIndexFromElapsed(elapsedSeconds) {
  let idx = Math.floor(elapsedSeconds / 60);
  return clamp(idx, 0, DOWN_FRAME_COUNT - 1);
}

function pad5(n) {
  let v = Math.floor(n);
  if (v < 0) v = 0;
  let s = str(v);
  while (s.length < 5) s = "0" + s;
  return s;
}

function downFramePath(idx) {
  return DOWN_FRAMES_DIR + "/" + DOWN_FRAME_PREFIX + pad5(idx) + ".png";
}

function formatMmss(totalSeconds) {
  let t = Math.max(0, Math.floor(totalSeconds + 0.5));
  let mm = Math.floor(t / 60);
  let ss = t - mm * 60;
  let mmStr = mm < 10 ? "0" + str(mm) : str(mm);
  let ssStr = ss < 10 ? "0" + str(ss) : str(ss);
  return mmStr + ":" + ssStr;
}

function stopTimer(t) {
  if (t !== null && t !== undefined) {
    timer.cancel(t);
  }
}

function cleanupTimers() {
  stopTimer(tickTimer);
  tickTimer = null;
  stopTimer(flashTimer);
  flashTimer = null;
  flashOn = false;
  stopTimer(downFlashTimer);
  downFlashTimer = null;
  downFlashOn = false;
}

function startFrontAnim(loop) {
  // Use display.anim so the anim position is controllable.
  display.anim(ANIM_UP_PATH, { x: CUP_ANIM_X, y: CUP_ANIM_Y, loop: loop });
}

function drawBackground() {
  display.rect(0, 0, 72, 16, { filled: true, color: COLOR_BG });
}

function drawFrontTimeText(text) {
  display.text(text, { font: TIMER_FONT, x: TIME_TEXT_X, y: TIME_TEXT_Y, align: "left" });
}

function renderFillIntro() {
  // Show the fill animation on the *front* strip and overlay the starting time.
  // (Some firmware builds play `.anim` via display.anim, while gui.anim targets the back GUI layer.)
  drawBackground();
  startFrontAnim(false);
  drawFrontTimeText(formatMmss(durationSeconds));
  display.show();
}

function renderStart() {
  // Tint first, then photo on top (do not use background:true or the image can sit behind the fill).
  drawBackground();
  display.image(START_PHOTO_PATH, { x: START_PHOTO_X, y: START_PHOTO_Y });
  display.image(START_IMAGE_PATH, { x: LABEL_IMAGE_X, y: LABEL_IMAGE_Y });
  display.text("Water Timer", { font: "small", x: 2, y: 0, align: "left", display: "back" });
  display.text("OK / Start: begin", { font: "small", x: 2, y: 16, align: "left", display: "back" });
  display.text("Dial +/-: time", { font: "small", x: 2, y: 48, align: "left", display: "back" });
  display.text("Target: " + str(Math.floor(durationSeconds / 60)) + " min", {
    font: "small",
    x: 2,
    y: 64,
    align: "left",
    display: "back",
  });
  display.show();
}

function renderDown() {
  let remaining = downTotalSeconds - downElapsedSeconds;
  drawBackground();
  // New frame set counts down from 00030 -> 00000 as time elapses.
  let frameIdx = (DOWN_FRAME_COUNT - 1) - downFrameIndexFromElapsed(downElapsedSeconds);
  display.image(downFramePath(frameIdx), { x: CUP_PNG_X, y: CUP_PNG_Y });
  let isLast3 = remaining <= 3 && remaining > 0;
  let timeColor = isLast3 ? (downFlashOn ? COLOR_RED : COLOR_WHITE) : COLOR_WHITE;
  display.text(formatMmss(remaining), { font: TIMER_FONT, x: TIME_TEXT_X, y: TIME_TEXT_Y, align: "left", color: timeColor });
  display.show();
}

function renderWaitingRefill() {
  drawBackground();
  // After the countdown completes, cup is "empty" (final down frame).
  display.image(downFramePath(0), { x: CUP_PNG_X, y: CUP_PNG_Y });
  // flashOn false → DRINK first, then WATER (reads as “drink … water”).
  let labelPath = flashOn ? WATER_IMAGE_PATH : DRINK_IMAGE_PATH;
  display.image(labelPath, { x: LABEL_IMAGE_X, y: LABEL_IMAGE_Y });
  display.show();
}

/** Play fill animation once, then start the countdown. */
function enterFillIntroPhase() {
  cleanupTimers();
  resetFastForwardState();
  state = "fill_intro";
  durationSeconds = clamp(durationSeconds, MIN_SECONDS, MAX_SECONDS);
  // While the animation plays, show the countdown starting time (e.g. 30:00).
  downTotalSeconds = durationSeconds;
  downElapsedSeconds = 0;
  gui.close();
  display.clear();
  renderFillIntro();
  // End a hair early so we don't show the animation loop point.
  let fillIntroLeft = Math.max(1, FILL_INTRO_SECONDS - 1);
  tickTimer = timer.every(1, function() {
    fillIntroLeft--;
    if (fillIntroLeft > 0) return;
    stopTimer(tickTimer);
    tickTimer = null;
    if (state !== "fill_intro") return;
    enterDownPhase();
  });
}

function enterDownPhase() {
  cleanupTimers();
  resetFastForwardState();
  state = "down";
  durationSeconds = clamp(durationSeconds, MIN_SECONDS, MAX_SECONDS);
  downTotalSeconds = durationSeconds;
  downElapsedSeconds = 0;
  gui.close();
  display.clear();
  renderDown();

  // Blink red during the last 3 seconds.
  downFlashTimer = timer.every(0.25, function() {
    if (state !== "down") return;
    let remaining = downTotalSeconds - downElapsedSeconds;
    if (remaining <= 3 && remaining > 0) {
      downFlashOn = !downFlashOn;
      renderDown();
    } else if (downFlashOn) {
      downFlashOn = false;
    }
  });

  function downTick() {
    if (state !== "down") return;

    let remainingBefore = downTotalSeconds - downElapsedSeconds;
    if (fastForward && remainingBefore <= STOP_FAST_AT_REMAINING_SECONDS) {
      // Must stop fast-forward at the last 3 seconds.
      fastForward = false;
      fastHoldLevel = 0;
      fastHoldElapsed = 0;
      fastMinuteMode = false;
      stopFastHoldTimer();
      restartDownTicker();
      return;
    }

    let cfg = fastForward ? fastConfigForRemaining(remainingBefore) : { step: 1, interval: 1 };
    let step = cfg.step;
    if (fastForward && step > 1 && (remainingBefore - step) <= STOP_FAST_AT_REMAINING_SECONDS) {
      // Don't let bigger jumps overshoot into the last 3 seconds.
      fastForward = false;
      fastHoldLevel = 0;
      fastHoldElapsed = 0;
      fastMinuteMode = false;
      stopFastHoldTimer();
      restartDownTicker();
      return;
    }
    downElapsedSeconds = downElapsedSeconds + step;
    if (downElapsedSeconds >= downTotalSeconds) {
      downElapsedSeconds = downTotalSeconds;
      stopTimer(tickTimer);
      tickTimer = null;
      resetFastForwardState();
      // Stop last-3s flash ticker so it cannot fire alongside waiting_refill.
      stopTimer(downFlashTimer);
      downFlashTimer = null;
      downFlashOn = false;
      state = "waiting_refill";
      gui.close();

      flashOn = false;
      renderWaitingRefill();
      flashTimer = timer.every(0.5, function() {
        if (state !== "waiting_refill") return;
        flashOn = !flashOn;
        renderWaitingRefill();
      });
      return;
    }

    renderDown();

    // If we're fast-forwarding, the desired interval may have changed as remaining changed.
    if (fastForward) {
      restartDownTicker();
    }
  }

  function restartDownTicker() {
    stopTimer(tickTimer);
    let remaining = downTotalSeconds - downElapsedSeconds;
    let interval = fastForward ? fastConfigForRemaining(remaining).interval : 1;
    tickTimer = timer.every(interval, downTick);
  }

  // Expose for OK-hold updates.
  enterDownPhase.restartTicker = restartDownTicker;
  restartDownTicker();
}

function enterStartPhase() {
  cleanupTimers();
  state = "start";
  gui.close();
  renderStart();
}

function adjustTime(deltaSeconds) {
  if (deltaSeconds === 0) return;
  if (state === "fill_intro") return;

  if (state === "start") {
    durationSeconds = clamp(durationSeconds + deltaSeconds, MIN_SECONDS, MAX_SECONDS);
    renderStart();
    return;
  }

  if (state === "down") {
    downElapsedSeconds = clamp(downElapsedSeconds - deltaSeconds, 0, downTotalSeconds);
    renderDown();
    return;
  }
}

function onPrimaryShort() {
  if (state === "fill_intro") {
    cleanupTimers();
    enterDownPhase();
    return;
  }
  if (state === "start") {
    enterFillIntroPhase();
    return;
  }
  if (state === "waiting_refill") {
    enterFillIntroPhase();
    return;
  }
}

input.on("ok", "short", onPrimaryShort);
input.on("start", "short", onPrimaryShort);

input.on("ok", "long", function() {
  if (state !== "down") return;
  fastForward = true;
  fastHoldLevel = 0;
  fastHoldElapsed = 0;
  fastMinuteMode = false;
  stopFastHoldTimer();
  fastHoldTimer = timer.every(FAST_HOLD_STEP_SECONDS, function() {
    if (!fastForward || state !== "down") return;
    fastHoldLevel++;
    fastHoldElapsed += FAST_HOLD_STEP_SECONDS;
    if (enterDownPhase.restartTicker) enterDownPhase.restartTicker();
  });
  if (enterDownPhase.restartTicker) enterDownPhase.restartTicker();
});

input.on("ok", "release", function() {
  if (!fastForward) return;
  fastForward = false;
  fastHoldLevel = 0;
  fastHoldElapsed = 0;
  fastMinuteMode = false;
  stopFastHoldTimer();
  if (state === "down" && enterDownPhase.restartTicker) enterDownPhase.restartTicker();
});

input.on("right", "short", function() {
  adjustTime(STEP_SECONDS);
});
input.on("left", "short", function() {
  adjustTime(-STEP_SECONDS);
});
input.on("right", "repeat", function() {
  adjustTime(STEP_SECONDS);
});
input.on("left", "repeat", function() {
  adjustTime(-STEP_SECONDS);
});

enterStartPhase();
__runLoop();
