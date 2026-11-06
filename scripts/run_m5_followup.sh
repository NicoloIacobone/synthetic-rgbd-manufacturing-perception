#!/usr/bin/env bash
# Follow-ups on seeds 0-9 decided after M5 (A-63, A-64), each in its own depth folders; no protocol depth or result is touched.
# Usage: scripts/run_m5_followup.sh match   then   scripts/run_m5_followup.sh eval   (results in data/m5/results_s58_v2)
# A-63: §5.8 with the left-right check really off. A-64: sensor noise with e_per_dn 1 instead of 0.087.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
R=data/m5/results_s58_v2
SEEDS=$(seq 0 9)
stamp() { echo "=== $(date '+%H:%M:%S') $1"; }
mkdir -p "$R/logs"
case "${1:-}" in
  match)
    for S in $SEEDS; do
      stamp "matching scene $S"
      $PY scripts/stereo_scene.py data/m5 "$S" --variant looselr --passes metal matte > "$R/logs/stereo_looselr_$S.log" 2>&1
      $PY scripts/stereo_scene.py data/m5 "$S" --variant nolr1000 --passes metal > "$R/logs/stereo_nolr1000_$S.log" 2>&1
      $PY scripts/stereo_scene.py data/m5 "$S" --e-per-dn 1 --passes metal matte > "$R/logs/stereo_e1_$S.log" 2>&1
    done
    stamp "MATCH_DONE"
    ;;
  eval)
    stamp "ICP at 10 mm / 10 deg"
    $PY scripts/run_eval.py data/m5 "$R" 0 9 --conditions C3looselr C4looselr C3e1 C4e1 --offsets 10 --no-task-b
    stamp "sensor metrics"
    # shellcheck disable=SC2086
    $PY scripts/sensor_metrics.py data/m5 $SEEDS --conditions C3 C4 C3loose C4loose C3looselr C4looselr C3nolr1000 C3e1 C4e1 \
      --out "$R/sensor.json" > "$R/logs/sensor.log" 2>&1
    stamp "§5.8 flip rule"
    $PY scripts/robustness_s58.py data/m5/results_v2 "$R" --loose C3looselr C4looselr --redraw-dir data/m5/results_v2_s58 \
      --out "$R/robustness.json"
    stamp "EVAL_DONE"
    ;;
  *)
    echo "usage: $0 match|eval" >&2
    exit 2
    ;;
esac
