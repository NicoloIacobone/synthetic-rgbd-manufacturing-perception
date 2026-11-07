#!/usr/bin/env bash
# Dot-density test on seeds 0-9 (A-74, A-76), descriptive: render, match, evaluate, summarise. Only new folders are written.
# Usage: scripts/run_dots_test.sh <test_root> [dots]     e.g. data/hfov71/test 60000; dots is 10000 (default), 30000 (control) or 60000
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
D=$1
N=${2:-10000}
L=$((N / 1000))k
R=$D/results
O=${R}_dots$N
stamp() { echo "=== $(date '+%H:%M:%S') $1"; }
mkdir -p "$O/logs"
for K in $(seq 0 9); do
  if [ -f "$D/synthrgbd/train_pbr/$(printf %06d "$K")/ir_dots$N/meta.json" ]; then
    stamp "scene $K already rendered"
    continue
  fi
  stamp "render scene $K"
  scripts/bproc.sh scripts/bproc_render_scene.py --scene-seed "$K" --out "$D" --dots "$N" > "$O/logs/render_$K.log" 2>&1
  grep DOT_TEST "$O/logs/render_$K.log"
done
stamp RENDER_DONE
for K in $(seq 0 9); do
  $PY scripts/stereo_scene.py "$D" "$K" --dots "$N" > "$O/logs/stereo_$K.log" 2>&1
done
stamp MATCH_DONE
$PY scripts/run_eval.py "$D" "$O" 0 9 --conditions "C3dots$L" "C4dots$L" --offsets 10 --no-task-b
stamp EVAL_DONE
# shellcheck disable=SC2046
$PY scripts/sensor_metrics.py "$D" $(seq 0 9) --conditions C3 C4 "C3dots$L" "C4dots$L" --out "$O/sensor.json" > "$O/logs/sensor.log" 2>&1
# shellcheck disable=SC2046
$PY scripts/ir_appearance.py "$D" $(seq 0 9) --passes metal matte --dots "$N" --out "$O/ir_appearance.json"
$PY scripts/dots_summary.py "$R" "$O" --count "$N" --out "$O/dots.json"
stamp DOTS_DONE
