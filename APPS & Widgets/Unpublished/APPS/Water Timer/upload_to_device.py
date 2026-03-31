#!/usr/bin/env python3
"""Upload Water Timer (JerryScript) to a BUSY Bar over HTTP (default USB: http://10.0.4.20).

Creates /ext/apps/<app_id>/ and uploads main.js, app.json, assets (Water 2.anim, Water 3/*.png, etc.),
and `icon_front.bin` (run `build_water_timer_icons.py`). Prompt assets: `Drink.png`, `WATER.png`.
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_HOST = "http://10.0.4.20"
DEFAULT_APP_ID = "water_timer"

SKIP_NAMES = frozenset({"upload_to_device.py", ".DS_Store"})


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

def remove_file(host: str, remote_path: str, token: str | None) -> None:
    q = urllib.parse.urlencode({"path": remote_path})
    url = f"{host.rstrip('/')}/api/storage/remove?{q}"
    headers = {}
    if token:
        headers["X-API-Token"] = token
    req = urllib.request.Request(url, method="DELETE", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
    except urllib.error.HTTPError as e:
        # If it doesn't exist, that's fine.
        if e.code == 400:
            return
        raise


def should_skip(path: Path) -> bool:
    if path.name in SKIP_NAMES or path.name.startswith("."):
        return True
    if "__pycache__" in path.parts:
        return True
    return False


def main() -> int:
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description="Upload Water Timer to BUSY Bar /ext/apps/<app_id>")
    p.add_argument("--host", default=os.environ.get("BUSY_BAR_HOST", DEFAULT_HOST))
    p.add_argument("--app-id", default=os.environ.get("BUSY_BAR_WATER_TIMER_APP_ID", DEFAULT_APP_ID))
    p.add_argument("--token", default=os.environ.get("BUSY_BAR_API_KEY"))
    p.add_argument("--remove-legacy", action="store_true", help="Remove old assets (e.g. cup_2.anim) on device")
    args = p.parse_args()

    remote_root = f"/ext/apps/{args.app_id}"
    print(f"Uploading -> {args.host}{remote_root}")

    mkdir(args.host, remote_root, args.token)

    if args.remove_legacy:
        # Old animation from earlier versions; no longer used.
        remove_file(args.host, remote_root + "/cup_2.anim", args.token)

    subdirs = sorted(
        [p for p in here.rglob("*") if p.is_dir() and not should_skip(p)],
        key=lambda x: (len(x.parts), str(x)),
    )
    for d in subdirs:
        rel = d.relative_to(here)
        if not rel.parts:
            continue
        remote_dir = remote_root + "/" + "/".join(rel.parts)
        mkdir(args.host, remote_dir, args.token)

    files = sorted([p for p in here.rglob("*") if p.is_file() and not should_skip(p)])
    for f in files:
        rel = f.relative_to(here)
        remote_path = remote_root + "/" + "/".join(rel.parts)
        upload_file(args.host, remote_path, f.read_bytes(), args.token)
        print(f"  {remote_path}")

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
