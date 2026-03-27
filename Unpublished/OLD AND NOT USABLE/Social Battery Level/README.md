# Social Battery Level (Custom App)

Custom BUSY Bar app that shows one of five battery levels.
It displays only the battery image for the current level: `N_Battery.png`.

## Contents

- `main.lua` — renders `1_Battery.png` .. `5_Battery.png` and changes level using the scroll wheel.
- `app.json` — App name shown in the APPS menu.
- `1_Battery.png ... 5_Battery.png` — Battery view for each level.

## Deploy

1. Device on and reachable (USB: `10.0.4.20`, or your Wi-Fi IP).
2. From this folder run:
   ```bash
   python3 upload_to_device.py
   ```
   Or with a custom IP:
   ```bash
   python3 upload_to_device.py 192.168.1.100
   ```
3. On the BUSY Bar: switch to **APPS** → select the app.

## Use

- **Scroll up** — next level (1 → 2 → … → 5 → 1).
- **Scroll down** — previous level (1 → 5 → … → 2 → 1).
- **Back (short press)** — exit to APPS menu.

## Requirements

- Firmware with Lua Custom APPS (e.g. lua-addon build v8+).
