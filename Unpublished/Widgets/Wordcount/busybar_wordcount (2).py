"""
BUSY Bar — Daily Word Count Widget
===================================
Single-file, self-contained. No extra files needed.

Requirements (install once):
    python3 -m pip install --user requests pillow pynput

IMPORTANT — macOS permission (do this first!):
    System Settings → Privacy & Security → Input Monitoring
    → Enable the tick next to "Terminal" (or whichever app you run this from)
    Then RESTART Terminal and run the script again.

Usage:
    1. Edit DEVICE and DAILY_GOAL below if needed.
    2. python3  (drag this file into Terminal)  then press Enter.
    3. Ctrl+C to stop.
"""

# ─── CONFIGURE ME ─────────────────────────────────────────────────────────────
DEVICE      = "http://10.0.4.20"   # USB Virtual LAN default. Change for Wi-Fi.
DAILY_GOAL  = 1000                  # your daily word target
REFRESH_SECS = 3                    # seconds between display updates
DISPLAY     = "front"               # "front" or "back"
# ──────────────────────────────────────────────────────────────────────────────

import io
import sys
import time
import threading
from datetime import datetime

# ── Dependency checks ─────────────────────────────────────────────────────────
missing = []
try:
    import requests
except ImportError:
    missing.append("requests")

try:
    from PIL import Image, ImageDraw
except ImportError:
    missing.append("pillow")

try:
    from pynput import keyboard as kb
except ImportError:
    missing.append("pynput")

if missing:
    print("=" * 55)
    print("  Missing packages. Run this command, then try again:")
    print()
    print(f"  python3 -m pip install --user {' '.join(missing)}")
    print("=" * 55)
    sys.exit(1)

APP_ID     = "busybar_wordcount"
FRAME_FILE = "wc_frame.png"
W, H       = 72, 16

# ── Colour helpers ────────────────────────────────────────────────────────────
COL_BG        = (0,  0,  0,  255)
COL_BAR_EMPTY = (25, 25, 25, 255)
COL_DIM       = (65, 65, 65, 255)

def goal_color(pct: float):
    pct = max(0.0, min(1.0, pct))
    if pct < 0.5:
        t = pct / 0.5
        return (220, int(60 + 160 * t), 0, 255)
    else:
        t = (pct - 0.5) / 0.5
        return (int(220 - 120 * t), int(220 + 20 * t), int(40 * t), 255)

# ── 3×5 pixel font ────────────────────────────────────────────────────────────
GLYPHS = {
    '0': [0b111,0b101,0b101,0b101,0b111],
    '1': [0b010,0b110,0b010,0b010,0b111],
    '2': [0b111,0b001,0b111,0b100,0b111],
    '3': [0b111,0b001,0b111,0b001,0b111],
    '4': [0b101,0b101,0b111,0b001,0b001],
    '5': [0b111,0b100,0b111,0b001,0b111],
    '6': [0b111,0b100,0b111,0b101,0b111],
    '7': [0b111,0b001,0b001,0b001,0b001],
    '8': [0b111,0b101,0b111,0b101,0b111],
    '9': [0b111,0b101,0b111,0b001,0b111],
    '%': [0b101,0b001,0b010,0b100,0b101],
    'W': [0b101,0b101,0b101,0b111,0b010],
    ' ': [0b000,0b000,0b000,0b000,0b000],
}

def draw_char(d, x, y, ch, color):
    for ry, bits in enumerate(GLYPHS.get(ch, GLYPHS[' '])):
        for cx in range(3):
            if bits & (0b100 >> cx):
                d.point((x + cx, y + ry), fill=color)

def draw_text(d, x, y, text, color):
    cx = x
    for ch in text:
        draw_char(d, cx, y, ch, color)
        cx += 4

# ── Word tracking ─────────────────────────────────────────────────────────────
_lock         = threading.Lock()
_words        = 0
_last_key_t   = 0.0
_today        = datetime.now().date()
_last_was_sep = True
_listener_ok  = False

def _on_press(key):
    global _words, _last_key_t, _today, _last_was_sep
    today = datetime.now().date()
    with _lock:
        if today != _today:          # midnight — reset
            _today = today
            _words = 0
            _last_was_sep = True
    try:
        ch = key.char
        if ch is not None:
            with _lock:
                _last_was_sep = False
                _last_key_t   = time.time()
    except AttributeError:
        if key in (kb.Key.space, kb.Key.enter, kb.Key.tab):
            with _lock:
                if not _last_was_sep:
                    _words       += 1
                    _last_key_t   = time.time()
                _last_was_sep = True

def start_listener():
    global _listener_ok
    print("[SETUP] Starting keyboard listener...")
    try:
        listener = kb.Listener(on_press=_on_press)
        listener.daemon = True
        listener.start()
        time.sleep(0.5)   # give it a moment to fail if permissions are wrong
        if listener.is_alive():
            _listener_ok = True
            print("[OK]    Keyboard listener running — type something to test!")
        else:
            print("[WARN]  Listener started but stopped immediately.")
            print("        → macOS: go to System Settings → Privacy & Security")
            print("          → Input Monitoring → enable Terminal, then restart Terminal.")
    except Exception as e:
        print(f"[ERR]   Listener failed: {e}")
        print("        → macOS: System Settings → Privacy & Security → Input Monitoring")
        print("          → enable Terminal, restart Terminal, and try again.")

def get_state():
    with _lock:
        return _words, _last_key_t

# ── Frame renderer ────────────────────────────────────────────────────────────

def render(words: int, goal: int, typing: bool, tick: int) -> bytes:
    img = Image.new("RGBA", (W, H), COL_BG)
    d   = ImageDraw.Draw(img)
    pct       = min(1.0, words / goal) if goal > 0 else 0.0
    bar_color = goal_color(pct)
    pct_int   = round(pct * 100)

    # Vertical progress bar — right 4px
    bx = W - 4
    d.rectangle((bx, 0, bx + 3, H - 1), fill=COL_BAR_EMPTY)
    bh = round(pct * H)
    if bh > 0:
        d.rectangle((bx, H - bh, bx + 3, H - 1), fill=bar_color)

    # Word count — 2× scaled pixel font
    num_str  = str(words)
    mini_w   = len(num_str) * 4 - 1
    mi       = Image.new("RGBA", (mini_w + 1, 5), (0, 0, 0, 0))
    md       = ImageDraw.Draw(mi)
    draw_text(md, 0, 0, num_str, bar_color)
    scaled_w = (mini_w + 1) * 2
    scaled_h = 10
    big      = mi.resize((scaled_w, scaled_h), Image.NEAREST)
    px, py   = 1, (H - scaled_h) // 2
    img.paste(big, (px, py), big)

    # "W" label after number
    lx = px + scaled_w + 2
    if lx + 3 < bx - 8:
        draw_char(d, lx, py + scaled_h - 5, 'W', COL_DIM)

    # Percentage top-right
    pct_str = f"{pct_int}%"
    rx = bx - len(pct_str) * 4 - 2
    if rx > lx + 6:
        draw_text(d, rx, 1, pct_str, COL_DIM)

    # Progress dots — bottom strip
    num_dots = (bx - 1) // 3
    filled   = round(pct * num_dots)
    for i in range(num_dots):
        col = bar_color if i < filled else COL_BAR_EMPTY
        d.rectangle((i * 3, H - 2, i * 3 + 1, H - 1), fill=col)

    # Typing pulse — top-left 2×2 dot
    if typing:
        dot = (80, 220, 80, 255) if tick % 3 < 2 else (20, 60, 20, 255)
    else:
        dot = COL_BAR_EMPTY
    d.rectangle((0, 0, 1, 1), fill=dot)

    # Goal flash border
    if pct >= 1.0 and tick % 6 < 3:
        flash = (200, 255, 60, 220)
        d.rectangle((0, 0, bx - 2, 0),          fill=flash)
        d.rectangle((0, H - 3, bx - 2, H - 3), fill=flash)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ── Device comms ──────────────────────────────────────────────────────────────

def push_to_device(png: bytes):
    # Upload the rendered frame as an image asset
    r = requests.post(
        f"{DEVICE}/api/assets/upload",
        params={"app_id": APP_ID, "file": FRAME_FILE},
        data=png,
        timeout=8,
    )
    r.raise_for_status()
    # Tell the display to show it
    r = requests.post(
        f"{DEVICE}/api/display/draw",
        json={
            "app_id": APP_ID,
            "elements": [{
                "id":      "frame",
                "type":    "image",
                "path":    FRAME_FILE,
                "x": 0, "y": 0,
                "align":   "top_left",
                "display": DISPLAY,
            }],
        },
        timeout=8,
    )
    r.raise_for_status()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║   BUSY Bar — Daily Word Count                   ║")
    print("╠══════════════════════════════════════════════════╣")
    print(f"║  Device : {DEVICE:<39}║")
    print(f"║  Goal   : {str(DAILY_GOAL)+' words':<39}║")
    print(f"║  Refresh: every {str(REFRESH_SECS)+'s':<33}║")
    print("╠══════════════════════════════════════════════════╣")
    print("║  macOS TIP: System Settings → Privacy & Security║")
    print("║  → Input Monitoring → enable Terminal           ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    start_listener()
    print()

    tick = 0
    while True:
        try:
            words, last_key = get_state()
            typing = (time.time() - last_key) < 4.0

            png = render(words, DAILY_GOAL, typing, tick)
            push_to_device(png)

            pct     = min(100, round(words / DAILY_GOAL * 100))
            bar_len = round(pct / 5)
            bar     = "█" * bar_len + "░" * (20 - bar_len)
            icon    = "✍ " if typing else "  "
            print(f"  {datetime.now().strftime('%H:%M:%S')}  {icon}{words:>5,} words  [{bar}] {pct:>3}%"
                  + ("  🎉 GOAL!" if pct >= 100 else ""))

            tick += 1

        except requests.RequestException as e:
            print(f"  [WARN] Device unreachable — retrying in {REFRESH_SECS}s  ({e})")
        except KeyboardInterrupt:
            print("\n  Stopped.")
            break
        except Exception as e:
            print(f"  [ERR] {e}")

        try:
            time.sleep(REFRESH_SECS)
        except KeyboardInterrupt:
            print("\n  Stopped.")
            break

if __name__ == "__main__":
    main()
