# UXP Plugin Installation Guide

## Quick Start

1. **Install UXP Developer Tool (UDT)**
   - Download from: https://developer.adobe.com/premiere-pro/uxp/
   - Or install via Creative Cloud Desktop app

2. **Enable Developer Mode**
   - Open Premiere Pro
   - Settings → Plugins → Enable Developer Mode
   - Restart Premiere Pro

3. **Load Plugin in UDT**
   - Open UXP Developer Tool
   - Click "Load Plugin"
   - Select the `com.ppro.timeline.uxp` folder
   - Plugin appears in Premiere Pro under Window → Extensions

4. **Start the Server**
   - Open the plugin panel in Premiere Pro
   - Click "Start Server"
   - Open `web-client/index.html` in your browser
   - Timecode will update in real-time!

## Using Cursor for Development

1. **Open plugin folder in Cursor:**
   ```bash
   cd com.ppro.timeline.uxp
   cursor .
   ```

2. **Edit files:**
   - `src/main.js` - Main plugin logic
   - `src/panel.html` - Panel UI
   - `src/panel.js` - Panel JavaScript

3. **Reload in UDT:**
   - Make changes in Cursor
   - Save files
   - Click "Reload" in UDT (or auto-reload if enabled)

## Troubleshooting

### Plugin doesn't appear
- Verify Developer Mode is enabled
- Check UDT shows plugin as loaded
- Restart Premiere Pro

### API errors
- Make sure a sequence is open in Premiere Pro
- Check UDT console for error messages
- Verify Premiere Pro version is 25.6 or later

### Server won't start
- Check if port 8080 is in use
- Look at UDT console for errors
- Try restarting the plugin

## File Structure

```
com.ppro.timeline.uxp/
├── manifest.json          # Plugin configuration
├── src/
│   ├── main.js            # Main plugin code
│   ├── panel.html          # Panel UI
│   └── panel.js            # Panel JavaScript
├── README.md               # Plugin documentation
└── INSTALLATION.md         # This file
```

## Next Steps

- See `README.md` for full documentation
- Check UXP_SETUP.md for development setup
- Visit https://developer.adobe.com/premiere-pro/uxp/ for API docs

