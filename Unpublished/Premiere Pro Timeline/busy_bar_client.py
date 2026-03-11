#!/usr/bin/env python3
"""
BUSY Bar Timecode Display Client
Monitors the Premiere Pro timecode file and displays it on the BUSY Bar OLED screen
"""

import time
import json
import requests
from pathlib import Path
import os

# Configuration
BUSY_BAR_IP = os.getenv("BUSY_BAR_IP", "10.0.4.20")  # Default IP, can be set via environment variable
BUSY_BAR_API_URL = f"http://{BUSY_BAR_IP}/api/display/draw"
BUSY_BAR_UPLOAD_URL = f"http://{BUSY_BAR_IP}/api/assets/upload"
BUSY_BAR_CLEAR_URL = f"http://{BUSY_BAR_IP}/api/display/draw"
APP_ID = "premiere_timecode"
SCREEN_WIDTH = 72
SCREEN_HEIGHT = 16
UPDATE_INTERVAL = 0.016  # Check for updates every 16ms (~60fps) for minimal latency
API_TIMEOUT = 2.0
# Logo configuration - adjust based on actual logo size
# The logo is 16x16 pixels, but we reserve space for it plus a small gap
LOGO_WIDTH = 18  # Space reserved for logo on the left side (adjust if needed)
LOGO_FILENAME = "premiere_logo.png"  # Name to use on device

# Font widths in pixels per character (from BUSY Bar documentation and examples)
# Available fonts (from OpenAPI spec):
#   - small: 4px per character
#   - medium: 5px per character  
#   - medium_condensed: ~4px per character (estimated, similar to small)
#   - big: 7px per character
#   - tiny5_8: default font (width not documented in examples)
FONT_WIDTHS = {
    "small": 4,
    "medium": 5,
    "medium_condensed": 4,  # Estimated based on name
    "big": 7,
    "tiny5_8": 4  # Estimated, likely similar to small
}

def center_x(text, font):
    """Calculate X position to center text on screen"""
    font_width = FONT_WIDTHS.get(font, 5)
    text_width = len(text) * font_width
    x = max((SCREEN_WIDTH - text_width) // 2, 0)
    return x

def center_x_with_offset(text, font, offset):
    """Calculate X position to center text on screen with an offset (e.g., for logo space)"""
    font_width = FONT_WIDTHS.get(font, 5)
    text_width = len(text) * font_width
    available_width = SCREEN_WIDTH - offset
    x = offset + max((available_width - text_width) // 2, 0)
    return x

# Find the data file (same paths as server.py)
home = Path.home()
possible_paths = [
    home / "Library" / "Application Support" / "Adobe" / "UXP" / "PluginsStorage" / "PPRO" / "26" / "Developer" / "com.ppro.timeline.uxp" / "PluginData" / "ppro_timeline_data.json",
    home / "Library" / "Application Support" / "Adobe" / "UXP" / "PluginsStorage" / "PPRO" / "25" / "Developer" / "com.ppro.timeline.uxp" / "PluginData" / "ppro_timeline_data.json",
    Path(__file__).parent / "ppro_timeline_data.json",  # Fallback: same directory
]

data_file_path = None
for file_path in possible_paths:
    if file_path.exists():
        data_file_path = file_path
        print(f"✓ Found timecode file at: {file_path}")
        break

if not data_file_path:
    print("⚠ Timecode file not found. Make sure the Premiere Pro plugin is running.")
    print("Looking in:")
    for p in possible_paths:
        print(f"  - {p}")
    exit(1)

# Track last update to avoid duplicate sends
last_timestamp = None
last_timecode = None
last_sent_sequence_name = None


def upload_logo(logo_path, debug=False):
    """
    Upload the Premiere Pro logo to the BUSY Bar device.
    
    Args:
        logo_path: Path to the logo PNG file
        debug: Enable debug output
    
    Returns:
        True if upload successful, False otherwise
    """
    if not os.path.exists(logo_path):
        print(f"⚠ Logo file not found: {logo_path}")
        return False
    
    try:
        with open(logo_path, 'rb') as f:
            logo_data = f.read()
        
        upload_url = f"{BUSY_BAR_UPLOAD_URL}?app_id={APP_ID}&file={LOGO_FILENAME}"
        
        if debug:
            print(f"Uploading logo from {logo_path} to {upload_url}")
            print(f"Logo size: {len(logo_data)} bytes")
        
        response = requests.post(
            upload_url,
            data=logo_data,
            headers={'Content-Type': 'application/octet-stream'},
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        
        if debug:
            print(f"✓ Logo uploaded successfully: {response.json()}")
        return True
        
    except requests.RequestException as e:
        print(f"✗ Error uploading logo: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"✗ Error reading logo file: {e}")
        return False


def format_timecode_for_display(timecode_str):
    """
    Format timecode for the 72x16 OLED display.
    The timecode format is typically HH:MM:SS:FF
    For a compact display, we can show it centered or left-aligned.
    """
    # Remove any extra whitespace
    timecode_str = timecode_str.strip()
    
    # If timecode is too long, truncate it
    # Standard timecode is 11 chars: "00:00:00:00"
    if len(timecode_str) > 11:
        timecode_str = timecode_str[:11]
    
    return timecode_str


def send_to_busy_bar(timecode_str, sequence_name=None, send_sequence=False, debug=False):
    """
    Send timecode to BUSY Bar display.
    Layout: Logo on left, timecode shifted right, optionally sequence name below.
    If text is too long, it will scroll across the screen.
    
    Args:
        timecode_str: The timecode string to display
        sequence_name: The sequence name (only sent if send_sequence is True)
        send_sequence: Whether to include sequence name in this update (to avoid resetting scroll)
        debug: Enable debug output
    """
    formatted_timecode = format_timecode_for_display(timecode_str)
    
    # Build display elements
    elements = []
    
    # Add logo on the left side (always include it)
    elements.append({
        "id": "logo",
        "type": "image",
        "path": LOGO_FILENAME,
        "x": 0,
        "y": 0,
        "timeout": 0,  # Continuous display
    })
    
    # Calculate available width for text (screen width minus logo width)
    available_width = SCREEN_WIDTH - LOGO_WIDTH
    
    # Check if timecode fits in available space (medium font: 5px per char)
    timecode_width = len(formatted_timecode) * FONT_WIDTHS["medium"]
    timecode_fits = timecode_width <= available_width
    
    # Main timecode display - shifted right to make room for logo
    timecode_element = {
        "id": "timecode",
        "type": "text",
        "text": formatted_timecode,
        "font": "medium",
        "color": "#FFFFFFFF",  # White
        "y": 0,  # Top of screen
        "timeout": 0,  # 0 = continuous display
    }
    
    if timecode_fits:
        # Center it in the available space (after logo)
        timecode_element["x"] = center_x_with_offset(formatted_timecode, "medium", LOGO_WIDTH)
    else:
        # Enable scrolling if it doesn't fit (left-to-right, one direction)
        timecode_element["x"] = LOGO_WIDTH  # Start after logo
        timecode_element["width"] = available_width
        timecode_element["scroll_rate"] = 30  # characters per minute (slower)
    
    elements.append(timecode_element)
    
    # Only include sequence name if explicitly requested (to avoid resetting scroll)
    if sequence_name and send_sequence:
        # Check if sequence name fits in available space (small font: 4px per char)
        seq_width = len(sequence_name) * FONT_WIDTHS["small"]
        seq_fits = seq_width <= available_width
        
        seq_element = {
            "id": "sequence",
            "type": "text",
            "text": sequence_name,  # Don't truncate, let it scroll if needed
            "font": "small",
            "color": "#888888FF",  # Dimmer gray
            "y": 10,  # Below timecode (medium font is ~8-9px high)
            "timeout": 0,
        }
        
        if seq_fits:
            # Center it in the available space (after logo)
            seq_element["x"] = center_x_with_offset(sequence_name, "small", LOGO_WIDTH)
        else:
            # Enable scrolling if it doesn't fit (left-to-right, one direction)
            seq_element["x"] = LOGO_WIDTH  # Start after logo
            seq_element["width"] = available_width
            seq_element["scroll_rate"] = 30  # characters per minute (slower)
        
        elements.append(seq_element)
    
    payload = {
        "app_id": APP_ID,
        "elements": elements
    }
    
    if debug:
        print("\n--- Sending to BUSY Bar ---")
        print(json.dumps(payload, indent=2))
    
    try:
        response = requests.post(
            BUSY_BAR_API_URL,
            json=payload,
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        if debug:
            print(f"✗ Error sending to BUSY Bar: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
        return False


def read_timecode_data():
    """Read the latest timecode data from the file."""
    global last_timestamp, last_timecode, last_sent_sequence_name
    
    if not data_file_path or not data_file_path.exists():
        return None
    
    try:
        with open(data_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check if this is a new update
        timestamp = data.get('timestamp', 0)
        if timestamp == last_timestamp:
            return None  # No new data
        
        last_timestamp = timestamp
        
        timecode_data = data.get('data', {})
        timecode_str = timecode_data.get('timecode', '')
        sequence_name = timecode_data.get('sequenceName', '')
        
        # Check if timecode changed
        timecode_changed = timecode_str != last_timecode
        # Check if sequence name changed
        sequence_changed = sequence_name != last_sent_sequence_name
        
        if timecode_changed or sequence_changed:
            result = {
                'timecode': timecode_str,
                'sequence_name': sequence_name,
                'send_sequence': sequence_changed  # Only send sequence if it changed
            }
            
            if timecode_changed:
                last_timecode = timecode_str
            if sequence_changed:
                last_sent_sequence_name = sequence_name
            
            return result
        
        return None
        
    except (json.JSONDecodeError, IOError) as e:
        # File might be in the middle of being written, ignore errors
        return None


def main():
    print(f"\n🎬 BUSY Bar Timecode Display Client")
    print(f"📡 Connecting to BUSY Bar at: {BUSY_BAR_IP}")
    print(f"📁 Monitoring: {data_file_path}")
    print(f"⏱️  Update interval: {UPDATE_INTERVAL}s")
    print("\nPress Ctrl+C to stop.\n")
    
    # Find and upload logo
    script_dir = Path(__file__).parent
    logo_paths = [
        script_dir / "PNG" / "Premiere Pro Pixel Logo.png",
        script_dir / "Premiere Pro Pixel Logo.png",
        script_dir / "PNG" / "Adobe_Premiere_Pro_CC_icon 2.png",
        script_dir / "Adobe_Premiere_Pro_CC_icon 2.png",
        script_dir / "premiere_logo.png",
    ]
    
    logo_path = None
    for path in logo_paths:
        if path.exists():
            logo_path = path
            break
    
    if logo_path:
        print(f"📤 Uploading logo: {logo_path}")
        if upload_logo(logo_path, debug=True):
            print("✓ Logo uploaded successfully!\n")
        else:
            print("⚠ Logo upload failed, continuing without logo...\n")
    else:
        print("⚠ Logo file not found, continuing without logo...")
        print("Looking for logo in:")
        for p in logo_paths:
            print(f"  - {p}")
        print()
    
    # Test connection on startup
    print("Testing BUSY Bar connection...")
    if send_to_busy_bar("00:00:00:00", debug=True):
        print("✓ Connected to BUSY Bar successfully!\n")
    else:
        print("⚠ Could not connect to BUSY Bar. Check IP address and network connection.")
        print(f"   Current IP: {BUSY_BAR_IP}")
        print(f"   Set BUSY_BAR_IP environment variable to change IP.\n")
    
    update_count = 0
    
    try:
        while True:
            timecode_data = read_timecode_data()
            
            if timecode_data:
                success = send_to_busy_bar(
                    timecode_data['timecode'],
                    timecode_data.get('sequence_name'),
                    send_sequence=timecode_data.get('send_sequence', False),  # Only send sequence if it changed
                    debug=(update_count < 3)  # Debug first 3 updates
                )
                
                if success:
                    update_count += 1
                    # Print status every 10 updates to avoid spam
                    if update_count % 10 == 0:
                        print(f"✓ Updated BUSY Bar ({update_count} updates) - {timecode_data['timecode']}", end='\r')
            
            time.sleep(UPDATE_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\nStopping BUSY Bar client...")
        # Clear the display on exit
        try:
            clear_url = f"{BUSY_BAR_CLEAR_URL}?app_id={APP_ID}"
            response = requests.delete(clear_url, timeout=API_TIMEOUT)
            response.raise_for_status()
            print("✓ Display cleared")
        except Exception as e:
            print(f"⚠ Could not clear display: {e}")
        print("Done.")


if __name__ == "__main__":
    main()

