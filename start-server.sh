#!/usr/bin/env sh
# Start the Design Assistant for everyone on the network.
#
#   ./start-server.sh                  http://<this server>:8000
#   PORT=8600 ./start-server.sh        another port
#   HOST=127.0.0.1 ./start-server.sh   only this machine (behind a proxy)
#
# The networks people open are kept in data/designs.db (LODEDATA_DB to put
# it elsewhere).  Keep it to one server process: changes to a network are
# taken one at a time inside the process.
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Not installed yet: run ./install.sh first." >&2
  exit 1
fi
export LODEDATA_DB="${LODEDATA_DB:-$(pwd)/data/designs.db}"
exec .venv/bin/python -m uvicorn api:app --app-dir app \
  --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" --proxy-headers
