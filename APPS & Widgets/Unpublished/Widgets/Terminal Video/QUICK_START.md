# Quick Start Guide - Busylib Remote Demo

## What This Does
The remote demo streams your Busy Bar device's screen to your terminal in real-time and lets you control it with your keyboard.

## ⚠️ Important Notes
- **API Version**: Device runs API 4.1.0. Set `export BUSY_API_VERSION=4.1.0` before running.
- **Interactive vs Non-Interactive**: Keyboard controls require a real interactive terminal (Terminal.app, iTerm2). Use `--no-send-input` for Cursor or non-interactive environments.
- **Terminal Size**: Default spacing requires large terminals (143x18 for front display). Use `--spacer ""` for compact output.

## Setup (Done! ✓)
```bash
✓ brew install uv
✓ brew install font-sauce-code-pro-nerd-font
✓ Fixed missing package files
✓ Fixed keymap bug
```

## Terminal Setup (Manual)
Open your Terminal/iTerm preferences and set:
- **Background color**: Black
- **Font**: SauceCodePro Nerd Font (or SauceCodePro Nerd Font Mono)
- **Font size**: 12pt or larger
- **Minimum terminal size**: 80x24 (larger recommended)

## Running the Demo

**IMPORTANT**: Set the API version first:
```bash
export BUSY_API_VERSION=4.1.0
```

### Basic Usage
```bash
# You need a Busy Bar device's IP address
uv run python -m examples.remote --addr 192.168.1.100

# Or use the wrapper script that sets API version automatically
./run_demo.sh 192.168.1.100
```

### View-Only Mode (recommended for Cursor/non-interactive terminals)
```bash
export BUSY_API_VERSION=4.1.0
uv run python -m examples.remote --addr 192.168.1.100 --no-send-input
```

### With Cloud Token
```bash
uv run python -m examples.remote --addr busy-cloud-url.com --token YOUR_TOKEN
```

### HTTP Polling Mode (Slower Connections)
```bash
uv run python -m examples.remote --addr 192.168.1.100 --http-poll-interval 1.0
```

### View All Options
```bash
uv run python -m examples.remote --help
```

## Keyboard Controls

### Navigation Keys
| Key | Action |
|-----|--------|
| **↑** | Scroll Up / Navigate Up |
| **↓** | Scroll Down / Navigate Down |
| **→** or **Enter** | OK / Skip / Select |
| **←** or **Esc** | Back / Cancel |
| **Space** | Start Button |

### Mode Switching
| Key | Action |
|-----|--------|
| **Tab** or **Ctrl+R** | Switch Front ↔ Back Display |
| **Ctrl+A** | Apps Mode |
| **Ctrl+B** | BUSY Mode |
| **Ctrl+P** | Settings Mode |

### Application Controls
| Key | Action |
|-----|--------|
| **h** or **H** | Show/Hide Help Overlay |
| **Ctrl+Q** | Quit Application |
| **:** | Enter Command Mode |

## Command Mode

Press **:** to enter command mode (like vim). Available commands:

### Text Commands
```
:text Hello World              # Display text on screen
:text --font big Hello         # Big font
:text --align center Hi        # Centered text
:t Quick message              # Shorthand (t = text)
```

### Display Commands
```
:clear                        # Clear the display
:clock                        # Show clock
```

### Audio Commands
```
:audio play sound.wav         # Play audio file
:audio stop                   # Stop audio
:audio volume 50              # Set volume to 50%
```

### API Commands
```
:call get_status              # Call any API method
:call get_version             # Get device version
:api get_status               # Same as :call
```

### Application Commands
```
:quit                         # Exit (or :q, :exit)
```

## Status Bar Legend

The top info bar shows device status with icons:

### With Nerd Fonts
- **󰌢** - Device name
- **** - System info (uptime)
- **󰋊** - Storage (used/total)
- **** - Current time
- **󰃟** - Display brightness
- **** - Audio volume
- **󰤟/󰤢/󰤥** - WiFi signal (low/mid/high)
- **** - Battery full
- **** - Battery low
- **** - USB connected
- **** - USB disconnected
- **󰌷** - Cloud link active
- **󰌸** - Cloud link inactive
- **󰏔** - Update available

### With Emoji (fallback)
- **📟** - Device name
- **🛠** - System info
- **💾** - Storage
- **⏰** - Time
- **💡** - Brightness
- **🔊** - Volume
- **📶** - WiFi
- **🔋** - Battery full
- **🪫** - Battery low
- **🔌** - USB connected
- **❌** - USB disconnected
- **🔗** - Cloud link
- **⬆️** - Update available

## Display Frame Modes

Control how the display is framed:

```bash
# No frame
uv run python -m examples.remote --addr 192.168.1.100 --frame none

# Horizontal lines only (default)
uv run python -m examples.remote --addr 192.168.1.100 --frame horizontal

# Full border
uv run python -m examples.remote --addr 192.168.1.100 --frame full

# Custom frame color
uv run python -m examples.remote --addr 192.168.1.100 --frame-color "#FF00FF"
```

## Pixel Spacing

Adjust spacing between pixels for better visibility:

```bash
# No spacing (default: single space)
uv run python -m examples.remote --addr 192.168.1.100 --spacer ""

# Double spacing
uv run python -m examples.remote --addr 192.168.1.100 --spacer "  "

# Custom character
uv run python -m examples.remote --addr 192.168.1.100 --spacer "·"
```

## Logging

```bash
# Enable verbose logging to file
uv run python -m examples.remote --addr 192.168.1.100 \
    --log-level DEBUG \
    --log-file remote.log

# View logs in another terminal
tail -f remote.log
```

## View-Only Mode

Watch the screen without sending keyboard input:

```bash
uv run python -m examples.remote --addr 192.168.1.100 --no-send-input
```

## Custom Keymap

Create a custom keymap JSON file:

```json
{
    "keymap": {
        "w": "up",
        "s": "down",
        "d": "ok",
        "a": "back"
    },
    "help": ["f1"],
    "exit": ["ctrl+q"]
}
```

Use it:
```bash
uv run python -m examples.remote --addr 192.168.1.100 --keymap-file my_keys.json
```

## Environment Variables

Configure defaults via environment:

```bash
export BUSYBAR_REMOTE_ICON_MODE=emoji
export BUSYBAR_REMOTE_SPACER="  "
export BUSYBAR_REMOTE_FRAME_MODE=full
export BUSYBAR_REMOTE_FRAME_COLOR="#00FF00"

uv run python -m examples.remote --addr 192.168.1.100
```

## Troubleshooting

### "No module named examples.remote"
- Files fixed! Should work now.

### "Connection timeout"
- Check device IP address
- Ensure device is on same network
- Try `ping <device-ip>`

### "Connection refused"
- Verify device API is running
- Check if device requires authentication token

### Colors look wrong
- Ensure terminal supports 24-bit true color
- Try iTerm2, Kitty, or Alacritty
- Enable true color in Terminal preferences

### Icons display as boxes/question marks
- Install Nerd Font: `brew install font-sauce-code-pro-nerd-font`
- Set terminal font to SauceCodePro Nerd Font
- Or use emoji mode: `--icon-mode emoji`
- Or use text mode: `BUSYBAR_REMOTE_ICON_MODE=text`

### Display is cut off
- Increase terminal size (make window larger)
- Reduce font size in terminal preferences
- The app shows size requirements in help

### Keyboard input not working
- Check if `--no-send-input` flag was used
- Verify device API supports input forwarding
- Check logs for connection errors

### Screen not updating
- WebSocket connection may have dropped
- Try HTTP polling mode: `--http-poll-interval 1.0`
- Check network connection stability

## Performance Tips

### Fast Local Network (Recommended)
```bash
# WebSocket mode - real-time updates
uv run python -m examples.remote --addr 192.168.1.100
```

### Slow Network / Cloud Device
```bash
# HTTP polling - 1 frame per second
uv run python -m examples.remote --addr cloud.device.com \
    --token TOKEN \
    --http-poll-interval 1.0
```

### Low CPU Usage
```bash
# Reduce frame rate checking
BUSYBAR_REMOTE_FRAME_SLEEP=0.2 \
uv run python -m examples.remote --addr 192.168.1.100
```

## Example Sessions

### Development & Testing
```bash
# Full featured with logging
uv run python -m examples.remote \
    --addr 192.168.1.100 \
    --log-level DEBUG \
    --log-file debug.log \
    --frame full \
    --frame-color "#00FFFF"
```

### Presentation Mode
```bash
# Clean view, no input
uv run python -m examples.remote \
    --addr 192.168.1.100 \
    --no-send-input \
    --frame none \
    --spacer "  "
```

### Remote Support
```bash
# Control cloud device
uv run python -m examples.remote \
    --addr https://busy.cloud/device/abc123 \
    --token YOUR_TOKEN \
    --http-poll-interval 1.0
```

---

**Ready to go!** Connect a Busy Bar device and start the demo. 🚀

For more details, see `CODE_OVERVIEW.md`
