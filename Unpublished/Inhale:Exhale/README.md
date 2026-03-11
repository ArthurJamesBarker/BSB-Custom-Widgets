# BUSY Bar Animation Player

Plays the "Inhale/Exhale" animation on the BUSY Bar OLED display (72x16 pixels) at 60fps in a continuous loop.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure your BUSY Bar is connected to the network at `http://10.0.4.20`

## Usage

Run the script:
```bash
python animation_player.py
```

Or use command-line arguments:
```bash
# Upload frames only (one-time setup)
python animation_player.py upload

# Play animation (frames must be uploaded first)
python animation_player.py play

# Upload and play
python animation_player.py both
```

## How it works

1. **Upload Phase**: Uploads all 636 PNG frames from `Animation/Main/` to the BUSY Bar device using the `/api/assets/upload` endpoint. This only needs to be done once.

2. **Playback Phase**: Continuously loops through all frames, sending each one to the display via `/api/display/draw` at 60fps (16.67ms per frame).

- The script shows real-time statistics: cycle count, current frame, and actual FPS achieved
- Press `Ctrl+C` to stop playback
- The display is automatically cleared when you stop the script

## Configuration

Edit the constants at the top of `animation_player.py`:
- `BUSY_BAR_IP`: Device IP address (default: `http://10.0.4.20`)
- `APP_ID`: Application identifier for organizing assets (default: `inhale_exhale`)
- `TARGET_FPS`: Target frame rate (default: `60`)
- `DISPLAY`: Which display to use - `"front"` or `"back"` (default: `"front"`)

## Notes

- 636 frames at 60fps = ~10.6 seconds per animation cycle
- Network latency may limit the actual achievable frame rate
- The script reports the actual FPS achieved during playback

