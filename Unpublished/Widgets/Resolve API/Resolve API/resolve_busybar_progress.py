#!/usr/bin/env python3
"""
DaVinci Resolve Export Progress Bar for Busy Bar

This script monitors DaVinci Resolve export progress and displays it on a Busy Bar device.
It polls Resolve's render status and sends visual progress updates via HTTP API.
"""

import sys
import time
import requests
import os
from typing import Optional, Dict, Any

# Add Resolve scripting module path for macOS
if sys.platform == "darwin":  # macOS
    resolve_script_path = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"
    if os.path.exists(resolve_script_path) and resolve_script_path not in sys.path:
        sys.path.insert(0, resolve_script_path)

# Configuration
DEVICE_IP = "10.0.4.20"  # Change this to your Busy Bar IP address
APP_ID = "resolve_export"
POLL_INTERVAL = 0.1  # Seconds between display updates (10x per second for smooth animation)
RESOLVE_POLL_INTERVAL = 0.5  # Seconds between Resolve API checks
BASE_INCREMENT = 0.3  # Base increment per display update
MIN_INCREMENT = 0.1  # Minimum increment (when ahead of target)
MAX_INCREMENT = 2.0  # Maximum increment (when catching up)
SCREEN_WIDTH = 72  # Busy Bar front display width in pixels

# Font widths in pixels per character
FONT_WIDTHS = {
    "small": 4,
    "medium": 5,
    "big": 7
}

# Progress bar configuration
PROGRESS_BAR_WIDTH = 29  # Number of characters for the progress bar (fills from x=17 to edge)
BAR_CHAR = "|"  # Use pipe character for both filled and background


def center_x(text: str, font: str) -> int:
    """Calculate x position to center text on screen."""
    text_width = len(text) * FONT_WIDTHS.get(font, 5)
    x = max((SCREEN_WIDTH - text_width) // 2, 0)
    return x


def create_progress_bar_filled(percentage: float) -> str:
    """Create the filled portion of progress bar."""
    filled = int(PROGRESS_BAR_WIDTH * percentage / 100)
    return BAR_CHAR * filled if filled > 0 else ""


def create_progress_bar_background() -> str:
    """Create the full background bar."""
    return BAR_CHAR * PROGRESS_BAR_WIDTH


def upload_logo_to_busybar() -> bool:
    """Upload the Resolve logo image to Busy Bar assets."""
    import os
    # Use the original logo (user has brightened it)
    logo_path = os.path.join(os.path.dirname(__file__), "..", "DaVinci_Resolve_17_logo 1.png")
    if not os.path.exists(logo_path):
        # Try current directory
        logo_path = "/Users/barker/Documents/General/Random Tests/Resolve API/DaVinci_Resolve_17_logo 1.png"
    
    if not os.path.exists(logo_path):
        print("Logo file not found, using text fallback")
        return False
    
    try:
        with open(logo_path, 'rb') as f:
            logo_data = f.read()
        
        url = f"http://{DEVICE_IP}/api/assets/upload?app_id={APP_ID}&file=resolve_logo.png"
        response = requests.post(url, data=logo_data, headers={'Content-Type': 'application/octet-stream'}, timeout=5)
        return response.ok
    except Exception as e:
        print(f"Failed to upload logo: {e}")
        return False


def send_image_element_to_busybar(element_id: str, image_path: str, x: int, y: int, verbose: bool = False) -> bool:
    """Send an image element to Busy Bar."""
    payload = {
        "app_id": APP_ID,
        "elements": [
            {
                "id": element_id,
                "type": "image",
                "path": image_path,
                "x": x,
                "y": y
            }
        ]
    }
    
    try:
        response = requests.post(f"http://{DEVICE_IP}/api/display/draw", json=payload, timeout=2)
        if verbose:
            print(f"  Image {element_id}: {response.status_code} - {response.text}")
        return response.ok
    except Exception as e:
        if verbose:
            print(f"  Error: {e}")
        return False


def send_single_element_to_busybar(element_id: str, text: str, x: int, y: int, font: str, color: str, verbose: bool = False) -> bool:
    """Send a single text element to Busy Bar - for testing."""
    payload = {
        "app_id": APP_ID,
        "elements": [
            {
                "id": element_id,
                "type": "text",
                "text": text,
                "x": x,
                "y": y,
                "font": font,
                "color": color
            }
        ]
    }
    
    try:
        url = f"http://{DEVICE_IP}/api/display/draw"
        if verbose:
            print(f"  Testing single element: {element_id}")
            print(f"  Payload: {payload}")
        
        response = requests.post(url, json=payload, timeout=2)
        
        if verbose:
            print(f"  Response: {response.status_code} - {response.text}")
        
        return response.ok
    except Exception as e:
        if verbose:
            print(f"  Error: {e}")
        return False


def format_time_remaining(seconds: float) -> str:
    """Format seconds into a compact time string showing seconds remaining."""
    if seconds < 0 or seconds > 86400:  # Cap at 24 hours
        return "--"
    
    total_seconds = int(seconds)
    
    if total_seconds >= 3600:
        # Over an hour - show hours and minutes
        hours = total_seconds // 3600
        mins = (total_seconds % 3600) // 60
        return f"{hours}h{mins:02d}"
    elif total_seconds >= 60:
        # Over a minute - show total seconds
        return f"{total_seconds}s"
    else:
        # Under a minute - show seconds
        return f"{total_seconds}s"


def send_progress_to_busybar(percentage: float, time_remaining: float = None, verbose: bool = False) -> bool:
    """Send progress display to Busy Bar via HTTP API - Resolve style."""
    background_bar = create_progress_bar_background()
    filled_bar = create_progress_bar_filled(percentage)
    percentage_text = f"{int(percentage)}%"
    
    # Layout: Logo on left, progress bar bottom, percentage left above bar, time right above bar
    # Display is 72px wide, ~13px tall
    
    # Position calculations
    bar_x = 17  # Progress bar starts after logo area (logo is 15px wide + 2px gap)
    
    # Percentage on the left side (after logo)
    percent_x = bar_x
    
    # Time remaining on the right side (smaller font)
    time_text = ""
    time_x = SCREEN_WIDTH  # Off screen by default
    if time_remaining is not None and time_remaining > 0:
        time_text = format_time_remaining(time_remaining)
        time_width = len(time_text) * FONT_WIDTHS["small"]
        time_x = SCREEN_WIDTH - time_width - 1  # Right-aligned with small margin
    
    # Build all elements in a single request to avoid flickering
    elements = [
        {"id": "logo", "type": "image", "path": "resolve_logo.png", "x": 0, "y": 1},
        {"id": "bg_bar", "type": "text", "text": background_bar, "x": bar_x, "y": 9, "font": "small", "color": "#1A4D1AFF"},
        {"id": "percentage", "type": "text", "text": percentage_text, "x": percent_x, "y": 2, "font": "small", "color": "#FFFFFFFF"},
        {"id": "time_remaining", "type": "text", "text": time_text if time_text else " ", "x": time_x, "y": 2, "font": "small", "color": "#AAAAAAFF"}
    ]
    
    # Add foreground bar only if there's progress
    if filled_bar:
        elements.append({"id": "fg_bar", "type": "text", "text": filled_bar, "x": bar_x, "y": 9, "font": "small", "color": "#00FF00FF"})
    
    payload = {"app_id": APP_ID, "elements": elements}
    
    try:
        url = f"http://{DEVICE_IP}/api/display/draw"
        response = requests.post(url, json=payload, timeout=2)
        if verbose:
            print(f"  Response: {response.status_code}")
        return response.ok
    except Exception as e:
        if verbose:
            print(f"  Error: {e}")
        return False


def clear_busybar_display() -> bool:
    """Clear the Busy Bar display."""
    try:
        # According to API docs, DELETE /api/display/draw with optional app_id query param
        response = requests.delete(
            f"http://{DEVICE_IP}/api/display/draw",
            params={"app_id": APP_ID},
            timeout=2
        )
        if not response.ok:
            print(f"Busy Bar clear error: {response.status_code} - {response.text}", file=sys.stderr)
        return response.ok
    except Exception as e:
        print(f"Error clearing Busy Bar: {e}", file=sys.stderr)
        return False


def test_busybar_connection() -> bool:
    """Test connection to Busy Bar by checking API version."""
    try:
        url = f"http://{DEVICE_IP}/api/version"
        response = requests.get(url, timeout=2)
        if response.ok:
            version_info = response.json()
            print(f"✓ Busy Bar connected at {DEVICE_IP}")
            print(f"  API version: {version_info.get('api_semver', 'unknown')}")
            return True
        else:
            print(f"✗ Busy Bar responded with error: {response.status_code}", file=sys.stderr)
            print(f"  Response: {response.text}", file=sys.stderr)
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to Busy Bar at {DEVICE_IP}", file=sys.stderr)
        print(f"  Check that the IP address is correct and Busy Bar is on the same network.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"✗ Error testing Busy Bar connection: {e}", file=sys.stderr)
        return False


def get_resolve_connection():
    """Connect to DaVinci Resolve and return project manager."""
    try:
        import DaVinciResolveScript as dvr_script
        resolve = dvr_script.scriptapp("Resolve")
        if not resolve:
            print("Error: Could not connect to DaVinci Resolve. Is Resolve running?", file=sys.stderr)
            return None
        
        project_manager = resolve.GetProjectManager()
        project = project_manager.GetCurrentProject()
        
        if not project:
            print("Error: No project is currently open in DaVinci Resolve.", file=sys.stderr)
            return None
        
        return project
    except ImportError:
        print("Error: DaVinciResolveScript module not found.", file=sys.stderr)
        print("Please ensure DaVinci Resolve is installed and the scripting API is available.", file=sys.stderr)
        if sys.platform == "darwin":
            print(f"Expected path: /Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules", file=sys.stderr)
            print("If Resolve is installed in a different location, you may need to set PYTHONPATH manually.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error connecting to Resolve: {e}", file=sys.stderr)
        return None


def get_render_progress(project, verbose: bool = False) -> Optional[float]:
    """Get the current render progress percentage from Resolve."""
    try:
        is_rendering = project.IsRenderingInProgress()
        if verbose:
            print(f"  [Debug] IsRenderingInProgress: {is_rendering}")
        
        if not is_rendering:
            return None
        
        # Get all render jobs
        job_list = project.GetRenderJobList()
        if verbose:
            print(f"  [Debug] Job list: {job_list}")
        
        if not job_list:
            return None
        
        # Find the first active render job
        for job in job_list:
            job_id = job.get("JobId")
            if job_id:
                status = project.GetRenderJobStatus(job_id)
                if verbose:
                    print(f"  [Debug] Job {job_id} status: {status}")
                
                if status:
                    # Status dict contains 'JobStatus' and 'CompletionPercentage'
                    completion = status.get("CompletionPercentage", 0)
                    job_status = status.get("JobStatus", "")
                    
                    if verbose:
                        print(f"  [Debug] JobStatus: '{job_status}', Completion: {completion}")
                    
                    # Accept any status that isn't explicitly "Complete" or "Failed"
                    # Different Resolve versions may use different status strings
                    if job_status.lower() not in ["complete", "completed", "failed", "cancelled", "canceled"]:
                        if completion is not None:
                            return float(completion)
        
        return None
    except Exception as e:
        print(f"Error getting render progress: {e}", file=sys.stderr)
        return None


def main():
    """Main monitoring loop."""
    # Test Busy Bar connection first
    print(f"Testing connection to Busy Bar at {DEVICE_IP}...")
    if not test_busybar_connection():
        print("\nPlease check your Busy Bar IP address and try again.", file=sys.stderr)
        sys.exit(1)
    
    # Upload Resolve logo to Busy Bar
    print("Uploading Resolve logo...")
    if upload_logo_to_busybar():
        print("✓ Logo uploaded")
    else:
        print("⚠ Logo upload failed, will use text fallback")
    
    print("\nConnecting to DaVinci Resolve...")
    project = get_resolve_connection()
    if not project:
        sys.exit(1)
    
    print(f"\n✓ Connected! Monitoring export progress on Busy Bar at {DEVICE_IP}")
    print("Press Ctrl+C to stop monitoring.\n")
    
    target_percentage = 0  # What Resolve reports
    display_percentage = 0  # What we're showing (smoothly interpolated)
    last_display_int = -1  # Last integer percentage shown
    was_rendering = False
    last_resolve_check = 0
    
    # For estimating progress rate
    start_time = None
    last_target = 0
    last_target_time = 0
    estimated_rate = 1.0  # Estimated % per second (will be calculated)
    
    try:
        while True:
            current_time = time.time()
            
            # Check Resolve less frequently than display updates
            if current_time - last_resolve_check >= RESOLVE_POLL_INTERVAL:
                progress = get_render_progress(project, verbose=False)
                last_resolve_check = current_time
                
                if progress is not None:
                    # Rendering is in progress
                    if not was_rendering:
                        print("Export started! Displaying progress on Busy Bar...")
                        clear_busybar_display()  # Clear any leftover display first
                        was_rendering = True
                        display_percentage = 0  # Start from 0 for smooth animation
                        start_time = current_time
                        last_target = 0
                        last_target_time = current_time
                        estimated_rate = 1.0  # Default: assume 100% in 100 seconds
                    
                    # Update estimated rate based on actual progress
                    if progress > last_target and current_time > last_target_time:
                        time_delta = current_time - last_target_time
                        progress_delta = progress - last_target
                        if time_delta > 0:
                            # Calculate rate and smooth it with previous estimate
                            new_rate = progress_delta / time_delta
                            estimated_rate = (estimated_rate * 0.5) + (new_rate * 0.5)
                    
                    last_target = progress
                    last_target_time = current_time
                    target_percentage = progress
                else:
                    # Rendering stopped or not in progress
                    if was_rendering:
                        # Export just finished - animate to 100% first
                        target_percentage = 100
            
            # Smart interpolation with adaptive speed
            if was_rendering:
                # Check if we're in completion mode (Resolve finished but we haven't hit 100 yet)
                resolve_done = (progress is None and target_percentage == 100)
                
                # Calculate how far behind/ahead we are
                gap = target_percentage - display_percentage
                
                if resolve_done and display_percentage < 100:
                    # Resolve finished - race to 100%!
                    increment = 5.0  # Fast finish
                elif gap > 0:
                    # We're behind the target - need to catch up
                    if gap > 10:
                        # Way behind - speed up significantly
                        increment = MAX_INCREMENT
                    elif gap > 5:
                        # Moderately behind - speed up
                        increment = BASE_INCREMENT * 2
                    else:
                        # Slightly behind or on track
                        increment = BASE_INCREMENT
                elif gap < -5:
                    # We're ahead of target (shouldn't happen much) - slow down
                    increment = MIN_INCREMENT
                else:
                    # Keep moving forward at base rate (even if slightly ahead)
                    # This creates the "fake it" effect
                    increment = BASE_INCREMENT
                
                # Always keep moving forward (unless we hit 99%)
                if display_percentage < 99:
                    display_percentage = min(display_percentage + increment, 99.9)
                
                # But never go past the actual target by too much (unless completing)
                if not resolve_done and display_percentage > target_percentage + 10:
                    display_percentage = target_percentage + 10
                
                # Snap to 100 when target is 100
                if target_percentage >= 100 and display_percentage >= 99:
                    display_percentage = 100
                
                # Calculate estimated time remaining
                time_remaining = None
                if start_time and display_percentage > 0 and display_percentage < 100:
                    elapsed = current_time - start_time
                    # Estimate based on current progress rate
                    if display_percentage > 1:  # Avoid division issues at very start
                        total_estimated = elapsed * 100 / display_percentage
                        time_remaining = total_estimated - elapsed
                        if time_remaining < 0:
                            time_remaining = 0
                
                # Update display when integer percentage changes
                current_int = int(display_percentage)
                if current_int != last_display_int:
                    time_str = format_time_remaining(time_remaining) if time_remaining else "--:--"
                    print(f"Progress: {current_int}% (actual: {int(target_percentage)}%) - ETA: {time_str}")
                    send_progress_to_busybar(display_percentage, time_remaining, verbose=False)
                    last_display_int = current_int
                
                # Once we've shown 100%, hold for a moment then show completion message
                if display_percentage >= 100 and resolve_done:
                    print("\nExport complete! Holding at 100%...")
                    time.sleep(1.0)  # Hold at 100% for 1 second
                    
                    # Show completion message by hiding other elements off-screen
                    # (clearing causes flickering issues)
                    print("Showing completion message...")
                    done_text = "DONE!"
                    done_x = center_x(done_text, "big")
                    payload = {
                        "app_id": APP_ID,
                        "elements": [
                            {"id": "done_msg", "type": "text", "text": done_text, "x": done_x, "y": 3, "font": "big", "color": "#00FF00FF"},
                            {"id": "logo", "type": "image", "path": "resolve_logo.png", "x": 200, "y": 200},
                            {"id": "bg_bar", "type": "text", "text": "|", "x": 200, "y": 0, "font": "small", "color": "#000000FF"},
                            {"id": "fg_bar", "type": "text", "text": "|", "x": 200, "y": 0, "font": "small", "color": "#000000FF"},
                            {"id": "percentage", "type": "text", "text": " ", "x": 200, "y": 0, "font": "small", "color": "#000000FF"},
                            {"id": "time_remaining", "type": "text", "text": " ", "x": 200, "y": 0, "font": "small", "color": "#000000FF"}
                        ]
                    }
                    try:
                        requests.post(f"http://{DEVICE_IP}/api/display/draw", json=payload, timeout=2)
                    except:
                        pass
                    
                    time.sleep(4.0)  # Show message for 4 seconds
                    
                    print("Clearing display...")
                    clear_busybar_display()
                    was_rendering = False
                    target_percentage = 0
                    display_percentage = 0
                    last_display_int = -1
                    start_time = None
            
            time.sleep(POLL_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\nStopping monitor...")
        if was_rendering:
            clear_busybar_display()
        print("Done.")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        if was_rendering:
            clear_busybar_display()
        sys.exit(1)


if __name__ == "__main__":
    main()
