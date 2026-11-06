#!/usr/bin/env bash
# Task A, Task B, statistics and sensor metrics on a rendered test set. Safe to re-run: run_eval.py keeps finished result files.
# Usage: scripts/run_m5.sh <data_root> <results_dir>     both explicit, so no earlier data folder can be touched by accident
# Stops with exit code 3 if the §5.11 check fails or a stop rule fires on the primary endpoint (ledger "Final-run stop rules").
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
D=$1
R=$2
ALL=(C1 C2a C2b C3 C4 C3r02 C3r04 C3nogloss C4bright)
PROTOCOL=(C1 C2a C2b C3 C4)
stamp() { echo "=== $(date '+%H:%M:%S') $1"; }

stamp "A1 on all conditions + Task B"           # run_eval.py runs the §5.11 sanity check first and stops if it fails
$PY scripts/run_eval.py "$D" "$R" 0 49 --conditions "${ALL[@]}" --offsets 10
stamp "statistics, A1 and Task B (interim)"
$PY scripts/stats_m5.py "$R" --out "$R/stats.json"
stamp "stop rules on the primary endpoint"
$PY scripts/check_stop.py --stats "$R/stats.json"
stamp "offset sweep, protocol conditions"
$PY scripts/run_eval.py "$D" "$R" 0 49 --conditions "${PROTOCOL[@]}" --offsets 2 5 20 --no-task-b
stamp "statistics, with the sweep"
$PY scripts/stats_m5.py "$R" --out "$R/stats.json"
stamp "sensor metrics"
# shellcheck disable=SC2046
$PY scripts/sensor_metrics.py "$D" $(seq 0 49) --conditions "${ALL[@]}" --out "$R/sensor.json" > "$R/logs/sensor.log" 2>&1
stamp "M5_METRICS_DONE"
