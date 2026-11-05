# Status

Handoff note between sessions. **Read first**, then CLAUDE.md's other context files (task_description, PLAN, ASSUMPTIONS). Keep it short; overwrite outdated content (history is in DIARY.md and git).

- **Updated:** 2026-11-05 (Thursday).
- **Phase:** Phase 1. **M1–M4 done. M5 STOPPED at the failed §5.11 sanity gate: diagnosis (option 1, A-62) done, no candidate passes, real bug found. Waiting for the user's decision on the fix; run nothing further until then.** The test render is complete (scenes 0–49, all passes, C2 depth). No recall at a real offset has been computed.
- **Protocol:** frozen at tag `protocol-v1`; 4 rows in PLAN §5.12. A new row and the A-53 update follow once the fix is decided (user, 2026-11-05: §5.11 takes precedence over A-53). Primary endpoint unchanged: A1 recall at MSSD < 5 mm, offset 10 mm / 10°; fixed-sequence testing C1 vs C3 → C2b vs C3 → C3 vs C4 at α = 0.05; unit = instance-view, visib_fract ≥ 0.1, a missing estimate = failure.
- **Gates:** A metrics by Fri 6 Nov; code freeze Sat 7 Nov 20:00; target submission Sun 8 Nov 18:00. Report skeleton: Thursday evening. Push at the end of each milestone.

## The stop: §5.11 sanity failed; diagnosis done (A-62)
C1, zero offset, test scenes, 459 instance-views, pass = at least 99% at MSSD < 0.5 mm (at most 4 failures). **None passes:** H0 452, H1 452, `solver: lm` 453, H3 421, H2 416 (control). Failed run kept in `data/m5/results`; diagnosis in `data/m5/diag_sanity` (`logs/report.log`).
- **Real bug (36 of 43):** `pose.py` `_model_scene` caches under `id(tri)`, while `pose_eval.py` passes a new array per instance, so profiles get the ray-cast mesh of another length. A longer mesh swallows the end faces. Affects H2 and H3 only.
- **Second cause (7 of 43, 0.51–0.85 mm):** remains without any ray cast. A few side-face points match end-face samples and alone set the axial pose. Drift bounded by about one CAD sample spacing (0.80 mm on the 150 mm profile).
- **Dev numbers:** every H2 and H3 number on dev, including the pilot below and the H2 pick, ran with this bug; not measured on dev.

**Proposed to the user, not run:** (1) fix the cache, with a regression test; (2) CAD samples 50 000 → 200 000, predicted worst drift about 0.43 mm, untested (fallback: exact closest point on the mesh); (3) pre-declare and re-run the sanity check for H0–H3; (4) re-run the dev selection among those that pass; (5) §5.12 row and A-53 update, including its "harness H3" wording; then all conditions.

## After the decision
1. Fix the harness as decided and log it (PLAN §5.12, ledger). Rendering is not affected and Task B does not use ICP.
2. Steps 5–7 below (a harness fix needs a new commit first). `run_eval.py` continues to real offsets as soon as sanity passes: use a new results folder and do not start it before the gate is cleared. §5.8 and noise-redraw depth for seeds 0–9 is already written (`depth_stereo_metal_{loose,nouniq,nolr,nospeckle,redraw1,redraw2}`, `depth_stereo_matte_loose`).
3. ROBI: one retry of the fetch (Zigzag remainder, Chrome screw `1qqG0KVW6_Upxc95Wuk9HecR0JrxGZSd4`); Drive refused range requests after 60 MB. Zigzag results so far in `data/m5/robi/zigzag.json` (26 views). `scripts/ir_appearance.py` and `scripts/fig_robi.py` still need the test `sensor.json`.
4. **Tell the user at the end:** C4 albedo 0.247 and H2 differ from what was approved or expected (A-24, ledger); the approved rule moved them.

## Decision taken (A-57, A-58)
BlenderProc's default Cycles `glossy_bounces = 0` was never overridden, so no IR render before the fix had a reflected image on metal. User decision 2026-11-04: fix it (glossy 3; max 12 and 32 samples by the ledger rules), re-run the dev rules, keep reflections off as a descriptive pass, C4 albedo by clipped-at-saturation matching.

## Operating mode (user, 2026-11-04; A-56)
Decide implementation details yourself and log each in **one line** (ASSUMPTIONS or the tuning ledger). **Stop only for:** (a) a change to a frozen value (§5, `configs/default.yaml`); (b) a result that threatens the experiment; (c) a failed gate. Report at the end of M5 + ROBI.

## Camera model and harness: fixed, no change once test data exist (A-53; §5.11 takes precedence for the harness, A-62)
- **Camera** (`configs/camera_d415_ir.yaml`): C3 metal roughness 0.15 + Lambertian D 0.015, base reflectance 0.868 (S-15, S-16); Cycles glossy 3, max 12, 32 samples; C4 part albedo 0.247 (A-24, clipped mean matching); auto exposure setpoint 20 DN on the C3 left image, gain shared with C4 (A-42); noise e_per_dn 0.087 (effective) + read 1 DN, shared draws (A-12). Extra passes `r02`, `r04`, `bright`, `nogloss` (reflections off), each on its own exposure.
- **Harness** (`configs/harness.yaml`): ICP **H2** (stages 20/10/5 mm, ray-cast visibility, no step clamp), erosion 2 px; suction grasp point plane_fit. Chosen on dev by the pooled rule (leximin, ledger A-45).
- **Dev pilot** (`data/m5_dev/pilot`, 40 instance-views): A1 recall@5 mm C1 0.70, C2a 0.80, C2b 0.55, **C3 0.05**, C4 0.325; reflections off 0.025; roughness 0.2 / 0.4 0.075 / 0.325; bright matte 0.425. Task B brackets (n = 12): C1 0.75, C2b 0.58, C3 0, C4 0.50. Anchor (a): (i), (ii), (iv) pass; (iii) Min-Z 5.51 / 5.76% (accepted, 3a); subpixel RMS 0.090 px.

## M5 steps after the decision (user decisions 2026-11-04: A-51…A-55)
1. **Mechanism check (A-54):** done on the final dev render (A-58; `scripts/mechanism_check.py`, `scripts/fig_mechanism.py`).
2. **Extra passes:** done (`ir_render.extra_passes`).
3. **Render test scenes 0–49:** done (commits 73f0305 and 8ccbd95).
4. **Sanity first:** `scripts/pose_eval.py data/m5 <seeds> --condition C1 --offset 0 0` must pass (≥ 99% < 0.5 mm, §5.11). **Failed with H2 and with every candidate, see above.**
5. **Metrics:** `scripts/run_eval.py data/m5 data/m5/results 0 49 --conditions C1 C2a C2b C3 C4 C3r02 C3r04 C3nogloss C4bright` (sanity first, then A1, sweep, Task B); `scripts/stats_m5.py` (bootstrap, McNemar, fixed sequence, MDE; rule A-60); `scripts/sensor_metrics.py` (A-61); §5.8 on seeds 0–9: `scripts/stereo_scene.py <seed> --variant loose --passes metal matte`, then `run_eval.py` with C3loose, C4loose, reporting filled vs invalid metal pixels, C3 A1 recall and whether the ranking flips.
6. **Push** at the end of M5.
7. **Then ROBI (A-55):** 3 h time box, one figure (ROBI-D415 vs C3 0.15 / 0.2 / 0.4 vs C4; mm and px; range mismatch stated), framed on the mechanism: on metal, does the real D415 fill (smooth or bias towards the background) or leave holes?

## Open items
- Pilot MDE (A-18) not computed yet; compute from the test discordance in the statistics step and report it.
- Cycles renders are not bit-reproducible and C3 can flip per view (A-59): consider a descriptive noise-redraw bound on C3 recall.
- Unverified: Cycles roughness → α = roughness² (S-16 caveat).
- Unexplained: about a fifth of the dark-face pixels stay behind the surface under both cuts (A-58).

## Where things are
| Need | Path |
|---|---|
| Configs | `configs/default.yaml` (frozen), `configs/camera_d415_ir.yaml`, `configs/harness.yaml` |
| Dev data, final settings | `data/m5_dev/` (scenes 1000–1004, all conditions and passes; `selection/`, `pilot/`) |
| Dev data, reflections off | `data/m4/` (M4 settings) |
| Convergence renders | `data/m5_diag/` (`gb3`, `gb3_max12`, `gb1`, `gb3_s128`) |
| Test data and results | `data/m5/` (scenes 0–49), `data/m5/results/` (failed sanity run, kept), `data/m5/diag_sanity/` (A-62) |
| Mechanism results and figure | `data/m5/mechanism/`, `data/m5/figures/mechanism_dev_1001_0.png` |
| Planes / anchor (a) | `data/m3/plane/` (`anchor_a.json`, `anchor_a_calibration.json`) |
| Scripts | `scripts/` (docstrings give usage): `bproc_render_scene.py` (Blender, via `scripts/bproc.sh` only), `benchmark_m3.sh`, `stereo_scene.py`, `c2_depth.py`, `pose_eval.py`, `suction_eval.py`, `anchor_a.py`, `select_setpoint.py`, `select_harness.py`, `sanity_candidates.py`, `sanity_diagnosis.py`, `mechanism_check.py`, `mechanism_compare_render.py`, `fig_mechanism.py`, `run_eval.py`, `stats_m5.py`, `sensor_metrics.py`, `fig_results.py`, `robi_fetch.py`, `robi_compare.py`, `ir_appearance.py`, `fig_robi.py` |
| Code / tests | `src/synthrgbd/` (pose, suction, stereo, …); `.venv/bin/python -m pytest` (94 pass) |
| Decisions, assumptions, ledger, sources | `docs/PLAN.md`, `docs/ASSUMPTIONS.md` (ledger under A-45), `docs/SOURCES.md` |
| Code dictionary (Italian) | `docs/GLOSSARY.md`; write codes with their meaning in messages to the user |

## Docs until Saturday (slimmed)
DIARY: one short entry per milestone. ASSUMPTIONS / ledger: one-line rows. SOURCES: only items the report cites. PLAN: §5.12 rows only.
