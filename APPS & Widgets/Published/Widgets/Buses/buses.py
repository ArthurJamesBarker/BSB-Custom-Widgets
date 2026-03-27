import requests
import math
import time

STOP_ID = "490007515D"  # Greenwich Town Centre / Cutty Sark (stand D)
PRIMARY_KEY = "5efbd8786ce54a4eb5ec98a98d2dbc49"  # TfL Primary Key

DISPLAY_HOST = "http://10.0.4.20"
DISPLAY_DRAW_ENDPOINT = "/api/display/draw"

# How often to poll TfL (seconds). Kept moderate so marquee scroll is not reset every few seconds.
POLL_INTERVAL = 30
REQUEST_TIMEOUT = 15

# Correction so device matches TfL site (seconds). Set to -60 if device runs 1 min high, 0 for no offset.
TIME_OFFSET_SECONDS = 0

def _top_arrivals(arrivals):
    return sorted(arrivals, key=lambda x: x.get("timeToStation", 0))[:2]


def row_display_fields(a):
    route = a.get("lineName") or "??"
    dest = (a.get("destinationName") or "??")
    seconds = max(0, a.get("timeToStation", 0) + TIME_OFFSET_SECONDS)
    mins = "due" if seconds < 30 else f"{math.ceil(seconds/60)}m"
    return route, dest, mins


def display_signature(arrivals):
    """What the user sees per row — only redraw when this changes (stops scroll reset)."""
    if not arrivals:
        return ()
    return tuple(row_display_fields(a) for a in _top_arrivals(arrivals))


def fetch_bus_arrivals(stop_id):
    url = f"https://api.tfl.gov.uk/StopPoint/{stop_id}/Arrivals"
    headers = {"Authorization": f"Bearer {PRIMARY_KEY}"}
    r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    if r.status_code != 200:
        print("TfL API error:", r.status_code, r.text)
        return []
    return r.json()

def format_arrival_elements(arrivals):
    elements = []
    base_y = 2
    line_height = 7
    for idx, a in enumerate(_top_arrivals(arrivals)):
        y = base_y + idx * line_height
        route, dest, mins = row_display_fields(a)

        elements.append({
            "id": f"route_{idx}",
            "timeout": 0,
            "align": "top_mid",
            "x": 6,
            "y": y,
            "type": "text",
            "text": route,
            "font": "small",
            "color": "#FFC500FF",
            "width": 12,
            "scroll_rate": 0,
            "display": "front"
        })

        elements.append({
            "id": f"dest_{idx}",
            "timeout": 0,
            "align": "top_left",
            "x": 14,
            "y": y,
            "type": "text",
            "text": dest,
            "font": "small",
            "color": "#FFC500FF",
            "width": 40,
            "scroll_rate": 400,
            "display": "front"
        })

        elements.append({
            "id": f"mins_{idx}",
            "timeout": 0,
            "align": "top_mid",
            "x": 65,
            "y": y,
            "type": "text",
            "text": mins,
            "font": "small",
            "color": "#FFC500FF",
            "display": "front"
        })

    return elements

def send_to_display(elements):
    draw_json = {"app_id": "bus_widget", "elements": elements}
    url = DISPLAY_HOST + DISPLAY_DRAW_ENDPOINT
    r = requests.post(url, json=draw_json, timeout=REQUEST_TIMEOUT)
    if r.status_code == 200:
        print("Sent to display successfully!")
    else:
        print("Display send error:", r.status_code, r.text)

def main():
    last_sig = None
    while True:
        try:
            arrivals = fetch_bus_arrivals(STOP_ID)
            if not arrivals:
                print("No bus arrival data.")
                last_sig = None
            else:
                sig = display_signature(arrivals)
                if sig != last_sig:
                    last_sig = sig
                    elements = format_arrival_elements(arrivals)
                    for e in elements:
                        print(f"{e['text']:>20}")
                    send_to_display(elements)
        except requests.RequestException as e:
            print("Network error:", e)
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
