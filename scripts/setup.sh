#!/usr/bin/env bash
# Install from zero: checks for Python 3.11, creates .venv from requirements.lock.txt and runs the tests.
# Usage: scripts/setup.sh            (PYTHON=/path/to/python3.11 scripts/setup.sh to choose the interpreter)
# BlenderProc is optional and separate: scripts/setup_blenderproc.sh, needed only to render new scenes.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3.11}
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "ERROR: '$PY' was not found. This project needs Python 3.11 (macOS: brew install python@3.11), or set PYTHON=/path/to/python3.11." >&2
  exit 1
fi
VER=$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
if [ "$VER" != "3.11" ]; then
  echo "ERROR: '$PY' is Python $VER. This project needs Python 3.11, because requirements.lock.txt is resolved for it." >&2
  exit 1
fi
if [ ! -x .venv/bin/python ]; then
  "$PY" -m venv .venv
fi
.venv/bin/python -m pip install --quiet -r requirements.lock.txt
.venv/bin/python -m pytest -q
echo "SETUP_OK: analysis environment ready in .venv. Next: .venv/bin/python scripts/quick_run.py"
