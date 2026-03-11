import requests
import math
import time

STOP_ID = "490000254EB"  # Waterloo Station, Mepham Street
PRIMARY_KEY = "5efbd8786ce54a4eb5ec98a98d2dbc49"  # TfL Primary Key

DISPLAY_HOST = "http://10.0.4.20"
DISPLAY_DRAW_ENDPOINT = "/api/display/draw"

# How often to refresh the display (seconds)
UPDATE_INTERVAL = 5
REQUEST_TIMEOUT = 15

# Correction so device matches TfL site (seconds). Set to -60 if device runs 1 min high, 0 for no offset.
TIME_OFFSET_SECONDS = 0

def fetch_bus_arrivals(stop_id):
    url = f"https://api.tfl.gov.uk/StopPoint/{stop_id}/Arrivals"
    headers = {"Authorization": f"Bearer {PRIMARY_KEY}"}
    r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    if r.status_code != 200:
        print("TfL API error:", r.status_code, r.text)
        return []
    return r.json()

def format_arrival_elements(arrivals):
    arrivals_sorted = sorted(arrivals, key=lambda x: x.get("timeToStation", 0))
    elements = []
    base_y = 2
    line_height = 7
    for idx, a in enumerate(arrivals_sorted[:2]):
        y = base_y + idx * line_height
        route = "47" if idx == 1 else (a.get("lineName") or "??")
        dest_full = a.get("destinationName") or "??"
        dest = "London Bridge" if idx == 1 else (dest_full.split()[0] if dest_full.split() else dest_full)
        seconds = max(0, a.get("timeToStation", 0) + TIME_OFFSET_SECONDS)
        # Match TfL site: "due" only when < 30s, else show minutes (30–59s = "1 min")
        mins = "due" if seconds < 30 else f"{math.ceil(seconds/60)}min"

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
    while True:
        try:
            arrivals = fetch_bus_arrivals(STOP_ID)
            if not arrivals:
                print("No bus arrival data.")
            else:
                elements = format_arrival_elements(arrivals)
                for e in elements:
                    print(f"{e['text']:>20}")
                send_to_display(elements)
        except requests.RequestException as e:
            print("Network error:", e)
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    main()
