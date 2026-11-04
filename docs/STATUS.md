# Status

Handoff note between sessions. **Read first.** Keep it short (≤ ~40 lines): update it at the end of every task, and overwrite outdated content rather than appending (history goes to DIARY.md and git).

- **Updated:** 2026-11-04, morning
- **Phase:** Phase 1. M1 and M2 done (2026-11-03). **Pre-M3 decisions closed** (2026-11-04, D15). M3 not started; it starts only when the user asks.
- **Protocol:** frozen at `protocol-v1`. §5.12 rows: 1 deviation (Task B per part type) + 1 editorial (348d49c / b6c5b00, no value changed).
- **Gates:** **M3 today, Wed 4 Nov, end of day**; M5 Fri 6 Nov; code freeze Sat 7 Nov 20:00.

## How to run (see script docstrings)
- BlenderProc env: `scripts/setup_blenderproc.sh` (`.venv-bproc` from `requirements-bproc.lock.txt` + macOS patch in `patches/`, D14). **Always run Blender through `scripts/bproc.sh`** (plain `blenderproc run` downloads a second Blender into ~/blender).
- Scenes: `scripts/render_scenes.sh data/m2 1000 1001` → BOP dataset in `data/m2/synthrgbd/` + logs and contact sheets in `data/m2/logs/`.
- Checks: `scripts/check_intrinsics.py` (A-28), `scripts/check_bop_scene.py` (GT consistency). Tests: `.venv/bin/python -m pytest` (38 pass).

## Measured (dev seeds 1000–1001, 1280×720, Metal GPU + CPU)
- RGB + depth + segmentation: 8.4–8.6 s/frame at 64 samples; 25 s per 2-view scene end to end; 2 MB/scene. IR renders not measured yet.
- GT consistency: worst p95 back-projection error 0.047 mm; K = A-28 within 4e-5 px.

## M3 inputs, fixed before any M3 data (D15)
- Projector 67° × 41° (A-36). Dot pattern: static, semi-random, 30 000 dots by default, uniform envelope, no speckle; seed is a camera constant (A-37, source [S-13]).
- **Gate pass criteria A-38** (matte plane, z = 0.5…1.0 m: bias < 1% z, ≥ 95% valid, left band within ±10% of f·B/z; Min-Z bracket 0.43/0.45 m). Noise level is M4. **If any criterion fails: stop and present Route 2 (D7) or the patched helper (D13) to the user. No automatic switch.**
- **Resolution rule A-39:** keep 1280×720 if ≤ 262 s per frame end to end (110 frames ≤ 8 h); otherwise propose a lower resolution to the user.
- **Pitfall A-40:** OpenCV SGBM invalidates the first 128 columns whatever the depth, and accepts only 8-bit input. Proposed fix (tested on synthetic texture): render the right IR 128 px wider, pad the left image, then invalidate x − d < 0.
- Put new camera-model parameters (projector, dots, exposure, SGBM) in a separate config file, not in the frozen `configs/default.yaml`.

## Next steps (M3, when asked)
1. IR stereo pair + projector, linear 16-bit export, own SGBM in `.venv` (D13); re-check A-32 (i–iii); plane anchor + gate A-38; benchmark A-39.
2. M4: metal/matte + brightness matching (A-24), aluminium reflectance near 850 nm (A-11), IR noise tuning (A-12, target 0.07–0.11 px [S-13]); optional dot-density sensitivity (A-37).
3. M5: re-check A-30 when implementing the offset sweep.

## Where things are
| Need | File |
|---|---|
| Requirements | `task_description.md` |
| Decisions, protocol, milestones, risks | `docs/PLAN.md` |
| Assumptions and hypotheses (A-36…A-40 new) | `docs/ASSUMPTIONS.md` |
| Sources and verification status (S-13 new) | `docs/SOURCES.md` |
| Report page budget and reflection outline | `docs/REPORT_PLAN.md` |
