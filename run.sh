#!/usr/bin/env sh
# Start the design tool on http://127.0.0.1:8000
set -e
python3 -m uvicorn api:app --app-dir app --reload --port "${PORT:-8000}"
