# Blackmagic Camera Control Web Application

A web-based control interface for Blackmagic cameras using **Bluetooth LE** connectivity. This application provides an intuitive interface for controlling recording and monitoring camera status wirelessly via Bluetooth.

## Features

- **Bluetooth LE Connectivity**: Wireless control via Bluetooth Low Energy
- **Device Discovery**: Scan for and connect to nearby Blackmagic cameras
- **Recording Control**: Start and stop recording with visual feedback
- **Real-time Status**: Monitor recording state and connection status
- **Timecode Display**: View current timecode in real-time via Bluetooth notifications
- **Camera Information**: Display device name, product name, and software version
- **Busy Bar Integration**: Display recording status on Busy Bar device (optional)
- **Modern UI**: Clean, responsive design with visual indicators

## Prerequisites

1. A compatible Blackmagic camera with Bluetooth LE support (see supported models below)
2. Bluetooth enabled on the camera and computer
3. Chrome, Edge, or Opera browser (Web Bluetooth API support required)
4. HTTPS connection or localhost (required for Web Bluetooth API security)
5. Camera must be in Bluetooth pairing/discoverable mode

### Supported Cameras

- Blackmagic URSA Cine 12K LF
- Blackmagic URSA Cine 17K 65
- Blackmagic URSA Cine Immersive
- Blackmagic PYXIS 6K
- Blackmagic Cinema Camera 6K
- Blackmagic URSA Broadcast G2
- Blackmagic Micro Studio Camera 4K G2
- Blackmagic Studio Camera 4K Plus / Plus G2
- Blackmagic Studio Camera 4K Pro / Pro G2
- Blackmagic Studio Camera 6K Pro

## Setup Instructions

### 1. Enable Bluetooth on Camera

1. Open **Blackmagic Camera Setup** on your camera
2. Navigate to **Bluetooth** settings
3. Enable **Bluetooth** and ensure the camera is discoverable
4. Note: The camera must be in pairing mode

### 2. Using a Local Web Server (Required)

**Important**: Web Bluetooth API requires HTTPS or localhost. You **must** use a local web server.

**Easy Method (Recommended):**

**Using Python script (easiest - no npm required):**
```bash
python3 scripts/server.py start    # Start the server (runs in foreground, Ctrl+C to stop)
python3 scripts/server.py stop     # Stop the server
python3 scripts/server.py restart  # Restart the server
python3 scripts/server.py status   # Check if server is running
```

**Or make it executable and run directly:**
```bash
./scripts/server.py start    # Start the server
./scripts/server.py stop     # Stop the server
./scripts/server.py status   # Check server status
```

**Using npm scripts (if you have Node.js installed):**
```bash
npm start    # Start the server
npm stop     # Stop the server
npm restart  # Restart the server
npm run status  # Check server status
```

**Manual Method:**

**Python 3:**
```bash
python3 -m http.server 8000
```

**Python 2:**
```bash
python -m SimpleHTTPServer 8000
```

**Node.js (with http-server):**
```bash
npx http-server -p 8000
```

Then open `http://localhost:8000` in your browser (Chrome, Edge, or Opera).

**Note**: For production use, you'll need HTTPS. You can use services like ngrok or deploy to a hosting service with SSL.

## Usage

### Connecting to Camera

1. **Start Local Web Server**: Use one of the methods above to serve the application
2. **Open Application**: Navigate to `http://localhost:8000` in Chrome, Edge, or Opera
3. **Scan for Cameras**: Click "Scan for Cameras" button
4. **Select Camera**: Choose your Blackmagic camera from the browser's device selection dialog
5. **Connected**: The application will automatically connect and show "Connected" status

### Recording Control

1. **Check Connection**: The connection status indicator at the top shows if the camera is connected (green) or disconnected (red)

2. **Start Recording**: Click the "Start Recording" button to begin recording. The status will update to "Recording" and the indicator will turn red and pulse

3. **Stop Recording**: Click the "Stop Recording" button to stop the current recording

4. **Monitor Status**: The application automatically updates:
   - Recording status every 2 seconds
   - Timecode every second (real-time for Bluetooth)
   - Connection status

### Busy Bar Integration

The application can optionally display recording status on a Busy Bar device. This feature is configured in `js/config.js`.

1. **Configure Busy Bar**: Edit `js/config.js` and set:
   - `busyBar.enabled`: Set to `true` to enable Busy Bar integration
   - `busyBar.ip`: Set to your Busy Bar device IP address (e.g., `http://10.0.4.20`)
   - `busyBar.appId`: Set to your application ID (default: `camera_control`)

2. **Connect Camera**: When you connect to a camera, the application will:
   - Check if Busy Bar is reachable
   - Upload status images (`Recording.png` and `Stand By.png`) to the Busy Bar
   - Display the current recording status on the Busy Bar

3. **Status Updates**: The Busy Bar display automatically updates when:
   - Recording starts (shows "Recording" image)
   - Recording stops (shows "Stand By" image)
   - Camera disconnects (clears the display)

4. **Manual Upload**: If images fail to upload automatically, click "Upload Images to Busy Bar" to retry.

**Note**: Busy Bar integration requires the device to be on the same network and reachable at the configured IP address. If the Busy Bar is unreachable, the application will continue to work normally for camera control.

## Troubleshooting

- **"Web Bluetooth API is not available"**:
  - Use Chrome, Edge, or Opera browser (Safari and Firefox have limited support)
  - Ensure you're accessing via HTTPS or localhost (not file://)
  - Check that your browser supports Web Bluetooth API

- **"No Blackmagic camera found"**:
  - Ensure Bluetooth is enabled on both camera and computer
  - Make sure the camera is in pairing/discoverable mode
  - Check that the camera supports Bluetooth LE
  - Try moving closer to the camera (Bluetooth range limitations)

- **"Bluetooth access denied"**:
  - Allow Bluetooth permissions in your browser settings
  - Check system Bluetooth permissions (macOS, Windows, Linux)

- **Connection drops**:
  - Stay within Bluetooth range (typically 10-30 meters)
  - Check for interference from other Bluetooth devices
  - Ensure camera battery is charged (low battery can affect Bluetooth)

- **Timecode not updating**:
  - Bluetooth timecode updates are real-time via notifications
  - If timecode shows "--:--:--:--", the camera may not be sending timecode data
  - Check camera settings for timecode configuration

- **Busy Bar not updating**:
  - Ensure Busy Bar is enabled in `js/config.js` (`busyBar.enabled: true`)
  - Verify the Busy Bar IP address is correct and the device is on the same network
  - Check that the Busy Bar device is powered on and reachable
  - Try clicking "Upload Images to Busy Bar" to manually upload status images
  - Check browser console for connection errors

## File Structure

```
.
├── index.html           # Main web interface
├── styles.css           # Styling
├── js/                  # JavaScript source files
│   ├── app.js           # Application logic and UI controller
│   ├── bluetooth-client.js  # Bluetooth LE client implementation
│   ├── busybar-client.js    # Busy Bar HTTP API client
│   ├── sdi-protocol.js      # SDI Camera Control Protocol encoder/decoder
│   └── config.js            # Camera and Busy Bar configuration
├── scripts/             # Server scripts
│   └── server.py        # Python web server control script
├── Images/              # Status images for Busy Bar
│   ├── Recording.png    # Recording status image
│   └── Stand By.png     # Standby status image
├── Documentation/       # Additional documentation
├── package.json         # npm scripts and project metadata
└── README.md            # This file
```

## Bluetooth Protocol

- **Service UUID**: `291d567a-6d75-11e6-8b77-86f30ca893d3` (Blackmagic Camera Service)
- **Characteristics**:
  - Outgoing Camera Control: `5dd3465f-1aee-4299-8493-d2eca2f8e1bb`
  - Incoming Camera Control: `b864e140-76a0-416a-bf30-5876504537d9`
  - Timecode: `6d8f2110-86f1-41bf-9afb-451d87e976c8`
  - Camera Status: `7fe8691d-95dc-4fc5-8abd-ca74339b51b9`
- **Protocol**: SDI Camera Control Protocol over encrypted Bluetooth characteristics
- **Transport Commands**: Group 10, ID 10.1 (Mode: 0=Preview, 2=Record)

## Browser Compatibility

- Chrome (recommended)
- Edge (Chromium-based)
- Opera
- **Not supported**: Firefox, Safari (limited Web Bluetooth API support)

## License

This is a sample application for controlling Blackmagic cameras. Use at your own risk.

## Support

For camera-specific issues, refer to the Blackmagic Camera Control documentation or contact Blackmagic Design support.

