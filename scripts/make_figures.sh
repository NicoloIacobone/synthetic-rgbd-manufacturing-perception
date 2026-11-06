#!/usr/bin/env bash
# All report figures from a finished final run (A-71). Regenerable: reads results and scenes, writes only <test_root>/figures and the distance table.
# Usage: scripts/make_figures.sh <test_root> <dev_root> <robi_json>     e.g. data/hfov71/test data/hfov71/dev data/m5/robi/zigzag.json
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
T=$1
DEV=$2
ROBI=$3
R=$T/results
F=$T/figures
mkdir -p "$F"
OMP_NUM_THREADS=2 $PY scripts/distance_table.py "$T" "$R" --out "$R/distance.json"
$PY scripts/fig_results.py "$R/stats.json" "$R/sensor.json" "$R/distance.json" --out "$F/results.png"
$PY scripts/fig_robi.py "$R/sensor.json" "$T/robi_sim/ir_appearance.json" "$ROBI" --out "$F/robi.png" \
  --note "ROBI Zigzag: 26 views at 0.32-0.41 m, one object. Our scenes: 0.61-1.24 m, 50 scenes; appearance on seeds 0-9. Compatible is not validated."
OMP_NUM_THREADS=2 $PY scripts/fig_examples.py "$T" "$R" --out "$F/examples.png"
$PY scripts/fig_mechanism.py "$DEV" "reflections off" "$DEV" "reflections on (C3)" -1 -1 --pass-a nogloss --out "$F/mechanism.png"
