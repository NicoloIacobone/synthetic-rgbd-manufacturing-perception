# Status

Handoff note between sessions. **Read first**, then CLAUDE.md's other context files (task_description, PLAN, ASSUMPTIONS). Keep it short; overwrite outdated content (history is in DIARY.md and git).

- **Updated:** 2026-11-04, ~18:55 CET (Wednesday). About one day ahead of plan.
- **Phase:** Phase 1. **M1–M4 done. M5 PAUSED by the user mid test render (computer shut down); restart only when the user says so.** The reflection bug is fixed (A-57) and the dev rules are re-run. Scenes 0–2 of 0–49 are rendered; no test metric has been computed yet.
- **Protocol:** frozen at tag `protocol-v1`; 4 rows in PLAN §5.12, none added. Primary endpoint unchanged: A1 recall at MSSD < 5 mm, offset 10 mm / 10°; fixed-sequence testing C1 vs C3 → C2b vs C3 → C3 vs C4 at α = 0.05; unit = instance-view, visib_fract ≥ 0.1, a missing estimate = failure.
- **Gates:** A metrics by Fri 6 Nov; code freeze Sat 7 Nov 20:00; target submission Sun 8 Nov 18:00. Report skeleton: Thursday evening. Push at the end of each milestone.

## How to resume (nothing is running; all state is on disk)
1. **Render:** `scripts/render_test.sh data/m5 0 49 > data/m5/logs/render_test.log 2>&1` in the background. It keeps finished scenes (0–2), renders the other 47 one at a time (105–130 s each, about 1.6 h), then writes C2 depth. Do not edit tracked files while it runs: scene_meta would log a dirty commit. Scenes 0–2 record commit 73f0305; later scenes record the docs-only commit that added this note; the code is identical.
2. **ROBI subset (can run alongside):** `.venv/bin/python -I scripts/robi_fetch.py 1lc2yNZo2W8cnd8oUe6Vb5cdUnR1t8YTK data/robi/subset --views-per-scene 12` (Zigzag, keeps the 24 files already there), then the same with `1qqG0KVW6_Upxc95Wuk9HecR0JrxGZSd4` (Chrome screw). Whole-file Drive downloads return "Quota exceeded"; range requests work. CAD models are in `data/robi/cad/`, camera files in `data/robi/toolkit/cam/`. The 3 h box has hardly started.
3. **Before evaluating, commit the three untracked scripts** (`scripts/fig_results.py`, `scripts/robi_fetch.py`, `scripts/robi_compare.py`), since `pose_eval.py` flags untracked files in `scripts/` as a dirty tree. `robi_compare.py` is untested: check the pose convention and CAD units with `--overlay` first.
4. **Then steps 4–7 below.** Also planned: a descriptive noise-redraw bound on C3 recall on seeds 0–9 (A-59), which needs a small `stereo_scene.py` option, added after the render.
5. **Tell the user at the end:** C4 albedo 0.247 and H2 differ from what was approved or expected (A-24, ledger); the approved rule moved them.

## Decision taken (A-57, A-58)
BlenderProc's default Cycles `glossy_bounces = 0` was never overridden, so no IR render before the fix had a reflected image on metal. User decision 2026-11-04: fix it (glossy 3; max 12 and 32 samples by the ledger rules), re-run the dev rules, keep reflections off as a descriptive pass, C4 albedo by clipped-at-saturation matching.

## Operating mode (user, 2026-11-04; A-56)
Decide implementation details yourself and log each in **one line** (ASSUMPTIONS or the tuning ledger). **Stop only for:** (a) a change to a frozen value (§5, `configs/default.yaml`); (b) a result that threatens the experiment; (c) a failed gate. Report at the end of M5 + ROBI.

## Camera model and harness: fixed, no change once test data exist (A-53)
- **Camera** (`configs/camera_d415_ir.yaml`): C3 metal roughness 0.15 + Lambertian D 0.015, base reflectance 0.868 (S-15, S-16); Cycles glossy 3, max 12, 32 samples; C4 part albedo 0.247 (A-24, clipped mean matching); auto exposure setpoint 20 DN on the C3 left image, gain shared with C4 (A-42); noise e_per_dn 0.087 (effective) + read 1 DN, shared draws (A-12). Extra passes `r02`, `r04`, `bright`, `nogloss` (reflections off), each on its own exposure.
- **Harness** (`configs/harness.yaml`): ICP **H2** (stages 20/10/5 mm, ray-cast visibility, no step clamp), erosion 2 px; suction grasp point plane_fit. Chosen on dev by the pooled rule (leximin, ledger A-45).
- **Dev pilot** (`data/m5_dev/pilot`, 40 instance-views): A1 recall@5 mm C1 0.70, C2a 0.80, C2b 0.55, **C3 0.05**, C4 0.325; reflections off 0.025; roughness 0.2 / 0.4 0.075 / 0.325; bright matte 0.425. Task B brackets (n = 12): C1 0.75, C2b 0.58, C3 0, C4 0.50. Anchor (a): (i), (ii), (iv) pass; (iii) Min-Z 5.51 / 5.76% (accepted, 3a); subpixel RMS 0.090 px.

## M5 steps after the decision (user decisions 2026-11-04: A-51…A-55)
1. **Mechanism check (A-54):** done on the final dev render (A-58; `scripts/mechanism_check.py`, `scripts/fig_mechanism.py`).
2. **Extra passes:** done (`ir_render.extra_passes`).
3. **Render test scenes 0–49** one at a time (8 GB): `scripts/benchmark_m3.sh data/m5 <seed>` per seed, about 105 s/scene; then `.venv/bin/python scripts/c2_depth.py data/m5 0 … 49`.
4. **Sanity first:** `scripts/pose_eval.py data/m5 <seeds> --condition C1 --offset 0 0` must pass (≥ 99% < 0.5 mm, §5.11).
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
| Test data and results | `data/m5/` (scenes 0–49), `data/m5/results/` |
| Mechanism results and figure | `data/m5/mechanism/`, `data/m5/figures/mechanism_dev_1001_0.png` |
| Planes / anchor (a) | `data/m3/plane/` (`anchor_a.json`, `anchor_a_calibration.json`) |
| Scripts | `scripts/` (docstrings give usage): `bproc_render_scene.py` (Blender, via `scripts/bproc.sh` only), `benchmark_m3.sh`, `stereo_scene.py`, `c2_depth.py`, `pose_eval.py`, `suction_eval.py`, `anchor_a.py`, `select_setpoint.py`, `select_harness.py`, `mechanism_check.py`, `mechanism_compare_render.py`, `fig_mechanism.py`, `run_eval.py`, `stats_m5.py`, `sensor_metrics.py` |
| Code / tests | `src/synthrgbd/` (pose, suction, stereo, …); `.venv/bin/python -m pytest` (94 pass) |
| Decisions, assumptions, ledger, sources | `docs/PLAN.md`, `docs/ASSUMPTIONS.md` (ledger under A-45), `docs/SOURCES.md` |

## Docs until Saturday (slimmed)
DIARY: one short entry per milestone. ASSUMPTIONS / ledger: one-line rows. SOURCES: only items the report cites. PLAN: §5.12 rows only.
