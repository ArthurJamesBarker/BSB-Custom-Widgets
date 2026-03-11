# Premiere Pro Timeline Timecode Display

A CEP (Common Extensibility Platform) extension for Adobe Premiere Pro that displays the current playhead timecode in a standalone web browser window with real-time updates.

> **Note:** Adobe has moved to UXP (Unified Extensibility Platform) as the new standard. This plugin uses CEP (still supported through September 2026). For UXP development, see [UXP_SETUP.md](UXP_SETUP.md).

## Features

- **Real-time timecode display** - Shows current playhead position as you scrub the timeline
- **Standalone web client** - Beautiful, modern web interface that runs in any browser
- **BUSY Bar OLED support** - Display timecode on a 72×16px BUSY Bar OLED screen
- **WebSocket communication** - Low-latency updates via WebSocket (with HTTP polling fallback)
- **Auto-reconnect** - Automatically reconnects if connection is lost
- **Sequence information** - Displays sequence name, frame rate, and time in seconds

## Architecture

```
┌─────────────────────┐     WebSocket/HTTP      ┌──────────────────────┐
│   Premiere Pro      │ ──────────────────────► │  Standalone Browser  │
│   (CEP Panel)       │    localhost:8080      │   (HTML Page)        │
│                     │                         │                      │
│ - ExtendScript API  │                         │  - Timecode Display  │
│ - HTTP/WS Server    │                         │  - Connection Status │
│ - Playhead Monitor  │                         │  - Auto-reconnect    │
└─────────────────────┘                         └──────────────────────┘
```

## Installation

### Step 1: Install CEP Extension

1. **Locate the CEP extensions folder:**

   - **macOS:** `~/Library/Application Support/Adobe/CEP/extensions/`
   - **Windows:** `%APPDATA%\Adobe\CEP\extensions\`

2. **Copy the extension folder:**
   ```bash
   # macOS
   cp -r "com.ppro.timeline" ~/Library/Application\ Support/Adobe/CEP/extensions/
   
   # Windows (PowerShell)
   xcopy /E /I "com.ppro.timeline" "%APPDATA%\Adobe\CEP\extensions\com.ppro.timeline"
   ```

3. **Enable CEP debugging (required for unsigned extensions):**

   Create or edit the debug configuration file:

   - **macOS:** `~/Library/Application Support/Adobe/CEP/extensions/.debug`
   - **Windows:** `%APPDATA%\Adobe\CEP\extensions\.debug`

   Copy the contents from `com.ppro.timeline/.debug` to this file, or merge the extension ID:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <ExtensionList>
       <Extension Id="com.ppro.timeline.panel">
           <HostList>
               <Host Name="PPRO" Port="8093"/>
           </HostList>
       </Extension>
   </ExtensionList>
   ```

4. **Enable unsigned extensions (macOS only):**

   Run this command in Terminal:
   ```bash
   defaults write com.adobe.CSXS.7 PlayerDebugMode 1
   defaults write com.adobe.CSXS.8 PlayerDebugMode 1
   defaults write com.adobe.CSXS.9 PlayerDebugMode 1
   defaults write com.adobe.CSXS.10 PlayerDebugMode 1
   ```

   For Windows, edit the registry:
   ```
   HKEY_CURRENT_USER\Software\Adobe\CSXS.7
   HKEY_CURRENT_USER\Software\Adobe\CSXS.8
   HKEY_CURRENT_USER\Software\Adobe\CSXS.9
   HKEY_CURRENT_USER\Software\Adobe\CSXS.10
   
   Add DWORD: PlayerDebugMode = 1
   ```

### Step 2: Open the Extension in Premiere Pro

1. Launch Adobe Premiere Pro
2. Go to **Window** → **Extensions** → **Premiere Pro Timeline Timecode**
3. The CEP panel should open

### Step 3: Open the Web Client

1. Open `web-client/index.html` in your web browser
   - You can double-click the file, or
   - Open it via File → Open in your browser
2. Click the **Connect** button (or it will auto-connect)

### Step 4: Start the Server

1. In the CEP panel inside Premiere Pro, click **Start Server**
2. The status should change to "Running on port 8080"
3. The web client should automatically connect and start displaying timecode

## Usage

### Basic Usage (Web Client)

1. **Start Premiere Pro** and open a project with a sequence
2. **Open the CEP panel** (Window → Extensions → Premiere Pro Timeline Timecode)
3. **Click "Start Server"** in the CEP panel
4. **Open the web client** (`web-client/index.html`) in your browser
5. **Scrub the timeline** in Premiere Pro - the timecode will update in real-time in the browser

### BUSY Bar OLED Display

Display timecode on a BUSY Bar 72×16px OLED screen:

1. **Start the Python server** (if not already running):
   ```bash
   python3 server.py
   ```

2. **Start the BUSY Bar client**:
   ```bash
   # Set your BUSY Bar IP (default: 10.0.4.20)
   export BUSY_BAR_IP="10.0.4.20"
   python3 busy_bar_client.py
   ```

3. **Start the Premiere Pro plugin** (as described above)

The timecode will automatically appear on the BUSY Bar display and update in real-time.

For detailed BUSY Bar setup instructions, see [BUSY_BAR_SETUP.md](BUSY_BAR_SETUP.md).

## Troubleshooting

### Extension doesn't appear in Premiere Pro

- Make sure the extension is in the correct CEP extensions folder
- Verify the `.debug` file is in place
- Check that PlayerDebugMode is enabled (macOS: run the defaults commands, Windows: check registry)
- Restart Premiere Pro after making changes

### Web client can't connect

- Make sure the CEP panel is open and the server is started
- Check that port 8080 is not in use by another application
- Try clicking "Disconnect" and then "Connect" again
- Check browser console for error messages (F12)

### Timecode shows "No active sequence"

- Make sure you have a sequence open in Premiere Pro
- The sequence must be the active sequence (click on it in the timeline)

### WebSocket connection fails

- The extension will automatically fall back to HTTP polling if WebSocket is unavailable
- HTTP polling works without any additional dependencies
- Both methods provide real-time updates

## Technical Details

### API Usage

The extension uses the following Premiere Pro ExtendScript API:

- `app.project.activeSequence` - Get the current sequence
- `sequence.getPlayerPosition()` - Get playhead position as Time object
- `Time.getFormatted(frameRate, displayFormat)` - Format timecode string
- `sequence.timebase` - Get frame duration
- `sequence.videoDisplayFormat` - Get display format (24fps, 29.97df, etc.)

### Communication Protocol

- **Primary:** WebSocket on `ws://localhost:8080`
- **Fallback:** HTTP polling on `http://localhost:8080/timecode`
- **Update rate:** 100ms (10 updates per second)

### File Structure

```
Premiere Pro Timeline/
├── com.ppro.timeline/          # CEP Extension
│   ├── CSXS/
│   │   └── manifest.xml        # Extension manifest
│   ├── js/
│   │   └── main.js             # CEP panel JavaScript
│   ├── jsx/
│   │   └── timeline.jsx        # ExtendScript (not used directly)
│   ├── index.html              # CEP panel UI
│   └── .debug                  # Debug configuration
├── web-client/                 # Standalone Web Client
│   ├── index.html              # Web page
│   └── client.js               # WebSocket/HTTP client
└── README.md                   # This file
```

## Development

### Testing Changes

1. Make changes to the extension files
2. Reload the CEP panel (close and reopen, or restart Premiere Pro)
3. Use browser DevTools (F12) in the web client for debugging

### Modifying the Port

To change the port from 8080:

1. Edit `com.ppro.timeline/js/main.js` - change the `port` variable
2. Edit `web-client/client.js` - change `wsUrl` and `httpUrl`

## License

This project is for educational purposes. All Premiere Pro API content is copyright Adobe Systems Incorporated.

## Credits

Built using the [Premiere Pro Scripting Guide](https://ppro-scripting.docsforadobe.dev/)

