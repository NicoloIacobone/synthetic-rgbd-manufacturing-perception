# Status

Handoff note between sessions. **Read first.** Keep it short (≤ ~40 lines): update it at the end of every task, and overwrite outdated content rather than appending (history goes to DIARY.md and git).

- **Updated:** 2026-11-03
- **Phase:** pre-Phase-1 setup done. Next is Phase 1 (implementation), which starts only when the user asks.
- **Protocol:** frozen at git tag `protocol-v1` (PLAN §5.12). Deviations since then: none.
- **Next milestone:** M1, BlenderProc environment (PLAN §7). Gates: M3 Wed 4 Nov, M5 Fri 6 Nov, code freeze Sat 7 Nov 20:00.

## Next steps
1. M1: install BlenderProc 2.8 (PyPI) and run its quickstart. Time-box 1 h, then fall back to Open3D raycasting (D3, R1). This Mac runs macOS 27.2, so expect issue #768 (grant terminal permission).
2. M2: procedural profile and bracket meshes in the model frames fixed in A-20 (`src/synthrgbd/mssd.py`); check BlenderProc's K matrix against A-28.
3. M3: IR stereo pair + projector, linear 16-bit IR export, our own SGBM in `.venv` (D13), plane anchor (a), render benchmark per frame. **Re-check D13 feasibility (A-32 checks i–iii)** before the M3 gate; fallback in PLAN D13.
4. M5: when implementing the A1 offset sweep, re-check A-30 (confirmed 2026-11-03).

## Open items waiting for the user
- None.

## Research to do when the milestone needs it (not blocking)
- M3: D415 projector pattern (dot density, projector FOV) for the projector model; check the datasheet first [S-01].
- M3/M4: aluminium reflectance near 850 nm, to set the IR material (A-11).
- M6: report tooling (LaTeX/Typst/pandoc) and a short related-work paragraph (depth-sensor simulation); not adopted yet.

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
