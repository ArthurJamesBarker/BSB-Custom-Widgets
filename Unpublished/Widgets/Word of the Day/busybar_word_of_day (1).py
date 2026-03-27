import io
import time
from datetime import datetime

import requests

try:
    from PIL import Image, ImageDraw
except Exception:
    Image = None
    ImageDraw = None

# ─────────────────────────────────────────────
#  SETTINGS — edit these before running
# ─────────────────────────────────────────────
DEVICE = "http://10.0.4.20"   # Replace with your BUSY Bar IP if needed
APP_ID = "busybar_word_of_day"
DISPLAY = "front"
REFRESH_SECONDS = 3600         # Re-send every hour (word only changes daily)

# ─────────────────────────────────────────────
#  WORD LIST  (one word shown per day, cycles)
# ─────────────────────────────────────────────
WORDS = [
    "Serenity", "Tenacity", "Luminary", "Ephemeral", "Resilient",
    "Solstice", "Eloquent", "Zenith", "Mutable", "Clarity",
    "Vivacity", "Harmony", "Reverie", "Stoic", "Catalyst",
    "Whimsy", "Verve", "Labyrinth", "Nimble", "Candor",
    "Jubilant", "Cryptic", "Flourish", "Tacit", "Sanguine",
    "Opulent", "Frugal", "Ardent", "Liminal", "Bespoke",
    "Concord", "Diaphanous", "Ebullient", "Fervent", "Gossamer",
    "Halcyon", "Impetus", "Jovial", "Kinetic", "Loquacious",
    "Mellifluous", "Nascent", "Oblique", "Pensive", "Quixotic",
    "Radiant", "Sublime", "Tenuous", "Umbral", "Vexillology",
    "Wistful", "Xenial", "Yonder", "Zeal", "Aplomb",
    "Blithe", "Cacophony", "Dauntless", "Ethereal", "Furtive",
    "Galvanize", "Hiraeth", "Incandescent", "Jocular", "Kismetic",
    "Laconic", "Mirth", "Numinous", "Ominous", "Placid",
    "Quell", "Raucous", "Serene", "Tranquil", "Ubiquitous",
    "Valor", "Wander", "Xenolith", "Yearn", "Zephyr",
    "Ablaze", "Bravado", "Chimera", "Duality", "Envelop",
    "Finesse", "Grasp", "Hustle", "Intrigue", "Juxtapose",
    "Keen", "Levity", "Mystic", "Nuance", "Orbit",
    "Poise", "Quest", "Rapture", "Savor", "Thrive",
]

ICON_FILE = "wotd_icon.png"
ICON_SIZE = 11


def get_word_of_day() -> str:
    day_of_year = datetime.now().timetuple().tm_yday
    return WORDS[day_of_year % len(WORDS)]


def http_post(path, *, params=None, json=None, data=None, timeout=10):
    url = DEVICE.rstrip("/") + path
    return requests.post(url, params=params, json=json, data=data, timeout=timeout)


def make_icon_png_bytes() -> bytes:
    """Small golden book icon."""
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Book cover (golden yellow)
    d.rectangle((1, 0, ICON_SIZE - 2, ICON_SIZE - 1), fill=(255, 197, 0, 255))
    # Spine (darker amber)
    d.rectangle((1, 0, 3, ICON_SIZE - 1), fill=(200, 140, 0, 255))
    # Pages (white lines)
    for py in [3, 5, 7]:
        d.line([(4, py), (ICON_SIZE - 3, py)], fill=(255, 255, 255, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def upload_icon_once() -> bool:
    if not (Image and ImageDraw):
        return False
    try:
        png = make_icon_png_bytes()
        r = http_post(
            "/api/assets/upload",
            params={"app_id": APP_ID, "file": ICON_FILE},
            data=png,
            timeout=10,
        )
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print("Icon upload failed (continuing without icon):", e)
        return False


def build_elements(word: str, icon_available: bool) -> list:
    # Top row: "WORD" label (small, dimmed)
    # Bottom row: the actual word (scrolling if long)
    elements = []

    if icon_available:
        elements.append({
            "id": "icon",
            "type": "image",
            "path": ICON_FILE,
            "x": 0,
            "y": 0,
            "align": "top_left",
            "display": DISPLAY,
        })
        label_x = ICON_SIZE + 2
    else:
        label_x = 0

    # Top label: "WORD OF DAY"
    elements.append({
        "id": "label",
        "type": "text",
        "text": "WORD",
        "x": label_x,
        "y": 0,
        "align": "top_left",
        "font": "small",
        "color": "#FFC500AA",   # amber, slightly transparent
        "display": DISPLAY,
    })

    # Bottom: the word itself — starts after icon to avoid overlap
    word_x = (ICON_SIZE + 2) if icon_available else 0
    word_width = 72 - word_x
    elements.append({
        "id": "word",
        "type": "text",
        "text": word,
        "x": word_x,
        "y": 15,
        "align": "bottom_left",
        "font": "small",
        "color": "#FFFFFFFF",
        "width": word_width,
        "scroll_rate": 400 if len(word) > 8 else 0,
        "display": DISPLAY,
    })

    return elements


def send_draw(elements):
    r = http_post(
        "/api/display/draw",
        json={"app_id": APP_ID, "elements": elements},
        timeout=10,
    )
    r.raise_for_status()


def main():
    print("BUSY Bar — Word of the Day widget starting…")
    icon_available = upload_icon_once()

    last_word = None

    while True:
        try:
            word = get_word_of_day()
            if word != last_word:
                print(f"Word of the day: {word}")
                last_word = word
            elements = build_elements(word, icon_available)
            send_draw(elements)
            print("Sent to display.")
        except requests.RequestException as e:
            print("BUSY Bar request failed (will retry):", e)
        except KeyboardInterrupt:
            print("\nStopped.")
            break

        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    main()
