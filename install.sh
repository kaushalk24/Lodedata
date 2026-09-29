#!/usr/bin/env sh
# Install the Design Assistant on a Linux server.
#
# Makes a Python environment in .venv next to this file and installs the
# packages into it -- from the wheels/ folder shipped in the zip when it is
# there (no internet needed), otherwise from the internet.
#
#   ./install.sh                      uses python3
#   PYTHON=python3.12 ./install.sh    uses another Python (3.10 or newer)
set -e
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python was not found ($PYTHON). Install Python 3.10 or newer." >&2
  exit 1
fi
if ! "$PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
  echo "$("$PYTHON" --version) is too old: Python 3.10 or newer is needed." >&2
  exit 1
fi
if ! "$PYTHON" -m venv .venv; then
  echo "Could not make a Python environment. On Debian/Ubuntu install it with:" >&2
  echo "  sudo apt install python3-venv" >&2
  exit 1
fi

if [ -d wheels ] && ls wheels/*.whl >/dev/null 2>&1; then
  echo "Installing the packages from wheels/ (offline)..."
  .venv/bin/python -m pip install --no-index --find-links wheels -r requirements.txt
else
  echo "Installing the packages from the internet..."
  .venv/bin/python -m pip install -r requirements.txt
fi

mkdir -p data
echo
echo "Installed. Start the server with:  ./start-server.sh"
echo "Run the tests with:                ./run-tests.sh"
