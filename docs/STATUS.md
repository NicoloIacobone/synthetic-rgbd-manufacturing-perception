# Status

Handoff note between sessions. **Read first**, then CLAUDE.md's other context files (task_description, PLAN, ASSUMPTIONS). Keep it short; overwrite outdated content (history is in DIARY.md and git).

- **Updated:** 2026-11-08 (Sunday) evening, after revising the report on a simulated expert review (A-78).
- **Phase:** **final run at 71° done, steps 0–11 of the user's prompt of 2026-11-06 complete.** It is the primary result (A-66, PLAN §5.12); M1–M5 at 65° are the archived run. **Report: first draft in `report/report.pdf` (2026-11-07, at the user's request), written by the agent; the user verifies it.**
- **Protocol:** tag `protocol-v1`; 7 rows in PLAN §5.12. Primary endpoint and fixed sequence unchanged. **Disclosed: the earlier test results had been seen.** 65° is a descriptive sensitivity.
- **Dates:** code freeze Sat 7 Nov 20:00, submission Sun 8 Nov 23:59 CET, both triggered by the user. Mail to jpetrik@ethz.ch: the user sends it.
- **Git:** pushed to `origin/main` on 2026-11-07 at the user's request, up to c5d41d9. Later commits are local only. The repository is still private. Push again only when the user asks.
- **Left to the user:** push (main is ahead of origin), repository visibility, tag, Release, mail with PDF and link before 23:59 CET. The sample-scene URL (`SAMPLE_SCENE_URL` in `scripts/quick_run.py`) is empty until the archive is published.
- **Pre-publication check (2026-11-07, nothing rewritten):** no secrets, no absolute local paths, no generated data, largest blob 968 KB. Personal data for the user to decide on: the author's address on all commits (a rewrite would be needed to change it), `jpetrik@ethz.ch` in this file and in commit b132514, "J. Petrik" in A-02. Also the user's call: `task_description.md`, `docs/DIARY.md`, `docs/AI_USE_LOG.md`, `CLAUDE.md` and the ROBI-derived numbers in `results/` are tracked.

## Report, first draft
`report/report.pdf`, 8 pages (contents list on page 1; "The first six months" is now Section 11, AI-use note Section 12; page 8 holds only the end of the references), source `report/report.tex`. Written by the agent; **the user verifies it.** To confirm: author name, the AI-note sentence "checked the results and this text", other AI tools used if any, the repository link (private today). Check: `.venv/bin/python report/check_numbers.py`. Two checks added while writing: ICP repeat (no view crosses 5 mm, A-72), error structure (direction does not matter, size and layout do, A-73).

## Report revised after the simulated review, 2026-11-08 evening
The user had a separate AI session review the PDF as a sceptical ETH professor and approved a plan of wording-only edits. **No number, setting or result changed**; 8 pages; `check_numbers` 99 of 99; no overfull boxes. Applied: Summary scoped (independent per-pixel noise, 27 of 49 points metal-specific, ROBI 21% vs 2.3%); ambient light as visible + IR on unfiltered imagers (Table 1, Results, Limitations, plan); McNemar two-sided and unadjusted for clustering, p < 1e-29; decomposition 21.7 + 27.4; suction false grasps on profiles in every non-ideal condition (planner property); ROBI 78 px shift; roughness convention stated; "Even the kind of failure is uncertain" in the Reflection; E2/E3 as month-1 tests; AI note lists the user's decisions and the AI review. Sections 10–11 are 0.87 page but cross the page 7–8 break: a footnote says so. **Rejected with the data:** a roughness-convention error (none) and the 93.9% false grasps as a metal headline (A-78, AI_USE_LOG section B).
**Round 2 (same evening):** a second AI review judged the report ready; applied its wording fixes (instance-view used consistently, 46–98% false grasps, "likely geometric", r = 0.13–0.15 rough end, "same ten scenes", 416/459 from the 65° run, "2 h 28 min"). Still 8 pages, Sections 10–11 still 0.87 page, `check_numbers` 99/99. The README `@@TESTED@@` and A-77 `@@A77@@` placeholders are filled from the earlier session's logs: macOS arm64 exact pass 146 s; Linux aarch64 container pass 199 s, depth identical; x86-64 untested (emulated run without AVX2 never finished ICP).

## Source check against the PDFs, 2026-11-08
Every cited claim checked against `docs/references/` (results in `docs/SOURCES.md`, paragraph "Full-text check of 2026-11-08"). **Fixes applied at the user's request, citations and wording only; no number or result changed** (report still 8 pages, `check_numbers` 94 of 94; list in DIARY 2026-11-08):
- Report: Zhang et al. "replicas" corrected in Related work and Reflection; 126 px cited to [13, 22]; "1.62 mm … with my f"; ROBI's 0.8 mm camera-pose residual named; Intel's guide computing with 65° added to the focal-length item; XYZ-IBD "on metal parts in cluttered bins"; references [3] full title, [10] v3 2026, [22] now the BKMs PDF Rev 2.0.
- Docs: datasheet summary §10, A-16, A-25, A-36, the projector comment in `configs/camera_d415_ir.yaml`, SOURCES S-03 and S-16.
- **Still missing from the folder:** the CGF paper and GGX supplement for [18] (the file there is a different workshop paper); Carfagni [13]. Both were re-read online; the values match.

## After the review of 2026-11-07
**Applied at the user's request:** all wording corrections in the report (still 7 pages, `check_numbers` 87 of 87); the uint16 depth wrap documented in the README and under "What did not work", not fixed (A-75); results figure panel (c) with its own colours. Primary numbers unchanged.

**Dot-density test, done, not in the report (A-74, `results/hfov71/dots.json`):** seeds 0–9, 10 000 dots, new render: C3 0.102 → 0.041, −6.1 points (−11.4 to −1.0); C4 0.265 → 0.184, −8.2 points (−20.6 to +4.4); order held. The report only says the density is assumed.

**Open, the user decides:** (1) whether the dot test enters the report: a row in Table 3 and one sentence in Limitations are proposed; optional extra runs, not started: a 30 000 re-render as control and 60 000 dots, about 20 min each; (2) quick run off macOS: the pass rule demands identical pixels; proposed: tolerance off the reference platform plus a Dockerfile tested here on Linux ARM and emulated x86; (3) README commands for the ICP repeat and error structure checks, and the stale comments in `conditions.py` and `camera_d415_ir.yaml`.

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
