import time
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from unidecode import unidecode
import re
import os

# --- CONFIG ---
DEVICE_IP = "10.0.4.20"
DEVICE_URL = f"http://{DEVICE_IP}/api/display/draw"
APP_ID = "spotify_display"
SHOW_TIMER = False  # toggle on/off
UPDATE_INTERVAL = 2  # seconds
DISPLAY_WIDTH = 72  # max width before scrolling


SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"

# --- SPOTIFY SETUP ---
scope = "user-read-currently-playing"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="7358f578dbc54693bc23fb00c73de8e2",
    client_secret="aa3ef89bef3e49908c4b6d537f78927e",
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope=scope
))

# --- MAIN LOOP AND DISPLAY FUNCTIONS ---

def upload_image(device_ip, app_id, path, remote_name):
    """Upload a local image to the device once."""
    if not os.path.exists(path):
        print(f"?????? Image {path} not found, skipping upload.")
        return False
    with open(path, "rb") as f:
        img_bytes = f.read()
    try:
        r = requests.post(
            f"http://{device_ip}/api/assets/upload",
            params={"app_id": app_id, "file": remote_name},
            data=img_bytes,
            headers={"Content-Type": "application/octet-stream"},
            timeout=5
        )
        r.raise_for_status()
        print(f"Uploaded {remote_name} successfully.")
        return True
    except Exception as e:
        print("Image upload failed:", e)
        return False


def sanitize(text):
    """Sanitize text for display: convert to ASCII and strip unsupported chars."""
    if not text:
        return "???"
    text = unidecode(text)
    text = re.sub(r'[^ -~]', '', text)  # only printable ASCII
    return text if text else "???"

IMAGE_REMOTE_NAME = "spotify_icon.png"  # the 16x16 image uploaded to the device
IMAGE_WIDTH = 16
TEXT_X = 53  # leave 1px padding after the icon


def send_display(artist, song, timer=""):
    """Send Spotify info to the display with 16x16 image on the left."""
    # Sanitize
    artist = sanitize(artist)
    song = sanitize(song)

    top_line = f"{artist} - {timer}" if timer else artist

    # Pad shorter line to match longer line
    max_len = max(len(top_line), len(song))
    top_line_padded = top_line.ljust(max_len)
    song_padded = song.ljust(max_len)

    # Scroll only if text is longer than display width
    SCROLL_THRESHOLD = 20
    scroll_rate = 50 if max(len(top_line_padded), len(song_padded)) > SCROLL_THRESHOLD else 0

    payload = {
        "app_id": APP_ID,
        "elements": [
            # Image element
            {
                "id": "spotify_img",
                "type": "image",
                "path": IMAGE_REMOTE_NAME,
                "x": 0,
                "y": 0,
                "timeout": 6,
                "display": "front"
            },
            # First text line
            {
                "id": "0",
                "type": "text",
                "text": top_line_padded,
                "x": TEXT_X,
                "y": 5,
                "align": "center",
                "font": "small",
                "color": "#FFFFFFFF",
                "width": 72,
                "scroll_rate": scroll_rate,
                "display": "front",
                "timeout": 6
            },
            # Second text line
            {
                "id": "1",
                "type": "text",
                "text": song_padded,
                "x": TEXT_X,
                "y": 12,
                "align": "center",
                "font": "small",
                "color": "#AAFF00FF",
                "width": 72,
                "scroll_rate": scroll_rate,
                "display": "front",
                "timeout": 6
            }
        ]
    }

    try:
        r = requests.post(DEVICE_URL, json=payload, timeout=2)
        if r.status_code >= 400:
            print("Display update failed:", r.status_code, r.text)
    except Exception as e:
        print("Display error:", e)


def get_current_track():
    """Return (artist, song, progress_str) or (None, None, None)."""
    try:
        current = sp.currently_playing()
        if current and current["is_playing"]:
            artist = ", ".join([a["name"] for a in current["item"]["artists"]])
            song = current["item"]["name"]
            if SHOW_TIMER:
                progress_ms = current["progress_ms"]
                duration_ms = current["item"]["duration_ms"]
                minutes_progress = progress_ms // 60000
                seconds_progress = (progress_ms // 1000) % 60
                minutes_total = duration_ms // 60000
                seconds_total = (duration_ms // 1000) % 60

                progress_str = f"{minutes_progress}:{seconds_progress:02d} / {minutes_total}:{seconds_total:02d}"
            else:
                progress_str = ""
            return artist, song, progress_str
    except Exception as e:
        print("Spotify error:", e)
    return None, None, None

def clear_display():
    """Clear the display instantly."""
    payload = {"app_id": APP_ID, "elements": []}
    try:
        requests.post(DEVICE_URL, json=payload, timeout=2)
    except Exception:
        pass

# --- MAIN LOOP ---
if __name__ == "__main__":
    # upload the icon once
    upload_image(DEVICE_IP, APP_ID, IMAGE_REMOTE_NAME, IMAGE_REMOTE_NAME)
    
    try:
        while True:
            artist, song, timer = get_current_track()
            if artist and song:
                send_display(artist, song, timer)
            else:
                clear_display()
            time.sleep(UPDATE_INTERVAL)
    except KeyboardInterrupt:
        print("\nQuitting??? clearing display.")
        clear_display()
