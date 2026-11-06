# Status

Handoff note between sessions. **Read first**, then CLAUDE.md's other context files (task_description, PLAN, ASSUMPTIONS). Keep it short; overwrite outdated content (history is in DIARY.md and git).

- **Updated:** 2026-11-06 (Friday afternoon).
- **Phase:** Phase 1. **M1–M5 done; M6 not started.** M5 closed on 2026-11-05; independent review done on 2026-11-06, its decisions are in A-63, A-64, A-65. Open items and their triage: [`M5_OPEN_ITEMS.md`](M5_OPEN_ITEMS.md).
- **Protocol:** frozen at tag `protocol-v1`; 6 rows in PLAN §5.12. Primary endpoint: A1 recall at MSSD < 5 mm, offset 10 mm / 10°; fixed-sequence testing C1 vs C3 → C2b vs C3 → C3 vs C4 at α = 0.05; unit = instance-view, visib_fract ≥ 0.1, a missing estimate = failure.
- **Gates:** A metrics by Fri 6 Nov **met**; code freeze Sat 7 Nov 20:00; target submission Sun 8 Nov 18:00. Report skeleton: planned for Thursday evening, not started.
- **Git:** pushed to `origin/main` through 7ecbcb0 (2026-11-05). Later commits are local: push only when the user asks.
- **Budget:** about 18 h to Sun 18:00 at 6 h/day; the essential work below is about 17 h. Page budget in REPORT_PLAN sums to exactly 8.00.
- **Delivery (user's mail, re-sent 2026-11-06):** send to jpetrik@ethz.ch as an attachment or download link by Sun 8 Nov 23:59 CET. The user sends it.

## User decisions, 2026-11-06 (they override the proposals below; not started)
- **Focal length: change it and re-run render and experiment.** Target value to be confirmed by the user (proposed: imager 71°, fx 897.2 px). Results below become the archived 65° run.
- **Yes:** ambient-IR test on 10 scenes; fix the overexposed RGB; C3 noise redraws on all 50 scenes; from-zero install, quick-run, README, clean-clone test, pre-publication check.
- **Time:** ignore the 6 h/day budget; agents may run 10–12 h/day and overnight. Code freeze date not moved, and the freeze and tag run only when the user says so.
- **Waits for the user:** what becomes public, push, Release, visibility, the mail.

## Audit against the mail, 2026-11-06 (no decision taken yet)
- **Repo is private:** the reader cannot open a plain GitHub link. Choose how to share it; 2 commits are unpushed, plus this one.
- **RGB is overexposed:** test frames, part pixels with all channels ≥ 250: median 36%, max 92%; median part grey 242 (light energy 150, `scripts/bproc_render_scene.py`). Neither task reads RGB, so no result is affected, but the example-frame figure is. Proposed: RGB-only re-render into a new folder.
- **Dates do not fit 6 h/day:** 11.25 h of draft work is due by Sat 12:00 and 15.25 h by the Sat 20:00 code freeze, against at most 12 h available by then. Proposed: move the freeze to Sun 12:00.
- **Proposed, not run, user decides:** one ambient-IR sensitivity on seeds 0–9 (descriptive, A-03, open item 35); C3 noise redraws on all 50 scenes (open items 4, 31).
- **Datasheet Rev 017 read (`docs/D415_DATASHEET_SUMMARY.md`), two points to decide:** fx 1004.6 px comes from the 65° depth FOV, while the imager is 71° ± 1° and ROBI's camera has 905.9 px (A-28; `hfov_deg` is frozen, proposal: disclose, no re-render). Imager filter "None", so zero ambient is weaker than stated (A-03). The PDF is in `docs/`, gitignored at the user's request.

## Next steps, in order
1. **Report skeleton from the three-sentence story** (0.5 h). No new codes, assumptions or open-item work until submission unless a result demands it.
2. **Figures from existing data** (3 h): results (fix item 32, add a distance panel, item 34), ROBI (`scripts/fig_robi.py` with `data/m5/results_v2/sensor.json` and `data/m5/robi/zigzag.json`, framed in px and invalid pixels per A-65, no further download), example frames.
3. **Text with "what did not work"** (6 h), **reflection** (1.5 h), **AI note** (0.25 h). **Complete draft by Sat 12:00;** if not, cut the plane figure and the Task B detail.
4. **README** (1.5 h) and **quick-run plus a clean-clone test** (2.5 h), **by the Sat 20:00 code freeze**. Quick-run per A-65; confirm the release upload and the push with the user. No script creates `.venv` yet, and `scripts/run_m5.sh` needs zsh and `data/m5`.
5. **Final pass and PDF** (2 h). Sun 12:00 complete, Sun 18:00 submit.

## Results (commit 26cd449, clean tree; `data/m5/results_v2/stats.json`)
Seeds 0–49, 459 instance-views (342 profile, 117 bracket), 1 excluded. Sanity on C1 at zero offset: 459/459 < 0.5 mm.

| Condition | A1 recall@5 mm [95% scene CI] | Profile | Bracket | Task B brackets |
|---|---|---|---|---|
| C1 ideal | 0.732 [0.682, 0.779] | 0.713 | 0.786 | 0.821 |
| C2a noise 0.08 px | 0.749 [0.697, 0.799] | 0.754 | 0.735 | 0.761 |
| C2b noise 0.26 px | 0.590 [0.521, 0.657] | 0.675 | 0.342 | 0.615 |
| C3 metal stereo | 0.085 [0.054, 0.118] | 0.102 | 0.034 | 0.145 |
| C4 matte stereo | 0.386 [0.327, 0.444] | 0.412 | 0.308 | 0.359 |

- **Fixed sequence, all reject:** C1−C3 +0.647 [0.583, 0.708], p 2e-78; C2b−C3 +0.505 [0.429, 0.580], p 7e-59; C3−C4 −0.301 [−0.356, −0.244], p 6e-31.
- **Descriptive:** roughness 0.2 0.159, roughness 0.4 0.288, reflections off 0.102, bright matte 0.444.
- **Sweep:** the ordering C1 ≈ C2a > C2b > C4 > C3 holds at 2, 5, 10 and 20 mm. C1 is 1.00 at 2 mm and 0.67 at 20 mm, so its 0.73 is largely a harness limit.
- **§5.8, seeds 0–9, all three filters off (re-run, commit c44cd7a, `data/m5/results_s58_v2/robustness.json`):** no ranking flip. C1−C3 +0.561, C2b−C3 +0.337, C3−C4 −0.214; C3 0.153, C4 0.367. First run with the left-right check left on: PLAN §5.12. C3 noise redraws 0.143, 0.133, 0.071.
- **Noise at about a third (A-64, descriptive, same folder):** C3 0.143 → 0.143, C4 0.357 → 0.408. The noise level does not explain C3's recall at this value.
- **Figure:** `data/m5/figures/results.png`.
- **Headline wording (A-65):** metal 0.085 confirmatory, with the range 0.085–0.288 (roughness 0.15–0.4) in the same sentence. Claims hold for this ICP and this simulated camera, not for a physical D415.
- **Read before writing the report:** open items 4, 18, 20, 21, 22, 23, 24, 25, 26, 34, 35, 36, 37. The 200 000-sample choice and the harness change after the test render must be disclosed (items 1, 2; PLAN §5.12).

## Fixed configuration
- **Camera** (`configs/camera_d415_ir.yaml`): C3 metal roughness 0.15 + Lambertian D 0.015, base reflectance 0.868 (S-15, S-16); Cycles glossy 3, max 12, 32 samples; C4 part albedo 0.247 (A-24, clipped mean matching); auto exposure setpoint 20 DN on the C3 left image, gain shared with C4 (A-42); noise e_per_dn 0.087 (effective) + read 1 DN, shared draws (A-12). Extra passes `r02`, `r04`, `bright`, `nogloss` (reflections off), each on its own exposure.
- **Harness** (`configs/harness.yaml`): ICP **H3** (stages 20/10/5 mm, ray-cast visibility, 5 mm / 5° step clamp), erosion 2 px, 200 000 CAD samples; suction grasp point plane_fit. Pick on dev: H3 C3 0.05, C4 0.35, C2b 0.575, C1 0.75, C2a 0.80 (`data/m5_dev/selection_fix`). It rests on one instance-view (open item 1).
- **Stale:** `data/m5_dev/pilot` ran with the cache bug and 50 000 samples.

## Operating mode (user, 2026-11-04; A-56)
Decide implementation details yourself and log each in **one line** (ASSUMPTIONS or the tuning ledger). **Stop only for:** (a) a change to a frozen value (§5, `configs/default.yaml`); (b) a result that threatens the experiment; (c) a failed gate.

## Where things are
| Need | Path |
|---|---|
| Configs | `configs/default.yaml` (frozen), `configs/camera_d415_ir.yaml`, `configs/harness.yaml` |
| Test data | `data/m5/` (scenes 0–49) |
| **Final results** | `data/m5/results_v2/` (`stats.json`, `sensor.json`), `data/m5/results_s58_v2/` (§5.8 as defined and noise sensitivity, `robustness.json`, `sensor.json`), `data/m5/results_v2_s58/` (first §5.8 run, noise redraws), log `data/m5/results_v2_run.log` |
| Earlier M5 runs, kept | `data/m5/results/` (failed sanity), `data/m5/diag_sanity/`, `data/m5/diag_sanity_fix/` (A-62) |
| Dev data, final settings | `data/m5_dev/` (scenes 1000–1004; `selection_fix/` current, `selection/` and `pilot/` stale) |
| Dev data, reflections off | `data/m4/` (M4 settings) |
| Convergence renders | `data/m5_diag/` (`gb3`, `gb3_max12`, `gb1`, `gb3_s128`) |
| Mechanism results and figure | `data/m5/mechanism/`, `data/m5/figures/mechanism_dev_1001_0.png` |
| Planes / anchor (a) | `data/m3/plane/` (`anchor_a.json`, `anchor_a_calibration.json`) |
| Scripts | `scripts/` (docstrings give usage): `bproc_render_scene.py` (Blender, via `scripts/bproc.sh` only), `benchmark_m3.sh`, `stereo_scene.py`, `c2_depth.py`, `pose_eval.py`, `suction_eval.py`, `anchor_a.py`, `select_setpoint.py`, `select_harness.py`, `sanity_candidates.py`, `sanity_diagnosis.py`, `mechanism_check.py`, `mechanism_compare_render.py`, `fig_mechanism.py`, `run_m5.sh`, `run_m5_followup.sh`, `run_eval.py`, `stats_m5.py`, `sensor_metrics.py`, `robustness_s58.py`, `fig_results.py`, `robi_fetch.py`, `robi_compare.py`, `ir_appearance.py`, `fig_robi.py` |
| Code / tests | `src/synthrgbd/` (pose, suction, stereo, …); `.venv/bin/python -m pytest` (98 pass) |
| Decisions, assumptions, ledger, sources | `docs/PLAN.md`, `docs/ASSUMPTIONS.md` (ledger under A-45), `docs/SOURCES.md` |
| Open items of M5 | `docs/M5_OPEN_ITEMS.md` |
| Camera facts with datasheet pages | `docs/D415_DATASHEET_SUMMARY.md` |
| Code dictionary (Italian) | `docs/GLOSSARY.md`; write codes with their meaning in messages to the user |

## Docs until Saturday (slimmed)
DIARY: one short entry per milestone. ASSUMPTIONS / ledger: one-line rows. SOURCES: only items the report cites. PLAN: §5.12 rows only.
