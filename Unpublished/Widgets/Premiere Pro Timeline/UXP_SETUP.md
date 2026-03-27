# UXP Development Setup Guide

## CEP vs UXP

**Current Implementation (CEP):**
- Uses ExtendScript (older JavaScript engine)
- Installed to `~/Library/Application Support/Adobe/CEP/extensions/`
- Requires `.debug` file and PlayerDebugMode
- Still supported through September 2026

**New Standard (UXP):**
- Uses modern JavaScript (ES6+)
- Installed via UXP Developer Tool (UDT)
- Better performance and modern APIs
- **Recommended for new development**

## Setting Up UXP Development

### Step 1: Install UXP Developer Tool (UDT)

1. **Download UDT:**
   - Visit: https://developer.adobe.com/premiere-pro/uxp/
   - Download UXP Developer Tool v2.2 or later
   - Install the application

2. **Enable Developer Mode in Premiere Pro:**
   - Open Premiere Pro
   - Go to **Settings** → **Plugins**
   - Check **Enable Developer Mode**
   - Restart Premiere Pro

### Step 2: Create a New UXP Plugin

1. **Open UXP Developer Tool (UDT)**
2. **Click "Create Plugin"**
3. **Fill in details:**
   - **Name:** `Premiere Timeline Timecode`
   - **Host Application:** Adobe Premiere Pro
   - **Host Application Version:** 25.6 or later
   - **Template:** `premierepro-quick-starter` or `panel`
4. **Choose location:** Select a folder for your plugin
5. **UDT will scaffold the plugin structure**

### Step 3: Using Cursor with UXP Development

**Cursor works perfectly with UXP development!** Here's how:

1. **Open the plugin folder in Cursor:**
   ```bash
   cd /path/to/your/uxp/plugin
   cursor .
   ```

2. **UXP Plugin Structure:**
   ```
   your-plugin/
   ├── manifest.json          # Plugin configuration
   ├── src/
   │   ├── main.js            # Main plugin code
   │   └── index.html         # Panel UI (if panel plugin)
   └── package.json           # Dependencies
   ```

3. **Edit files in Cursor:**
   - Use Cursor's AI assistance for code completion
   - Cursor understands JavaScript/TypeScript
   - Use Cursor's terminal for npm commands

4. **Load plugin in UDT:**
   - In UDT, click "Load Plugin"
   - Select your plugin folder
   - The plugin will appear in Premiere Pro

5. **Hot Reload:**
   - UDT supports hot reload during development
   - Make changes in Cursor → Save → UDT reloads automatically

### Step 4: Development Workflow

**Recommended workflow:**

1. **In Cursor:**
   - Edit your plugin code
   - Use Cursor's AI for help with UXP APIs
   - Save files

2. **In UDT:**
   - Click "Reload" to refresh the plugin
   - View console logs for debugging

3. **In Premiere Pro:**
   - Test the plugin functionality
   - Check Window → Extensions → Your Plugin

## Converting CEP to UXP

The current CEP implementation can be converted to UXP. Key differences:

### API Changes

**CEP (ExtendScript):**
```javascript
// CEP uses evalScript to call ExtendScript
csInterface.evalScript('app.project.activeSequence.getPlayerPosition()', callback);
```

**UXP (Modern JavaScript):**
```javascript
// UXP uses direct API access
const { app } = require('scenegraph');
const sequence = app.project.activeSequence;
const playerPosition = sequence.getPlayerPosition();
```

### Manifest Differences

**CEP manifest.xml:**
```xml
<ExtensionManifest Version="7.0" ...>
```

**UXP manifest.json:**
```json
{
  "id": "com.ppro.timeline",
  "name": "Premiere Timeline Timecode",
  "version": "1.0.0",
  "main": "src/main.js",
  "host": {
    "app": "PPRO",
    "minVersion": "25.6"
  }
}
```

## Quick Start: Create UXP Plugin in Cursor

1. **Create plugin folder:**
   ```bash
   mkdir premiere-timeline-uxp
   cd premiere-timeline-uxp
   cursor .
   ```

2. **Create manifest.json:**
   ```json
   {
     "id": "com.ppro.timeline.uxp",
     "name": "Premiere Timeline Timecode",
     "version": "1.0.0",
     "main": "src/main.js",
     "host": {
       "app": "PPRO",
       "minVersion": "25.6"
     },
     "uiAccess": {
       "type": "panel",
       "geometry": {
         "size": {
           "width": 300,
           "height": 200
         }
       }
     }
   }
   ```

3. **Create src/main.js:**
   ```javascript
   const { app } = require('scenegraph');
   
   // Your plugin code here
   ```

4. **Load in UDT:**
   - Open UDT
   - Click "Load Plugin"
   - Select your folder

## Resources

- **UXP Documentation:** https://developer.adobe.com/premiere-pro/uxp/
- **Premiere DOM API:** https://developer.adobe.com/premiere-pro/uxp/reference/dom/
- **UXP JavaScript API:** https://developer.adobe.com/premiere-pro/uxp/reference/uxp/
- **Sample Plugins:** https://github.com/Adobe-CEP/UXP-Samples

## Next Steps

Would you like me to:
1. **Convert the existing CEP plugin to UXP format?**
2. **Create a new UXP version from scratch?**
3. **Keep both versions (CEP for compatibility, UXP for future)?**

Let me know and I'll help you set it up!

