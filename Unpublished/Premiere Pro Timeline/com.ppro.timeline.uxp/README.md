# Premiere Pro Timeline Timecode - UXP Version

This is the UXP (Unified Extensibility Platform) version of the Premiere Pro Timeline Timecode plugin.

## Installation

### Step 1: Install UXP Developer Tool (UDT)

1. Download UXP Developer Tool from: https://developer.adobe.com/premiere-pro/uxp/
2. Install UDT v2.2 or later

### Step 2: Enable Developer Mode

1. Open Premiere Pro
2. Go to **Settings** → **Plugins**
3. Check **Enable Developer Mode**
4. Restart Premiere Pro

### Step 3: Load the Plugin

1. Open UXP Developer Tool (UDT)
2. Click **"Load Plugin"**
3. Navigate to and select the `com.ppro.timeline.uxp` folder
4. The plugin will appear in Premiere Pro under **Window** → **Extensions** → **Premiere Timeline Timecode**

### Step 4: Open the Web Client

1. Open `web-client/index.html` in your browser
2. Click **Connect** (or it will auto-connect)
3. In the UXP panel, click **Start Server**
4. The timecode will start updating in real-time!

## Development

### Using Cursor

1. Open the plugin folder in Cursor:
   ```bash
   cd com.ppro.timeline.uxp
   cursor .
   ```

2. Edit files in Cursor:
   - `src/main.js` - Main plugin logic
   - `src/panel.html` - Panel UI
   - `src/panel.js` - Panel JavaScript

3. Reload in UDT:
   - Make changes in Cursor
   - Save files
   - Click **Reload** in UDT (or it may auto-reload)

### File Structure

```
com.ppro.timeline.uxp/
├── manifest.json          # Plugin manifest
├── src/
│   ├── main.js            # Main plugin code (direct UXP API access)
│   ├── panel.html          # Panel UI
│   └── panel.js            # Panel JavaScript
└── README.md               # This file
```

## Key Differences from CEP Version

### API Access

**CEP (old):**
```javascript
// Required evalScript bridge
csInterface.evalScript('app.project.activeSequence.getPlayerPosition()', callback);
```

**UXP (new):**
```javascript
// Direct API access
const { app } = require('scenegraph');
const sequence = app.project.activeSequence;
const playerPosition = sequence.getPlayerPosition();
```

### Modern JavaScript

- ES6+ syntax (const, let, arrow functions)
- No evalScript needed
- Better performance
- Direct module imports

## Troubleshooting

### Plugin doesn't appear in Premiere Pro

- Make sure Developer Mode is enabled
- Check that UDT shows the plugin as loaded
- Restart Premiere Pro

### Server won't start

- Check UDT console for errors
- Make sure port 8080 is not in use
- Verify the plugin loaded correctly

### Web client can't connect

- Make sure the server is started in the panel
- Check that port 8080 is accessible
- Try clicking Disconnect then Connect again

## API Reference

The plugin uses the Premiere Pro DOM API:

- `app.project.activeSequence` - Get active sequence
- `sequence.getPlayerPosition()` - Get playhead position
- `Time.getFormatted()` - Format timecode string
- `sequence.timebase` - Get frame rate
- `sequence.videoDisplayFormat` - Get display format

For full API documentation, see: https://developer.adobe.com/premiere-pro/uxp/reference/dom/

