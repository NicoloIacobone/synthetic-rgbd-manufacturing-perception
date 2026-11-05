#!/bin/zsh
# M5 metrics, in order (ledger "M5 run scope"). Safe to re-run: run_eval.py keeps finished result files.
# Usage: scripts/run_m5.sh [results_dir]   (default data/m5/results_v2; §5.8 goes to <results_dir>_s58)
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
R=${1:-data/m5/results_v2}
S=${R}_s58
ALL=(C1 C2a C2b C3 C4 C3r02 C3r04 C3nogloss C4bright)
PROTOCOL=(C1 C2a C2b C3 C4)
stamp() { print -- "=== $(date '+%H:%M:%S') $1"; }

stamp "A1 on all conditions + Task B"           # run_eval.py runs the §5.11 sanity check first and stops if it fails
$PY scripts/run_eval.py data/m5 $R 0 49 --conditions $ALL --offsets 10
stamp "statistics, A1 and Task B (interim)"
$PY scripts/stats_m5.py $R --out $R/stats.json
stamp "offset sweep, protocol conditions"
$PY scripts/run_eval.py data/m5 $R 0 49 --conditions $PROTOCOL --offsets 2 5 20 --no-task-b
stamp "statistics, with the sweep"
$PY scripts/stats_m5.py $R --out $R/stats.json
stamp "sensor metrics"
$PY scripts/sensor_metrics.py data/m5 {0..49} --conditions $ALL --out $R/sensor.json > $R/logs/sensor.log 2>&1
stamp "§5.8 on seeds 0-9: strict vs loose, noise redraws"
$PY scripts/run_eval.py data/m5 $S 0 9 --conditions C3loose C4loose C3redraw1 C3redraw2 --offsets 10 --no-task-b
$PY scripts/sensor_metrics.py data/m5 {0..9} --conditions C3 C4 C3loose C4loose C3nouniq C3nolr C3nospeckle --out $S/sensor.json > $S/logs/sensor.log 2>&1
$PY scripts/robustness_s58.py $R $S --out $S/robustness.json
stamp "figure"
$PY scripts/fig_results.py $R/stats.json $R/sensor.json --out data/m5/figures/results.png
stamp "ALL_DONE"
