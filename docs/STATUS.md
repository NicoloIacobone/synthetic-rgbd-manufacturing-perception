# Status

Handoff note between sessions. **Read first.** Keep it short (≤ ~40 lines): update it at the end of every task, and overwrite outdated content rather than appending (history goes to DIARY.md and git).

- **Updated:** 2026-11-04, afternoon
- **Phase:** Phase 1. M1, M2 done (2026-11-03). **M3 done (2026-11-04) with one marginal gate failure**, accepted by the user (option 3a). **M4 not started:** it waits for the user's design review, which may change how M4 handles exposure and subpixel matching.
- **Protocol:** frozen at `protocol-v1`, unchanged by M3 (camera model in the separate `configs/camera_d415_ir.yaml`; the gate outcome is not a §5.12 deviation). §5.12: 1 deviation + 1 editorial.
- **Gates:** M5 Fri 6 Nov (A metrics); code freeze Sat 7 Nov 20:00.

## M3 results (commit 044ee81, dev seeds 1000–1001, 1280×720)
- Gate A-38 on the matte plane: (i) bias ≤ 0.29% z ✅; (ii) 100% valid ✅; (iv) band within 1 px of f·B/z ✅; **(iii) ❌ marginal: 5.03% / 5.07% valid at 0.42 / 0.43 m (limit ≤ 5%)**, 100% at 0.44–0.46 m. Cause: out-of-range false matches in clumps of ≈ 120 px that pass the 100 px speckle window. Expected effect on the experiment nil (nearest scene pixel 0.609 m, A-16). Goes to the report's "what did not work".
- Matcher settings stay as in 044ee81 (speckle window 100 px; option 3b = 200 px rejected; evidence `data/m3/logs/gate_variants_diagnostic.log`).
- A-32 (i)–(iii) pass. A-39: median 43.7 s/frame end to end (limit 262 s) → 110 frames ≈ 1.3–1.6 h; 1280×720 kept.

## Open items for M4 (nothing chosen yet; wait for the design review)
1. **Dark IR at fixed exposure** (A-42): gain 5700 calibrated on the 0.45 m plane gives scene means of 3.6–8.6 DN (of 255) on dev scenes 1000–1001. No exposure rule chosen.
2. **SGBM pixel-locking** (A-43): 58–64% of stereo disparities within ±0.125 px of an integer (25% if uniform); disparity error MAD 0.12 px, p95 0.28–0.30 px; striped ±5–10 mm depth error on a tilted view. Subpixel handling unchanged.
3. Then the planned M4: metal/matte + brightness matching (A-24), A-11, IR noise (A-12, target 0.07–0.11 px [S-13]), dev pilot; optional dot density (A-37). M5: re-check A-30.

## How to run (see script docstrings)
- BlenderProc env: `scripts/setup_blenderproc.sh` (D14). **Always run Blender through `scripts/bproc.sh`.**
- Planes + gate: `scripts/bproc.sh scripts/bproc_ir_plane.py --out data/m3/plane`, then `.venv/bin/python scripts/plane_gate.py data/m3/plane`.
- Scenes with IR + stereo + timing: `scripts/benchmark_m3.sh data/m3 1000 1001` (RGB only: `scripts/render_scenes.sh`).
- Tests: `.venv/bin/python -m pytest` (54 pass).

## Where things are
| Need | File |
|---|---|
| Requirements | `task_description.md` |
| Decisions, protocol, milestones, risks | `docs/PLAN.md` |
| Assumptions (A-38 tested-failed/accepted; A-41…A-43 new) | `docs/ASSUMPTIONS.md` |
| Camera-model parameters (not frozen) | `configs/camera_d415_ir.yaml` |
| Sources | `docs/SOURCES.md` |
| Report page budget | `docs/REPORT_PLAN.md` |
