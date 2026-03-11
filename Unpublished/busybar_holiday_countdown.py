import io
import time
from datetime import datetime, date

import requests
from PIL import Image, ImageDraw

# =========================
# EDIT THESE
# =========================

DEVICE = "http://10.0.4.20"   # Change to your BUSY Bar IP if needed
HOLIDAY_DATE = "2026-12-25"   # Format: YYYY-MM-DD
HOLIDAY_NAME = "Christmas"

# =========================

APP_ID = "office_holiday_countdown"
DISPLAY = "front"
REFRESH_SECONDS = 60

ICON_FILE = "calendar.png"
ICON_SIZE = 13  # max 15x15


def http_post(path: str, *, params=None, json=None, data=None, timeout=10):
    url = DEVICE.rstrip("/") + path
    return requests.post(url, params=params, json=json, data=data, timeout=timeout)


def make_calendar_icon():
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # white body
    d.rectangle((0, 3, ICON_SIZE - 1, ICON_SIZE - 1), fill=(255, 255, 255, 255))

    # red header
    d.rectangle((0, 0, ICON_SIZE - 1, 4), fill=(255, 60, 60, 255))

    # small black lines
    for y in range(6, ICON_SIZE - 2, 3):
        d.line((3, y, ICON_SIZE - 4, y), fill=(0, 0, 0, 255))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def upload_icon():
    try:
        png = make_calendar_icon()
        r = http_post(
            "/api/assets/upload",
            params={"app_id": APP_ID, "file": ICON_FILE},
            data=png,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        print("Icon upload failed:", e)
        return False


def calculate_days():
    target = datetime.strptime(HOLIDAY_DATE, "%Y-%m-%d").date()
    today = date.today()
    return (target - today).days


def build_elements(icon_available):
    days = calculate_days()

    if days > 1:
        line2 = f"{days} DAYS"
    elif days == 1:
        line2 = "1 DAY"
    elif days == 0:
        line2 = "TODAY!"
    else:
        line2 = "PASSED"

    elements = []

    if icon_available:
        elements.append({
            "id": "icon",
            "type": "image",
            "path": ICON_FILE,
            "x": 0,
            "y": 0,
            "align": "top_left",
            "display": DISPLAY
        })
        name_x = 18
        name_align = "mid_left"
    else:
        name_x = 36
        name_align = "center"

    elements.append({
        "id": "holiday_name",
        "type": "text",
        "text": HOLIDAY_NAME,
        "x": name_x,
        "y": 4,
        "align": name_align,
        "font": "small",
        "color": "#FFFFFFFF",
        "display": DISPLAY
    })

    elements.append({
        "id": "days",
        "type": "text",
        "text": line2,
        "x": name_x,
        "y": 12,
        "align": name_align,
        "font": "small",
        "color": "#00FF88FF",
        "display": DISPLAY
    })

    return elements


def send_draw(elements):
    r = http_post(
        "/api/display/draw",
        json={
            "app_id": APP_ID,
            "priority": 7,
            "elements": elements
        }
    )
    r.raise_for_status()


def main():
    icon_available = upload_icon()

    while True:
        try:
            elements = build_elements(icon_available)
            send_draw(elements)
            print("Updated countdown")
        except Exception as e:
            print("Error:", e)

        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    main()
