# Status

Handoff note between sessions. **Read first**, then CLAUDE.md's other context files (task_description, PLAN, ASSUMPTIONS). Keep it short; overwrite outdated content (history is in DIARY.md and git).

- **Updated:** 2026-11-06 (Friday, before the test render at 71°).
- **Phase:** M1–M5 done at 65°, now the **archived run**. **Final run at 71° in progress** (A-66, PLAN §5.12 row 2026-11-06): the user's prompt of 2026-11-06 sets steps 0–11; the plan is in the session, the rules are in A-66 to A-71 and the ledger.
- **Protocol:** tag `protocol-v1`; 7 rows in PLAN §5.12. Primary endpoint and fixed sequence unchanged. **Disclosed: the earlier test results had been seen.** The new run is primary whatever its direction; 65° is a descriptive sensitivity.
- **Dates:** code freeze Sat 7 Nov 20:00, submission Sun 8 Nov 23:59 CET, both triggered by the user. Mail to jpetrik@ethz.ch: the user sends it.
- **Git:** pushed to `origin/main` through 7ecbcb0. Later commits are local: push only when the user asks. **No commit on main while the final run is alive** (`pose_eval.py` records HEAD): tooling goes in a temporary worktree.
- **Out of scope for agents:** report text, freeze and tag, push, Release, visibility, what becomes public, mail.

## Where the final run stands
| Step | State |
|---|---|
| 0 Pre-declaration | done, a6c1b36 |
| 1 Focal length, gate, re-derived values | done, b459488. Gate passes in full (A-67). `e_per_dn` 0.42, setpoint 20 DN, albedo 0.25 |
| 2 RGB light | done: energy 12 (A-69) |
| Lock | commit right before the test render; dev sanity 40/40 |
| 3–5 Experiment, redraws, ambient | `scripts/run_final.sh data/hfov71/test data/hfov71/dev`, detached with `scripts/detach.py`, log `data/hfov71/test_run.log`. Resumes from stage markers. Stops on the rules in the ledger "Final-run stop rules" |
| 6–11 Figures, results in repo, install, quick-run, README, pre-publication | not started |

**Check that the run is alive:** `pgrep -f run_final.sh`, `cat data/hfov71/test/heartbeat`, `grep '^===' data/hfov71/test_run.log | tail`.

## Fixed configuration at 71°
- **Camera** (`configs/default.yaml`, `configs/camera_d415_ir.yaml`): fx 897.25 px; C2a 0.08 px, C2b 0.234 px; C3 metal roughness 0.15, D 0.015, base 0.868; Cycles glossy 3, max 12, 32 samples; C4 albedo 0.25; setpoint 20 DN; `e_per_dn` 0.42, read 1 DN. Projector 67° × 41°, so 86.5% of the image is lit.
- **Harness** (`configs/harness.yaml`): not re-selected. H3, erosion 2 px, 200 000 CAD samples, `plane_fit`.

## Archived run at 65° (commit 26cd449, `data/m5/results_v2/stats.json`)
459 instance-views. A1 recall@5 mm: C1 0.732, C2a 0.749, C2b 0.590, C3 0.085, C4 0.386. Fixed sequence, all reject. Roughness 0.2 0.159, 0.4 0.288. Not to be compared to choose settings.

## Where things are
| Need | Path |
|---|---|
| Configs | `configs/default.yaml` (frozen, deviations in PLAN §5.12), `configs/camera_d415_ir.yaml`, `configs/harness.yaml` |
| Final-run data | `data/hfov71/` (`plane`, `intrinsics`, `dev_iter*`, `rgb_sweep`, `dev`, `test`) |
| Archived 65° data, never written | `data/m5`, `data/m5_dev`, `data/m3`, `data/m5_diag`; check against `data/hfov71/protected_snapshot.txt` |
| Code / tests | `src/synthrgbd/`, `scripts/` (docstrings give usage); `.venv/bin/python -m pytest` |
| Decisions, assumptions, ledger, sources | `docs/PLAN.md`, `docs/ASSUMPTIONS.md` (ledger under A-45), `docs/SOURCES.md` |
| Open items of M5 | `docs/M5_OPEN_ITEMS.md` |
| Camera facts with datasheet pages | `docs/D415_DATASHEET_SUMMARY.md` |
| Code dictionary (Italian) | `docs/GLOSSARY.md`; write codes with their meaning in messages to the user |
