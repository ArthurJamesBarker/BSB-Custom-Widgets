import os
import time
import requests
from datetime import datetime

DEVICE_IP = "10.46.30.23"
APP_ID = "clock_app"

# -----------------------------------------
# PATHS — assets folder next to script
# -----------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(SCRIPT_DIR, "assets")

ASSETS = [
    "0.png","1.png","2.png","3.png","4.png",
    "5.png","6.png","7.png","8.png","9.png",
    "am.png","pm.png","minutes.png",
    "fade_left.png","fade_right.png",
    "tick.png"   # <-- STATIC tick only
]

def upload_assets():
    print("Uploading assets...")
    for name in ASSETS:
        filepath = os.path.join(ASSET_DIR, name)

        if not os.path.exists(filepath):
            print("WARNING: file not found:", filepath)
            continue

        with open(filepath, "rb") as f:
            r = requests.post(
                f"http://{DEVICE_IP}/api/assets/upload?app_id={APP_ID}&file={name}",
                headers={"Content-Type": "application/octet-stream"},
                data=f
            )
        print(name, "=>", r.status_code)
    print("Done.\n")


# -----------------------------------------
# SCREEN & CONSTANTS
# -----------------------------------------

W = 72
H = 16

DIG_W, DIG_H = 8, 14
AM_W, AM_H = 11, 4

MIN_W, MIN_H = 60, 8
TICK_W, TICK_H = 5, 16

# Minutes baseline X (shifted +1 px right earlier)
MIN_BASE_X = (W - MIN_W) + 1

# Additional correction shift
MIN_EXTRA_SHIFT = 1

# Tick centered at old X = 45
TICK_CENTER_X = 45
TICK_X = TICK_CENTER_X - (TICK_W // 2)
TICK_Y = 0


# -----------------------------------------
# MINUTE SCROLL POSITIONING
# -----------------------------------------

def minute_scroll_offset(minute: int) -> int:
    """
    Ensures pixel (5 + minute) of minutes.png sits exactly under tick.
    """
    local_tick = TICK_CENTER_X - MIN_BASE_X
    target = (5 + minute) % MIN_W
    return (target - local_tick) % MIN_W


# -----------------------------------------
# MAIN DRAW FUNCTION
# -----------------------------------------

def draw_clock():
    now = datetime.now()

    hour = now.strftime("%I")
    ampm = now.strftime("%p").lower()
    minute = now.minute

    h1 = f"{hour[0]}.png"
    h2 = f"{hour[1]}.png"

    # Hour digits (shifted +2 px right)
    x_h1 = 2
    x_h2 = x_h1 + DIG_W + 2

    # AM/PM shifted +1 px right
    x_ampm = x_h2 + DIG_W + 3 + 1

    y_digits = 1
    y_ampm = 1

    # minutes scale up by 1 px
    y_min = H - MIN_H - 2

    # scroll minutes
    offset = minute_scroll_offset(minute)
    scroll1 = (MIN_BASE_X - offset) + MIN_EXTRA_SHIFT
    scroll2 = scroll1 + MIN_W

    tick_asset = "tick.png"   # <-- STATIC tick

    elements = [

        # MINUTES
        {
            "id": "mb1",
            "type": "image",
            "path": "minutes.png",
            "x": scroll1,
            "y": y_min,
            "timeout": 2
        },
        {
            "id": "mb2",
            "type": "image",
            "path": "minutes.png",
            "x": scroll2,
            "y": y_min,
            "timeout": 2
        },

        # FADES
        {
            "id": "fade_right",
            "type": "image",
            "path": "fade_right.png",
            "x": 0,
            "y": 0,
            "timeout": 2
        },
        {
            "id": "fade_left",
            "type": "image",
            "path": "fade_left.png",
            "x": 0,
            "y": 0,
            "timeout": 2
        },

        # DIGITS
        {
            "id": "h1",
            "type": "image",
            "path": h1,
            "x": x_h1,
            "y": y_digits,
            "timeout": 2
        },
        {
            "id": "h2",
            "type": "image",
            "path": h2,
            "x": x_h2,
            "y": y_digits,
            "timeout": 2
        },

        # AM/PM
        {
            "id": "ampm",
            "type": "image",
            "path": "am.png" if ampm == "am" else "pm.png",
            "x": x_ampm,
            "y": y_ampm,
            "timeout": 2
        },

        # STATIC TICK
        {
            "id": "tick",
            "type": "image",
            "path": tick_asset,
            "x": TICK_X,
            "y": TICK_Y,
            "timeout": 2
        }
    ]

    payload = {
        "app_id": APP_ID,
        "elements": elements
    }

    requests.post(
        f"http://{DEVICE_IP}/api/display/draw",
        json=payload
    )


# -----------------------------------------
# MAIN LOOP
# -----------------------------------------

def main():
    upload_assets()
    
    # Clear the display before starting
    print("Clearing display...")
    try:
        r = requests.delete(
            f"http://{DEVICE_IP}/api/display/draw?app_id={APP_ID}",
            timeout=5
        )
        print(f"Display cleared: {r.status_code}")
    except Exception as e:
        print(f"Warning: Could not clear display: {e}")
    
    print("Starting clock display...")
    while True:
        draw_clock()
        time.sleep(0.5)


if __name__ == "__main__":
    main()
