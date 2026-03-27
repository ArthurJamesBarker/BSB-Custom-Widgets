import requests
import math
import time
import os
import re

STOP_ID = "490010374A"  # North Greenwich Station
PRIMARY_KEY = "5efbd8786ce54a4eb5ec98a98d2dbc49"  # TfL Primary Key

DISPLAY_HOST = "http://10.0.4.20"
DISPLAY_DRAW_ENDPOINT = "/api/display/draw"
DISPLAY_UPLOAD_ENDPOINT = "/api/assets/upload"
APP_ID = "bus_widget"

# How often to refresh the display (seconds)
UPDATE_INTERVAL = 5
REQUEST_TIMEOUT = 15

# Correction so device matches TfL site (seconds). Set to -60 if device runs 1 min high, 0 for no offset.
TIME_OFFSET_SECONDS = 0

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LETTER_ASSET_FILES = {
    "A": "A.png",
    "B": "B.png",
    "C": "C.png",
    "D": "D.png",
    "E": "E.png",
    "F": "F.png",
    "G": "G.png",
}

def fetch_bus_arrivals(stop_id):
    url = f"https://api.tfl.gov.uk/StopPoint/{stop_id}/Arrivals"
    headers = {"Authorization": f"Bearer {PRIMARY_KEY}"}
    r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    if r.status_code != 200:
        print("TfL API error:", r.status_code, r.text)
        return []
    return r.json()

def upload_letter_assets():
    for filename in LETTER_ASSET_FILES.values():
        local_path = os.path.join(SCRIPT_DIR, filename)
        if not os.path.exists(local_path):
            print(f"Asset missing, skipping upload: {filename}")
            continue
        with open(local_path, "rb") as f:
            data = f.read()
        url = f"{DISPLAY_HOST}{DISPLAY_UPLOAD_ENDPOINT}?app_id={APP_ID}&file={filename}"
        r = requests.post(url, data=data, headers={"Content-Type": "application/octet-stream"}, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            print(f"Uploaded asset: {filename}")
        else:
            print(f"Asset upload error ({filename}):", r.status_code, r.text)

def get_platform_letter(platform_name):
    raw = (platform_name or "").upper()
    direct = raw.strip()
    if direct in LETTER_ASSET_FILES:
        return direct
    m = re.search(r"\b([A-G])\b", raw)
    return m.group(1) if m else ""

def format_arrival_elements(arrivals):
    arrivals_sorted = sorted(arrivals, key=lambda x: x.get("timeToStation", 0))
    elements = []
    base_y = 3
    line_height = 7
    letter_x = 53
    # Letter PNGs are 6x7; use a 1px vertical gap between rows.
    letter_y_positions = [1, 9]
    for idx, a in enumerate(arrivals_sorted[:2]):
        y = base_y + idx * line_height
        letter_y = letter_y_positions[idx] if idx < len(letter_y_positions) else (y + 7)
        mins_y = y + 1 if idx == 1 else y
        route = (a.get("lineName") or "??")[:3]
        dest_full = a.get("destinationName") or "??"
        dest = dest_full
        bus_letter = get_platform_letter(a.get("platformName"))
        seconds = max(0, a.get("timeToStation", 0) + TIME_OFFSET_SECONDS)
        mins = "due" if seconds < 30 else f"{min(99, math.ceil(seconds / 60))}m"

        elements.append({
            "id": f"route_{idx}",
            "timeout": 0,
            "align": "top_left",
            "x": 1,
            "y": y,
            "type": "text",
            "text": route,
            "font": "small",
            "color": "#FFFFFFFF",
            "width": 12,
            "scroll_rate": 0,
            "display": "front"
        })

        elements.append({
            "id": f"dest_{idx}",
            "timeout": 0,
            "align": "top_left",
            "x": 15,
            "y": y,
            "type": "text",
            "text": dest,
            "font": "small",
            "color": "#FFFFFFFF",
            "width": 35,
            "scroll_rate": 400,
            "display": "front"
        })

        if bus_letter in LETTER_ASSET_FILES:
            elements.append({
                "id": f"letters_{idx}",
                "timeout": 0,
                "type": "image",
                "path": LETTER_ASSET_FILES[bus_letter],
                "x": letter_x,
                "y": letter_y,
                "display": "front"
            })
        else:
            elements.append({
                "id": f"letters_{idx}",
                "timeout": 0,
                "align": "top_left",
                "x": letter_x,
                "y": letter_y,
                "type": "text",
                "text": bus_letter,
                "font": "small",
                "color": "#FFFFFFFF",
                "width": 8,
                "scroll_rate": 0,
                "display": "front"
            })

        elements.append({
            "id": f"mins_{idx}",
            "timeout": 0,
            "align": "top_left",
            "x": 61,
            "y": mins_y,
            "type": "text",
            "text": mins,
            "font": "small",
            "color": "#FFFFFFFF",
            "width": 11,
            "scroll_rate": 0,
            "display": "front"
        })

    return elements

def send_to_display(elements):
    draw_json = {"app_id": APP_ID, "elements": elements}
    url = DISPLAY_HOST + DISPLAY_DRAW_ENDPOINT
    r = requests.post(url, json=draw_json, timeout=REQUEST_TIMEOUT)
    if r.status_code == 200:
        print("Sent to display successfully!")
    else:
        print("Display send error:", r.status_code, r.text)

def build_elements_signature(elements):
    # Only track fields that affect on-screen output/placement.
    signature = []
    for e in elements:
        signature.append((
            e.get("id"),
            e.get("type"),
            e.get("text"),
            e.get("path"),
            e.get("x"),
            e.get("y"),
            e.get("align"),
            e.get("width"),
            e.get("font"),
            e.get("color"),
            e.get("scroll_rate"),
            e.get("display"),
        ))
    return tuple(signature)

def main():
    upload_letter_assets()
    last_signature = None
    while True:
        try:
            arrivals = fetch_bus_arrivals(STOP_ID)
            if not arrivals:
                print("No bus arrival data.")
            else:
                elements = format_arrival_elements(arrivals)
                current_signature = build_elements_signature(elements)
                if current_signature != last_signature:
                    for e in elements:
                        label = e.get("text") or e.get("path") or e.get("id", "")
                        print(f"{label:>20}")
                    send_to_display(elements)
                    last_signature = current_signature
                else:
                    print("No visible changes; keeping current scroll position.")
        except requests.RequestException as e:
            print("Network error:", e)
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    main()
