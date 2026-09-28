#!/bin/bash
# Daily digest run (launchd entry point). Collects live, runs the loop, and pauses
# at approval (a Discord preview is sent if a webhook/bot is configured).
set -euo pipefail
cd "$(dirname "$0")/../orchestrator"
exec /opt/homebrew/bin/uv run --no-sync python -m orchestrator.run
