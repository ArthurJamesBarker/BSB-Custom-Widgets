"""
BUSY Bar widget: displays "hello world" on the front display.
"""
import time
import requests

DEVICE = "http://10.0.4.20"
APP_ID = "busybar_hello_world"
DISPLAY = "front"

REFRESH_SECONDS = 5


def http_post(path: str, *, json=None):
    url = DEVICE.rstrip("/") + path
    return requests.post(url, json=json, timeout=10)


def send_draw():
    elements = [
        {
            "id": "hello",
            "type": "text",
            "text": "hello world",
            "x": 36,
            "y": 8,
            "align": "center",
            "font": "medium",
            "color": "#FFFFFFFF",
            "display": DISPLAY,
        },
    ]
    http_post(
        "/api/display/draw",
        json={"app_id": APP_ID, "elements": elements},
    )


def main():
    while True:
        try:
            send_draw()
            print("hello world")
        except Exception as e:
            print("Error:", e)
        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    main()
