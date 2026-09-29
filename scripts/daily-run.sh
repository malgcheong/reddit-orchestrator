#!/bin/bash
# Daily digest run (launchd entry point). Collects live, runs the loop, and pauses
# at approval (a Discord preview is sent if a webhook/bot is configured).
# Venv python directly: `uv run` hangs without spawning a child under launchd.
set -euo pipefail
cd "$(dirname "$0")/../orchestrator"
export PYTHONUNBUFFERED=1
exec .venv/bin/python -m orchestrator.run
