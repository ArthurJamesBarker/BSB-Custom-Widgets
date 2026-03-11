# Changelog

## [Unreleased]

### Changed
- Time remaining display now shows total seconds (e.g., "130s", "45s") instead of minute:second format for clearer countdown

### Added
- **Resolve Export Progress Bar Script** (`resolve_busybar_progress.py`)
  - Python script that monitors DaVinci Resolve export progress in real-time
  - Displays visual progress bar and percentage on Busy Bar device via HTTP API
  - Automatically detects when exports start/stop and updates display accordingly
  - Features:
    - Resolve-style design with DaVinci Resolve logo on the left
    - Layered progress bar: dim green background with bright green progress overlay
    - Centered percentage display above the progress bar
    - Seconds remaining displayed on the right above the progress bar
    - Smooth animation with adaptive speed interpolation
    - Starts animating immediately, even before exact progress is known
    - Speeds up automatically when falling behind actual progress
    - Races to 100% when export completes
    - "DONE!" completion message displayed for 4 seconds
    - Configurable Busy Bar IP address and display settings
