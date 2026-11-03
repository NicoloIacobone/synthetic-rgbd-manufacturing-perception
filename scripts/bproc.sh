#!/usr/bin/env bash
# Run a BlenderProc script with the repo-local Blender (blender/, gitignored) and a repo-local temp
# dir. Always use this wrapper: plain `blenderproc run` defaults to ~/blender and downloads a
# second Blender there.
#   scripts/bproc.sh scripts/bproc_render_scene.py --scene-seed 1000 --out data/m2
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$REPO/data/tmp"
exec "$REPO/.venv-bproc/bin/blenderproc" run \
  --blender-install-path "$REPO/blender" \
  --temp-dir "$REPO/data/tmp" "$@"
