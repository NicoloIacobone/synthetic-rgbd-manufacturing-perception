# Status

Handoff note between sessions. **Read first.** Keep it short (≤ ~40 lines): update it at the end of every task, and overwrite outdated content rather than appending (history goes to DIARY.md and git).

- **Updated:** 2026-11-03
- **Phase:** pre-Phase-1 setup done. Next is Phase 1 (implementation), which starts only when the user asks.
- **Protocol:** frozen at git tag `protocol-v1` (PLAN §5.12). Deviations since then: none.
- **Next milestone:** M1, BlenderProc environment (PLAN §7). Gates: M3 Wed 4 Nov, M5 Fri 6 Nov, code freeze Sat 7 Nov 20:00.

## Next steps
1. M1: install BlenderProc 2.8 (PyPI) and run its quickstart. Time-box 1 h, then fall back to Open3D raycasting (D3, R1). This Mac runs macOS 27.2, so expect issue #768 (grant terminal permission).
2. M2: procedural profile and bracket meshes in the model frames fixed in A-20 (`src/synthrgbd/mssd.py`); check BlenderProc's K matrix against A-28.
3. M3: IR stereo pair + projector + SGBM, plane anchor (a), render benchmark per frame.

## Open items waiting for the user
- A-30 (offset sweep moves mm and degrees together) was chosen by the agent; confirm or change it before the first experiment run.
- Design choice for M3: run SGBM inside Blender's Python (BlenderProc's `stereo_global_matching`, S-11) or in `.venv` (OpenCV 5.0, with full control over IR noise and invalidation; the ×16 scaling is unit-tested there). Not decided yet.

## Environment
- Analysis env: `.venv` (Python 3.11.6), pins in `requirements.txt`, full lock in `requirements.lock.txt`. Recreate: `python3.11 -m venv .venv && .venv/bin/pip install -r requirements.lock.txt`.
- Tests: `.venv/bin/python -m pytest` (13 tests pass at the commit that tags `protocol-v1`).
- Protocol parameters: `configs/default.yaml`.

## Where things are
| Need | File |
|---|---|
| Requirements | `task_description.md` |
| Decisions, protocol, milestones, risks | `docs/PLAN.md` |
| Assumptions and hypotheses | `docs/ASSUMPTIONS.md` |
| Sources and verification status | `docs/SOURCES.md` (read when citing) |
| Report page budget and reflection outline | `docs/REPORT_PLAN.md` (read at M6 or when choosing figures) |
