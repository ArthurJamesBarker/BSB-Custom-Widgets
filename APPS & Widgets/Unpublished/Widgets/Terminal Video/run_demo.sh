#!/bin/bash
# Simple wrapper to run the remote demo with correct API version

export BUSY_API_VERSION=4.1.0
cd "$(dirname "$0")"
uv run python -m examples.remote --addr "$@"
