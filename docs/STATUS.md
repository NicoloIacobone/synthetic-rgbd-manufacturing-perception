# Status

Handoff note between sessions. **Read first.** Keep it short (≤ ~40 lines): update it at the end of every task, and overwrite outdated content rather than appending (history goes to DIARY.md and git).

- **Updated:** 2026-11-04, afternoon
- **Phase:** Phase 1. M1, M2 done (2026-11-03). **M3 run 2026-11-04: stereo route implemented; gate NOT passed** (A-38 (iii) fails marginally). **Route decision pending with the user**; do not start M4 or switch route before it.
- **Protocol:** frozen at `protocol-v1`, unchanged by M3 (camera model in the separate `configs/camera_d415_ir.yaml`). §5.12: 1 deviation + 1 editorial.
- **Gates:** M3 Wed 4 Nov end of day (pending decision); M5 Fri 6 Nov; code freeze Sat 7 Nov 20:00.

## M3 results (commit 044ee81, dev seeds 1000–1001, 1280×720)
- Gate A-38 on matte plane: (i) bias ≤ 0.29% z ✅; (ii) 100% valid ✅; (iv) band within 1 px of f·B/z ✅; **(iii) ❌ 5.03% / 5.07% valid at 0.42 / 0.43 m (limit ≤ 5%)**, 100% at 0.44–0.46 m. Valid pixels below Min-Z are false-match blobs (~120 px) passing the 100 px speckle window.
- Diagnostics (not adopted): speckle window 200 → (iii) 0.34 / 0.41%, (i)(ii)(iv) unchanged; BlenderProc helper matcher with LR check → (iii) 16%, band fixed at 128 px without the A-40 fix.
- A-32: (i) linear (power ×2 → 1.9997, radiance ∝ z^−2.003); (ii) metal peak 1159× matte max, unclipped; (iii) export 0.13 s/image, SGBM 0.2–0.36 s/pair ✅.
- A-39: **median 43.7 s/frame end to end** (worst 51.5 s; limit 262 s) → 110 frames ≈ 1.3–1.6 h; keep 1280×720. ~8.5 MB/scene IR.
- Flags for M4: fixed exposure leaves scenes dark (mean 3.6–8.6 DN); SGBM pixel-locking (58–64% of disparities within ±0.125 px of an integer; striped ±5–10 mm error on tilted views).

## Decisions pending for the user
1. M3 gate route (A-38 iii): Route 2 (D7) / patched helper (D13) / keep stereo route with a logged deviation (accept as-is, or speckle window 200).
2. If the stereo route is kept: M4 handling of exposure (auto exposure?) and pixel-locking.

## How to run (see script docstrings)
- BlenderProc env: `scripts/setup_blenderproc.sh` (D14). **Always run Blender through `scripts/bproc.sh`.**
- Planes + gate: `scripts/bproc.sh scripts/bproc_ir_plane.py --out data/m3/plane`, then `.venv/bin/python scripts/plane_gate.py data/m3/plane`.
- Scenes with IR + stereo + timing: `scripts/benchmark_m3.sh data/m3 1000 1001` (RGB-only: `scripts/render_scenes.sh`).
- Tests: `.venv/bin/python -m pytest` (54 pass).

## Next steps
1. User decision above, then close M3 (log deviation in PLAN §5.12 / ASSUMPTIONS if the route stays).
2. M4: metal/matte + brightness matching (A-24), A-11, IR noise tuning (A-12, target 0.07–0.11 px [S-13]), exposure (A-42), pixel-locking (A-43), dev pilot; optional dot density (A-37).
3. M5: re-check A-30 when implementing the offset sweep.

## Where things are
| Need | File |
|---|---|
| Requirements | `task_description.md` |
| Decisions, protocol, milestones, risks | `docs/PLAN.md` |
| Assumptions (A-41…A-43 new; A-38 tested-failed) | `docs/ASSUMPTIONS.md` |
| Camera-model parameters (not frozen) | `configs/camera_d415_ir.yaml` |
| Sources | `docs/SOURCES.md` |
| Report page budget | `docs/REPORT_PLAN.md` |
