#!/usr/bin/env python3
"""
TfL bus arrivals HTTP proxy (for Busy Bar Next Bus app).

Busy Bar Lua can only fetch http:// (no https://). TfL arrivals are HTTPS-only.
Run this on your computer (same Wi‑Fi as the device); the app calls it over HTTP.

Run from this folder:
  python3 server.py

Test:
  curl "http://127.0.0.1:8787/arrivals?stop=490000037S&limit=3"

Optional (TfL higher rate limits):
  export TFL_APP_ID="..." TFL_APP_KEY="..."
  python3 server.py
"""

from __future__ import annotations

import json
import os
import ssl
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# #region agent log
DEBUG_LOG_PATH = "/Users/barker/Documents/Github/BSB-Custom-Widgets/.cursor/debug-4e36b1.log"
def _debug_log(message: str, hypothesis_id: str, data: dict) -> None:
    try:
        payload = {"sessionId": "4e36b1", "runId": "run1", "hypothesisId": hypothesis_id, "location": "server.py", "message": message, "data": data, "timestamp": int(time.time() * 1000)}
        with open(DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass
# #endregion


def _tfl_url(stop_id: str) -> str:
    return f"https://api.tfl.gov.uk/StopPoint/{urllib.parse.quote(stop_id)}/Arrivals"


class Cache:
    def __init__(self, ttl_seconds: int = 25):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, bytes]] = {}

    def get(self, key: str) -> bytes | None:
        item = self._store.get(key)
        if not item:
            return None
        ts, payload = item
        if time.time() - ts > self.ttl:
            self._store.pop(key, None)
            return None
        return payload

    def set(self, key: str, payload: bytes) -> None:
        self._store[key] = (time.time(), payload)


cache = Cache()


class Handler(BaseHTTPRequestHandler):
    server_version = "tfl-bus-proxy/1.0"

    def _send(self, code: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path not in ("/arrivals", "/arrivals/"):
            self._send(
                404,
                b'{"error":"Not found. Use /arrivals?stop=<StopPointId>&limit=8"}',
            )
            return

        qs = urllib.parse.parse_qs(parsed.query)
        stop_id = (qs.get("stop") or [""])[0].strip()
        if not stop_id:
            self._send(400, b'{"error":"Missing required query param: stop"}')
            return

        try:
            limit = int((qs.get("limit") or ["8"])[0])
        except ValueError:
            limit = 8
        limit = max(1, min(16, limit))
        # #region agent log
        _debug_log("arrivals request received", "A", {"stop_id": stop_id, "limit": limit, "client": self.client_address[0] if self.client_address else "?"})
        # #endregion

        app_id = os.getenv("TFL_APP_ID", "").strip()
        app_key = os.getenv("TFL_APP_KEY", "").strip()

        url = _tfl_url(stop_id)
        if app_id and app_key:
            url += f"?app_id={urllib.parse.quote(app_id)}&app_key={urllib.parse.quote(app_key)}"

        cache_key = f"{stop_id}:{limit}:{bool(app_id and app_key)}"
        cached = cache.get(cache_key)
        if cached:
            # #region agent log
            _debug_log("sending cached response", "C", {"status": 200, "body_len": len(cached)})
            # #endregion
            self._send(200, cached)
            return

        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "tfl-bus-proxy/1.0 (+BusyBar)",
                    "Accept": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                    raw = resp.read()
            except Exception as e:
                if "CERTIFICATE_VERIFY_FAILED" not in str(e):
                    raise
                insecure = ssl._create_unverified_context()  # noqa: SLF001
                with urllib.request.urlopen(req, timeout=10, context=insecure) as resp:
                    raw = resp.read()
        except Exception as e:  # pragma: no cover
            msg = json.dumps({"error": "Upstream fetch failed", "detail": str(e)}).encode("utf-8")
            self._send(502, msg)
            return

        try:
            data = json.loads(raw.decode("utf-8"))
            if isinstance(data, list):
                data = data[:limit]
            payload = json.dumps(data, separators=(",", ":")).encode("utf-8")
        except Exception as e:  # pragma: no cover
            msg = json.dumps({"error": "Upstream returned invalid JSON", "detail": str(e)}).encode("utf-8")
            self._send(502, msg)
            return

        cache.set(cache_key, payload)
        # #region agent log
        _debug_log("sending response", "C", {"status": 200, "body_len": len(payload)})
        # #endregion
        self._send(200, payload)

    def log_message(self, fmt: str, *args) -> None:
        return


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8787"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Listening on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
