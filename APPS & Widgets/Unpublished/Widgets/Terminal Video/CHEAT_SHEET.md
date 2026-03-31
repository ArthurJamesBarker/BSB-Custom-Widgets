# Busylib Remote Demo - Cheat Sheet

## Prerequisites
```bash
export BUSY_API_VERSION=4.1.0
cd "/Users/barker/Documents/General/Random Tests/busylib-py-main"
```

## Quick Commands

### View-Only (Works Anywhere)
```bash
./run_demo.sh 10.0.4.20 --no-send-input --spacer ""
```

### Interactive (Terminal.app/iTerm2 only)
```bash
./run_demo.sh 10.0.4.20
```

### HTTP Polling (Slow/Remote Connections)
```bash
./run_demo.sh 10.0.4.20 --http-poll-interval 1.0
```

### Full Options
```bash
export BUSY_API_VERSION=4.1.0
uv run python -m examples.remote \
    --addr 10.0.4.20 \
    --no-send-input \
    --spacer "" \
    --frame horizontal \
    --frame-color "#00FF00" \
    --log-level DEBUG \
    --log-file /tmp/remote.log
```

## Keyboard Controls

```
Navigation:         Display:            Modes:
  ↑↓  - Scroll       Tab     - Switch    Ctrl+A - Apps
  →   - OK           h       - Help      Ctrl+B - BUSY
  ←   - Back         :       - Command   Ctrl+P - Settings
  ⏎   - OK           Ctrl+Q  - Quit
  Esc - Back
```

## Command Mode (Press :)

```bash
:text Hello                    # Simple text
:text --font big Welcome       # Big font
:text --align center Hi        # Centered
:text --scroll-rate 500 Long message goes here
:clear                         # Clear display
:clock                         # Show clock
:audio play file.wav           # Play audio
:audio stop                    # Stop audio
:audio volume 75               # Set volume
:call get_status               # API call
:api get_version               # API call
:quit                          # Exit (:q)
```

## Device API (curl)

```bash
# Version
curl http://10.0.4.20/api/version | jq

# Status
curl http://10.0.4.20/api/status | jq

# Device name
curl http://10.0.4.20/api/name | jq

# Screen capture (front=0, back=1)
curl "http://10.0.4.20/api/screen?display=0" -o frame.bmp

# Clear display
curl -X POST http://10.0.4.20/api/display/clear

# Simple text
curl -X POST http://10.0.4.20/api/display/draw \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "test",
    "elements": [{
      "id": "text1",
      "x": 0,
      "y": 8,
      "text": "Hello!",
      "display": "front"
    }]
  }'
```

## Test Device
```bash
export BUSY_API_VERSION=4.1.0
uv run python test_device.py
```

## Common Issues

| Issue | Solution |
|-------|----------|
| "Operation not supported" | Add `--no-send-input` |
| "API version mismatch" | `export BUSY_API_VERSION=4.1.0` |
| "Terminal too small" | Add `--spacer ""` |
| WebSocket fails | Add `--http-poll-interval 0.5` |
| No display | Check `ping 10.0.4.20` |

## Environment Variables

```bash
# Set in ~/.zshrc for persistence
export BUSY_API_VERSION=4.1.0
export BUSYBAR_REMOTE_ICON_MODE=nerd     # or emoji, text
export BUSYBAR_REMOTE_SPACER=" "
export BUSYBAR_REMOTE_FRAME_MODE=horizontal  # or full, none
export BUSYBAR_REMOTE_FRAME_COLOR="#00FF00"
```

## Display Sizes

| Display | Size | With Spacer | No Spacer |
|---------|------|-------------|-----------|
| Front | 72x16 | 143x18 | 72x16 |
| Back | 160x80 | 319x82 | 160x80 |

## Icon Modes

```bash
# Nerd Fonts (requires font-sauce-code-pro-nerd-font)
export BUSYBAR_REMOTE_ICON_MODE=nerd

# Emoji (works anywhere)
export BUSYBAR_REMOTE_ICON_MODE=emoji

# Text (ASCII only)
export BUSYBAR_REMOTE_ICON_MODE=text
```

## Quick Python Usage

```python
import os
os.environ['BUSY_API_VERSION'] = '4.1.0'

from busylib import AsyncBusyBar
import asyncio

async def main():
    async with AsyncBusyBar("10.0.4.20") as bb:
        # Get version
        version = await bb.get_version()
        print(f"API: {version.api_semver}")
        
        # Get name
        name = await bb.get_device_name()
        print(f"Device: {name.name}")
        
        # Get status
        status = await bb.get_status()
        print(f"Uptime: {status.system.uptime}")
        print(f"Battery: {status.power.battery_charge}%")
        
        # Get screen frame
        from busylib import display
        frame = await bb.get_screen_frame(
            display.FRONT_DISPLAY.index
        )
        print(f"Frame: {len(frame)} bytes")

asyncio.run(main())
```

## Files Reference

| File | Purpose |
|------|---------|
| `SESSION_SUMMARY.md` | Complete session overview |
| `FIXES_AND_USAGE.md` | All bugs fixed + solutions |
| `CODE_OVERVIEW.md` | Project architecture |
| `QUICK_START.md` | User guide |
| `CHEAT_SHEET.md` | This file |
| `run_demo.sh` | Convenience script |
| `test_device.py` | Connection test |

## Recovery Mode

If device is bricked:

1. Hold **Start** + **Back** for 3+ seconds
2. Release **Back**
3. Release **Start**
4. Go to https://recovery.dev.busy.app/
5. Select recovery firmware
6. Click Install

## Device URLs

- Web Interface: http://10.0.4.20/
- API Docs: http://10.0.4.20/docs/
- OpenAPI: http://10.0.4.20/openapi.yaml
- Recovery: https://recovery.dev.busy.app/

---

**Device**: BB Arthur Studio (10.0.4.20)  
**Firmware**: r504 (dev)  
**API**: 4.1.0
