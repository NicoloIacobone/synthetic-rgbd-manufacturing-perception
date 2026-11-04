# Status

Handoff note between sessions. **Read first.** Keep it short (≤ ~40 lines): update it at the end of every task, and overwrite outdated content rather than appending (history goes to DIARY.md and git).

- **Updated:** 2026-11-04, late
- **Phase:** Phase 1, M4. Steps 1–2 done; step 3 harness selection and pilot done on dev. **STOPPED (criterion b): C3 at floor** (A1 recall 0.00 at every offset; Task B 0.00). Waiting for the user's decision (options in the chat report).
- **Protocol:** frozen at `protocol-v1`. §5.12: 4 rows (latest: C2b + fixed sequence; instance inclusion), logged 2026-11-04.
- **Gates:** M5 Fri 6 Nov (A metrics); code freeze Sat 7 Nov 20:00. Report skeleton starts Thu evening.

## M4 order (user, 2026-11-04)
1. ICP harness + C1 zero-offset sanity check (§5.11) on the ideal depth of dev scenes 1000–1001, then the suction code. No hyperparameter tuning yet. **STOP and report the sanity result.**
2. Roughness (A-11, awaiting the user) → A-24 albedo matching → exposure rule (A-42) → IR noise + anchor (a) → re-measure locking and metal statistics.
3. C2a/C2b (C2b written into `configs/default.yaml`), render dev scenes 1000–1004 in all conditions, tune the harness with the pooled worst-case rule (ledger), pilot (ceiling/floor, MDE). **STOP before any test scene is rendered.**
- Propose extra measurements; never run them unasked.
- ROBI (b): optional #1, only after Friday's Task A metrics, time box 3 h.

## How to run (see script docstrings)
- BlenderProc env: `scripts/setup_blenderproc.sh` (D14). **Always run Blender through `scripts/bproc.sh`.**
- Planes + gate: `scripts/bproc.sh scripts/bproc_ir_plane.py --out data/m3/plane`, then `.venv/bin/python scripts/plane_gate.py data/m3/plane`.
- Scenes with IR + stereo + timing: `scripts/benchmark_m3.sh data/m3 1000 1001`.
- Task A: `.venv/bin/python scripts/pose_eval.py data/m3 1000 1001 --condition C1 --offset 0 0 --out data/m4/pose/<name>.jsonl`; Task B: `scripts/suction_eval.py` (same arguments, no --offset). Harness settings: `configs/harness.yaml` (provisional).
- Tests: `.venv/bin/python -m pytest` (75 pass).

## Docs until Saturday (slimmed)
DIARY: one terse entry per step. ASSUMPTIONS: one-line rows. SOURCES: only items the report cites. PLAN: §5.12 rows only.
