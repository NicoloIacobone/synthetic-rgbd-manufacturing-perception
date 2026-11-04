# Status

Handoff note between sessions. **Read first.** Keep it short (≤ ~40 lines): update it at the end of every task, and overwrite outdated content rather than appending (history goes to DIARY.md and git).

- **Updated:** 2026-11-04, evening
- **Phase:** Phase 1. M1–M3 done (M3 with the marginal gate failure A-38 iii, option 3a). **Pre-M4 design review done; decisions recorded** (ASSUMPTIONS A-11, A-14, A-15, A-18, A-24, A-42, A-43, new A-44–A-47 and the **tuning ledger**; SOURCES S-05, S-13, new S-14). **M4 in progress.**
- **Protocol:** frozen at `protocol-v1`. **Pending:** a §5.12 row (H-1 uses C2b at ε_d = 0.26 px; "C1 ≥ C2" descriptive; fixed-sequence C1–C3 → C2b–C3 → C3–C4 at α = 0.05). The user approved the content; the row text waits for the user's OK before it goes into PLAN.md.
- **Gates:** M5 Fri 6 Nov (A metrics); code freeze Sat 7 Nov 20:00. Report skeleton starts Thu evening.

## M4 order (user, 2026-11-04)
1. ICP harness + C1 zero-offset sanity check (§5.11) on the ideal depth of dev scenes 1000–1001, then the suction code. No hyperparameter tuning yet. **STOP and report the sanity result.**
2. A-24 albedo matching → exposure rule (A-42) → IR noise + anchor (a) → roughness by rationale (A-11; search for a source first) → re-measure locking and metal statistics.
3. C2a/C2b (C2b written into `configs/default.yaml`), render dev scenes 1000–1004 in all conditions, tune the harness with the pooled worst-case rule (ledger), pilot (ceiling/floor, MDE). **STOP before any test scene is rendered.**
- Propose extra measurements; never run them unasked.
- ROBI (b): optional #1, only after Friday's Task A metrics, time box 3 h.

## How to run (see script docstrings)
- BlenderProc env: `scripts/setup_blenderproc.sh` (D14). **Always run Blender through `scripts/bproc.sh`.**
- Planes + gate: `scripts/bproc.sh scripts/bproc_ir_plane.py --out data/m3/plane`, then `.venv/bin/python scripts/plane_gate.py data/m3/plane`.
- Scenes with IR + stereo + timing: `scripts/benchmark_m3.sh data/m3 1000 1001`.
- Tests: `.venv/bin/python -m pytest` (54 pass).

## Docs until Saturday (slimmed)
DIARY: one terse entry per step. ASSUMPTIONS: one-line rows. SOURCES: only items the report cites. PLAN: §5.12 rows only.
