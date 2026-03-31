# Busylib-py Code Overview

## Project Summary
**busylib-py** is a Python library for controlling the **Busy Bar** device - a hardware gadget with dual displays (front and back). The library provides both synchronous and asynchronous clients for interacting with the device's API.

## What is Busy Bar?
Busy Bar is a physical device with:
- **Dual displays** (front and back screens)
- **Hardware controls** (Up, Down, OK/Skip, Back buttons)
- **Network connectivity** (WiFi, USB)
- **Audio capabilities**
- **Storage** for assets (images, audio files)
- **Cloud connectivity** option

## Project Structure

### Core Library (`src/busylib/`)
The main library providing device control functionality:

#### Client Modules (`src/busylib/client/`)
- `base.py` - Base HTTP client with API communication
- `busy.py` - Main BusyBar and AsyncBusyBar client classes
- `display.py` - Display control (drawing text/images)
- `audio.py` - Audio playback control
- `storage.py` - File system operations
- `assets.py` - Asset upload/management
- `input.py` - Input key forwarding
- `wifi.py` - WiFi configuration
- `ble.py` - Bluetooth functionality
- `usb.py` - USB operations
- `firmware.py` - Firmware updates
- `updater.py` - Software updates
- `time.py` - Time synchronization
- `access.py` - Device access control
- `account.py` - Account management

#### Converter Modules (`src/busylib/converter/`)
- `image.py` - Image format conversion for display
- `audio.py` - Audio format conversion
- `video.py` - Video processing

#### Feature Modules (`src/busylib/features/`)
- `app_assets.py` - Application asset management
- `dashboard.py` - Device status information (DeviceSnapshot)

#### Core Files
- `types.py` - Data models and enums (InputKey, DisplayName, etc.)
- `display.py` - Display specifications and helpers
- `exceptions.py` - Custom exception classes
- `settings.py` - Configuration settings
- `versioning.py` - Version management

### Remote Example (`examples/remote/`)
A powerful terminal-based UI for streaming the device's screen to your console and controlling it remotely.

#### Key Files
- `main.py` - Entry point with argument parsing
- `runner.py` - Main streaming loop coordinator
- `renderers.py` - Terminal rendering with RGB pixel display
- `keymap.py` - Keyboard input mapping and forwarding
- `command_plugins.py` - Command implementations
- `commands.py` - Command registry and parsing
- `periodic_tasks.py` - Background tasks (dashboard updates, link checks)
- `settings.py` - Configuration via environment variables
- `constants.py` - Icon sets (emoji, nerd fonts, text), messages
- `terminal_utils.py` - Terminal control utilities

## Remote Demo Features

### Display Streaming
The remote demo can:
- Stream device screen via **WebSocket** (real-time) or **HTTP polling** (slower)
- Render RGB pixel data in the terminal using colored characters
- Support **front and back displays** with Tab key switching
- Display frames with customizable borders and colors
- Auto-detect terminal size and warn if too small

### Keyboard Controls

#### Navigation
- **Up/Down** - Navigate menus on device
- **Right** - OK/Skip button
- **Left** - Back button
- **Enter** - OK button
- **Esc** - Back button
- **Space** - Start button

#### Display & Mode Switching
- **Tab** - Switch between front and back displays
- **Ctrl+A** - Apps mode
- **Ctrl+B** - BUSY mode
- **Ctrl+P** - Settings mode

#### Other
- **h** - Show help overlay
- **Ctrl+Q** - Quit the application
- **:** - Enter command mode (vim-style)

### Command Mode
Type `:` to enter command mode and execute commands:

- `:text <message>` - Display scrolling text on front screen
- `:clear` - Clear the display
- `:clock` - Show clock on display
- `:audio <action>` - Audio control (play/stop/volume)
- `:call <api_method>` - Call any device API method
- `:quit` - Exit the application

### Status Dashboard
The UI displays real-time device information:
- **Device name**
- **System uptime**
- **Storage usage** (used/total)
- **Time** (local device time)
- **Brightness** (front/back)
- **Volume**
- **WiFi status** with signal strength icons
- **Battery level** with charging indicator
- **USB connection** status
- **Cloud link** status with user info
- **Update availability** indicator

### Icon Modes
Three display modes for status icons:
1. **nerd** - Nerd Fonts icons (requires font-sauce-code-pro-nerd-font)
2. **emoji** - Unicode emoji
3. **text** - ASCII text labels

## Architecture Highlights

### Async-First Design
- Uses `httpx` for HTTP/WebSocket communication
- `AsyncBusyBar` class for non-blocking operations
- Concurrent task management with `asyncio`

### Display Rendering
The renderer converts RGB byte data into terminal output:
```
RGB bytes (width × height × 3) → Colored terminal characters
```
- Uses ANSI escape codes for 24-bit true color
- Customizable pixel characters and spacing
- Frame decorations with configurable colors

### Key Forwarding
- Reads raw terminal input in non-canonical mode
- Decodes escape sequences (arrow keys, function keys)
- Maps to device `InputKey` enum
- Forwards via `/api/input` endpoint

### Periodic Tasks
Background tasks run at different intervals:
- Dashboard update: 1 second
- Cloud link check: 10 seconds
- Update check: 3600 seconds (1 hour)

### Command System
Modular command architecture:
- `CommandBase` abstract class
- `CommandRegistry` for registration
- `CommandArgumentParser` with help support
- Support for aliases (e.g., `q` for `quit`)

## Installation & Setup

### Prerequisites
```bash
# Install UV package manager
brew install uv

# Install Nerd Font for icons
brew install font-sauce-code-pro-nerd-font
```

### Terminal Configuration
For best results, configure your terminal:
- **Background**: Black
- **Font**: SauceCodePro Nerd Font
- **Size**: Large enough for display (check help for requirements)

### Running the Demo
```bash
# Basic usage (requires device address)
uv run python -m examples.remote --addr <device-ip>

# With authentication token
uv run python -m examples.remote --addr <device-ip> --token <bearer-token>

# HTTP polling mode (for cloud/slower connections)
uv run python -m examples.remote --addr <device-ip> --http-poll-interval 1.0

# Customize appearance
uv run python -m examples.remote --addr <device-ip> \
    --spacer "  " \
    --frame full \
    --frame-color "#FF00FF"

# View-only mode (no keyboard forwarding)
uv run python -m examples.remote --addr <device-ip> --no-send-input
```

## Device API Capabilities

### Display Control
- Draw text with multiple fonts and alignments
- Display images (PNG format)
- Scrolling text support
- Multi-element composition
- Per-display targeting (front/back)

### Audio
- Upload audio files (WAV format)
- Play/stop audio
- Volume control
- Audio status queries

### Storage
- File read/write operations
- Directory management
- File listing with metadata
- Recursive deletion

### Assets
- Upload app-specific assets
- Asset deletion per app
- Image/audio file management

### Input Simulation
- Send button presses remotely
- Support all device buttons
- Hotkey triggers (BUSY, APPS, SETTINGS)

### System Info
- Version information
- Device status (uptime, battery, WiFi)
- Storage capacity
- Brightness levels
- Network configuration

## Development Notes

### Fixed Issues
1. **Missing `__init__.py` files** - Added package markers for `examples/` and `examples/remote/`
2. **Missing `__main__.py`** - Created entry point for `python -m examples.remote`
3. **InputKey.STATUS removed** - Removed obsolete F2 key mapping from keymap

### Environment Variables
Configure via `BUSYBAR_REMOTE_*` prefix:
- `BUSYBAR_REMOTE_ICON_MODE` - Icon set (nerd/emoji/text)
- `BUSYBAR_REMOTE_SPACER` - Pixel spacing
- `BUSYBAR_REMOTE_FRAME_MODE` - Frame style
- `BUSYBAR_REMOTE_FRAME_COLOR` - Frame color (hex)

### Testing
```bash
# Run test suite
make test

# Install dev dependencies
make install-dev
```

## Use Cases

### Remote Monitoring
Stream device display to terminal for remote debugging or monitoring

### Development & Testing
Test display layouts and content without physical device access

### Automation
Control device programmatically via API commands

### Asset Management
Upload and manage device assets remotely

### Live Demos
Share device screen during presentations or demonstrations

## Technology Stack
- **Python 3.10+** (uses modern async/await)
- **httpx** - HTTP client with HTTP/2 and WebSocket support
- **websockets** - WebSocket protocol
- **Pillow** - Image processing
- **Pydantic** - Data validation and settings
- **termios/tty** - Terminal control (Unix-only)

## Documentation Links
- GitHub: https://github.com/busy-app/busylib-py
- PyPI: https://pypi.org/project/busylib/
- Docs: https://busylib.readthedocs.io

---

*This overview was generated by analyzing the busylib-py codebase on Feb 10, 2026*
