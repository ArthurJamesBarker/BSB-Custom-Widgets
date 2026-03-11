import io
import re
import time
from datetime import datetime, timezone

import requests

try:
    from PIL import Image, ImageDraw
except Exception:
    Image = None
    ImageDraw = None

# BUSY Bar device URL (USB virtual LAN is often http://10.0.4.20)
DEVICE = "http://10.0.4.20"
APP_ID = "busybar_instagram_busy_focus"
DISPLAY = "front"

# Instagram handle to track.
INSTAGRAM_USERNAME = "busy.focus"

# Fetch + animate cadence.
REFRESH_SECONDS = 15
REQUEST_TIMEOUT_SECONDS = 10

ICON_FILE = "instagram_icon.png"
ICON_SIZE = 11  # Keep <= 15 for BUSY Bar
TEXT_X = ICON_SIZE + 2


def http_post(path: str, *, params=None, json=None, data=None, timeout=10):
    url = DEVICE.rstrip("/") + path
    return requests.post(url, params=params, json=json, data=data, timeout=timeout)


def format_count(value: int) -> str:
    return f"{value:,}"


def make_instagram_icon_png_bytes() -> bytes:
    if not (Image and ImageDraw):
        raise RuntimeError("Pillow not available")

    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    p = img.load()

    # Brand-style Instagram gradient background for a more recognizable icon.
    stops = [
        (131, 58, 180),
        (193, 53, 132),
        (253, 29, 29),
        (245, 96, 64),
        (252, 175, 69),
    ]
    for y in range(ICON_SIZE):
        for x in range(ICON_SIZE):
            t = ((x + y) / 2) / (ICON_SIZE - 1)
            seg = min(int(t * (len(stops) - 1)), len(stops) - 2)
            local_t = (t * (len(stops) - 1)) - seg
            c0 = stops[seg]
            c1 = stops[seg + 1]
            r = int(c0[0] + (c1[0] - c0[0]) * local_t)
            g = int(c0[1] + (c1[1] - c0[1]) * local_t)
            b = int(c0[2] + (c1[2] - c0[2]) * local_t)
            p[x, y] = (r, g, b, 255)

    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, ICON_SIZE - 1, ICON_SIZE - 1), radius=3, fill=None, outline=(255, 255, 255, 180), width=1)
    d.rounded_rectangle((2, 2, ICON_SIZE - 3, ICON_SIZE - 3), radius=2, fill=None, outline=(255, 255, 255, 255), width=1)
    d.ellipse((4, 4, 6, 6), outline=(255, 255, 255, 255), width=1)
    d.point((7, 3), fill=(255, 255, 255, 255))

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def upload_icon_once() -> bool:
    if not (Image and ImageDraw):
        return False

    icon_bytes = make_instagram_icon_png_bytes()
    r = http_post(
        "/api/assets/upload",
        params={"app_id": APP_ID, "file": ICON_FILE},
        data=icon_bytes,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    r.raise_for_status()
    return True


def draw_widget(count_value: int, icon_available: bool, stale: bool = False) -> None:
    title = f"@{INSTAGRAM_USERNAME}" + (" *" if stale else "")
    count_text = f"{format_count(count_value)}"

    elements = []
    if icon_available:
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
        text_x = TEXT_X
        text_align = "top_left"
    else:
        text_x = 36
        text_align = "top_mid"

    elements.extend(
        [
            {
                "id": "title",
                "type": "text",
                "text": title,
                "x": text_x,
                "y": 0,
                "align": text_align,
                "font": "small",
                "color": "#FF7A00FF",
                "display": DISPLAY,
                "timeout": 0,
            },
            {
                "id": "count",
                "type": "text",
                "text": count_text,
                "x": text_x,
                "y": 15,
                "align": "bottom_left" if icon_available else "bottom_mid",
                "font": "small",
                "color": "#FFFFFFFF",
                "display": DISPLAY,
                "timeout": 0,
            },
        ]
    )

    payload = {
        "app_id": APP_ID,
        "priority": 6,
        "elements": elements,
    }
    r = http_post("/api/display/draw", json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
    r.raise_for_status()


def extract_count_from_html(html: str) -> int:
    patterns = [
        r'"edge_followed_by"\s*:\s*\{"count"\s*:\s*([0-9]+)',
        r'"followers"\s*:\s*([0-9]+)',
        r'"follower_count"\s*:\s*([0-9]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return int(match.group(1))
    raise ValueError("Could not find follower count in Instagram response.")


def fetch_instagram_count(username: str) -> int:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    }

    endpoint = "https://www.instagram.com/api/v1/users/web_profile_info/"
    r = requests.get(
        endpoint,
        params={"username": username},
        headers={**headers, "X-IG-App-ID": "936619743392459"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if r.ok:
        try:
            data = r.json()
            return int(data["data"]["user"]["edge_followed_by"]["count"])
        except Exception:
            pass

    profile_url = f"https://www.instagram.com/{username}/"
    r = requests.get(profile_url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    r.raise_for_status()
    return extract_count_from_html(r.text)


def run() -> None:
    backoff = REFRESH_SECONDS
    icon_available = False

    try:
        icon_available = upload_icon_once()
    except Exception as exc:
        print(f"[warn] Icon upload skipped: {exc}")

    while True:
        loop_started = time.time()
        try:
            latest_count = fetch_instagram_count(INSTAGRAM_USERNAME)
            draw_widget(latest_count, icon_available=icon_available, stale=False)

            print(
                f"[{datetime.now(timezone.utc).isoformat()}] "
                f"{INSTAGRAM_USERNAME} followers: {latest_count}"
            )
            backoff = REFRESH_SECONDS
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as exc:
            print(f"[warn] Update failed: {exc}")
            try:
                draw_widget(0, icon_available=icon_available, stale=True)
            except Exception as draw_exc:
                print(f"[warn] Draw failed: {draw_exc}")
            backoff = min(backoff * 2, 120)

        elapsed = time.time() - loop_started
        sleep_for = max(1, backoff - elapsed)
        time.sleep(sleep_for)


if __name__ == "__main__":
    run()
