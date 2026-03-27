#!/usr/bin/env python3
"""
BUSY Bar Animation Player
Plays a PNG frame sequence on the BUSY Bar OLED display at 60fps in a loop.
"""

import os
import sys
import time
import glob
import requests
import threading
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuration
BUSY_BAR_IP = "http://10.0.4.20"
APP_ID = "inhale_exhale"
FRAMES_DIR = Path(__file__).parent / "Animation" / "Main"
TARGET_FPS = 12
DISPLAY = "front"  # "front" or "back"


def upload_frames():
    """Upload all animation frames to the BUSY Bar device."""
    frame_files = sorted(glob.glob(str(FRAMES_DIR / "Inhale_Exhale_*.png")))
    total = len(frame_files)
    
    if total == 0:
        print(f"No frames found in {FRAMES_DIR}")
        return False
    
    print(f"Found {total} frames to upload...")
    print(f"Uploading to {BUSY_BAR_IP} with app_id: {APP_ID}")
    print()
    
    for i, frame_path in enumerate(frame_files):
        filename = os.path.basename(frame_path)
        
        # Upload the frame
        url = f"{BUSY_BAR_IP}/api/assets/upload?app_id={APP_ID}&file={filename}"
        
        try:
            with open(frame_path, 'rb') as f:
                response = requests.post(
                    url,
                    data=f.read(),
                    headers={'Content-Type': 'application/octet-stream'}
                )
            
            if response.status_code == 200:
                progress = (i + 1) / total * 100
                print(f"\rUploading: [{i+1}/{total}] {progress:.1f}% - {filename}", end="", flush=True)
            else:
                print(f"\nError uploading {filename}: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"\nConnection error uploading {filename}: {e}")
            return False
    
    print(f"\n\nSuccessfully uploaded {total} frames!")
    return True


def send_frame_async(session, url, payload):
    """Send frame request in background thread."""
    try:
        session.post(url, json=payload, timeout=0.05, stream=False)
    except:
        pass  # Ignore errors to maintain frame rate


def play_animation():
    """Play the animation in a loop at the target FPS."""
    frame_files = sorted(glob.glob(str(FRAMES_DIR / "Inhale_Exhale_*.png")))
    total_frames = len(frame_files)
    
    if total_frames == 0:
        print(f"No frames found in {FRAMES_DIR}")
        return
    
    frame_names = [os.path.basename(f) for f in frame_files]
    frame_time = 1.0 / TARGET_FPS
    
    print(f"\nPlaying {total_frames} frames at {TARGET_FPS}fps on {DISPLAY} display")
    print(f"Animation duration: {total_frames / TARGET_FPS:.2f} seconds per cycle")
    print("Press Ctrl+C to stop\n")
    
    # Create optimized session with connection pooling
    session = requests.Session()
    retry_strategy = Retry(
        total=0,  # No retries - we want speed
        backoff_factor=0
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=2,
        pool_maxsize=10,
        pool_block=False
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    url = f"{BUSY_BAR_IP}/api/display/draw"
    frame_index = 0
    frames_played = 0
    start_time = time.perf_counter()
    cycle_count = 0
    next_frame_time = start_time
    
    try:
        while True:
            # Send draw command asynchronously (don't wait for response)
            payload = {
                "app_id": APP_ID,
                "elements": [{
                    "id": "frame",
                    "type": "image",
                    "path": frame_names[frame_index],
                    "x": 0,
                    "y": 0,
                    "display": DISPLAY
                }]
            }
            
            # Send request in background thread
            thread = threading.Thread(target=send_frame_async, args=(session, url, payload))
            thread.daemon = True
            thread.start()
            
            frames_played += 1
            frame_index = (frame_index + 1) % total_frames
            
            # Track cycles
            if frame_index == 0:
                cycle_count += 1
            
            # Calculate next frame time and sleep precisely
            next_frame_time += frame_time
            current_time = time.perf_counter()
            sleep_time = next_frame_time - current_time
            
            # Sleep until next frame time
            if sleep_time > 0:
                time.sleep(sleep_time)
            elif sleep_time < -0.1:  # If we're more than 100ms behind, reset
                next_frame_time = time.perf_counter()
            
            # Show stats every second
            total_elapsed = time.perf_counter() - start_time
            if frames_played % TARGET_FPS == 0:
                actual_fps = frames_played / total_elapsed
                print(f"\rCycle: {cycle_count} | Frame: {frame_index:3d}/{total_frames} | FPS: {actual_fps:.1f}", end="", flush=True)
                
    except KeyboardInterrupt:
        total_elapsed = time.perf_counter() - start_time
        actual_fps = frames_played / total_elapsed if total_elapsed > 0 else 0
        print(f"\n\nStopped after {frames_played} frames ({cycle_count} cycles)")
        print(f"Average FPS: {actual_fps:.1f}")
        
        # Clear the display
        clear_display()
        session.close()


def clear_display():
    """Clear the display on the BUSY Bar."""
    try:
        response = requests.delete(f"{BUSY_BAR_IP}/api/display/draw?app_id={APP_ID}", timeout=3)
        if response.status_code == 200:
            print("Display cleared successfully!")
            return True
        else:
            print(f"Failed to clear display: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error clearing display: {e}")
        return False


def check_connection():
    """Check if the BUSY Bar is reachable."""
    try:
        response = requests.get(f"{BUSY_BAR_IP}/api/version", timeout=3)
        if response.status_code == 200:
            data = response.json()
            print(f"Connected to BUSY Bar (API version: {data.get('api_semver', 'unknown')})")
            return True
    except requests.exceptions.RequestException as e:
        print(f"Cannot connect to BUSY Bar at {BUSY_BAR_IP}")
        print(f"Error: {e}")
    return False


def main():
    print("=" * 50)
    print("BUSY Bar Animation Player")
    print("=" * 50)
    print()
    
    # Check connection
    if not check_connection():
        sys.exit(1)
    
    print()
    
    # Menu
    if len(sys.argv) > 1:
        action = sys.argv[1]
    else:
        print("Options:")
        print("  1. Upload frames (one-time setup)")
        print("  2. Play animation")
        print("  3. Upload and play")
        print("  4. Clear display")
        print()
        choice = input("Enter choice (1-4): ").strip()
        
        action_map = {"1": "upload", "2": "play", "3": "both", "4": "clear"}
        action = action_map.get(choice, "play")
    
    if action == "clear":
        clear_display()
    elif action in ("upload", "both"):
        if not upload_frames():
            sys.exit(1)
    
    if action in ("play", "both"):
        play_animation()


if __name__ == "__main__":
    main()

