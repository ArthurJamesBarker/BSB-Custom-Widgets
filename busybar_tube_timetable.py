import io
import os
import time
from collections import defaultdict
from datetime import datetime, timezone

import requests

try:
    from PIL import Image, ImageDraw
except Exception:
    Image = None
    ImageDraw = None


# BUSY Bar device URL (USB virtual LAN is often http://10.0.4.20)
DEVICE = os.getenv("BUSYBAR_DEVICE", "http://10.0.4.20")
APP_ID = "busybar_tube_london_bridge"
DISPLAY = "front"

# TfL stop/line for London Bridge Underground - Northern line
STOPPOINT_ID = "940GZZLULNB"
LINE_ID = "northern"
TFL_API_BASE = os.getenv("TFL_API_BASE", "https://api.tfl.gov.uk")
TFL_APP_ID = os.getenv("TFL_APP_ID", "")
TFL_APP_KEY = os.getenv("TFL_APP_KEY", "")

REFRESH_SECONDS = 30
REQUEST_TIMEOUT_SECONDS = 10

ICON_FILE = "tube_icon.png"
ICON_SIZE = 11  # Keep <= 15 for BUSY Bar
TEXT_X = ICON_SIZE + 3


def http_post(path: str, *, params=None, json=None, data=None, timeout=10):
    url = DEVICE.rstrip("/") + path
    return requests.post(url, params=params, json=json, data=data, timeout=timeout)


def make_tube_icon_png_bytes() -> bytes:
    if not (Image and ImageDraw):
        raise RuntimeError("Pillow not available. Install with: python3 -m pip install --user pillow")

    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Tiny Tube-style roundel: red ring + blue center band.
    d.ellipse((0, 0, ICON_SIZE - 1, ICON_SIZE - 1), fill=(220, 36, 31, 255))
    d.ellipse((2, 2, ICON_SIZE - 3, ICON_SIZE - 3), fill=(0, 0, 0, 0))

    band_h = 3
    y0 = (ICON_SIZE - band_h) // 2
    d.rectangle((0, y0, ICON_SIZE - 1, y0 + band_h - 1), fill=(0, 25, 168, 255))

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def upload_icon() -> None:
    if not (Image and ImageDraw):
        return

    icon_bytes = make_tube_icon_png_bytes()
    r = http_post(
        "/api/assets/upload",
        params={"app_id": APP_ID, "file": ICON_FILE},
        data=icon_bytes,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    r.raise_for_status()


def fetch_arrivals() -> list[dict]:
    params = {}
    if TFL_APP_ID:
        params["app_id"] = TFL_APP_ID
    if TFL_APP_KEY:
        params["app_key"] = TFL_APP_KEY

    url = f"{TFL_API_BASE.rstrip('/')}/StopPoint/{STOPPOINT_ID}/Arrivals"
    r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    r.raise_for_status()
    arrivals = r.json()

    return [a for a in arrivals if (a.get("lineId") or "").lower() == LINE_ID]


def classify_direction(item: dict) -> str:
    raw = (item.get("direction") or "").strip().lower()
    platform = (item.get("platformName") or "").strip().lower()

    if "north" in raw or "north" in platform:
        return "NB"
    if "south" in raw or "south" in platform:
        return "SB"
    if raw:
        return raw[:2].upper()
    return "--"


def format_rows(arrivals: list[dict], stale: bool = False) -> tuple[str, str]:
    if not arrivals:
        return ("Northern: no svc", datetime.now().strftime("%H:%M"))

    grouped: dict[str, list[int]] = defaultdict(list)
    for a in arrivals:
        tts = a.get("timeToStation")
        if isinstance(tts, (int, float)) and tts >= 0:
            grouped[classify_direction(a)].append(int(tts // 60))

    for k in grouped:
        grouped[k].sort()

    first, second = "", ""
    if grouped.get("NB"):
        first = "NB " + ",".join(f"{m}m" for m in grouped["NB"][:2])
    if grouped.get("SB"):
        second = "SB " + ",".join(f"{m}m" for m in grouped["SB"][:2])

    if not first and grouped:
        k = sorted(grouped.keys())[0]
        first = f"{k} " + ",".join(f"{m}m" for m in grouped[k][:2])

    if not second and len(grouped) > 1:
        keys = [k for k in sorted(grouped.keys()) if k != "NB"]
        if keys:
            k = keys[0]
            second = f"{k} " + ",".join(f"{m}m" for m in grouped[k][:2])

    if not second:
        second = datetime.now().strftime("%H:%M")

    if stale:
        first = (first or "No live data") + "*"
        second = (second or "Retrying") + "*"

    return first or "No live data", second or "Retrying"


def mark_stale(rows: tuple[str, str]) -> tuple[str, str]:
    row1, row2 = rows
    suffix = " *"
    if not row1.endswith(suffix):
        row1 += suffix
    if not row2.endswith(suffix):
        row2 += suffix
    return row1, row2


def draw_widget(row1: str, row2: str) -> None:
    elements = []

    if Image and ImageDraw:
        elements.append(
            {
                "id": "icon",
                "type": "image",
                "path": ICON_FILE,
                "x": 0,
                "y": 8,
                "align": "mid_left",
                "display": DISPLAY,
            }
        )

    elements.extend(
        [
            {
                "id": "line1",
                "type": "text",
                "text": row1,
                "x": TEXT_X,
                "y": 0,
                "align": "top_left",
                "font": "small",
                "color": "#FFFFFFFF",
                "width": 72 - TEXT_X,
                "scroll_rate": 360,
                "display": DISPLAY,
                "timeout": 0,
            },
            {
                "id": "line2",
                "type": "text",
                "text": row2,
                "x": TEXT_X,
                "y": 8,
                "align": "top_left",
                "font": "small",
                "color": "#2DD4BFFF",
                "width": 72 - TEXT_X,
                "scroll_rate": 300,
                "display": DISPLAY,
                "timeout": 0,
            },
        ]
    )

    payload = {"app_id": APP_ID, "priority": 6, "elements": elements}
    r = http_post("/api/display/draw", json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
    r.raise_for_status()


def run() -> None:
    last_rows: tuple[str, str] | None = None
    backoff = REFRESH_SECONDS

    try:
        upload_icon()
    except Exception as exc:
        print(f"[warn] Icon upload skipped: {exc}")

    while True:
        try:
            arrivals = fetch_arrivals()
            row1, row2 = format_rows(arrivals, stale=False)
            draw_widget(row1, row2)
            last_rows = (row1, row2)
            backoff = REFRESH_SECONDS
            print(f"[{datetime.now(timezone.utc).isoformat()}] Updated: {row1} | {row2}")
        except Exception as exc:
            print(f"[warn] Update failed: {exc}")
            try:
                if last_rows:
                    draw_widget(*mark_stale(last_rows))
                else:
                    draw_widget("TfL unavailable", "Retrying...")
            except Exception as draw_exc:
                print(f"[warn] Draw fallback failed: {draw_exc}")

            backoff = min(backoff * 2, 300)

        time.sleep(backoff)


if __name__ == "__main__":
    run()
