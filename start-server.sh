#!/usr/bin/env sh
# Start the Design Assistant for everyone on the network.
#
#   ./start-server.sh                  http://<this server>:8000
#   PORT=8600 ./start-server.sh        another port
#   HOST=127.0.0.1 ./start-server.sh   only this machine (behind a proxy)
#   WORKERS=2 ./start-server.sh        server processes (default: one per
#                                      CPU core, at most 4)
#
# The networks people open are kept in data/designs.db (LODEDATA_DB to put
# it elsewhere).
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Not installed yet: run ./install.sh first." >&2
  exit 1
fi
if [ -z "$WORKERS" ]; then
  WORKERS=$(nproc 2>/dev/null || echo 1)
  if [ "$WORKERS" -gt 4 ]; then WORKERS=4; fi
fi
export LODEDATA_DB="${LODEDATA_DB:-$(pwd)/data/designs.db}"
exec .venv/bin/python -m uvicorn api:app --app-dir app \
  --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" --workers "$WORKERS" --proxy-headers
