#!/usr/bin/env python3
"""
Internet speed monitor for BUSY Bar.

This script:
1) Uploads a PNG containing the static "UP/DOWN" labels to the device
2) Draws that image once
3) Updates the RX/TX values on a fixed refresh interval
"""

import argparse
import sys
import time

import psutil
import requests


def upload_image(*, device_ip: str, app_id: str, image_path: str, image_name: str, timeout: float = 5.0) -> None:
    """Upload a PNG to the device using the BUSY Bar assets upload endpoint."""
    upload_url = f"http://{device_ip}/api/assets/upload?app_id={app_id}&file={image_name}"
    headers = {
        "Content-Type": "application/octet-stream",
        "accept": "application/json",
    }

    try:
        with open(image_path, "rb") as img_file:
            r = requests.post(upload_url, headers=headers, data=img_file, timeout=timeout)
        r.raise_for_status()
        print("[OK] Uploaded label image.")
    except requests.RequestException as e:
        print(f"[ERROR] Failed to upload label image: {e}")
        raise


def draw_static_image(*, device_ip: str, app_id: str, image_name: str, timeout: float = 5.0) -> None:
    """Display the uploaded label image on the left side (constant)."""
    display_url = f"http://{device_ip}/api/display/draw"
    payload = {
        "app_id": app_id,
        "elements": [
            {
                "id": "labels_img",
                "timeout": 0,  # 0 = display continuously
                "type": "image",
                "path": image_name,
                "x": 0,
                "y": 0,
                "display": "front",
            }
        ],
    }

    try:
        r = requests.post(display_url, json=payload, timeout=timeout)
        r.raise_for_status()
        print("[OK] Drew static label image.")
    except requests.RequestException as e:
        print(f"[ERROR] Failed to draw static label image: {e}")
        raise


def get_available_interfaces() -> list[str]:
    """Return available network interface names (best-effort)."""
    try:
        return list(psutil.net_io_counters(pernic=True).keys())
    except Exception:
        return []


def get_speed(*, interface: str, interval: float = 0.1) -> tuple[int, int]:
    """Measure RX/TX speed (Mbps) using psutil counters."""
    counters = psutil.net_io_counters(pernic=True)
    if interface not in counters:
        available = get_available_interfaces()
        print(f"[ERROR] Interface '{interface}' not found.")
        if available:
            print(f"[ERROR] Available interfaces: {', '.join(available)}")
        raise SystemExit(1)

    stats1 = counters[interface]
    rx1, tx1 = stats1.bytes_recv, stats1.bytes_sent
    time.sleep(interval)

    stats2 = psutil.net_io_counters(pernic=True)[interface]
    rx2, tx2 = stats2.bytes_recv, stats2.bytes_sent

    # Bits/s -> Mbps
    rx_speed_mbps = (rx2 - rx1) * 8 / 1_000_000 / interval
    tx_speed_mbps = (tx2 - tx1) * 8 / 1_000_000 / interval

    return max(int(rx_speed_mbps), 0), max(int(tx_speed_mbps), 0)


def draw_speeds(*, device_ip: str, app_id: str, rx_mbps: int, tx_mbps: int, display_timeout: int) -> None:
    """Draw RX and TX speed values on the right side."""
    display_url = f"http://{device_ip}/api/display/draw"
    payload = {
        "app_id": app_id,
        "elements": [
            {
                "id": "down_speed",
                "timeout": display_timeout,
                "type": "text",
                "text": f"{rx_mbps} Mb/s",
                "x": 38,
                # Lower text by a few pixels for better vertical alignment
                "y": 3,
                "display": "front",
                # BUSY Bar expects #RRGGBBAA format for text colors
                "color": "#FFFFFFFF",
                "font": "small",
            },
            {
                "id": "up_speed",
                "timeout": display_timeout,
                "type": "text",
                "text": f"{tx_mbps} Mb/s",
                "x": 38,
                "y": 11,
                "display": "front",
                # BUSY Bar expects #RRGGBBAA format for text colors
                "color": "#FFFFFFFF",
                "font": "small",
            },
        ],
    }

    try:
        r = requests.post(display_url, json=payload, timeout=2)
        r.raise_for_status()
    except requests.RequestException as e:
        # Non-fatal: keep monitoring, but print the reason
        detail = ""
        if getattr(e, "response", None) is not None:
            try:
                detail = f" | response={e.response.text}"
            except Exception:
                detail = ""
        print(f"[WARN] Failed to update display: {e}{detail}")


def main() -> None:
    parser = argparse.ArgumentParser(description="BUSY Bar Internet speed monitor")
    parser.add_argument("--interface", default="en0", help="Network interface to monitor (default: en0)")
    parser.add_argument("--device-ip", default="10.0.4.20", help="BUSY Bar device IP (default: 10.0.4.20)")
    parser.add_argument("--app-id", default="net_monitor", help="BUSY Bar app_id (default: net_monitor)")
    parser.add_argument("--labels-png", default="Speed_down-up.png", help="Local PNG file with UP/DOWN labels")
    parser.add_argument("--device-labels-name", default="speed_labels.png", help="Asset name to use on device")
    parser.add_argument("--refresh-interval", type=float, default=0.25, help="Update interval in seconds (default: 0.25)")
    parser.add_argument("--display-timeout", type=int, default=1, help="Text timeout in seconds (default: 1)")
    args = parser.parse_args()

    try:
        print("[INFO] Uploading label image...")
        upload_image(
            device_ip=args.device_ip,
            app_id=args.app_id,
            image_path=args.labels_png,
            image_name=args.device_labels_name,
        )
        draw_static_image(device_ip=args.device_ip, app_id=args.app_id, image_name=args.device_labels_name)

        update_hz = 1.0 / args.refresh_interval if args.refresh_interval > 0 else 0.0
        print(f"[INFO] Monitoring '{args.interface}' (update ~{update_hz:.0f} times/sec)")

        while True:
            rx_mbps, tx_mbps = get_speed(interface=args.interface, interval=0.1)
            draw_speeds(
                device_ip=args.device_ip,
                app_id=args.app_id,
                rx_mbps=rx_mbps,
                tx_mbps=tx_mbps,
                display_timeout=args.display_timeout,
            )
            time.sleep(args.refresh_interval)
    except KeyboardInterrupt:
        print("\n[INFO] Stopped.")
    except Exception as e:
        print(f"[FATAL] {e}")
        raise


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(1)
