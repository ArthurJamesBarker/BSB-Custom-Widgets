#!/usr/bin/env bash
# Run from any directory (use && in the shell — not the word "then"):
#   bash "/path/to/Subtitles/run_subtitles.sh"
#   SUBTITLE_MIC_DEVICE=3 bash "/path/to/Subtitles/run_subtitles.sh"
# From inside Subtitles: chmod +x run_subtitles.sh && ./run_subtitles.sh
set -euo pipefail
cd "$(dirname "$0")"
exec python3 subtitle_widget.py "$@"
