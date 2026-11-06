#!/usr/bin/env bash
# The whole final run after the configuration lock, one stage at a time; resumes from the last finished stage. Stops on a stop rule.
# Usage: scripts/run_final.sh <test_root> <dev_root>     e.g. data/hfov71/test data/hfov71/dev
# Stage markers: <test_root>/.done_<stage>. Heartbeat: <test_root>/heartbeat, updated every minute while the run is alive.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
D=$1
DEV=$2
R=$D/results
A=${R}_ambient
mkdir -p "$D"
(while sleep 60; do date '+%F %T' > "$D/heartbeat"; done) &
HEART=$!
trap 'kill "$HEART" 2>/dev/null || true' EXIT
stage() {
  local name=$1; shift
  if [[ -f "$D/.done_$name" ]]; then echo "=== $(date '+%H:%M:%S') kept $name"; return; fi
  echo "=== $(date '+%H:%M:%S') START $name"
  "$@"
  touch "$D/.done_$name"
  echo "=== $(date '+%H:%M:%S') END $name"
}
level=$($PY -c "from synthrgbd.config import load_config, REPO_ROOT; print(load_config(REPO_ROOT / 'configs' / 'camera_d415_ir.yaml')['ambient_test']['level'])" 2>/dev/null \
  || PYTHONPATH=src $PY -c "from synthrgbd.config import load_config, REPO_ROOT; print(load_config(REPO_ROOT / 'configs' / 'camera_d415_ir.yaml')['ambient_test']['level'])")

ambient_render() { for K in $(seq 0 9); do scripts/bproc.sh scripts/bproc_render_scene.py --scene-seed "$K" --out "$D" --ambient > "$D/logs/ambient_$K.log" 2>&1; done; }
ambient_match() { mkdir -p "$A/logs"; for K in $(seq 0 9); do $PY scripts/stereo_scene.py "$D" "$K" --ambient > "$A/logs/stereo_amb_$K.log" 2>&1; done; }
ambient_eval() {
  $PY scripts/run_eval.py "$D" "$A" 0 9 --conditions C3amb C4amb --offsets 10 --no-task-b
  # shellcheck disable=SC2046
  $PY scripts/sensor_metrics.py "$D" $(seq 0 9) --conditions C3 C4 C3amb C4amb --out "$A/sensor.json" > "$A/logs/sensor.log" 2>&1
  # shellcheck disable=SC2046
  $PY scripts/ir_appearance.py "$D" $(seq 0 9) --passes metal matte --ambient --out "$A/ir_appearance.json"
  $PY scripts/ambient_summary.py "$R" "$A" --out "$A/ambient.json"
}
ambient_stop() { $PY scripts/check_stop.py --ambient "$A/ambient.json"; }
appearance() {
  mkdir -p "$D/robi_sim"
  # shellcheck disable=SC2046
  $PY scripts/ir_appearance.py "$D" $(seq 0 9) --passes metal matte r02 r04 --out "$D/robi_sim/ir_appearance.json"
}
mechanism() {
  mkdir -p "$D/mechanism"
  # shellcheck disable=SC2046
  $PY scripts/mechanism_check.py "$DEV" $(seq 1000 1004) --out "$D/mechanism/dev_final.json" > "$D/mechanism/dev_final.log" 2>&1
}
unlit() { $PY scripts/unlit_share.py "$D" 0 49 --out "$D/unlit_share.json"; }

stage render scripts/render_test.sh "$D" 0 49
stage unlit unlit
stage metrics scripts/run_m5.sh "$D" "$R"
stage s58_match scripts/run_m5_followup.sh "$D" "$R" match
stage s58_eval scripts/run_m5_followup.sh "$D" "$R" eval
stage redraw scripts/run_m5_followup.sh "$D" "$R" redraw
stage robust scripts/run_m5_followup.sh "$D" "$R" robust
stage mechanism mechanism
stage appearance appearance
if [[ "$level" == "None" ]]; then
  echo "=== ambient test skipped: 21 DN is not reachable or the level is not set (A-70)"
else
  stage ambient_render ambient_render
  stage ambient_match ambient_match
  stage ambient_eval ambient_eval
  stage ambient_stop ambient_stop
fi
echo "=== $(date '+%H:%M:%S') ALL_DONE"
