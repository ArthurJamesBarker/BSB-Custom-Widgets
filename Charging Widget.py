# @ui text refresh_seconds "30" font=busy_regular_5px

import io
import time
import requests
from PIL import Image, ImageDraw

# ==============================
# Configuration
# ==============================

DEVICE = "http://10.46.21.110"
APP_ID = "busybar_battery_widget"
DISPLAY = "front"

REFRESH_SECONDS = 30

ICON_WIDTH = 34
ICON_HEIGHT = 14

BOLT_W = 7
BOLT_H = 10
CHARGE_CENTER_X = 14


# ==============================
# Helpers
# ==============================

def http_get(path: str):
    url = DEVICE.rstrip("/") + path
    return requests.get(url, timeout=10)


def http_post(path: str, *, params=None, json=None, data=None):
    url = DEVICE.rstrip("/") + path
    return requests.post(url, params=params, json=json, data=data, timeout=10)


def get_battery_status():
    r = http_get("/api/status/power")
    r.raise_for_status()
    data = r.json()

    percent = data.get("battery_charge", 0)
    current_ma = data.get("battery_current", 0)
    state = data.get("state", "unknown")

    return percent, current_ma, state


# ==============================
# Battery Icon
# ==============================

def make_battery_icon(percent: int) -> bytes:
    img = Image.new("RGBA", (ICON_WIDTH, ICON_HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    body_width = ICON_WIDTH - 5
    body_height = ICON_HEIGHT - 1

    d.rectangle((0, 0, body_width, body_height), outline=(255, 255, 255, 255))

    term_x = body_width
    d.rectangle(
        (term_x, ICON_HEIGHT // 3, ICON_WIDTH - 2, 2 * ICON_HEIGHT // 3),
        fill=(255, 255, 255, 255),
    )

    fill_width_max = body_width - 3
    fill_width = int(fill_width_max * percent / 100)

    fill_color = (34, 197, 94, 255) if percent > 20 else (220, 38, 38, 255)

    if fill_width > 0:
        d.rectangle((2, 2, 2 + fill_width, ICON_HEIGHT - 3), fill=fill_color)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ==============================
# Status Icon (bolt or no-charge dash)
# ==============================

def make_status_icon(charging: bool) -> bytes:
    img = Image.new("RGBA", (BOLT_W, BOLT_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Yellow when charging, grey when not — same bolt shape either way.
    # Two parallelograms forming a Z/⚡:
    #   Upper slants top-right (3,0)-(6,0) → mid-left (0,4)-(3,4)
    #   Lower slants mid-right (4,4)-(6,4) → bottom-left (1,9)-(3,9)
    #   At y=4 they span the full width, creating the crossover kink.
    color = (255, 215, 0, 255) if charging else (110, 110, 110, 255)
    d.polygon([(3, 0), (6, 0), (3, 4), (0, 4)], fill=color)
    d.polygon([(4, 4), (6, 4), (3, 9), (1, 9)], fill=color)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def upload_asset(filename: str, data: bytes):
    r = http_post(
        "/api/assets/upload",
        params={"app_id": APP_ID, "file": filename},
        data=data,
    )
    r.raise_for_status()


# ==============================
# Draw
# ==============================

def send_draw(percent: int, bottom_text: str):
    body_width = ICON_WIDTH - 5
    left_edge = 70 - (ICON_WIDTH - 1)
    percent_center_x = left_edge + (body_width // 2)

    elements = [
        # Status icon: yellow bolt (charging) or grey bolt (not charging).
        # top_mid centres it horizontally above the bottom text.
        {
            "id": "status_icon",
            "type": "image",
            "path": "status.png",
            "x": CHARGE_CENTER_X,
            "y": 0,
            "align": "top_mid",
            "display": DISPLAY,
        },
        # Amps when charging, HH:MM of last state-change when not.
        {
            "id": "bottom_text",
            "type": "text",
            "text": bottom_text,
            "x": CHARGE_CENTER_X,
            "y": 15,
            "align": "bottom_mid",
            "font": "small",
            "color": "#FFFFFFFF",
            "display": DISPLAY,
        },
        # Battery icon (right side)
        {
            "id": "battery_icon",
            "type": "image",
            "path": "battery.png",
            "x": 70,
            "y": 8,
            "align": "mid_right",
            "display": DISPLAY,
        },
        # Percent text overlaid on battery body
        {
            "id": "percent_text",
            "type": "text",
            "text": f"{percent}%",
            "x": percent_center_x,
            "y": 8,
            "align": "center",
            "font": "small",
            "color": "#FFFFFFFF",
            "display": DISPLAY,
        },
    ]

    r = http_post(
        "/api/display/draw",
        json={"app_id": APP_ID, "elements": elements},
    )
    r.raise_for_status()


# ==============================
# Main loop
# ==============================

def main():
    last_charging = None
    last_change_time = None

    while True:
        try:
            percent, current_ma, state = get_battery_status()
            charging = state == "charging" and current_ma > 0

            # Record the time whenever charging state flips
            if charging != last_charging:
                last_change_time = time.localtime()
                last_charging = charging

            # Charging: show live amps. Not charging: show when it last changed.
            if charging:
                bottom_text = f"{current_ma / 1000.0:.2f}A"
            else:
                bottom_text = time.strftime("%H:%M", last_change_time) if last_change_time else "--:--"

            battery_icon = make_battery_icon(percent)
            status_icon = make_status_icon(charging)

            upload_asset("battery.png", battery_icon)
            upload_asset("status.png", status_icon)

            send_draw(percent, bottom_text)

            print(
                f"Battery: {percent}%  "
                f"{(current_ma/1000):.2f}A  "
                f"State: {state}  "
                f"Shown: {bottom_text}"
            )

        except Exception as e:
            print("Error:", e)

        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    main()