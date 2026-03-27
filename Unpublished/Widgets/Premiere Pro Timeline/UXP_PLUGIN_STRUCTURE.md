# UXP Plugin Structure for Timeline Timecode

This document outlines the structure needed to convert the CEP plugin to UXP format.

## UXP Plugin File Structure

```
premiere-timeline-uxp/
├── manifest.json              # Plugin manifest (replaces CSXS/manifest.xml)
├── src/
│   ├── main.js                # Main plugin entry point
│   ├── panel.html             # Panel UI (replaces index.html)
│   ├── panel.js               # Panel JavaScript (replaces js/main.js)
│   └── timeline.js            # Timeline/timecode logic
├── web-client/                # (Same as before)
│   ├── index.html
│   └── client.js
└── package.json               # npm dependencies (optional)
```

## Key Differences from CEP

### 1. Manifest Format

**CEP (XML):**
```xml
<ExtensionManifest Version="7.0">
  <ExtensionList>...</ExtensionList>
</ExtensionManifest>
```

**UXP (JSON):**
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
      "size": { "width": 300, "height": 200 }
    }
  }
}
```

### 2. API Access

**CEP (via evalScript):**
```javascript
// CEP requires evalScript bridge
csInterface.evalScript('app.project.activeSequence.getPlayerPosition()', callback);
```

**UXP (direct access):**
```javascript
// UXP has direct API access
const { app } = require('scenegraph');
const sequence = app.project.activeSequence;
const playerPosition = sequence.getPlayerPosition();
```

### 3. Node.js Modules

**CEP:**
- Limited Node.js access
- Requires special setup for modules

**UXP:**
- Full Node.js support
- Can use npm packages directly
- Better WebSocket support

### 4. Installation

**CEP:**
- Manual copy to extensions folder
- Requires .debug file
- Requires PlayerDebugMode

**UXP:**
- Use UXP Developer Tool (UDT)
- Click "Load Plugin"
- No debug files needed

## UXP Implementation Example

### manifest.json
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
  },
  "requiredPermissions": [
    "network"
  ]
}
```

### src/main.js
```javascript
const { app } = require('scenegraph');
const http = require('http');
const WebSocket = require('ws');

let wsServer = null;
let pollingInterval = null;
const port = 8080;

// Get playhead timecode
function getPlayheadTimecode() {
  try {
    if (!app.project || !app.project.activeSequence) {
      return null;
    }
    
    const sequence = app.project.activeSequence;
    const playerPosition = sequence.getPlayerPosition();
    
    if (!playerPosition) {
      return null;
    }
    
    // Get frame rate
    const frameRate = sequence.timebase;
    const ticksPerSecond = 254016000000;
    const fps = ticksPerSecond / parseFloat(frameRate);
    
    // Create frame duration
    const frameDuration = new Time();
    frameDuration.seconds = 1.0 / fps;
    
    // Format timecode
    const displayFormat = sequence.videoDisplayFormat;
    const timecodeString = playerPosition.getFormatted(frameDuration, displayFormat);
    
    return {
      timecode: timecodeString,
      seconds: playerPosition.seconds,
      ticks: playerPosition.ticks,
      sequenceName: sequence.name,
      frameRate: fps,
      displayFormat: displayFormat
    };
  } catch (e) {
    return { error: e.toString() };
  }
}

// Start server
function startServer() {
  const httpServer = http.createServer((req, res) => {
    // CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    
    if (req.method === 'OPTIONS') {
      res.writeHead(200);
      res.end();
      return;
    }
    
    if (req.url === '/timecode' || req.url === '/') {
      const data = getPlayheadTimecode();
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        type: 'timecode',
        data: data,
        timestamp: Date.now()
      }));
      return;
    }
    
    res.writeHead(404);
    res.end('Not found');
  });
  
  // WebSocket server
  const wss = new WebSocket.Server({ server: httpServer });
  let latestData = null;
  
  wss.on('connection', (ws) => {
    console.log('Client connected');
    
    // Send initial data
    if (latestData) {
      ws.send(JSON.stringify(latestData));
    }
    
    ws.on('close', () => {
      console.log('Client disconnected');
    });
  });
  
  // Poll playhead position
  pollingInterval = setInterval(() => {
    const timecodeData = getPlayheadTimecode();
    if (timecodeData) {
      latestData = {
        type: 'timecode',
        data: timecodeData,
        timestamp: Date.now()
      };
      
      // Broadcast to all WebSocket clients
      wss.clients.forEach((client) => {
        if (client.readyState === WebSocket.OPEN) {
          client.send(JSON.stringify(latestData));
        }
      });
    }
  }, 100);
  
  httpServer.listen(port, 'localhost', () => {
    console.log(`Server running on port ${port}`);
  });
  
  return { server: httpServer, wss };
}

// Plugin lifecycle
module.exports = {
  start: startServer,
  stop: () => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }
    if (wsServer) {
      wsServer.server.close();
    }
  }
};
```

## Using Cursor for UXP Development

1. **Open plugin folder in Cursor:**
   ```bash
   cursor /path/to/premiere-timeline-uxp
   ```

2. **Cursor features that help:**
   - **AI Code Completion:** Cursor understands UXP APIs
   - **Terminal:** Run npm commands, start UDT
   - **File Explorer:** Navigate plugin structure
   - **Git Integration:** Version control your plugin

3. **Development workflow:**
   - Edit code in Cursor
   - Save files
   - UDT auto-reloads (or click Reload)
   - Test in Premiere Pro

4. **Ask Cursor for help:**
   - "How do I access the active sequence in UXP?"
   - "Show me the UXP API for getting playhead position"
   - "Help me set up WebSocket in UXP"

## Benefits of UXP over CEP

1. **Modern JavaScript:** ES6+, async/await, modules
2. **Better Performance:** Faster execution
3. **Easier Development:** Direct API access, no evalScript
4. **Better Tooling:** UDT provides better debugging
5. **Future-Proof:** CEP deprecated after 2026

## Migration Checklist

- [ ] Install UXP Developer Tool
- [ ] Enable Developer Mode in Premiere Pro
- [ ] Create new UXP plugin structure
- [ ] Convert manifest.xml to manifest.json
- [ ] Update API calls (remove evalScript)
- [ ] Test WebSocket server
- [ ] Update web client (should work as-is)
- [ ] Test in Premiere Pro

