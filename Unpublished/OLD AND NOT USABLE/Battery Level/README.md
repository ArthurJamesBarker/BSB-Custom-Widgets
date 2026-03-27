# Battery Level (Custom App)

Custom BUSY Bar app that shows one of five battery-level states. You flip between states using the **scroll wheel** (up/down).

## Contents

- **main.lua** — Lua app: draws `1.png`..`5.png`, up = next state, down = previous state.
- **app.json** — App name shown in the APPS menu: "Battery Level".
- **1.png … 5.png** — Your five battery-level images (72×16 or similar).
- **upload_to_device.py** — Deploys the app to the device.

## Deploy

1. Device on and reachable (USB: `10.0.4.20`, or your Wi‑Fi IP).
2. From this folder run:
   ```bash
   python3 upload_to_device.py
   ```
   Or with a custom IP:
   ```bash
   python3 upload_to_device.py 192.168.1.100
   ```
3. On the BUSY Bar: switch to **APPS** → select **Battery Level**.

## Use

- **Scroll up** — next state (1 → 2 → … → 5 → 1).
- **Scroll down** — previous state (1 → 5 → 4 → … → 2 → 1).
- **Back (short press)** — exit to APPS menu.

## Requirements

- Firmware with Lua Custom APPS (e.g. lua-addon build v8+).
- Paths are URL-encoded in the script; no manual encoding needed.
