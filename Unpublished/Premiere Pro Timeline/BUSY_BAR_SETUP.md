# BUSY Bar Integration

This project includes support for displaying Premiere Pro timecode on a BUSY Bar OLED screen (72px × 16px).

## Prerequisites

1. **BUSY Bar device** connected to your network
2. **Python requests library** (for HTTP API calls)

### Install Python requests library

```bash
pip3 install requests
```

## Setup

### 1. Find your BUSY Bar IP address

The BUSY Bar needs to be on the same network as your computer. Find its IP address:
- Check the BUSY Bar settings/display
- Or scan your network for the device

### 2. Configure the IP address

You can set the BUSY Bar IP in two ways:

**Option A: Environment variable (recommended)**
```bash
export BUSY_BAR_IP="10.0.4.20"  # Replace with your BUSY Bar's IP
```

**Option B: Edit the script**
Edit `busy_bar_client.py` and change the default IP:
```python
BUSY_BAR_IP = os.getenv("BUSY_BAR_IP", "10.0.4.20")  # Change this
```

## Usage

### Start the BUSY Bar client

```bash
python3 busy_bar_client.py
```

Or with a custom IP:
```bash
BUSY_BAR_IP="192.168.1.100" python3 busy_bar_client.py
```

### What it does

1. **Monitors** the timecode file written by the Premiere Pro plugin
2. **Sends updates** to the BUSY Bar display whenever the timecode changes
3. **Displays** the timecode centered on the 72×16 OLED screen
4. **Optionally shows** the sequence name below the timecode (if short enough)

### Display Layout

- **Timecode**: Centered, medium font, white color
- **Sequence name** (optional): Centered below, small font, gray color

## Troubleshooting

### "Could not connect to BUSY Bar"

1. **Check IP address**: Make sure the BUSY Bar IP is correct
2. **Check network**: Ensure both devices are on the same network
3. **Check BUSY Bar**: Verify the device is powered on and connected
4. **Test manually**: Try accessing `http://BUSY_BAR_IP/api/version` in a browser

### Timecode not updating

1. **Check Premiere Pro plugin**: Make sure the plugin is running and "Start Server" is clicked
2. **Check timecode file**: Verify the file exists and is being updated:
   ```bash
   cat "/Users/YOUR_USERNAME/Library/Application Support/Adobe/UXP/PluginsStorage/PPRO/25/Developer/com.ppro.timeline.uxp/PluginData/ppro_timeline_data.json"
   ```
3. **Check console output**: The script will show connection status and errors

### Display shows old data

- The BUSY Bar caches display elements. The script sends updates every 100ms when timecode changes
- If stuck, restart the BUSY Bar client

## API Reference

The BUSY Bar client uses the `/api/display/draw` endpoint:

- **Method**: POST
- **URL**: `http://BUSY_BAR_IP/api/display/draw`
- **Content-Type**: `application/json`
- **Payload**: See `busy_bar_client.py` for the exact format

For full API documentation, see `Documentation/BUSY Bar/openapi- 3.1.0 From Wifi.rtf`

## Example Projects

See example implementations in:
- `Documentation/BUSY Bar/clock-widget/` - Clock display examples
- `Documentation/BUSY Bar/Internet Speed Test/` - Network speed monitor
- `Documentation/BUSY Bar/weather-widget/` - Weather display examples

