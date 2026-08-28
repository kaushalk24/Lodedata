#!/bin/sh
# OpenLode Design Assistant -- double-click launcher for macOS and Linux.
cd "$(dirname "$0")" || exit 1

printf '\n  OpenLode Design Assistant\n  =========================\n\n'

if [ ! -f "lode/__main__.py" ]; then
    printf '  PROBLEM: this launcher is not in the OpenLode folder.\n'
    printf '  It must sit next to the "lode" folder.\n\n'
    printf '  Currently in: %s\n\n' "$(pwd)"
    read -r _ 2>/dev/null
    exit 1
fi

PY=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done

if [ -z "$PY" ]; then
    printf '  PROBLEM: Python was not found.\n'
    printf '  Install Python 3.10 or newer from https://python.org/downloads\n\n'
    read -r _ 2>/dev/null
    exit 1
fi

printf '  Starting with: %s\n' "$PY"
printf '  Your browser will open at http://127.0.0.1:8765\n\n'
printf '  Leave this window open while you work; Ctrl+C stops it.\n\n'

"$PY" -m lode serve
CODE=$?
if [ "$CODE" -ne 0 ]; then
    printf '\n  OpenLode stopped with error code %s.\n\n' "$CODE"
    read -r _ 2>/dev/null
fi
