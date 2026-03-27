"""
Offline fake bus arrivals for the BUSY Bar when TfL (or network) is unavailable.

Uses the same layout and draw path as `buses.py` — run from this folder:
  python buses_fake.py

Edit MOCK_ROUTES and _CYCLE below to change lines/destinations and how fast times repeat.
"""
import time

import buses as _bus

# Match buses.py (or set a smaller value while testing)
POLL_INTERVAL = _bus.POLL_INTERVAL

# Simulated routes (TfL-shaped). Only lineName + destinationName are required here.
_MOCK_ROW = {"lineName": "286", "destinationName": "Sidcup, Queen Mary's Hospital"}
MOCK_ROUTES = [_MOCK_ROW, dict(_MOCK_ROW)]

# Per-row cycle length (seconds) for countdown before wrapping (loops indefinitely).
_CYCLE = (14 * 60, 18 * 60)

_FAKE_START = time.time()


def mock_arrivals():
    """Return two fake predictions with decreasing timeToStation (no network)."""
    elapsed = time.time() - _FAKE_START
    out = []
    for i, base in enumerate(MOCK_ROUTES[:2]):
        cycle = _CYCLE[i] if i < len(_CYCLE) else 15 * 60
        raw = cycle - (elapsed % cycle)
        secs = int(max(5, raw))
        row = dict(base)
        row["timeToStation"] = secs
        out.append(row)
    return out


def main():
    print("[FAKE] buses_fake.py — no TfL API; edit MOCK_ROUTES in this file to change text.")
    last_sig = None
    while True:
        try:
            arrivals = mock_arrivals()
            sig = _bus.display_signature(arrivals)
            if sig != last_sig:
                last_sig = sig
                elements = _bus.format_arrival_elements(arrivals)
                for e in elements:
                    if e.get("type") == "text":
                        print(f"{e['text']:>20}")
                _bus.send_to_display(elements)
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
