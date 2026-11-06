#!/usr/bin/env bash
# RGB light rule on the dev scenes (A-69): decreasing energies, stops at the first that passes. RGB, depth and masks only, no IR.
# Usage: scripts/rgb_sweep.sh <out_root> [--fill <world_fill>]     one Blender process at a time
# Writes <out_root>/e<energy>/rule.json and a contact sheet, <out_root>/e<energy>/sheet.jpg.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
OUT=$1
FILL=()
[[ "${2:-}" == "--fill" ]] && FILL=(--rgb-world-fill "$3")
SEEDS=$(seq 1000 1004)
for E in 150 100 70 50 35 25 18 12; do
  D="$OUT/e$E"
  mkdir -p "$D/logs"
  for S in $SEEDS; do
    scripts/bproc.sh scripts/bproc_render_scene.py --scene-seed "$S" --out "$D" --rgb-light-energy "$E" "${FILL[@]+"${FILL[@]}"}" > "$D/logs/scene_$S.log" 2>&1
    $PY scripts/bop_gt_info.py "$D" "$S" >> "$D/logs/scene_$S.log" 2>&1
  done
  # shellcheck disable=SC2086
  R=$($PY scripts/select_rgb_light.py "$D" $SEEDS --out "$D/rule.json" --sheet "$D/sheet.jpg")
  echo "energy $E: $R"
  if echo "$R" | grep -q '"passes": true'; then
    echo "CHOSEN energy $E"
    exit 0
  fi
done
echo "NO_ENERGY_PASSES"
