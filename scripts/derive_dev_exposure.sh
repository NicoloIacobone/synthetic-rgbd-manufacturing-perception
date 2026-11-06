#!/usr/bin/env bash
# One iteration of the setpoint + C4 albedo rule on the dev scenes (ledger "Setpoint and C4 albedo (71°)"): render metal and matte only with
# the values in configs/camera_d415_ir.yaml, then the setpoint rule (saturation only) and the clipped-mean albedo rule (radiance only).
# Usage: scripts/derive_dev_exposure.sh <out_root>     one Blender process at a time
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
OUT=$1
SEEDS=$(seq 1000 1004)
mkdir -p "$OUT/logs"
for S in $SEEDS; do
  scripts/bproc.sh scripts/bproc_render_scene.py --scene-seed "$S" --out "$OUT" --ir --extra-pass none > "$OUT/logs/scene_$S.log" 2>&1
  $PY scripts/bop_gt_info.py "$OUT" "$S" >> "$OUT/logs/scene_$S.log" 2>&1
done
# shellcheck disable=SC2086
$PY scripts/select_setpoint.py "$OUT" $SEEDS | tee "$OUT/select_setpoint.log" | grep -E '"setpoint_dn": (10|20|30|40),|CHOSEN'
# shellcheck disable=SC2086
$PY scripts/mechanism_compare_render.py "$OUT" "$OUT" $SEEDS --out "$OUT/albedo_rule.json" | grep -E 'rule_A24_albedo_clipped_a|n_views|all_same'
