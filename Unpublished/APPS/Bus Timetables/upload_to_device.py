#!/usr/bin/env python3
"""Upload this app to the BUSY Bar over HTTP (default USB: http://10.0.4.20)."""

from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_HOST = "http://10.0.4.20"
DEFAULT_REMOTE_DIR = "/ext/apps/bus_timetables"

FILES = [
    "app.json",
    "main.js",
    "icon_front.bin",
    "icon_back.bin",
    "BlueSign.png",
    "RedSign.png",
]


def mkdir(host: str, remote_dir: str, token: str | None) -> None:
    q = urllib.parse.urlencode({"path": remote_dir})
    url = f"{host.rstrip('/')}/api/storage/mkdir?{q}"
    headers = {}
    if token:
        headers["X-API-Token"] = token
    req = urllib.request.Request(url, data=b"", method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
    except urllib.error.HTTPError as e:
        if e.code == 400:
            return
        raise


def upload_file(host: str, remote_path: str, data: bytes, token: str | None) -> None:
    q = urllib.parse.urlencode({"path": remote_path})
    url = f"{host.rstrip('/')}/api/storage/write?{q}"
    headers = {"Content-Type": "application/octet-stream"}
    if token:
        headers["X-API-Token"] = token
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        r.read()


def main() -> int:
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description="Upload Bus Timetables to BUSY Bar /ext/apps/bus_timetables")
    p.add_argument("--host", default=os.environ.get("BUSY_BAR_HOST", DEFAULT_HOST))
    p.add_argument("--remote-dir", default=os.environ.get("BUSY_BAR_APP_DIR", DEFAULT_REMOTE_DIR))
    p.add_argument("--token", default=os.environ.get("BUSY_BAR_API_KEY"))
    args = p.parse_args()

    mkdir(args.host, args.remote_dir, args.token)
    for name in FILES:
        local = here / name
        if not local.is_file():
            print(f"Missing: {local}", file=sys.stderr)
            return 1
        remote = args.remote_dir.rstrip("/") + "/" + name
        upload_file(args.host, remote, local.read_bytes(), args.token)
        print(remote)
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
