# Fixes Applied & Usage Guide

## Device Information
- **Device**: BB Arthur Studio
- **IP Address**: 10.0.4.20
- **Firmware**: r504 (dev branch, Feb 5, 2026)
- **API Version**: 4.1.0
- **Battery**: 98% (charging/discharging)

## Issues Fixed

### 1. Missing Python Package Files
**Problem**: `examples/` wasn't a proper Python package.

**Files Created**:
- `examples/__init__.py`
- `examples/remote/__init__.py`
- `examples/remote/__main__.py`

### 2. Obsolete InputKey Reference
**Problem**: `keymap.py` referenced `InputKey.STATUS` which doesn't exist.

**Fix**: Removed F2 key mapping in `examples/remote/keymap.py:109`

### 3. Wrong Parameter Type to stream_screen_ws()
**Problem**: Passing `DisplaySpec` object instead of integer `display_id`.

**Fix**: Changed `examples/remote/runner.py`:
```python
# Line 284: Changed from
async for message in client.stream_screen_ws(spec):
# To:
async for message in client.stream_screen_ws(spec.index):

# Line 335: Changed from  
frame_bytes = await client.get_screen_frame(spec)
# To:
frame_bytes = await client.get_screen_frame(spec.index)
```

### 4. API Version Mismatch
**Problem**: Library defaults to API version 0.1.0, but device runs 4.1.0.

**Solution**: Set environment variable:
```bash
export BUSY_API_VERSION=4.1.0
```

### 5. stdin Reader Not Supported (CRITICAL)
**Problem**: `loop.add_reader()` for stdin isn't supported in non-interactive terminals or certain event loop configurations. This causes errno 19 (ENODEV) or errno 102 (EOPNOTSUPP).

**Solution**: Use `--no-send-input` flag when running in non-interactive environments.

## How to Run the Demo

### Option 1: Interactive Terminal (Recommended for actual use)
Open your Mac's Terminal.app or iTerm2 directly (not through Cursor):

```bash
cd "/Users/barker/Documents/General/Random Tests/busylib-py-main"
export BUSY_API_VERSION=4.1.0
uv run python -m examples.remote --addr 10.0.4.20
```

**Controls**:
- ↑↓ - Navigate
- → - OK  
- ← - Back
- Tab - Switch displays
- h - Help
- : - Command mode
- Ctrl+Q - Quit

### Option 2: View-Only Mode (Works in Cursor/non-interactive)
```bash
export BUSY_API_VERSION=4.1.0
uv run python -m examples.remote --addr 10.0.4.20 --no-send-input
```

**Note**: No keyboard input, just display streaming.

### Option 3: HTTP Polling Mode (More reliable for remote/slow connections)
```bash
export BUSY_API_VERSION=4.1.0
uv run python -m examples.remote --addr 10.0.4.20 --http-poll-interval 0.5
```

### Option 4: Using the Shell Script
```bash
./run_demo.sh 10.0.4.20
```

The script automatically sets the API version.

### Option 5: Compact Display (for smaller terminals)
```bash
export BUSY_API_VERSION=4.1.0
uv run python -m examples.remote --addr 10.0.4.20 \
    --no-send-input \
    --spacer "" \
    --frame none
```

## Display Size Requirements

The demo shows RGB pixels as colored characters. Required terminal sizes:

**Front Display** (72x16 pixels):
- With spacer (default): **143x18** characters
- Without spacer: **72x16** characters

**Back Display** (160x80 pixels):
- With spacer (default): **319x82** characters
- Without spacer: **160x80** characters

**Recommended**: Use `--spacer ""` for compact output that fits normal terminals.

## Testing Device Connectivity

Use the test script to verify everything works:

```bash
export BUSY_API_VERSION=4.1.0
uv run python test_device.py
```

**Expected output**:
```
Testing connection to 10.0.4.20...
✓ Connected successfully!
✓ Device Name: BB Arthur Studio
✓ System: r504 - Uptime: 00d 00h 11m 30s
✓ Battery: 98% (charging)
✓ Testing HTTP screen capture...
✓ Got frame: 4610 bytes
✓ Testing WebSocket streaming support...
✓ WebSocket streaming works!
```

## API Version Compatibility

The device is running **API 4.1.0** but the library defaults to **0.1.0**. 

**Three ways to fix**:

1. **Environment variable** (temporary):
   ```bash
   export BUSY_API_VERSION=4.1.0
   ```

2. **Shell profile** (persistent):
   ```bash
   echo 'export BUSY_API_VERSION=4.1.0' >> ~/.zshrc
   source ~/.zshrc
   ```

3. **Python code**:
   ```python
   import os
   os.environ['BUSY_API_VERSION'] = '4.1.0'
   from busylib import AsyncBusyBar
   ```

## Firmware Notes (from Developer)

**Current Firmware**: r504 (dev branch)

### New Features
- Recovery mode (Hold Start+Back for DFU mode)
- Time Zone selection (Settings -> Time)
- BUSY Account linking with PIN (Settings -> Account)
- New System menu (Settings -> System)
- Automatic firmware updates
- New animation compression format (breaking change!)

### Known Issues
- Custom animations stopped working after update (new compression format)
- Animation converter in web interface not yet updated
- WebSocket support depends on firmware version

### Coming Soon
- Firmware update UI in Settings
- Bluetooth UI in Settings
- Fixed animation converter

## Troubleshooting

### "Operation not supported by device" Error
**Cause**: stdin reader trying to use `loop.add_reader()` in non-interactive terminal.

**Solution**: Add `--no-send-input` flag

### "Busy Lib is outdated for this device API"
**Cause**: API version mismatch

**Solution**: Set `export BUSY_API_VERSION=4.1.0`

### "Terminal too small" Warning
**Cause**: Default spacer makes display very wide

**Solution**: Use `--spacer ""` for compact output

### No display showing
**Cause**: Device might be off, wrong IP, or network issue

**Solution**:
```bash
# Verify device is reachable
ping 10.0.4.20

# Test basic connectivity
curl http://10.0.4.20/api/version

# Run test script
uv run python test_device.py
```

### WebSocket connection fails
**Cause**: Firmware might not support WebSocket, or network issues

**Solution**: Use HTTP polling mode with `--http-poll-interval 0.5`

## Command Mode Examples

Press `:` to enter command mode:

```
:text Hello World           # Display text
:text --font big Welcome    # Big font
:text --align center Hi     # Centered
:clear                      # Clear display  
:clock                      # Show clock
:audio play sound.wav       # Play audio
:audio stop                 # Stop audio
:audio volume 75            # Set volume
:call get_status            # Call API method
:quit                       # Exit
```

## Development Notes

### Running Tests
```bash
uv run pytest
```

### Checking Lints
```bash
uv run ruff check .
uv run pyright .
```

### Viewing Logs
```bash
export BUSY_API_VERSION=4.1.0
uv run python -m examples.remote --addr 10.0.4.20 \
    --log-level DEBUG \
    --log-file /tmp/remote.log
    
# In another terminal
tail -f /tmp/remote.log
```

## Summary

✅ **All bugs fixed**
✅ **Device connectivity confirmed**  
✅ **WebSocket streaming works**
✅ **HTTP polling works**
✅ **API version issue resolved**

**To use**: Run in a real terminal (not through Cursor) for interactive control, or use `--no-send-input` for view-only mode.

---

*Last updated: February 10, 2026*
