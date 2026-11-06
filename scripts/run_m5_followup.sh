#!/usr/bin/env bash
# Descriptive follow-ups on a rendered test set, each in its own depth folders; no protocol depth or result is touched.
# Usage: scripts/run_m5_followup.sh <data_root> <results_dir> match | eval | redraw | robust
#   match   seeds 0-9: §5.8 matcher variants (A-63) and sensor noise with e_per_dn 1 (A-64)
#   eval    seeds 0-9: ICP at 10 mm / 10 deg and sensor metrics, in <results_dir>_s58
#   redraw  seeds 0-49: two new sensor-noise draws on the metal pass, ICP at 10 mm / 10 deg (A-59), in <results_dir>_redraw
#   robust  the §5.8 flip rule and the redraw summary, after eval and redraw
# Safe to re-run: stereo_scene.py is deterministic from the stored IR images and run_eval.py keeps finished result files.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
D=$1
R=$2
S=${R}_s58
RD=${R}_redraw
SEEDS=$(seq 0 9)
ALL_SEEDS=$(seq 0 49)
stamp() { echo "=== $(date '+%H:%M:%S') $1"; }
mkdir -p "$S/logs" "$RD/logs"
case "${3:-}" in
  match)
    for K in $SEEDS; do
      stamp "matching scene $K"
      $PY scripts/stereo_scene.py "$D" "$K" --variant looselr --passes metal matte > "$S/logs/stereo_looselr_$K.log" 2>&1
      for V in nolr1000 nouniq nospeckle; do
        $PY scripts/stereo_scene.py "$D" "$K" --variant "$V" --passes metal > "$S/logs/stereo_${V}_$K.log" 2>&1
      done
      $PY scripts/stereo_scene.py "$D" "$K" --e-per-dn 1 --passes metal matte > "$S/logs/stereo_e1_$K.log" 2>&1
    done
    stamp "MATCH_DONE"
    ;;
  eval)
    stamp "ICP at 10 mm / 10 deg"
    $PY scripts/run_eval.py "$D" "$S" 0 9 --conditions C3looselr C4looselr C3e1 C4e1 --offsets 10 --no-task-b
    stamp "sensor metrics"
    # shellcheck disable=SC2086
    $PY scripts/sensor_metrics.py "$D" $SEEDS --conditions C3 C4 C3looselr C4looselr C3nolr1000 C3nouniq C3nospeckle C3e1 C4e1 \
      --out "$S/sensor.json" > "$S/logs/sensor.log" 2>&1
    stamp "EVAL_DONE"
    ;;
  redraw)
    for K in $ALL_SEEDS; do
      stamp "noise redraws, scene $K"
      for N in 1 2; do
        $PY scripts/stereo_scene.py "$D" "$K" --noise-redraw "$N" --passes metal > "$RD/logs/stereo_redraw${N}_$K.log" 2>&1
      done
    done
    stamp "ICP at 10 mm / 10 deg"
    $PY scripts/run_eval.py "$D" "$RD" 0 49 --conditions C3redraw1 C3redraw2 --offsets 10 --no-task-b
    stamp "sensor metrics"
    # shellcheck disable=SC2086
    $PY scripts/sensor_metrics.py "$D" $ALL_SEEDS --conditions C3 C3redraw1 C3redraw2 --out "$RD/sensor.json" > "$RD/logs/sensor.log" 2>&1
    stamp "REDRAW_DONE"
    ;;
  robust)
    stamp "§5.8 flip rule"
    $PY scripts/robustness_s58.py "$R" "$S" --loose C3looselr C4looselr --redraw-dir "$RD" --out "$S/robustness.json"
    stamp "redraw summary"
    $PY scripts/redraw_summary.py "$R" "$RD" --out "$RD/redraw.json"
    stamp "stop rules on §5.8 and the redraws"
    $PY scripts/check_stop.py --robustness "$S/robustness.json" --redraw "$RD/redraw.json"
    stamp "ROBUST_DONE"
    ;;
  *)
    echo "usage: $0 <data_root> <results_dir> match|eval|redraw|robust" >&2
    exit 2
    ;;
esac
