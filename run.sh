#!/usr/bin/env sh
# Start the design tool on http://127.0.0.1:8000
set -e
# networks are held only while it runs: none from an earlier run
rm -f data/designs.db data/designs.db-wal data/designs.db-shm
python3 -m uvicorn api:app --app-dir app --reload --port "${PORT:-8000}"
