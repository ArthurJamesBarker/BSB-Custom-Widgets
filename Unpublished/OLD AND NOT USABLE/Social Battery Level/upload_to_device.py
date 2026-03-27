#!/usr/bin/env python3
"""Upload Social Battery Level custom app to a BUSY Bar device over HTTP.

Usage:
  python3 upload_to_device.py [IP]

Default IP is 10.0.4.20
"""

import os
import sys
import urllib.parse
import urllib.request

APP_ID = "social_battery_level"  # becomes /ext/apps/<APP_ID>
DEFAULT_IP = "10.0.4.20"


def enc(path: str) -> str:
    # URL-encode for /api/storage/* paths.
    return urllib.parse.quote(path, safe="")


def http_url(base_ip: str, path: str) -> str:
    if base_ip.startswith("http://") or base_ip.startswith("https://"):
        return base_ip.rstrip("/") + path
    return f"http://{base_ip}" + path


def mkdir(base_ip: str, device_path: str) -> None:
    url = http_url(base_ip, f"/api/storage/mkdir?path={enc(device_path)}")
    req = urllib.request.Request(url, method="POST")
    req.add_header("Content-Length", "0")
    with urllib.request.urlopen(req, timeout=20) as r:
        if r.status != 200:
            raise SystemExit(f"mkdir failed: HTTP {r.status} ({device_path})")


def write_file(base_ip: str, local_path: str, device_path: str) -> None:
    url = http_url(base_ip, f"/api/storage/write?path={enc(device_path)}")
    with open(local_path, "rb") as f:
        data = f.read()

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/octet-stream")

    with urllib.request.urlopen(req, timeout=20) as r:
        if r.status != 200:
            raise SystemExit(f"write failed: HTTP {r.status} ({device_path})")


def main() -> None:
    device_ip = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IP
    script_dir = os.path.dirname(os.path.abspath(__file__))

    device_app_path = f"/ext/apps/{APP_ID}"

    print(f"Uploading to {device_ip} -> {device_app_path}")
    mkdir(device_ip, device_app_path)

    # Upload required files + any png assets in this app folder.
    for filename in ["main.lua", "app.json"]:
        local = os.path.join(script_dir, filename)
        if os.path.isfile(local):
            write_file(device_ip, local, f"{device_app_path}/{filename}")
            print(f"  uploaded {filename}")
        else:
            print(f"  missing {filename} (skipping)")

    for filename in sorted(os.listdir(script_dir)):
        if filename.lower().endswith(".png"):
            local = os.path.join(script_dir, filename)
            write_file(device_ip, local, f"{device_app_path}/{filename}")

    print("Done. On the device: APPS -> select 'Battery Level'.")


if __name__ == "__main__":
    main()
