#!/usr/bin/env bash
# A-39 / A-32 (iii) benchmark: end-to-end wall time per frame of the full per-scene pipeline
# (scene set-up + physics + RGB/depth/segmentation + IR pairs metal-proxy and matte + export
# + BOP gt_info + SGBM for both passes + BOP consistency check), one scene at a time.
#   scripts/benchmark_m3.sh <out_root> <seed> [<seed> ...]
# Logs: <out_root>/logs/scene_<seed>.log ; timings: <out_root>/logs/benchmark.jsonl
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$1"; shift
mkdir -p "$OUT/logs"
[[ -f "$OUT/synthrgbd/models/models_info.json" ]] || "$REPO/.venv/bin/python" "$REPO/scripts/export_models.py" "$OUT"
now() { "$REPO/.venv/bin/python" -c 'import time; print(f"{time.time():.3f}")'; }
for SEED in "$@"; do
  LOG="$OUT/logs/scene_${SEED}.log"
  t0=$(now)
  "$REPO/scripts/bproc.sh" "$REPO/scripts/bproc_render_scene.py" --scene-seed "$SEED" --out "$OUT" --ir > "$LOG" 2>&1
  t1=$(now)
  "$REPO/.venv/bin/python" "$REPO/scripts/bop_gt_info.py" "$OUT" "$SEED" >> "$LOG" 2>&1
  t2=$(now)
  "$REPO/.venv/bin/python" "$REPO/scripts/stereo_scene.py" "$OUT" "$SEED" --sheet "$OUT/logs/stereo_sheet_${SEED}.png" >> "$LOG" 2>&1
  t3=$(now)
  "$REPO/.venv/bin/python" "$REPO/scripts/check_bop_scene.py" "$OUT" "$SEED" --sheet "$OUT/logs/sheet_${SEED}.png" >> "$LOG" 2>&1
  t4=$(now)
  echo "{\"seed\": $SEED, \"blender_s\": $(echo "$t1 - $t0" | bc), \"gt_info_s\": $(echo "$t2 - $t1" | bc), \"stereo_s\": $(echo "$t3 - $t2" | bc), \"check_s\": $(echo "$t4 - $t3" | bc), \"total_s\": $(echo "$t4 - $t0" | bc)}" | tee -a "$OUT/logs/benchmark.jsonl"
done
