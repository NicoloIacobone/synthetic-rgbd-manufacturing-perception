# Status

Handoff note between sessions. **Read first**, then CLAUDE.md's other context files (task_description, PLAN, ASSUMPTIONS). Keep it short; overwrite outdated content (history is in DIARY.md and git).

- **Updated:** 2026-11-05 (Thursday evening).
- **Phase:** Phase 1. **M1–M5 done.** M5 closed on 2026-11-05 with its uncertainties written down rather than resolved (user's decision): [`M5_OPEN_ITEMS.md`](M5_OPEN_ITEMS.md).
- **Protocol:** frozen at tag `protocol-v1`; 5 rows in PLAN §5.12. Primary endpoint: A1 recall at MSSD < 5 mm, offset 10 mm / 10°; fixed-sequence testing C1 vs C3 → C2b vs C3 → C3 vs C4 at α = 0.05; unit = instance-view, visib_fract ≥ 0.1, a missing estimate = failure.
- **Gates:** A metrics by Fri 6 Nov **met**; code freeze Sat 7 Nov 20:00; target submission Sun 8 Nov 18:00. Report skeleton: Thursday evening.
- **Git:** everything through the M5 closure is pushed to `origin/main` (2026-11-05, user's approval).

## Next steps, in order
1. **The user runs a review agent** on the finished milestone (planned for Fri 6 Nov). Start nothing else until then.
2. **The user decides open item 18:** the §5.8 loose variants left the left-right check on, because `disp12MaxDiff` −1 behaves as 1 in OpenCV 5.0.0. Either re-match seeds 0–9 with a large value and re-run `C3loose` and `C4loose` (about 20 min of ICP plus matching), or keep and disclose it with a §5.12 row.
3. **ROBI (A-55):** 3 h time box, one figure (ROBI-D415 vs C3 0.15 / 0.2 / 0.4 vs C4; mm and px; range mismatch stated), framed on the mechanism: on metal, does the real D415 fill (smooth or bias towards the background) or leave holes? One retry of the fetch (Zigzag remainder, Chrome screw `1qqG0KVW6_Upxc95Wuk9HecR0JrxGZSd4`); Drive refused range requests after 60 MB. Zigzag results so far in `data/m5/robi/zigzag.json` (26 views). `scripts/ir_appearance.py` and `scripts/fig_robi.py` take the test `sensor.json` (`data/m5/results_v2/sensor.json`).
4. **M6:** report, reflection, AI note, README. Tell the user: C4 albedo 0.247 and harness H3 differ from what was approved or expected (A-24, A-62); the approved rules moved them.

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
- **§5.8, seeds 0–9:** no ranking flip, with the limit of open item 18. C3 noise redraws 0.143, 0.133, 0.071.
- **Figure:** `data/m5/figures/results.png`.
- **Read before writing the report:** open items 4, 18, 20, 21, 22, 23, 24, 25, 26. The 200 000-sample choice and the harness change after the test render must be disclosed (items 1, 2; PLAN §5.12).

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
| **Final results** | `data/m5/results_v2/` (`stats.json`, `sensor.json`), `data/m5/results_v2_s58/` (§5.8, `robustness.json`), log `data/m5/results_v2_run.log` |
| Earlier M5 runs, kept | `data/m5/results/` (failed sanity), `data/m5/diag_sanity/`, `data/m5/diag_sanity_fix/` (A-62) |
| Dev data, final settings | `data/m5_dev/` (scenes 1000–1004; `selection_fix/` current, `selection/` and `pilot/` stale) |
| Dev data, reflections off | `data/m4/` (M4 settings) |
| Convergence renders | `data/m5_diag/` (`gb3`, `gb3_max12`, `gb1`, `gb3_s128`) |
| Mechanism results and figure | `data/m5/mechanism/`, `data/m5/figures/mechanism_dev_1001_0.png` |
| Planes / anchor (a) | `data/m3/plane/` (`anchor_a.json`, `anchor_a_calibration.json`) |
| Scripts | `scripts/` (docstrings give usage): `bproc_render_scene.py` (Blender, via `scripts/bproc.sh` only), `benchmark_m3.sh`, `stereo_scene.py`, `c2_depth.py`, `pose_eval.py`, `suction_eval.py`, `anchor_a.py`, `select_setpoint.py`, `select_harness.py`, `sanity_candidates.py`, `sanity_diagnosis.py`, `mechanism_check.py`, `mechanism_compare_render.py`, `fig_mechanism.py`, `run_m5.sh`, `run_eval.py`, `stats_m5.py`, `sensor_metrics.py`, `robustness_s58.py`, `fig_results.py`, `robi_fetch.py`, `robi_compare.py`, `ir_appearance.py`, `fig_robi.py` |
| Code / tests | `src/synthrgbd/` (pose, suction, stereo, …); `.venv/bin/python -m pytest` (96 pass) |
| Decisions, assumptions, ledger, sources | `docs/PLAN.md`, `docs/ASSUMPTIONS.md` (ledger under A-45), `docs/SOURCES.md` |
| Open items of M5 | `docs/M5_OPEN_ITEMS.md` |
| Code dictionary (Italian) | `docs/GLOSSARY.md`; write codes with their meaning in messages to the user |

## Docs until Saturday (slimmed)
DIARY: one short entry per milestone. ASSUMPTIONS / ledger: one-line rows. SOURCES: only items the report cites. PLAN: §5.12 rows only.
