#!/usr/bin/env python3
"""
Live subtitles widget for BUSY Bar: microphone -> speech-to-text -> POST /api/display/draw.

Follows the dynamic widget pattern in BSB-AI Lessons (HTTP API, DisplayElements, ASCII-safe text).

Bundled **`8px_cl-sound-100.png`** is uploaded as an app asset for the idle **Subtitle App** label.
The first live subtitle draw **DELETE**s that app’s previous draw so the idle icon cannot cover transcript text.

Dependencies (no PortAudio compile; uses wheels on macOS):
  python3 -m pip install --user -r requirements.txt

This script lives only under **Subtitles/** (not the repo root). From repo root, `python3 subtitle_widget.py` will fail.

  **One line (zsh/bash):** use `&&` between commands — do **not** type the words `then` or `run`.
  cd ".../BSB-Custom-Widgets/APPS & Widgets/Unpublished/Widgets/Subtitles" && SUBTITLE_MIC_DEVICE=3 python3 subtitle_widget.py

  **Or** from anywhere: `SUBTITLE_MIC_DEVICE=3 bash "/full/path/to/Subtitles/run_subtitles.sh"`

macOS: grant Terminal (or your IDE) microphone access in System Settings > Privacy & Security.

Optional: PyAudio + sr.Microphone is not required; capture uses sounddevice + numpy.

Speech-to-text backend (**SUBTITLE_STT_BACKEND**):
  whisper — default: local **faster-whisper** (offline after model download; install `faster-whisper`).
  google — SpeechRecognition + Google Web API (network; set `SUBTITLE_STT_BACKEND=google`).
  Set SPEECH_LANGUAGE (default en-US), e.g. en-GB, fr-FR (Whisper uses the two-letter prefix, e.g. en).
  Whisper: SUBTITLE_WHISPER_MODEL (tiny/base/small/…; default base), SUBTITLE_WHISPER_DEVICE (cpu/cuda),
  SUBTITLE_WHISPER_COMPUTE (int8/float16), SUBTITLE_WHISPER_VAD (1/0 — VAD pre-filter; default 0 for live mic).

If recognition worked once then never again after restart: stay **silent** during “Calibrating…” — talking there raises the speech threshold and can block phrase detection. SUBTITLE_DEBUG=1 shows noise percentiles vs threshold.

If the idle screen never updates:
  SUBTITLE_DEBUG=1 — print energy threshold and input device.
  SUBTITLE_MIC_DEVICE — input index (0,1,...) or substring of the mic name (see printed list).
  SUBTITLE_INPUT_GAIN — digital boost before STT (default 2.5).
  SUBTITLE_ENERGY_FLOOR — min energy threshold (default ~22); speech RMS alone is often 15–40 on laptop mics.
  SUBTITLE_THRESH_MULT — scales ambient noise term (default 2.0).
  SUBTITLE_SAMPLE_RATE — force capture rate (e.g. 48000); default = device native rate (fixes silence at 16000 on some Macs).
  SUBTITLE_CAPTURE_CHANNELS — 1 or 2 (stereo); auto-probes if unset.
  SUBTITLE_SCROLL_RATE — 0 (default, static text); set e.g. 400 for horizontal scroll (pixels/min).
  SUBTITLE_FONT — default small (two-line layout); medium/medium_condensed/big also supported.
  SUBTITLE_LINE_CHARS — max characters per line before wrap (default 18 for 72px-wide small).
  SUBTITLE_TYPE_DELAY — seconds between typewriter steps (default ~0.022); 0 = show full phrase at once.
  SUBTITLE_TYPE_STEP_CHARS — characters revealed per step (default 2); higher = fewer HTTP draws, snappier.
  SUBTITLE_WHISPER_BEAM — Whisper beam size 1–5 (default 1 = faster; 5 = slower, slightly better quality).
  SUBTITLE_LINE_OFFSET_Y — shift both lines down (default 3px; avoids top-edge clipping on 16px-tall front).
  SUBTITLE_LINE0_Y / SUBTITLE_LINE1_Y — optional overrides (defaults: offset and offset+8).
  SUBTITLE_IDLE_ROW_Y — vertical anchor for idle icon + label (default 8, mid_* = centred on 16px-tall strip).
  SUBTITLE_MAX_PHRASE_SECONDS — max length of one audio chunk before flush (default 45; longer speech splits here).
  SUBTITLE_SILENCE_END_SECONDS — how long energy must stay *below* the release threshold to end a phrase (default ~0.7s).
  SUBTITLE_RELEASE_RATIO — fraction of speech threshold; energy above this still resets “silence” (default 0.52; helps fast speech).
  SUBTITLE_MIN_PHRASE_SECONDS — minimum audio before a phrase is sent (default 0.2).
  SUBTITLE_ECHO_TRANSCRIPTS — print each transcription to the terminal (default 1; set 0 to disable).
  SUBTITLE_CLEAR_ON_EXIT — DELETE this app's draw when stopping (default 1). Set 0 if the next run never shows text until device reboot.
  SUBTITLE_SKIP_DELETE_BEFORE_LIVE — if 1, do not DELETE before first live subtitle (default 0). Try if idle shows but live text never does (idle icon may overlap text).
  SUBTITLE_MIN_VOICE_CHUNKS — minimum voiced chunks before a phrase can end (default 2; higher can stall short lines).
  SUBTITLE_GOOGLE_STT_RETRIES — Google Web STT attempts on UnknownValueError (default 2).
  SUBTITLE_STT_MIN_ENERGY — if set above 0, skip STT when post-gain energy is below this (reduces junk phrases).
  SUBTITLE_MAX_CHARS — max characters per draw after sanitize (default 600); overflow keeps the **end** of the text.
  SUBTITLE_MAX_THRESHOLD — hard cap on the speech-detection threshold after calibration (default 200); prevents noisy calibration from making speech undetectable.
  SUBTITLE_PHRASE_QUEUE_MAX — max pending phrases waiting for STT (default 12); if STT is slow, oldest may be dropped.
  SUBTITLE_DRAW_PRIORITY — priority for live subtitle POSTs (1–10, default 9). Per-device docs: lower priority is ignored when a higher-priority draw is active — if nothing shows while another app is on-screen, raise this (e.g. 10).

Diagnostics:
  python3 subtitle_widget.py --test-mic
  Prints live RMS/peak for ~5s (no BUSY Bar). If peak stays 0, macOS is not delivering audio to this Python binary.
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import time
import warnings
from collections import deque
from collections.abc import Callable
from pathlib import Path

import numpy as np
import requests
import sounddevice as sd

# #region agent log
_DBG_LOG_PATH = "/Users/barker/Documents/Github/BSB-Custom-Widgets/.cursor/debug-484d8f.log"
def _dbg(loc: str, msg: str, data: dict | None = None, hyp: str = "") -> None:
    import json as _j
    try:
        with open(_DBG_LOG_PATH, "a") as _f:
            _f.write(_j.dumps({"sessionId": "484d8f", "timestamp": int(time.time() * 1000), "location": loc, "message": msg, "data": data or {}, "hypothesisId": hyp}) + "\n")
    except Exception:
        pass
# #endregion

try:
    import speech_recognition as sr
except ImportError:
    print("Install: python3 -m pip install --user -r requirements.txt", file=sys.stderr)
    raise

# --- Config (env overrides) ---
STT_BACKEND = os.environ.get("SUBTITLE_STT_BACKEND", "whisper").strip().lower()
WHISPER_MODEL = os.environ.get("SUBTITLE_WHISPER_MODEL", "base").strip() or "base"
WHISPER_DEVICE = os.environ.get("SUBTITLE_WHISPER_DEVICE", "cpu").strip() or "cpu"
WHISPER_COMPUTE = os.environ.get("SUBTITLE_WHISPER_COMPUTE", "int8").strip() or "int8"
# Default off: built-in VAD often drops short phrases on live mic chunks.
WHISPER_VAD = os.environ.get("SUBTITLE_WHISPER_VAD", "0").strip() in ("1", "true", "yes", "on")
DEVICE = os.environ.get("BUSY_BAR_HOST", "http://10.0.4.20").rstrip("/")
if not DEVICE.startswith("http"):
    DEVICE = "http://" + DEVICE

APP_ID = os.environ.get("BUSY_BAR_SUBTITLES_APP_ID", "busybar_subtitles")
DISPLAY = os.environ.get("BUSY_BAR_DISPLAY", "front")
SPEECH_LANGUAGE = os.environ.get("SPEECH_LANGUAGE", "en-US")

# Scrolling: 0 = static (default); >0 = pixels per minute (OpenAPI TextElement)
SCROLL_RATE = int(os.environ.get("SUBTITLE_SCROLL_RATE", "0"))
# Long rambles exceed this; we keep the **tail** so the latest words still show (see sanitize_for_display).
MAX_CHARS = int(os.environ.get("SUBTITLE_MAX_CHARS", "600"))
FONT = os.environ.get("SUBTITLE_FONT", "small")
# ~4px/char at small → 18 chars across 72px; BSB lessons suggest ≤12 for “safe” single line — override if needed.
LINE_CHARS = max(4, int(os.environ.get("SUBTITLE_LINE_CHARS", "18")))
SCREEN_WIDTH = 72

# Idle label (shown before first transcription); paired with optional app icon on device.
SUBTITLE_APP_LABEL = "Subtitle App"
PLACEHOLDER = SUBTITLE_APP_LABEL
# Bundled PNG uploaded to the bar as an app asset (see upload_app_icon).
ICON_FILE = "8px_cl-sound-100.png"
ICON_SIZE = 8
REQUEST_TIMEOUT = 12

SAMPLE_RATE = 16000
CHUNK_DURATION = 0.03
CALIBRATION_SECONDS = 0.9


def _parse_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _parse_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return raw.lower() in ("1", "true", "yes", "on")


_DEBUG = os.environ.get("SUBTITLE_DEBUG", "").strip() in ("1", "true", "yes", "on")
ECHO_TRANSCRIPTS = _env_bool("SUBTITLE_ECHO_TRANSCRIPTS", True)
# If false, do not DELETE this app's draw on Ctrl+C (some setups recover better for the next run).
CLEAR_ON_EXIT = _env_bool("SUBTITLE_CLEAR_ON_EXIT", True)
# If true, skip DELETE before first live subtitle (try if live text never appears after idle screen works).
SKIP_DELETE_BEFORE_LIVE = _env_bool("SUBTITLE_SKIP_DELETE_BEFORE_LIVE", False)

# Default small delay = typewriter; set SUBTITLE_TYPE_DELAY=0 for one draw per phrase.
TYPE_DELAY = _parse_float("SUBTITLE_TYPE_DELAY", 0.055)
TYPE_STEP_CHARS = max(1, _parse_int("SUBTITLE_TYPE_STEP_CHARS", 1))
WHISPER_BEAM = max(1, min(5, _parse_int("SUBTITLE_WHISPER_BEAM", 1)))

# Phrase segmentation (long continuous speech splits when max duration hit, or after silence).
MAX_PHRASE_SECONDS = max(5.0, _parse_float("SUBTITLE_MAX_PHRASE_SECONDS", 45.0))
# Longer default: word gaps in fast speech must not look like end-of-phrase silence.
SILENCE_END_SECONDS = max(0.12, _parse_float("SUBTITLE_SILENCE_END_SECONDS", 0.7))
MIN_PHRASE_SECONDS = max(0.12, _parse_float("SUBTITLE_MIN_PHRASE_SECONDS", 0.2))
MIN_VOICE_CHUNKS = max(2, _parse_int("SUBTITLE_MIN_VOICE_CHUNKS", 2))
GOOGLE_STT_RETRIES = max(1, _parse_int("SUBTITLE_GOOGLE_STT_RETRIES", 2))
STT_MIN_ENERGY = _parse_float("SUBTITLE_STT_MIN_ENERGY", 0.0)
# Below speech threshold but above (threshold * ratio) = still “inside” an utterance (hysteresis).
RELEASE_RATIO = max(0.15, min(0.95, _parse_float("SUBTITLE_RELEASE_RATIO", 0.52)))

# Vertical layout: original (0,8) clipped the top row; default +3px inset, keep 8px between anchors.
_LINE_OFFSET_Y = _parse_int("SUBTITLE_LINE_OFFSET_Y", 3)
LINE0_Y = _parse_int("SUBTITLE_LINE0_Y", _LINE_OFFSET_Y)
LINE1_Y = _parse_int("SUBTITLE_LINE1_Y", LINE0_Y + 8)
# 72×16 strip: y=8 + mid_* anchors vertically centers a single row (idle icon + label).
IDLE_ROW_Y = _parse_int("SUBTITLE_IDLE_ROW_Y", 8)

PHRASE_QUEUE_MAX = max(1, _parse_int("SUBTITLE_PHRASE_QUEUE_MAX", 12))
# Live transcript draws use this; idle placeholder uses priority 6. Higher = wins over other apps.
DRAW_PRIORITY_LIVE = max(1, min(10, _parse_int("SUBTITLE_DRAW_PRIORITY", 9)))

_whisper_model = None
_whisper_lock = threading.Lock()

# Idle screen uses an image + text; some firmware merges by element id. Clear once before first live draw.
_clear_idle_before_live_subtitles = True
_live_draw_http_count = 0


def _resolve_rec_sr(device: int | None) -> int:
    """Capture sample rate. Built-in Mac mics sometimes return silence at 16 kHz; prefer device default."""
    forced = os.environ.get("SUBTITLE_SAMPLE_RATE", "").strip()
    if forced.isdigit():
        return max(8000, int(forced))
    try:
        if device is None:
            info = sd.query_devices(kind="input")
        else:
            info = sd.query_devices(device)
        sr = float(info.get("default_samplerate") or 0)
        if sr >= 8000:
            return int(sr)
    except OSError:
        pass
    return SAMPLE_RATE


def _dev_max_channels(device: int | None) -> int:
    try:
        if device is None:
            d = sd.query_devices(kind="input")
        else:
            d = sd.query_devices(device)
        return max(1, int(d.get("max_input_channels", 1) or 1))
    except OSError:
        return 1


def _set_default_input_device(device: int | None) -> None:
    """Point PortAudio default input at the chosen device (helps some macOS configs)."""
    if device is None:
        return
    try:
        cur = sd.default.device
        if isinstance(cur, tuple) and len(cur) >= 2:
            sd.default.device = (device, cur[1])
        else:
            sd.default.device = device
    except Exception:
        pass


def _int16_mono_from_rec(chunk: np.ndarray) -> np.ndarray:
    """Interleaved capture -> mono int16: pick the loudest channel per block (odd routing on some Macs)."""
    if chunk.ndim == 1:
        return chunk.copy()
    if chunk.ndim != 2:
        return chunk.astype(np.int16).ravel()
    best = 0
    best_abs = -1
    for c in range(chunk.shape[1]):
        mx = int(np.max(np.abs(chunk[:, c])))
        if mx > best_abs:
            best_abs = mx
            best = c
    return chunk[:, best].copy()


def _resolve_capture_channels(device: int | None, rec_sr: int) -> int:
    """1 or 2 channels. SUBTITLE_CAPTURE_CHANNELS=1|2 forces; else probe for non-silent stereo."""
    raw = os.environ.get("SUBTITLE_CAPTURE_CHANNELS", "").strip()
    if raw in ("1", "2"):
        return int(raw)
    max_ch = _dev_max_channels(device)
    n = max(1, int(rec_sr * 0.2))
    order = [1, 2] if max_ch >= 2 else [1]
    for ch in order:
        try:
            chunk = sd.rec(n, samplerate=rec_sr, channels=ch, dtype="int16", device=device)
            sd.wait()
            mono = _int16_mono_from_rec(chunk)
            if int(np.max(np.abs(mono))) > 0:
                return ch
        except OSError:
            continue
    return 2 if max_ch >= 2 else 1


def _record_mono_chunk(
    device: int | None,
    rec_sr: int,
    chunk_frames: int,
    cap_channels: int,
) -> np.ndarray:
    chunk = sd.rec(
        chunk_frames,
        samplerate=rec_sr,
        channels=cap_channels,
        dtype="int16",
        device=device,
    )
    sd.wait()
    return _int16_mono_from_rec(np.asarray(chunk, dtype=np.int16).copy())


def _read_mono_from_stream(
    stream: sd.InputStream,
    chunk_frames: int,
    cap_channels: int,
) -> tuple[np.ndarray, bool]:
    """Blocking read from a long-lived InputStream. Returns (mono_int16, overflowed)."""
    data, overflowed = stream.read(chunk_frames)
    arr = np.asarray(data, dtype=np.int16).copy()
    return _int16_mono_from_rec(arr), overflowed


def _python_org_app_bundle() -> str | None:
    """Python.org installer: the .app bundle that macOS may list separately in Microphone privacy."""
    if sys.platform != "darwin":
        return None
    if "Python.framework" not in sys.executable:
        return None
    exe = os.path.realpath(sys.executable)
    bindir = os.path.dirname(exe)
    verdir = os.path.dirname(bindir)
    app = os.path.join(verdir, "Resources", "Python.app")
    if os.path.isdir(app):
        return app
    return None


def _resample_int16_mono(x: np.ndarray, rate_in: int, rate_out: int) -> np.ndarray:
    if rate_in == rate_out or x.size == 0:
        return x
    n_out = max(1, int(len(x) * rate_out / rate_in))
    if len(x) < 2:
        return x
    old_idx = np.arange(len(x), dtype=np.float64)
    new_idx = np.linspace(0.0, float(len(x) - 1), n_out)
    y = np.interp(new_idx, old_idx, x.astype(np.float64))
    return np.clip(y, -32768, 32767).astype(np.int16)


def _buffer_to_audio_data(buffer: bytes, rec_sr: int) -> sr.AudioData:
    pcm = np.frombuffer(buffer, dtype=np.int16)
    if rec_sr != SAMPLE_RATE:
        pcm = _resample_int16_mono(pcm, rec_sr, SAMPLE_RATE)
    return sr.AudioData(pcm.tobytes(), SAMPLE_RATE, 2)


def _resolve_input_device() -> int | None:
    """None = PortAudio default. Or int index, or substring match against device name."""
    raw = os.environ.get("SUBTITLE_MIC_DEVICE", "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return int(raw)
    devs = sd.query_devices()
    for i, d in enumerate(devs):
        if int(d.get("max_input_channels", 0) or 0) > 0 and raw.lower() in (d.get("name") or "").lower():
            return i
    print(f"SUBTITLE_MIC_DEVICE={raw!r} not found; using default input.", file=sys.stderr)
    return None


def _input_device_label(dev_index: int | None) -> str:
    if dev_index is None:
        d = sd.query_devices(kind="input")
        return f"default: {d['name']}"
    d = sd.query_devices(dev_index)
    return f"#{dev_index}: {d['name']}"


def _print_input_devices() -> None:
    print("[subtitles] Input devices (set SUBTITLE_MIC_DEVICE to index or name substring):", file=sys.stderr)
    for i, d in enumerate(sd.query_devices()):
        if int(d.get("max_input_channels", 0) or 0) > 0:
            print(f"  {i}: {d['name']}", file=sys.stderr)


def _apply_gain(audio: sr.AudioData, gain: float) -> sr.AudioData:
    if abs(gain - 1.0) < 0.01:
        return audio
    arr = np.frombuffer(audio.frame_data, dtype=np.int16)
    boosted = np.clip(arr.astype(np.float32) * gain, -32768, 32767).astype(np.int16)
    return sr.AudioData(boosted.tobytes(), audio.sample_rate, audio.sample_width)


def _audio_energy(audio: sr.AudioData) -> float:
    arr = np.frombuffer(audio.frame_data, dtype=np.int16)
    return _chunk_energy(arr)


def _recognize_google_with_retries(recognizer: sr.Recognizer, audio: sr.AudioData) -> str:
    """Google Web STT sometimes returns UnknownValueError on valid audio; retry briefly."""
    attempts = GOOGLE_STT_RETRIES
    for attempt in range(attempts):
        try:
            return recognizer.recognize_google(audio, language=SPEECH_LANGUAGE)
        except sr.UnknownValueError:
            if attempt < attempts - 1:
                time.sleep(0.15)
                continue
            raise


def _api_headers() -> dict[str, str]:
    tok = os.environ.get("BUSY_BAR_API_KEY")
    if tok:
        return {"X-API-Token": tok}
    return {}


def _post_display_draw(payload: dict) -> requests.Response:
    """POST /api/display/draw; logs response body on failure (common: wrong host, 401, validation)."""
    url = f"{DEVICE}/api/display/draw"
    try:
        r = requests.post(url, json=payload, headers=_api_headers(), timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r
    except requests.RequestException as e:
        resp = getattr(e, "response", None)
        detail = ""
        if resp is not None:
            try:
                detail = (resp.text or "")[:400].replace("\n", " ")
            except Exception:
                pass
            print(
                f"[subtitles] POST /api/display/draw failed  "
                f"host={DEVICE!r}  display={DISPLAY!r}  status={resp.status_code}  "
                f"body={detail!r}",
                file=sys.stderr,
            )
        else:
            print(f"[subtitles] POST /api/display/draw failed (no response): {e}", file=sys.stderr)
        raise


def _icon_path() -> Path:
    return Path(__file__).resolve().parent / ICON_FILE


def upload_app_icon() -> bool:
    """POST PNG bytes to the bar so image elements can reference it by filename."""
    path = _icon_path()
    if not path.is_file():
        print(f"[subtitles] Icon not found ({path}); idle screen will be text only.", file=sys.stderr)
        return False
    url = f"{DEVICE}/api/assets/upload"
    try:
        with open(path, "rb") as f:
            data = f.read()
        r = requests.post(
            url,
            params={"app_id": APP_ID, "file": ICON_FILE},
            data=data,
            headers=_api_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[subtitles] Icon upload failed (text-only idle): {e}", file=sys.stderr)
        return False


def send_placeholder_draw(*, show_icon: bool) -> None:
    """Idle screen: optional 8px icon + 'Subtitle App', vertically centred on the 16px strip."""
    text_x = (ICON_SIZE + 2) if show_icon else 0
    text_w = max(8, SCREEN_WIDTH - text_x)
    elements: list[dict] = []
    if show_icon:
        elements.append(
            {
                "id": "sub_idle_icon",
                "type": "image",
                "path": ICON_FILE,
                "x": 0,
                "y": IDLE_ROW_Y,
                "align": "mid_left",
                "display": DISPLAY,
            }
        )
    elements.append(
        {
            "id": "sub_l0",
            "type": "text",
            "text": SUBTITLE_APP_LABEL,
            "x": text_x,
            "y": IDLE_ROW_Y,
            "align": "mid_left",
            "font": FONT,
            "color": "#FFFFFFFF",
            "width": text_w,
            "scroll_rate": SCROLL_RATE,
            "display": DISPLAY,
        }
    )
    r = _post_display_draw({"app_id": APP_ID, "priority": 6, "elements": elements})
    print(
        f"[subtitles] Idle screen POST OK (HTTP {r.status_code}) — if the strip is blank, check USB/host "
        f"({DEVICE!r}) and SUBTITLE_DISPLAY.",
        file=sys.stderr,
        flush=True,
    )


def _whisper_language_code() -> str | None:
    raw = SPEECH_LANGUAGE.strip()
    if not raw:
        return None
    return raw.split("-")[0].lower()


def _audio_data_to_float32_mono(audio: sr.AudioData) -> np.ndarray:
    arr = np.frombuffer(audio.frame_data, dtype=np.int16)
    return np.clip(arr.astype(np.float32) / 32768.0, -1.0, 1.0)


def _load_whisper_model():
    """Lazy-load faster-whisper (downloads model on first use)."""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise RuntimeError(
            "Whisper backend requires faster-whisper: pip install faster-whisper"
        ) from e
    _whisper_model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)
    return _whisper_model


def transcribe_with_whisper(audio: sr.AudioData) -> str | None:
    """Local Whisper transcription; returns None if no text."""
    with _whisper_lock:
        model = _load_whisper_model()
        samples = _audio_data_to_float32_mono(audio)
        if samples.size < 240:
            return None
        lang = _whisper_language_code()
        kwargs: dict = {
            "beam_size": WHISPER_BEAM,
            "best_of": 1,
            "vad_filter": WHISPER_VAD,
            "without_timestamps": True,
        }
        if lang:
            kwargs["language"] = lang
        # faster-whisper's mel/STFT can emit RuntimeWarning (divide by zero / overflow in mel path)
        # on silence-heavy or very short clips; transcription still works. Narrow filter to this call.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                category=RuntimeWarning,
                module=r"faster_whisper\.",
            )
            segments, _info = model.transcribe(samples, **kwargs)
        parts = [s.text for s in segments]
        text = "".join(parts).strip()
        return text if text else None


def sanitize_for_display(s: str) -> str:
    """Strip unsupported characters so the bar shows readable ASCII (BSB-AI Lessons)."""
    out: list[str] = []
    for ch in s:
        o = ord(ch)
        if 32 <= o < 127:
            out.append(ch)
        elif ch in "\n\r\t":
            out.append(" ")
    cleaned = " ".join("".join(out).split())
    if not cleaned:
        return PLACEHOLDER
    if len(cleaned) <= MAX_CHARS:
        return cleaned
    # Keep the **tail** so long transcripts are not cut off at the end (subtitles: latest words matter).
    if MAX_CHARS <= 4:
        return cleaned[-MAX_CHARS:]
    return "..." + cleaned[-(MAX_CHARS - 3) :]


def wrap_text_to_lines(text: str, max_chars: int) -> list[str]:
    """Word-wrap into lines of at most max_chars (long words are split)."""
    if max_chars < 1:
        max_chars = 1
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    cur: list[str] = []
    cur_len = 0

    def flush() -> None:
        nonlocal cur, cur_len
        if cur:
            lines.append(" ".join(cur))
            cur = []
            cur_len = 0

    for w in words:
        while len(w) > max_chars:
            flush()
            lines.append(w[:max_chars])
            w = w[max_chars:]
        if not w:
            continue
        add = len(w) if not cur else 1 + len(w)
        if cur_len + add <= max_chars:
            cur.append(w)
            cur_len += add
        else:
            flush()
            cur = [w]
            cur_len = len(w)
    flush()
    return lines if lines else [""]


def last_two_lines(lines: list[str]) -> tuple[str, str]:
    """Show at most two lines; when there are more, keep the last two (subtitle-style roll)."""
    if not lines:
        return "", ""
    if len(lines) == 1:
        return lines[0], ""
    return lines[-2], lines[-1]


def send_subtitle_display(line0: str, line1: str) -> None:
    """Two stacked small-text lines: fill line 0, then line 1 (no horizontal scroll by default)."""
    global _clear_idle_before_live_subtitles, _live_draw_http_count
    if _clear_idle_before_live_subtitles:
        _clear_idle_before_live_subtitles = False
        if not SKIP_DELETE_BEFORE_LIVE:
            clear_display()
            time.sleep(0.15)
    # Second line: some devices skip empty strings; use a space so the row still commits.
    line1_out = line1 if line1.strip() else " "
    elements = [
        {
            "id": "sub_l0",
            "type": "text",
            "text": line0,
            "x": 0,
            "y": LINE0_Y,
            "align": "top_left",
            "font": FONT,
            "color": "#FFFFFFFF",
            "width": SCREEN_WIDTH,
            "scroll_rate": SCROLL_RATE,
            "display": DISPLAY,
        },
        {
            "id": "sub_l1",
            "type": "text",
            "text": line1_out,
            "x": 0,
            "y": LINE1_Y,
            "align": "top_left",
            "font": FONT,
            "color": "#FFFFFFFF",
            "width": SCREEN_WIDTH,
            "scroll_rate": SCROLL_RATE,
            "display": DISPLAY,
        },
    ]
    r = _post_display_draw({"app_id": APP_ID, "priority": DRAW_PRIORITY_LIVE, "elements": elements})
    _live_draw_http_count += 1
    if _live_draw_http_count == 1:
        p0 = line0[:48] + ("…" if len(line0) > 48 else "")
        p1 = line1[:24] + ("…" if len(line1) > 24 else "")
        print(
            f"[subtitles] First live subtitle frame POST OK (HTTP {r.status_code})  "
            f"line0={p0!r}  line1={p1!r}  — if you see this but the bar is blank, try "
            f"SUBTITLE_SKIP_DELETE_BEFORE_LIVE=1 or SUBTITLE_DISPLAY=back.",
            file=sys.stderr,
            flush=True,
        )


def send_subtitle_line(text: str) -> None:
    """Single update: sanitize, wrap, and draw (no typewriter)."""
    safe = sanitize_for_display(text)
    l0, l1 = last_two_lines(wrap_text_to_lines(safe, LINE_CHARS))
    send_subtitle_display(l0, l1)


def type_out_subtitle(
    safe: str,
    typing_gen_ref: list[int],
    my_gen: int,
    state_lock: threading.Lock,
    last_error: list[str | None],
) -> None:
    """Reveal text character-by-character; wrap fills lines L→R then down.

    If a new phrase arrives mid-animation, this phrase is drawn in full once before the next
    phrase types — otherwise most of the prior sentence would disappear from the display.
    """
    if not safe:
        return
    delay = TYPE_DELAY
    try:
        if delay <= 0.0:
            l0, l1 = last_two_lines(wrap_text_to_lines(safe, LINE_CHARS))
            send_subtitle_display(l0, l1)
            return
        step = TYPE_STEP_CHARS
        k = 0
        while k < len(safe):
            if typing_gen_ref[0] != my_gen:
                l0, l1 = last_two_lines(wrap_text_to_lines(safe, LINE_CHARS))
                send_subtitle_display(l0, l1)
                return
            k = min(k + step, len(safe))
            prefix = safe[:k]
            l0, l1 = last_two_lines(wrap_text_to_lines(prefix, LINE_CHARS))
            send_subtitle_display(l0, l1)
            if k < len(safe):
                time.sleep(delay)
    except requests.RequestException as e:
        with state_lock:
            last_error[0] = f"device: {e}"


def _display_worker_loop(
    display_queue: queue.Queue,
    typing_gen: list[int],
    state_lock: threading.Lock,
    last_error: list[str | None],
    stop_event: threading.Event,
) -> None:
    """Single long-lived thread for subtitle display updates — prevents race conditions
    from multiple concurrent typewriter threads doing interleaved HTTP POSTs."""
    while not stop_event.is_set():
        try:
            item = display_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        if item is None:
            break
        safe, my_gen = item
        while True:
            try:
                newer = display_queue.get_nowait()
                if newer is None:
                    return
                safe, my_gen = newer
            except queue.Empty:
                break
        type_out_subtitle(safe, typing_gen, my_gen, state_lock, last_error)
        if typing_gen[0] == my_gen:
            err = None
            with state_lock:
                err = last_error[0]
            if not err and not ECHO_TRANSCRIPTS:
                print("OK:", safe[:120])


def clear_display() -> None:
    try:
        url = f"{DEVICE}/api/display/draw"
        r = requests.delete(url, params={"app_id": APP_ID}, headers=_api_headers(), timeout=REQUEST_TIMEOUT)
        if r.status_code >= 400:
            try:
                detail = (r.text or "")[:300].replace("\n", " ")
            except Exception:
                detail = ""
            print(
                f"[subtitles] DELETE /api/display/draw failed  status={r.status_code}  body={detail!r}",
                file=sys.stderr,
            )
    except requests.RequestException as e:
        print(f"[subtitles] DELETE /api/display/draw failed: {e}", file=sys.stderr)


def _rms(int16_mono: np.ndarray) -> float:
    if int16_mono.size == 0:
        return 0.0
    x = int16_mono.astype(np.float64).ravel()
    return float(np.sqrt(np.mean(x * x)))


def _enqueue_phrase(phrase_queue: queue.Queue, audio: sr.AudioData) -> None:
    """
    Mic thread never blocks on STT: enqueue phrases for a separate consumer.
    If the queue is full, drop the oldest pending phrase so capture keeps up.
    """
    try:
        phrase_queue.put_nowait(audio)
    except queue.Full:
        try:
            phrase_queue.get_nowait()
        except queue.Empty:
            pass
        try:
            phrase_queue.put_nowait(audio)
        except queue.Full:
            if _DEBUG:
                print("[subtitles] phrase queue full; dropped a phrase", file=sys.stderr)


def _phrase_consumer_loop(
    phrase_queue: queue.Queue,
    on_phrase: Callable[[sr.AudioData], None],
    stop_event: threading.Event,
) -> None:
    """Run STT + display off the capture thread so the mic stream is always read."""
    while True:
        try:
            audio = phrase_queue.get(timeout=0.4)
        except queue.Empty:
            if stop_event.is_set():
                break
            continue
        on_phrase(audio)


def _chunk_energy(mono: np.ndarray) -> float:
    """
    Voice activity energy. RMS alone often stays ~15–35 for normal laptop speech while a hard
    floor of 70 never trips — blend with peak so short consonants still count.
    """
    if mono.size == 0:
        return 0.0
    r = _rms(mono)
    pk = float(np.max(np.abs(mono)))
    return max(r, pk * 0.35)


def _probe_input_rates(device: int | None) -> None:
    print("[subtitles] Short capture at different rates / channels (peak > 0 = signal):", file=sys.stderr)
    max_ch = _dev_max_channels(device)
    for sr in (48000, 44100, 16000):
        for ch in ([1, 2] if max_ch >= 2 else [1]):
            try:
                n = max(1, int(sr * 0.1))
                chunk = sd.rec(n, samplerate=sr, channels=ch, dtype="int16", device=device)
                sd.wait()
                mono = _int16_mono_from_rec(chunk)
                pk = int(np.max(np.abs(mono)))
                print(f"  {sr} Hz  ch={ch}  peak={pk}  rms={_rms(mono):.1f}", file=sys.stderr)
            except OSError as e:
                print(f"  {sr} Hz  ch={ch}  error: {e}", file=sys.stderr)


def run_test_mic() -> None:
    """Verify the OS delivers non-silent samples to this process (read sys.executable for Privacy)."""
    input_dev = _resolve_input_device()
    _set_default_input_device(input_dev)
    rec_sr = _resolve_rec_sr(input_dev)
    cap_ch = _resolve_capture_channels(input_dev, rec_sr)
    chunk_frames = max(1, int(rec_sr * CHUNK_DURATION))

    print(f"Python executable (Privacy & Security → Microphone may list this): {sys.executable}")
    app = _python_org_app_bundle()
    if app:
        print(f"Python.org app bundle (enable Microphone if listed): {app}")
    print(f"Input: {_input_device_label(input_dev)}  capture={rec_sr}Hz  channels={cap_ch}")
    _print_input_devices()
    print("Speak now for ~5 seconds. You should see peak > 0 and rms > 0 if audio reaches Python.\n")

    t0 = time.time()
    t_end = t0 + 5.0
    interval_peak = 0
    interval_rms = 0.0
    chunks = 0
    global_peak = 0
    while time.time() < t_end:
        try:
            chunk = _record_mono_chunk(input_dev, rec_sr, chunk_frames, cap_ch)
        except OSError as e:
            print(f"Capture error: {e}", file=sys.stderr)
            return
        pk = int(np.max(np.abs(chunk)))
        r = _rms(chunk)
        interval_peak = max(interval_peak, pk)
        interval_rms = max(interval_rms, r)
        global_peak = max(global_peak, pk)
        chunks += 1
        if chunks % 20 == 0 and chunks > 0:
            print(f"  ~{time.time() - t0:.0f}s  rms={interval_rms:.1f}  peak={interval_peak}")
            interval_peak = 0
            interval_rms = 0.0

    print("\n---")
    if global_peak == 0:
        print(
            "No audio samples received (peak stayed 0). Common fixes:\n"
            "  • macOS: System Settings → Privacy & Security → Microphone — enable **Terminal** "
            "(or **Cursor**) **and** look for **Python** or **Python.app** (Python.org install) and enable it.\n"
            "  • If you use Python from python.org, the mic prompt may be tied to **Python.app**, not Terminal.\n"
            "  • Use the **built-in mic**: SUBTITLE_MIC_DEVICE=3 (not BlackHole unless you route audio into it).\n"
            "  • Try: SUBTITLE_CAPTURE_CHANNELS=2  or  SUBTITLE_SAMPLE_RATE=48000\n"
            "  • Or use Homebrew Python: /opt/homebrew/bin/python3 (different binary → new permission prompt).",
            file=sys.stderr,
        )
        _probe_input_rates(input_dev)
    else:
        print(f"OK: microphone signal detected (peak={global_peak}). Run without --test-mic to use the widget.")


def _mic_capture_thread(
    phrase_queue: queue.Queue,
    state_lock: threading.Lock,
    last_error: list[str | None],
    stop_event: threading.Event,
    input_dev: int | None,
    rec_sr: int,
    cap_channels: int,
) -> None:
    """Record phrases using sounddevice (no PyAudio). End phrase after silence or max length."""
    chunk_duration = CHUNK_DURATION
    chunk_frames = max(1, int(rec_sr * chunk_duration))
    calib_chunks = max(1, int(CALIBRATION_SECONDS / chunk_duration))

    ambient: list[float] = []
    try:
        with sd.InputStream(
            device=input_dev,
            channels=cap_channels,
            samplerate=rec_sr,
            dtype="int16",
            blocksize=chunk_frames,
            latency="high",
        ) as stream:
            for _ in range(calib_chunks):
                if stop_event.is_set():
                    return
                mono, _ = _read_mono_from_stream(stream, chunk_frames, cap_channels)
                ambient.append(_chunk_energy(mono))

            # Noise floor: lower percentile so a few loud chunks (talking during "stay quiet") do not
            # dominate. p75 alone made the speech threshold unreachable on the next run after noisy calib.
            noise = float(np.percentile(ambient, 20))
            p75 = float(np.percentile(ambient, 75))
            p90 = float(np.percentile(ambient, 90))
            mult = _parse_float("SUBTITLE_THRESH_MULT", 2.0)
            floor = _parse_float("SUBTITLE_ENERGY_FLOOR", 22.0)
            # Cap p75 influence when calib included speech or spikes; keeps threshold in speech range (~20–120).
            p75_adj = min(p75, noise + 52.0)
            # Match real speech levels (~20–80 energy); a floor of 70 blocked typical laptop speech entirely.
            threshold = max(noise * mult + 6.0, p75_adj * 1.4 + 4.0, floor)
            max_thresh = _parse_float("SUBTITLE_MAX_THRESHOLD", 200.0)
            if threshold > max_thresh:
                if _DEBUG:
                    print(
                        f"[subtitles] threshold {threshold:.1f} capped to {max_thresh:.1f} "
                        f"(noisy calibration window; override with SUBTITLE_MAX_THRESHOLD)",
                        file=sys.stderr,
                    )
                threshold = max_thresh
            if p90 > noise + 38.0:
                print(
                    "[subtitles] Calibration heard loud sound during the quiet window (speech or noise). "
                    "If recognition stops working, restart and stay silent for the calibration line, "
                    "or set SUBTITLE_DEBUG=1 to see thresholds.",
                    file=sys.stderr,
                )
            release_threshold = max(floor * 0.85, noise * 1.2, p90 + 2.0, threshold * RELEASE_RATIO)
            if release_threshold >= threshold:
                release_threshold = threshold * 0.92
            silence_chunks = int(SILENCE_END_SECONDS / chunk_duration)
            min_raw_bytes = int(rec_sr * MIN_PHRASE_SECONDS) * 2

            if float(np.max(ambient)) < 0.5:
                print(
                    "[subtitles] Calibration heard only digital silence (RMS ~0). "
                    "On macOS: System Settings → Privacy & Security → Microphone → enable this app "
                    "(Terminal, Cursor, iTerm, etc.). Then run again.",
                    file=sys.stderr,
                )

            if _DEBUG:
                print(
                    f"[subtitles] mic {_input_device_label(input_dev)}  capture={rec_sr}Hz  ch={cap_channels}  "
                    f"noise_p20={noise:.1f}  p75={p75:.1f}  p90={p90:.1f}  speech_threshold={threshold:.1f}  "
                    f"release_threshold={release_threshold:.1f}  silence_end={SILENCE_END_SECONDS}s",
                    file=sys.stderr,
                )

            # #region agent log
            _dbg("calib", "calibration", {"threshold": round(threshold, 2), "release": round(release_threshold, 2), "noise_p20": round(noise, 2), "p75": round(p75, 2), "p90": round(p90, 2), "p75_adj": round(p75_adj, 2), "silence_chunks": silence_chunks}, hyp="F")
            # #endregion

            buffer = bytearray()
            voiced = False
            voiced_chunks = 0
            _sw_size = max(silence_chunks, int(SILENCE_END_SECONDS * 1.5 / chunk_duration))
            _sw_quiet_frac = 0.45
            silence_window: deque[bool] = deque(maxlen=_sw_size)

            # #region agent log
            _dbg("calib_sw", "window_params", {"sw_size": _sw_size, "sw_quiet_frac": _sw_quiet_frac, "silence_chunks": silence_chunks}, hyp="G")
            # #endregion

            while not stop_event.is_set():
                try:
                    mono, overflowed = _read_mono_from_stream(stream, chunk_frames, cap_channels)
                except OSError as e:
                    with state_lock:
                        last_error[0] = f"microphone: {e}"
                    time.sleep(0.5)
                    continue

                if mono.size == 0:
                    continue

                if overflowed and voiced:
                    if _DEBUG:
                        print("[subtitles] audio stream overflow; discarding current phrase", file=sys.stderr)
                    buffer.clear()
                    voiced = False
                    voiced_chunks = 0
                    silence_window.clear()
                    continue

                e = _chunk_energy(mono)

                if e > threshold:
                    if not voiced:
                        voiced = True
                        buffer.clear()
                        voiced_chunks = 0
                        silence_window.clear()
                        # #region agent log
                        _dbg("voice_start", "phrase_started", {"energy": round(e, 2), "threshold": round(threshold, 2), "release": round(release_threshold, 2)}, hyp="G")
                        # #endregion
                    buffer.extend(mono.tobytes())
                    voiced_chunks += 1
                    silence_window.append(False)
                elif voiced:
                    buffer.extend(mono.tobytes())
                    silence_window.append(e <= release_threshold)

                    if len(silence_window) >= _sw_size:
                        quiet_count = sum(silence_window)
                        quiet_frac = quiet_count / _sw_size
                        enough_voice = voiced_chunks >= MIN_VOICE_CHUNKS
                        extended_quiet = quiet_frac >= 0.85
                        if quiet_frac >= _sw_quiet_frac and (enough_voice or extended_quiet):
                            if len(buffer) >= min_raw_bytes:
                                # #region agent log
                                _dbg("phrase_end", "phrase_enqueued_silence", {"buf_s": round(len(buffer) / 2 / rec_sr, 2), "voiced_chunks": voiced_chunks, "quiet_frac": round(quiet_frac, 3), "quiet_count": quiet_count, "sw_size": _sw_size}, hyp="G")
                                # #endregion
                                _enqueue_phrase(phrase_queue, _buffer_to_audio_data(bytes(buffer), rec_sr))
                            else:
                                if _DEBUG:
                                    print(
                                        f"[subtitles] phrase too short ({len(buffer) // 2} samples < min); dropped",
                                        file=sys.stderr,
                                    )
                            buffer.clear()
                            voiced = False
                            voiced_chunks = 0
                            silence_window.clear()
                            continue

                    if len(buffer) // 2 > rec_sr * MAX_PHRASE_SECONDS:
                        if len(buffer) >= min_raw_bytes:
                            # #region agent log
                            _dbg("phrase_end", "phrase_MAX_DURATION", {"buf_s": round(len(buffer) / 2 / rec_sr, 2), "voiced_chunks": voiced_chunks}, hyp="G")
                            # #endregion
                            _enqueue_phrase(phrase_queue, _buffer_to_audio_data(bytes(buffer), rec_sr))
                        buffer.clear()
                        voiced = False
                        voiced_chunks = 0
                        silence_window.clear()
    except OSError as e:
        with state_lock:
            last_error[0] = f"microphone: {e}"
        return


def main() -> None:
    state_lock = threading.Lock()
    last_error: list[str | None] = [None]
    stop_event = threading.Event()
    last_unknown_at: list[float] = [0.0]
    typing_gen: list[int] = [0]
    display_queue: queue.Queue = queue.Queue()

    input_gain = _parse_float("SUBTITLE_INPUT_GAIN", 2.5)
    input_dev = _resolve_input_device()
    _set_default_input_device(input_dev)
    rec_sr = _resolve_rec_sr(input_dev)
    cap_ch = _resolve_capture_channels(input_dev, rec_sr)

    recognizer = sr.Recognizer()

    def on_phrase(audio: sr.AudioData) -> None:
        audio = _apply_gain(audio, input_gain)
        if STT_MIN_ENERGY > 0.0 and _audio_energy(audio) < STT_MIN_ENERGY:
            if _DEBUG:
                print(
                    f"[subtitles] skip STT (energy {_audio_energy(audio):.1f} < {STT_MIN_ENERGY})",
                    file=sys.stderr,
                )
            return
        text: str | None = None
        if STT_BACKEND == "whisper":
            try:
                text = transcribe_with_whisper(audio)
            except Exception as e:
                with state_lock:
                    last_error[0] = f"whisper: {e}"
                return
            if not text:
                now = time.time()
                if now - last_unknown_at[0] >= 5.0:
                    last_unknown_at[0] = now
                    print(
                        "Whisper returned no text for that phrase (too short/quiet?). "
                        "Try: SUBTITLE_INPUT_GAIN=3  SUBTITLE_WHISPER_VAD=0  SUBTITLE_DEBUG=1",
                        file=sys.stderr,
                    )
                return
        else:
            try:
                text = _recognize_google_with_retries(recognizer, audio)
            except sr.UnknownValueError:
                now = time.time()
                if now - last_unknown_at[0] >= 5.0:
                    last_unknown_at[0] = now
                    print(
                        "Could not transcribe that phrase (unclear/quiet). "
                        "Try: SUBTITLE_INPUT_GAIN=3  SUBTITLE_DEBUG=1  SUBTITLE_MIC_DEVICE=<index>",
                        file=sys.stderr,
                    )
                return
            except sr.RequestError as e:
                with state_lock:
                    last_error[0] = str(e)
                return
        with state_lock:
            last_error[0] = None
        safe = sanitize_for_display(text)
        if ECHO_TRANSCRIPTS:
            print(f"Transcribed: {safe[:200]}", flush=True)
        typing_gen[0] += 1
        display_queue.put((safe, typing_gen[0]))

    if STT_BACKEND not in ("google", "whisper"):
        print(f"Unknown SUBTITLE_STT_BACKEND={STT_BACKEND!r} (use google or whisper).", file=sys.stderr)
        sys.exit(1)
    if STT_BACKEND == "whisper":
        print(
            f"Loading Whisper ({WHISPER_MODEL}, {WHISPER_DEVICE}/{WHISPER_COMPUTE}); "
            "first run may download model weights...",
            flush=True,
        )
        try:
            with _whisper_lock:
                _load_whisper_model()
        except Exception as e:
            print(f"Failed to load Whisper: {e}", file=sys.stderr)
            sys.exit(1)

    print("Calibrating for ambient noise (stay quiet for a moment)...")
    if _DEBUG:
        _print_input_devices()
    print(
        f"Mic: {_input_device_label(input_dev)}  capture={rec_sr}Hz  ch={cap_ch}  input_gain={input_gain}  "
        f"STT: {STT_BACKEND}",
        flush=True,
    )
    app = _python_org_app_bundle()
    if app:
        print(f"If mic still silent: enable Microphone for Python.app → {app}", flush=True)

    phrase_queue: queue.Queue[sr.AudioData] = queue.Queue(maxsize=PHRASE_QUEUE_MAX)

    consumer = threading.Thread(
        target=_phrase_consumer_loop,
        args=(phrase_queue, on_phrase, stop_event),
        name="phrase-consumer",
        daemon=True,
    )
    consumer.start()

    display_worker = threading.Thread(
        target=_display_worker_loop,
        args=(display_queue, typing_gen, state_lock, last_error, stop_event),
        name="display-worker",
        daemon=True,
    )
    display_worker.start()

    worker = threading.Thread(
        target=_mic_capture_thread,
        args=(phrase_queue, state_lock, last_error, stop_event, input_dev, rec_sr, cap_ch),
        name="mic-capture",
        daemon=True,
    )
    worker.start()

    try:
        icon_ok = upload_app_icon()
        send_placeholder_draw(show_icon=icon_ok)
    except requests.RequestException as e:
        print(
            f"Cannot reach BUSY Bar at {DEVICE} ({e}). "
            "Check USB or set BUSY_BAR_HOST; mic will still work when speech is recognized.",
            file=sys.stderr,
        )
    type_info = f"type_delay: {TYPE_DELAY}s" if TYPE_DELAY > 0.0 else "type_delay: 0 (instant)"
    print(
        f"Subtitles running. BUSY Bar: {DEVICE}  app_id: {APP_ID}  display: {DISPLAY}  "
        f"draw_priority: {DRAW_PRIORITY_LIVE}  lang: {SPEECH_LANGUAGE}  "
        f"stt: {STT_BACKEND}"
        + (f"  whisper_model: {WHISPER_MODEL}" if STT_BACKEND == "whisper" else "")
        + f"  {type_info}",
    )
    print("Ctrl+C to stop (clears this app's draw).")

    try:
        while True:
            time.sleep(0.5)
            err = None
            with state_lock:
                err = last_error[0]
            if err:
                print("Error:", err, file=sys.stderr)
                with state_lock:
                    last_error[0] = None
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        stop_event.set()
        display_queue.put(None)
        worker.join(timeout=3.0)
        consumer.join(timeout=10.0)
        display_worker.join(timeout=3.0)
        if CLEAR_ON_EXIT:
            clear_display()
        else:
            print("[subtitles] SUBTITLE_CLEAR_ON_EXIT=0 — left last draw on the bar.", file=sys.stderr, flush=True)


if __name__ == "__main__":
    if "--test-mic" in sys.argv:
        run_test_mic()
    else:
        main()
