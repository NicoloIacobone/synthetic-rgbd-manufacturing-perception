#!/usr/bin/env bash
# Render scenes one at a time (8 GB machine), then add BOP gt_info and run the consistency check.
#   scripts/render_scenes.sh <out_root> <seed> [<seed> ...]
# Logs: <out_root>/logs/scene_<seed>.log
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$1"; shift
mkdir -p "$OUT/logs"
[[ -f "$OUT/synthrgbd/models/models_info.json" ]] || "$REPO/.venv/bin/python" "$REPO/scripts/export_models.py" "$OUT"
for SEED in "$@"; do
  LOG="$OUT/logs/scene_${SEED}.log"
  "$REPO/scripts/bproc.sh" "$REPO/scripts/bproc_render_scene.py" --scene-seed "$SEED" --out "$OUT" > "$LOG" 2>&1
  "$REPO/.venv/bin/python" "$REPO/scripts/bop_gt_info.py" "$OUT" "$SEED" >> "$LOG" 2>&1
  "$REPO/.venv/bin/python" "$REPO/scripts/check_bop_scene.py" "$OUT" "$SEED" --sheet "$OUT/logs/sheet_${SEED}.png" >> "$LOG" 2>&1
  echo "scene $SEED done"
done
