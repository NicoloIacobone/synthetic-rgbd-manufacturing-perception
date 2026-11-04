# Status

Handoff note between sessions. **Read first**, then CLAUDE.md's other context files (task_description, PLAN, ASSUMPTIONS). Keep it short; overwrite outdated content (history is in DIARY.md and git).

- **Updated:** 2026-11-04, ~17:45 CET (Wednesday). About one day ahead of plan.
- **Phase:** Phase 1. **M1–M4 done. M5 stopped at Step 1 on a bug (A-57), waiting for the user's decision.** No test data exist yet; Steps 2–5 not started.
- **Protocol:** frozen at tag `protocol-v1`; 4 rows in PLAN §5.12, none added. Primary endpoint unchanged: A1 recall at MSSD < 5 mm, offset 10 mm / 10°; fixed-sequence testing C1 vs C3 → C2b vs C3 → C3 vs C4 at α = 0.05; unit = instance-view, visib_fract ≥ 0.1, a missing estimate = failure.
- **Gates:** A metrics by Fri 6 Nov; code freeze Sat 7 Nov 20:00; target submission Sun 8 Nov 18:00. Report skeleton: Thursday evening. Push at the end of each milestone.

## Decision needed (A-57, A-58)
BlenderProc's default Cycles `glossy_bounces = 0` was never overridden, so **every IR render so far has no reflected image on metal**. On that data the C3 bias is SGBM filling dark metal, pulled towards the background; reflected dots cannot occur. With reflections on (dev diagnostic `data/m5_diag/gb3`), both mechanisms act. Dev pixel numbers: A-58. A1 and Task B were deliberately not run on glossy > 0.
- **Option 1 (agent's recommendation):** enable reflections in `configs/camera_d415_ir.yaml` (not frozen), re-run the dev rules (C4 albedo, setpoint, harness, grasp point), record the new pilot, then M5; keep glossy 0 as a descriptive pass.
- **Option 2:** keep glossy 0 as the headline with all M4 choices; add glossy 3 as a descriptive pass; correct PLAN §3.
- **Option 3:** keep glossy 0 only; disclose as a limitation.
- **If option 1, also decide the C4 albedo:** A-24 mean matching gives 1.90 (impossible). Clipped-at-saturation matching gives 0.317; keeping 0.085 gives up brightness matching. Decide before any A1 on the new render.
- **Proposed checks, not run:** 128 vs 32 samples on one dev view (Monte Carlo noise in reflected dots); glossy 1 vs 3 and max_bounces 12 on dev. About 5 min each.

## Operating mode (user, 2026-11-04; A-56)
Decide implementation details yourself and log each in **one line** (ASSUMPTIONS or the tuning ledger). **Stop only for:** (a) a change to a frozen value (§5, `configs/default.yaml`); (b) a result that threatens the experiment; (c) a failed gate. Report at the end of M5 + ROBI.

## Camera model and harness as of M4 (A-53 locks them once test data exist)
- **Camera** (`configs/camera_d415_ir.yaml`): C3 metal roughness 0.15 + Lambertian D 0.015, base reflectance 0.868 (S-15, S-16); C4 part albedo 0.085 (A-24, mean matching); auto exposure setpoint 10 DN on the C3 left image, gain shared with C4 (A-42); noise e_per_dn 0.12 (effective) + read 1 DN, shared draws (A-12). **Cycles glossy_bounces 0 (the bug; not in the config).**
- **Harness** (`configs/harness.yaml`): ICP **H3** (stages 20/10/5 mm, ray-cast visibility, step clamp), erosion 2 px; suction grasp point plane_fit. Chosen on dev by the pooled rule (leximin, ledger A-45).
- **Dev pilot, glossy 0** (seeds 1000–1004, `data/m4/selection/`): A1 recall@5 mm C1 0.70, C2a 0.78, C2b 0.55, **C3 0.00**, C4 0.23. Sweep (2/5/20): C1 0.98 / 0.88 / 0.60, C3 0.05 / 0 / 0. Task B brackets: C1 0.75, C3 0, C4 0.25. Anchor (a) under the rule: (i), (ii), (iv) pass; (iii) Min-Z 6.35 / 6.59% (marginal failure, accepted at M3, 3a); subpixel RMS 0.090 px.

## M5 steps after the decision (user decisions 2026-11-04: A-51…A-55)
1. **Mechanism check (A-54):** done (A-58). If reflections are enabled, re-run `scripts/mechanism_check.py` and `scripts/fig_mechanism.py` on the final dev render.
2. **Extra passes (to implement):** `scripts/bproc_render_scene.py` renders only `metal` and `matte`. Add extra IR passes for (B) metal roughness 0.2 and 0.4 and (D) bright matte albedo 0.5 (e.g. `--extra-pass name:kind:value` → `ir/<im>_<name>.npz`), and make `scripts/stereo_scene.py` match them into `depth_stereo_<name>`. Exposure of extra passes: decide and log (suggestion: each extra metal pass auto-exposes on its own left image; bright matte on its own). Same noise draws.
3. **Render test scenes 0–49** one at a time (8 GB): `scripts/benchmark_m3.sh data/m5 0 1 … 49` (render + gt_info + stereo + BOP check; ~50 s/scene base, + extra passes). Then `.venv/bin/python scripts/c2_depth.py data/m5 0 … 49`.
4. **Sanity first:** `scripts/pose_eval.py data/m5 <seeds> --condition C1 --offset 0 0` must pass (≥ 99% < 0.5 mm, §5.11).
5. **Metrics:** A1 (`--offset 10 10`) and the sweep (2/5/20) for C1, C2a, C2b, C3, C4 (+ the B/D passes, descriptive); Task B (`scripts/suction_eval.py`); sensor metrics (to write: MAE, **median**, **% > 5 mm**, invalid; edge vs interior; per part type, A-47); statistics (to write: scene bootstrap 10 000, McNemar, fixed sequence); strict/loose invalidation check §5.8 on seeds 0–9 (loose = uniqueness 0, left-right check off, speckle off; ledger), reporting filled vs invalid metal pixels, C3 A1 recall and whether the ranking flips.
6. **Push** at the end of M5.
7. **Then ROBI (A-55):** 3 h time box, one figure (ROBI-D415 vs C3 0.15 / 0.2 / 0.4 vs C4; mm and px; range mismatch stated), framed on the mechanism: on metal, does the real D415 fill (smooth or bias towards the background) or leave holes?

## Open items
- Pilot MDE (A-18) not computed yet; compute from the test discordance in the statistics step and report it.
- C4 is weak on dev (dark parts, albedo 0.085); the bright-matte pass (D) is the descriptive contrast.
- Unverified: Cycles roughness → α = roughness² (S-16 caveat).
- Unexplained at glossy 3: biased pixels on faces whose first-order mirror ray sees nothing also stop following the background (A-58).

## Where things are
| Need | Path |
|---|---|
| Configs | `configs/default.yaml` (frozen), `configs/camera_d415_ir.yaml`, `configs/harness.yaml` |
| Dev data (M4, glossy 0) | `data/m4/` (scenes 1000–1004, all conditions; `selection/` = harness and pilot runs; `logs/`) |
| Dev diagnostic (glossy 3) | `data/m5_diag/gb3/` (C3 and C4 depth only; no C2, no selection runs) |
| Mechanism results and figure | `data/m5/mechanism/`, `data/m5/figures/mechanism_dev_1001_0.png` |
| Planes / anchor (a) | `data/m3/plane/` (`anchor_a.json`, `anchor_a_calibration.json`) |
| Scripts | `scripts/` (docstrings give usage): `bproc_render_scene.py` (Blender, via `scripts/bproc.sh` only), `benchmark_m3.sh`, `stereo_scene.py`, `c2_depth.py`, `pose_eval.py`, `suction_eval.py`, `anchor_a.py`, `select_setpoint.py`, `select_harness.py`, `mechanism_check.py`, `mechanism_compare_render.py`, `fig_mechanism.py` |
| Code / tests | `src/synthrgbd/` (pose, suction, stereo, …); `.venv/bin/python -m pytest` (86 pass) |
| Decisions, assumptions, ledger, sources | `docs/PLAN.md`, `docs/ASSUMPTIONS.md` (ledger under A-45), `docs/SOURCES.md` |

## Docs until Saturday (slimmed)
DIARY: one short entry per milestone. ASSUMPTIONS / ledger: one-line rows. SOURCES: only items the report cites. PLAN: §5.12 rows only.
