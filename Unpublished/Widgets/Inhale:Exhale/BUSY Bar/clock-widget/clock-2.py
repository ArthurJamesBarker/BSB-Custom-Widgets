#!/usr/bin/env python3
"""
Network speed monitor for BUSY Bar

Requirements:
    pip install requests psutil

Assumptions:
    1) Busy Bar HTTP API is reachable at http://10.0.4.20
    2) The arrows image is already on the device as "arrows.png"
       and is 16 pixels wide, full height (16 px), placed at x=0.
    3) Screen resolution is 72x16.
"""

import time
import requests
import psutil

DEVICE_IP = "10.0.4.20"
API_URL = f"http://{DEVICE_IP}/api/display/draw"
APP_ID = "net_speed"
MEASURE_INTERVAL = 1.0  # seconds between measurements
UPDATE_TIMEOUT = 0      # 0 = continuous display

# Screen width in pixels
SCREEN_WIDTH = 72

# If your API requires an API key, set it here.
API_KEY = None  # "YOUR_API_KEY_HERE"
HEADERS = {}
if API_KEY:
    HEADERS["X-API-Key"] = API_KEY


def get_net_speeds(interval: float):
    """
    Measure upload and download speed over the given interval.
    Returns speeds in Mbps (megabits per second).
    """
    net1 = psutil.net_io_counters()
    time.sleep(interval)
    net2 = psutil.net_io_counters()

    bytes_sent = net2.bytes_sent - net1.bytes_sent
    bytes_recv = net2.bytes_recv - net1.bytes_recv

    # Convert to bits per second, then to Mbps
    up_bps = (bytes_sent * 8) / interval
    down_bps = (bytes_recv * 8) / interval

    up_mbps = up_bps / 1_000_000
    down_mbps = down_bps / 1_000_000

    return up_mbps, down_mbps


def format_speed(speed_mbps: float) -> str:
    """
    Format speed for compact display.
    Uses Mbps for values >= 1, Kbps otherwise.
    """
    if speed_mbps >= 1.0:
        return f"{speed_mbps:.1f}M"
    else:
        kbps = speed_mbps * 1000
        if kbps >= 1.0:
            return f"{kbps:.0f}K"
        else:
            return "0K"


def build_payload(up_mbps: float, down_mbps: float):
    """
    Build JSON payload for the Busy Bar display API.
    Layout:
      - arrows image on the left (x=0, 16px wide)
      - text on the right starting at x=18
      - first line: Up speed (↑)
      - second line: Down speed (↓)
    """
    up_str = format_speed(up_mbps)
    down_str = format_speed(down_mbps)

    # Use arrow symbols for compact display
    up_text = f"↑ {up_str}bps"
    down_text = f"↓ {down_str}bps"

    payload = {
        "app_id": APP_ID,
        "elements": [
            # Background arrows image on the left
            {
                "id": "img_arrows",
                "type": "image",
                "path": "arrows.png",
                "x": 0,
                "y": 0,
                "timeout": UPDATE_TIMEOUT
            },
            # Up speed, first line
            {
                "id": "txt_up",
                "type": "text",
                "text": up_text,
                "font": "small",
                "color": "#FFFFFFFF",
                "x": 18,
                "y": 0,
                "width": SCREEN_WIDTH,
                "scroll_rate": 60,
                "timeout": UPDATE_TIMEOUT
            },
            # Down speed, second line
            {
                "id": "txt_down",
                "type": "text",
                "text": down_text,
                "font": "small",
                "color": "#FFFFFFFF",
                "x": 18,
                "y": 8,
                "width": SCREEN_WIDTH,
                "scroll_rate": 60,
                "timeout": UPDATE_TIMEOUT
            },
        ]
    }

    return payload


def send_to_busy_bar(payload: dict, debug: bool = False):
    """
    Send a single POST request to the Busy Bar.
    """
    try:
        if debug:
            import json
            print("\n--- Sending payload ---")
            print(json.dumps(payload, indent=2))
        
        response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=2.0)
        response.raise_for_status()
        
        if debug:
            print(f"✓ Success: {response.status_code}")
            
    except requests.RequestException as e:
        # Print errors but keep running
        print(f"\n✗ Error talking to Busy Bar: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response body: {e.response.text}")
        if debug:
            import json
            print("Payload was:")
            print(json.dumps(payload, indent=2))


def main():
    print("Starting Busy Bar network speed monitor. Press Ctrl+C to stop.")
    print(f"Measuring every {MEASURE_INTERVAL}s, display timeout {UPDATE_TIMEOUT}s")

    # Enable debug for first request to see what's being sent
    first_run = True
    
    try:
        while True:
            up_mbps, down_mbps = get_net_speeds(MEASURE_INTERVAL)
            payload = build_payload(up_mbps, down_mbps)
            send_to_busy_bar(payload, debug=first_run)
            first_run = False
            
            # Optional: print to console for debugging
            print(f"Up: {format_speed(up_mbps)}bps | Down: {format_speed(down_mbps)}bps", end='\r')
            
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()