#!/usr/bin/env sh
# Run the test suite.
#
# The checks against real Lode Data files run when the files are in
# samples/ (see samples/README.md), or wherever LODEDATA_SAMPLES points;
# without them those checks are skipped and the rest still run.  The browser
# checks (tests/test_ui.py) also need Playwright and Chromium -- see DEPLOY.md.
#
#   ./run-tests.sh                 everything
#   ./run-tests.sh -k sn001        only the tests whose name has "sn001"
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Not installed yet: run ./install.sh first." >&2
  exit 1
fi
exec .venv/bin/python -m pytest -q "$@"
