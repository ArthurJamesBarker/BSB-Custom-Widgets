from pathlib import Path

import requests

DEVICE = "http://10.0.4.20"
APP_ID = "busybar_svg_display"
DISPLAY = "front"

# Put your SVG here (the one you pasted in chat).
SVG_PATH = Path("/Users/barker/Documents/New project/logo.svg")
PNG_FILE = "logo.png"

# Your SVG viewBox is 20x16; keep that size for clean pixel mapping.
SVG_WIDTH = 20
SVG_HEIGHT = 16


def http_post(path: str, *, params=None, json=None, data=None, timeout=10):
    url = DEVICE.rstrip("/") + path
    return requests.post(url, params=params, json=json, data=data, timeout=timeout)


def render_svg_to_png_bytes(svg_path: Path) -> bytes:
    if not svg_path.exists():
        raise FileNotFoundError(f"SVG file not found: {svg_path}")

    try:
        import cairosvg
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency: cairosvg. Install with: python3 -m pip install --user cairosvg"
        ) from exc

    svg_bytes = svg_path.read_bytes()
    return cairosvg.svg2png(
        bytestring=svg_bytes,
        output_width=SVG_WIDTH,
        output_height=SVG_HEIGHT,
    )


def upload_png(png_bytes: bytes) -> None:
    r = http_post(
        "/api/assets/upload",
        params={"app_id": APP_ID, "file": PNG_FILE},
        data=png_bytes,
        timeout=10,
    )
    r.raise_for_status()


def draw_png() -> None:
    payload = {
        "app_id": APP_ID,
        "priority": 6,
        "elements": [
            {
                "id": "svg_logo",
                "type": "image",
                "path": PNG_FILE,
                "x": 36,
                "y": 8,
                "align": "center",
                "display": DISPLAY,
                "timeout": 0,
            }
        ],
    }
    r = http_post("/api/display/draw", json=payload, timeout=10)
    r.raise_for_status()


def main() -> None:
    png_bytes = render_svg_to_png_bytes(SVG_PATH)
    upload_png(png_bytes)
    draw_png()
    print("Displayed SVG on BUSY Bar.")


if __name__ == "__main__":
    main()
