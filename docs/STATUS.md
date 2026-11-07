# Status

Handoff note between sessions. **Read first**, then CLAUDE.md's other context files (task_description, PLAN, ASSUMPTIONS). Keep it short; overwrite outdated content (history is in DIARY.md and git).

- **Updated:** 2026-11-07 (Saturday), after the final run at 71°.
- **Phase:** **final run at 71° done, steps 0–11 of the user's prompt of 2026-11-06 complete.** It is the primary result (A-66, PLAN §5.12); M1–M5 at 65° are the archived run. **Report: first draft in `report/report.pdf` (2026-11-07, at the user's request), written by the agent; the user verifies it.**
- **Protocol:** tag `protocol-v1`; 7 rows in PLAN §5.12. Primary endpoint and fixed sequence unchanged. **Disclosed: the earlier test results had been seen.** 65° is a descriptive sensitivity.
- **Dates:** code freeze Sat 7 Nov 20:00, submission Sun 8 Nov 23:59 CET, both triggered by the user. Mail to jpetrik@ethz.ch: the user sends it.
- **Git:** pushed to `origin/main` through 7ecbcb0. All later commits are local: push only when the user asks.
- **Left to the user:** verifying and editing the report, freeze and tag, push, Release, visibility, what becomes public, mail. The sample-scene URL (`SAMPLE_SCENE_URL` in `scripts/quick_run.py`) is empty until the archive is published.
- **Pre-publication check (2026-11-07, nothing rewritten):** no secrets, no absolute local paths, no generated data, largest blob 968 KB. Personal data for the user to decide on: the author's address on all commits (a rewrite would be needed to change it), `jpetrik@ethz.ch` in this file and in commit b132514, "J. Petrik" in A-02. Also the user's call: `task_description.md`, `docs/DIARY.md`, `docs/AI_USE_LOG.md`, `CLAUDE.md` and the ROBI-derived numbers in `results/` are tracked.

## Primary result at 71° (commit 7eca5f0, clean tree, `results/hfov71/stats.json`)
460 instance-views, seeds 0–49. A1 recall@5 mm: C1 0.717, C2a 0.735, C2b 0.561, C3 0.070, C4 0.343. Fixed sequence, all reject: C1−C3 +0.648, C2b−C3 +0.491, C3−C4 −0.274. Task B brackets: 0.771, 0.737, 0.534, 0.110, 0.381. Roughness 0.2 0.139, 0.4 0.276; reflections off 0.076; albedo 0.5 0.363. C3 redraws 0.061, 0.063. Ambient on seeds 0–9: C3amb 0.031, C4amb 0.224, next to C3 0.102, C4 0.265. No stop rule fired. New numbers by open item: `docs/M5_OPEN_ITEMS.md` section 5.

## Fixed configuration at 71°
- **Camera** (`configs/default.yaml`, `configs/camera_d415_ir.yaml`): fx 897.25 px; C2a 0.08 px, C2b 0.234 px; C3 metal roughness 0.15, D 0.015, base 0.868; Cycles glossy 3, max 12, 32 samples; C4 albedo 0.25; setpoint 20 DN; `e_per_dn` 0.42, read 1 DN. Projector 67° × 41°, so 86.5% of the image is lit.
- **Harness** (`configs/harness.yaml`): not re-selected. H3, erosion 2 px, 200 000 CAD samples, `plane_fit`.

## Archived run at 65° (commit 26cd449, `results/archive_hfov65/stats.json`)
459 instance-views. A1 recall@5 mm: C1 0.732, C2a 0.749, C2b 0.590, C3 0.085, C4 0.386. Fixed sequence, all reject. Roughness 0.2 0.159, 0.4 0.288. Not to be compared to choose settings.

## Where things are
| Need | Path |
|---|---|
| How to run everything | `README.md` |
| Tracked results, figures, manifest | `results/` |
| Configs | `configs/default.yaml` (frozen, deviations in PLAN §5.12), `configs/camera_d415_ir.yaml`, `configs/harness.yaml` |
| Final-run data, not in git | `data/hfov71/` (`plane`, `intrinsics`, `dev_iter*`, `rgb_sweep`, `dev`, `test`), log `data/hfov71/test_run.log` |
| Sample scene for the quick run, not in git | `dist/sample_scene_seed0.tar.gz` (6.5 MB) |
| Archived 65° data, never written | `data/m5`, `data/m5_dev`, `data/m3`, `data/m5_diag`; check against `data/hfov71/protected_snapshot.txt` |
| Code / tests | `src/synthrgbd/`, `scripts/` (docstrings give usage); `.venv/bin/python -m pytest` |
| Decisions, assumptions, ledger, sources | `docs/PLAN.md`, `docs/ASSUMPTIONS.md` (ledger under A-45), `docs/SOURCES.md` |
| Open items | `docs/M5_OPEN_ITEMS.md` |
| Report plan, figures to use | `docs/REPORT_PLAN.md` |
| Camera facts with datasheet pages | `docs/D415_DATASHEET_SUMMARY.md` |
| Code dictionary (Italian) | `docs/GLOSSARY.md`; write codes with their meaning in messages to the user |
