# How to Start the Timecode Server

Since UXP plugins can't create HTTP servers directly, we use a file-based approach with a simple Node.js server.

## Quick Start

1. **Start the UXP Plugin:**
   - In Premiere Pro, open the Timeline Timecode panel
   - Click "Start Server"
   - The plugin will start writing timecode data to a file

2. **Start the Node.js Server:**
   ```bash
   cd "/Users/barker/Documents/General/Random Tests/Premiere Pro Timeline"
   node server.js
   ```

3. **Open the Web Client:**
   - Open `web-client/index.html` in your browser
   - It will connect to `http://localhost:8080/timecode`
   - Timecode will update in real-time!

## How It Works

1. **UXP Plugin** → Writes timecode data to a JSON file
2. **Node.js Server** → Reads the file and serves it via HTTP
3. **Web Client** → Polls the HTTP endpoint for updates

## Troubleshooting

### Server can't find the data file

The server looks for the file in common UXP plugin data locations. If it can't find it:

1. Check the plugin panel - it shows the file path when started
2. Update `server.js` with the correct path
3. Or create a symlink to the file location

### Port 8080 already in use

Change the port in `server.js`:
```javascript
const port = 8081; // Change this
```

And update `web-client/client.js`:
```javascript
const httpUrl = 'http://localhost:8081/timecode'; // Match the port
```

## Alternative: Direct File Access

If you don't want to run the Node.js server, you can modify the web client to read the file directly (though this has browser security limitations).

