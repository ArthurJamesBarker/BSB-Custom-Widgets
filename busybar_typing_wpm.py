# BUSY Bar Typing Speed Tracker — functional app with design meter and layout

import io
import time
import threading

import requests
from pynput import keyboard

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ─────────────────────────────────────────────
# CONFIG — edit this before running
# ─────────────────────────────────────────────
DEVICE = "http://10.46.21.129"
APP_ID = "typing_speed_meter"
DISPLAY = "front"
BAR_FILE = "meter.png"

# How often the BUSY Bar display updates (seconds)
REFRESH_SECONDS = 0.5

# Rolling window for WPM calculation (seconds) — shorter = WPM drops sooner when you stop typing
WPM_WINDOW = 4

# WPM range for the meter (0 WPM = line at bottom, MAX_WPM = line at top)
MAX_WPM = 200
# ─────────────────────────────────────────────

keystroke_times = []
lock = threading.Lock()


def _meter_gradient_rgb(ratio):
    """Meter gradient at ratio 0 (bottom)..1 (top): green -> yellow -> orange -> red. Returns (r, g, b)."""
    r = max(0.0, min(1.0, ratio))

    def lerp(a, b, t):
        return int(a + (b - a) * t)

    if r <= 1/3:
        t = r * 3
        return (lerp(0, 255, t), lerp(200, 220, t), 0)
    if r <= 2/3:
        t = (r - 1/3) * 3
        return (255, lerp(220, 140, t), 0)
    t = (r - 2/3) * 3
    return (255, lerp(140, 0, t), 0)


def http_post(path, *, params=None, json=None, data=None, timeout=10):
    url = DEVICE.rstrip("/") + path
    return requests.post(url, params=params, json=json, data=data, timeout=timeout)


def create_meter_icon(wpm):
    """
    Creates a 15×16 vertical meter (design):
    - Green at bottom, yellow, orange, red at top
    - Blue horizontal line at current WPM level, 1px extended each side
    """
    if not PIL_AVAILABLE:
        return None

    width = 15
    height = 16

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Color stops: bottom (ratio=0) -> top (ratio=1): green -> yellow -> orange -> red
    def gradient_color(ratio):
        r, g, b = _meter_gradient_rgb(ratio)
        return (r, g, b, 255)

    # Draw vertical gradient (bar is x=4 to x=10) — top=green, bottom=red
    for y in range(height):
        ratio = 1 - (y / (height - 1))  # top = 1, bottom = 0
        color = gradient_color(1 - ratio)  # flipped: top green, bottom red
        draw.line((4, y, 10, y), fill=color)

    # Normalize WPM to meter scale (0 … MAX_WPM)
    normalized = min(max(wpm, 0), MAX_WPM) / MAX_WPM
    line_y = int((1 - normalized) * (height - 1))

    # Yellow line through the bar at current WPM, extended 1px each side
    line_color = (255, 220, 0, 255)
    draw.line((3, line_y, 11, line_y), fill=line_color)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def upload_bar(wpm):
    if not PIL_AVAILABLE:
        return False
    png = create_meter_icon(wpm)
    if png is None:
        return False
    try:
        r = http_post(
            "/api/assets/upload",
            params={"app_id": APP_ID, "file": BAR_FILE},
            data=png,
            timeout=10,
        )
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"\nMeter upload failed: {e}")
        return False


def calculate_wpm():
    now = time.time()
    cutoff = now - WPM_WINDOW
    with lock:
        while keystroke_times and keystroke_times[0] < cutoff:
            keystroke_times.pop(0)
        count = len(keystroke_times)
    return int((count / 5) * (60 / WPM_WINDOW))


def build_elements(wpm, bar_ok):
    # WPM number color matches meter gradient (flipped: high WPM = green, low = red)
    normalized = min(max(wpm, 0), MAX_WPM) / MAX_WPM
    r, g, b = _meter_gradient_rgb(1 - normalized)
    wpm_color = f"#{r:02x}{g:02x}{b:02x}ff"

    elements = [
        # Meter on the left (design)
        {
            "id": "meter",
            "type": "image",
            "path": BAR_FILE,
            "x": 0,
            "y": 0,
            "align": "top_left",
            "display": DISPLAY,
        },
        # Title (design)
        {
            "id": "title",
            "type": "text",
            "text": "TYPING SPEED",
            "x": 40,
            "y": 1,
            "align": "top_mid",
            "font": "small",
            "color": "#adadadff",
            "display": DISPLAY,
        },
        # WPM number (design position, functional color)
        {
            "id": "wpm_number",
            "type": "text",
            "text": f"{wpm}",
            "x": 29,
            "y": 12,
            "align": "center",
            "font": "medium",
            "color": wpm_color,
            "display": DISPLAY,
        },
        # "WPM" label (design)
        {
            "id": "wpm_label",
            "type": "text",
            "text": "WPM",
            "x": 48,
            "y": 16,
            "align": "bottom_mid",
            "font": "small",
            "color": "#FFFFFFFF",
            "display": DISPLAY,
        },
    ]

    # Only include meter image if upload succeeded
    if not bar_ok:
        elements = [e for e in elements if e["id"] != "meter"]

    return elements


def send_draw(elements):
    r = http_post(
        "/api/display/draw",
        json={
            "app_id": APP_ID,
            "priority": 7,
            "elements": elements,
        },
        timeout=10,
    )
    r.raise_for_status()


def display_loop():
    while True:
        try:
            wpm = calculate_wpm()
            bar_ok = upload_bar(wpm)
            elements = build_elements(wpm, bar_ok)
            send_draw(elements)
            print(f"\r⌨  Current WPM: {wpm:>4}   (press Ctrl+C to quit)", end="", flush=True)
        except requests.RequestException as e:
            print(f"\nBUSY Bar request failed (will retry): {e}")
        time.sleep(REFRESH_SECONDS)


def on_key_press(key):
    try:
        if hasattr(key, "char") and key.char is not None:
            with lock:
                keystroke_times.append(time.time())
        elif key in (
            keyboard.Key.space,
            keyboard.Key.backspace,
            keyboard.Key.enter,
            keyboard.Key.tab,
        ):
            with lock:
                keystroke_times.append(time.time())
    except Exception:
        pass


def main():
    print("\n" + "=" * 55)
    print("  BUSY Bar Typing Speed Tracker")
    print("=" * 55)
    print(f"  Device     : {DEVICE}")
    print(f"  WPM window : last {WPM_WINDOW} seconds  |  Meter max: {MAX_WPM} WPM")
    print("  Tracking ALL keypresses system-wide.")
    print("  Press Ctrl+C in this window to stop.\n")

    if not PIL_AVAILABLE:
        print("  Note: Pillow not found — meter disabled. Install with:")
        print("        python3 -m pip install --user pillow\n")

    print("Connecting to BUSY Bar…")
    try:
        send_draw(build_elements(0, False))
        print("Connected! Start typing anywhere.\n")
    except requests.RequestException as e:
        print(f"Warning: Could not reach BUSY Bar: {e}")
        print("Check your device IP and try again.")
        return

    t = threading.Thread(target=display_loop, daemon=True)
    t.start()

    listener = keyboard.Listener(on_press=on_key_press)
    listener.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
        print("\n\nStopped. Clearing display…")
        try:
            requests.delete(
                f"{DEVICE.rstrip('/')}/api/display/draw",
                params={"app_id": APP_ID},
                timeout=5,
            )
            print("Display cleared.")
        except Exception:
            pass


if __name__ == "__main__":
    main()
