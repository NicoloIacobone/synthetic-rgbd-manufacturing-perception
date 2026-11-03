# Status

Handoff note between sessions. **Read first.** Keep it short (≤ ~40 lines): update it at the end of every task, and overwrite outdated content rather than appending (history goes to DIARY.md and git).

- **Updated:** 2026-11-03, evening
- **Phase:** Phase 1. **M1 and M2 done** (commits 0c85357 … 81e583b). M3 not started; it starts only when the user asks.
- **Protocol:** frozen at `protocol-v1`. Deviations: 1 (Task B per part type, PLAN §5.12).
- **Gates:** M3 Wed 4 Nov, M5 Fri 6 Nov, code freeze Sat 7 Nov 20:00.

## How to run (see script docstrings)
- BlenderProc env: `scripts/setup_blenderproc.sh` (`.venv-bproc` from `requirements-bproc.lock.txt` + macOS patch in `patches/`, D14). **Always run Blender through `scripts/bproc.sh`** (plain `blenderproc run` downloads a second Blender into ~/blender).
- Scenes: `scripts/render_scenes.sh data/m2 1000 1001` → BOP dataset in `data/m2/synthrgbd/` + logs and contact sheets in `data/m2/logs/`.
- Checks: `scripts/check_intrinsics.py` (A-28), `scripts/check_bop_scene.py` (GT consistency). Tests: `.venv/bin/python -m pytest` (38 pass).

## Measured (dev seeds 1000–1001, 1280×720, Metal GPU + CPU)
- RGB + depth + segmentation: 8.4–8.6 s/frame at 64 samples; 25 s per 2-view scene end to end; 2 MB/scene. IR renders (M3) not measured.
- GT consistency: worst p95 back-projection error 0.047 mm; K = A-28 within 4e-5 px; re-render bit-identical in poses and depth.

## Open items waiting for the user
- None. Decided 2026-11-03: Task B reported per part type too (deviation logged in PLAN §5.12); keep the local BlenderProc patch (D14); BlenderProc pinned in `requirements-bproc.txt` + lock.

## Next steps (M3, when asked)
1. IR stereo pair + projector, linear 16-bit IR export, own SGBM in `.venv` (D13); **re-check A-32 (i–iii)** before the M3 gate; plane anchor (a); IR render benchmark per frame (decides 1280×720 vs 848×480, D8).
2. Research when needed: D415 dot count/density/layout (**not in the datasheet** [S-01]; projector FOV, power and wavelength are, see SOURCES); aluminium reflectance near 850 nm (A-11).
3. M5: re-check A-30 when implementing the offset sweep.

## Where things are
| Need | File |
|---|---|
| Requirements | `task_description.md` |
| Decisions, protocol, milestones, risks | `docs/PLAN.md` |
| Assumptions and hypotheses (A-33…A-35 new) | `docs/ASSUMPTIONS.md` |
| Sources and verification status | `docs/SOURCES.md` |
| Report page budget and reflection outline | `docs/REPORT_PLAN.md` |
