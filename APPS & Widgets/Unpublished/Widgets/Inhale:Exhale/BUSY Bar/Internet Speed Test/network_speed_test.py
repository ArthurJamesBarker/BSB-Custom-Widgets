#!/usr/bin/env python3
"""
Network speed monitor for BUSY Bar

Requirements:
    pip install requests psutil

Usage:
    python network_speed_monitor.py --server 10.0.4.20 --app_id net_speed
"""

import argparse
import time
import requests
import psutil

SCREEN_WIDTH = 72
SCREEN_HEIGHT = 16
MEASURE_INTERVAL = 1.0  # seconds between measurements


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


def send_to_display(server: str, app_id: str, up_mbps: float, down_mbps: float, debug: bool = False):
    """
    Send network speed data to the BUSY Bar display.
    Matches the exact format from the working ping monitor.
    """
    up_str = format_speed(up_mbps)
    down_str = format_speed(down_mbps)
    
    # Format: "UP 12.5Mbps" (no unicode arrows)
    up_text = f"UP {up_str}bps"
    down_text = f"DN {down_str}bps"
    
    payload = {
        "app_id": app_id,
        "elements": [
            # Up speed on first line
            {
                "id": "txt_up",
                "type": "text",
                "text": up_text,
                "x": 2,
                "y": 0,
                "font": "small",
                "color": "#00FF00FF",
                "width": SCREEN_WIDTH,
                "scroll_rate": 0,
                "timeout": 2,
            },
            # Down speed on second line
            {
                "id": "txt_down",
                "type": "text",
                "text": down_text,
                "x": 2,
                "y": 8,
                "font": "small",
                "color": "#00FFFFFF",
                "width": SCREEN_WIDTH,
                "scroll_rate": 0,
                "timeout": 2,
            },
        ],
    }
    
    url = f"http://{server}/api/display/draw"
    
    if debug:
        import json
        print("\n=== Sending payload ===")
        print(json.dumps(payload, indent=2))
    
    try:
        resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"\nDisplay update failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        if debug:
            import json
            print("Payload was:")
            print(json.dumps(payload, indent=2))
        return False


def main():
    parser = argparse.ArgumentParser(description="Network speed monitor for BUSY Bar")
    parser.add_argument("--server", default="10.0.4.20", help="Device IP (default: 10.0.4.20)")
    parser.add_argument("--app_id", default="net_speed", help="App ID (default: net_speed)")
    parser.add_argument("--interval", type=float, default=1.0, help="Update interval in seconds (default: 1.0)")
    args = parser.parse_args()

    print(f"Starting network speed monitor: {args.server} (app_id={args.app_id})")
    print("Press Ctrl+C to stop.")
    
    first_run = True
    
    try:
        while True:
            start = time.time()
            
            up_mbps, down_mbps = get_net_speeds(MEASURE_INTERVAL)
            
            # Display to console
            print(f"Up: {format_speed(up_mbps)}bps | Down: {format_speed(down_mbps)}bps", end='\r')
            
            # Send to device (debug first request only)
            send_to_display(args.server, args.app_id, up_mbps, down_mbps, debug=first_run)
            first_run = False
            
            # Wait for next update
            elapsed = time.time() - start
            to_sleep = args.interval - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)
                
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()