#!/usr/bin/env bash
# Render scenes one at a time (8 GB), resuming after an interruption, then add the C2 depth.
#   scripts/render_test.sh <out_root> <first_seed> <last_seed>
# A scene counts as finished when its last extra pass has depth for view 1. Stops at the first failure.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$1"; FIRST="$2"; LAST="$3"
for ((S = FIRST; S <= LAST; S++)); do
  SC="$OUT/synthrgbd/train_pbr/$(printf %06d "$S")"
  if [[ -f "$SC/depth_stereo_r04/000001.png" && -f "$SC/bop_check.json" ]]; then echo "scene $S kept"; continue; fi
  "$REPO/scripts/benchmark_m3.sh" "$OUT" "$S"
done
"$REPO/.venv/bin/python" "$REPO/scripts/c2_depth.py" "$OUT" $(seq "$FIRST" "$LAST")
echo ALL_DONE
