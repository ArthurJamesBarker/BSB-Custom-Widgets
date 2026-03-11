import io
import time
import calendar
from datetime import datetime, date

import requests

try:
    from PIL import Image, ImageDraw
except Exception:
    Image = None
    ImageDraw = None


# ─────────────────────────────────────────────
# SETTINGS — edit these before running
# ─────────────────────────────────────────────

# Your BUSY Bar IP address
# USB Virtual LAN: leave as http://10.0.4.20
# Wi-Fi: change to your device's IP, e.g. http://192.168.1.50
DEVICE = "http://10.0.4.20"

# Which day of the month do you get paid? (e.g. 25 = 25th of every month)
PAYDAY_DOM = 15  # <-- change this to your pay day number

# ─────────────────────────────────────────────
# Internals — no need to edit below this line
# ─────────────────────────────────────────────

APP_ID    = "busybar_payday"
ICON_FILE = "payday_icon.png"
DISPLAY   = "front"
ICON_SIZE = 13


def next_payday_midnight_utc() -> int:
    """Return the Unix UTC timestamp for midnight on the next payday."""
    today = date.today()

    # Try this month
    try:
        candidate = today.replace(day=PAYDAY_DOM)
    except ValueError:
        last_day  = calendar.monthrange(today.year, today.month)[1]
        candidate = today.replace(day=last_day)

    if candidate < today:
        # Move to next month
        year  = today.year + (today.month // 12)
        month = (today.month % 12) + 1
        try:
            candidate = date(year, month, PAYDAY_DOM)
        except ValueError:
            last_day  = calendar.monthrange(year, month)[1]
            candidate = date(year, month, last_day)

    # Convert date to UTC midnight Unix timestamp (as string, per API spec)
    dt_midnight = datetime(candidate.year, candidate.month, candidate.day, 0, 0, 0)
    return int(dt_midnight.timestamp())


def make_icon_png_bytes() -> bytes:
    """Gold coin with a simple pound mark."""
    if not (Image and ImageDraw):
        raise RuntimeError("Pillow not installed")

    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)

    # Gold circle
    d.ellipse((0, 0, ICON_SIZE - 1, ICON_SIZE - 1), fill=(255, 196, 0, 255))
    d.ellipse((0, 0, ICON_SIZE - 1, ICON_SIZE - 1), outline=(180, 130, 0, 255))

    # Simple pound symbol pixels for 13x13
    coin_color = (80, 40, 0, 255)
    for y in range(3, 10):
        d.point((5, y), fill=coin_color)
    d.point((6, 3), fill=coin_color)
    d.point((7, 3), fill=coin_color)
    for x in range(4, 8):
        d.point((x, 6), fill=coin_color)
    for x in range(4, 9):
        d.point((x, 9), fill=coin_color)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def http_post(path, *, params=None, json=None, data=None, timeout=10):
    url = DEVICE.rstrip("/") + path
    return requests.post(url, params=params, json=json, data=data, timeout=timeout)


def upload_icon_once() -> bool:
    if not (Image and ImageDraw):
        print("Pillow not available — no icon. Install: python3 -m pip install --user pillow")
        return False
    try:
        png = make_icon_png_bytes()
        r = http_post(
            "/api/assets/upload",
            params={"app_id": APP_ID, "file": ICON_FILE},
            data=png,
        )
        r.raise_for_status()
        print("Icon uploaded OK.")
        return True
    except requests.RequestException as e:
        print("Icon upload failed (continuing without icon):", e)
        return False


def send_widget(icon_ok: bool, payday_ts: int):
    """Send the layout: coin icon + PAYDAY label + live native countdown."""
    elements = []

    if icon_ok:
        elements.append({
            "id":      "icon",
            "type":    "image",
            "path":    ICON_FILE,
            "x":       0,
            "y":       0,
            "align":   "top_left",
            "display": DISPLAY,
        })
        label_x     = 42
        countdown_x = 42
    else:
        label_x     = 36
        countdown_x = 36

    # "PAYDAY" label at the top
    elements.append({
        "id":      "lbl",
        "type":    "text",
        "text":    "PAYDAY",
        "x":       label_x,
        "y":       0,
        "align":   "top_mid",
        "font":    "small",
        "color":   "#FFC500FF",
        "display": DISPLAY,
    })

    # Native countdown element — the BUSY Bar ticks this live itself
    elements.append({
        "id":         "cd",
        "type":       "countdown",
        "timestamp":  str(payday_ts),
        "direction":  "time_left",
        "show_hours": "when_non_zero",
        "color":      "#FFFFFFFF",
        "x":          countdown_x,
        "y":          15,
        "align":      "bottom_mid",
        "display":    DISPLAY,
    })

    r = http_post(
        "/api/display/draw",
        json={"app_id": APP_ID, "elements": elements},
    )
    r.raise_for_status()


def main():
    payday_ts   = next_payday_midnight_utc()
    payday_date = datetime.fromtimestamp(payday_ts).date()

    print(f"Payday Countdown widget starting...")
    print(f"Pay day = {PAYDAY_DOM}th of each month")
    print(f"Next payday: {payday_date}  (Unix ts: {payday_ts})")
    print(f"Device: {DEVICE}")
    print("The BUSY Bar's built-in countdown ticks live on the device itself.")
    print("Press Ctrl+C to stop.\n")

    icon_ok = upload_icon_once()

    # Send once — device counts down by itself from here
    try:
        send_widget(icon_ok, payday_ts)
        print(f"Done! Live countdown to {payday_date} is now on your BUSY Bar.")
    except requests.RequestException as e:
        print(f"Failed to reach BUSY Bar: {e}")
        return

    # Stay alive and re-send once a day so payday auto-rolls to next month
    print("Sleeping — will re-check daily in case payday rolls over to next month...")
    try:
        while True:
            time.sleep(86400)
            new_ts = next_payday_midnight_utc()
            if new_ts != payday_ts:
                payday_ts   = new_ts
                payday_date = datetime.fromtimestamp(payday_ts).date()
                print(f"New payday: {payday_date}")
            try:
                send_widget(icon_ok, payday_ts)
                print(f"Daily refresh sent — counting to {payday_date}")
            except requests.RequestException as e:
                print(f"Refresh failed (will retry tomorrow): {e}")
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
