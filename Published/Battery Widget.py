import io
import time
import requests
from PIL import Image, ImageDraw

# ==============================
# Configuration
# ==============================

DEVICE = "http://10.46.21.129"
APP_ID = "busybar_battery_widget"
DISPLAY = "front"

REFRESH_SECONDS = 1

ICON_WIDTH = 34
ICON_HEIGHT = 14

BOLT_W = 4
BOLT_H = 6
CHARGE_CENTER_X = 14

OFF = -20  # off-screen


# ==============================
# Helpers
# ==============================

def http_get(path: str):
    url = DEVICE.rstrip("/") + path
    return requests.get(url, timeout=10)


def http_post(path: str, *, params=None, json=None, data=None):
    url = DEVICE.rstrip("/") + path
    return requests.post(url, params=params, json=json, data=data, timeout=10)


def upload_asset(filename: str, data: bytes):
    r = http_post(
        "/api/assets/upload",
        params={"app_id": APP_ID, "file": filename},
        data=data,
    )
    r.raise_for_status()


def get_battery_status():
    r = http_get("/api/status/power")
    r.raise_for_status()
    data = r.json()
    percent    = data.get("battery_charge", 0)
    current_ma = data.get("battery_current", 0)
    usb_mv     = data.get("usb_voltage", 0)
    state      = data.get("state", "unknown")
    return percent, current_ma, usb_mv, state


# ==============================
# Image generators
# ==============================

def make_battery_icon(percent: int) -> bytes:
    img = Image.new("RGBA", (ICON_WIDTH, ICON_HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    body_width = ICON_WIDTH - 5
    body_height = ICON_HEIGHT - 1

    d.rectangle((0, 0, body_width, body_height), outline=(255, 255, 255, 255))
    d.rectangle(
        (body_width, ICON_HEIGHT // 3, ICON_WIDTH - 2, 2 * ICON_HEIGHT // 3),
        fill=(255, 255, 255, 255),
    )

    fill_width = int((body_width - 3) * percent / 100)
    fill_color = (34, 197, 94, 255) if percent > 20 else (220, 38, 38, 255)
    if fill_width > 0:
        d.rectangle((2, 2, 2 + fill_width, ICON_HEIGHT - 3), fill=fill_color)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_bolt_icon() -> bytes:
    img = Image.new("RGBA", (BOLT_W, BOLT_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    color = (255, 215, 0, 255)
    px = [(2,0),(1,1),(0,2),(2,3),(1,4),(0,5)]
    for x, y in px:
        d.point((x, y), fill=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ==============================
# Draw
# ==============================

def send_draw(percent: int, charging: bool, current_ma: int, usb_mv: int):
    body_width = ICON_WIDTH - 5
    left_edge = 70 - (ICON_WIDTH - 1)
    percent_center_x = left_edge + (body_width // 2)

    watts = (usb_mv / 1000.0) * (current_ma / 1000.0) if charging else 0

    elements = [
        # --- Charging group (on when charging, off when not) ---
        {
            "id": "bolt",
            "type": "image",
            "path": "bolt.png",
            "x": 24,
            "y": 1 if charging else OFF,
            "align": "top_mid",
            "display": DISPLAY,
        },
        {
            "id": "fast",
            "type": "text",
            "text": "Fast",
            "x": 0 + BOLT_W // 2 + 2,
            "y": 2 if charging else OFF,
            "align": "top_left",
            "font": "small",
            "color": "#FFD700FF",
            "display": DISPLAY,
        },
        {
            "id": "watts",
            "type": "text",
            "text": f"{watts:.1f}W",
            "x": 15,
            "y": 15 if charging else OFF,
            "align": "bottom_mid",
            "font": "small",
            "color": "#FFFFFFFF",
            "display": DISPLAY,
        },
        # --- Not charging group (on when discharging, off when charging) ---
        {
            "id": "line1",
            "type": "text",
            "text": "Not",
            "x": 21 - 4,
            "y": OFF if charging else 1,
            "align": "top_mid",
            "font": "small",
            "color": "#FFFFFFFF",
            "display": DISPLAY,
        },
        {
            "id": "line2",
            "type": "text",
            "text": "Charging",
            "x": 22 - 4,
            "y": OFF if charging else 15,
            "align": "bottom_mid",
            "font": "small",
            "color": "#FFFFFFFF",
            "display": DISPLAY,
        },
        # --- Always visible ---
        {
            "id": "battery_icon",
            "type": "image",
            "path": "battery.png",
            "x": 70,
            "y": 8,
            "align": "mid_right",
            "display": DISPLAY,
        },
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

    http_post(
        "/api/display/draw",
        json={"app_id": APP_ID, "elements": elements},
    )


# ==============================
# Main loop
# ==============================

def main():
    while True:
        try:
            percent, current_ma, usb_mv, state = get_battery_status()
            charging = state != "discharging"

            upload_asset("battery.png", make_battery_icon(percent))
            upload_asset("bolt.png", make_bolt_icon())

            send_draw(percent, charging, current_ma, usb_mv)

            watts = (usb_mv / 1000.0) * (current_ma / 1000.0) if charging else 0
            print(f"Battery: {percent}%  {current_ma/1000:.2f}A  {usb_mv/1000:.1f}V  {watts:.1f}W  State: '{state}'  Charging: {charging}")

        except Exception as e:
            print("Error:", e)

        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    main()