# Project plan

Synthetic RGB-D of aluminium profiles and brackets with a RealSense D415 camera model, and the effect on downstream pose estimation and suction grasping.

Authoritative requirements are in [`task_description.md`](../task_description.md). This file records **decisions and how they will be evaluated**. Assumptions live in [`ASSUMPTIONS.md`](ASSUMPTIONS.md) (IDs `A-xx`, `H-x`), sources in [`SOURCES.md`](SOURCES.md) (IDs `[S-xx]`), the report outline in [`REPORT_PLAN.md`](REPORT_PLAN.md), and the current state in [`STATUS.md`](STATUS.md).

- **Status:** Phase 0 (planning) and pre-Phase-1 setup are complete as of 2026-11-03; in Phase 1, milestones M1 and M2 are done (2026-11-03). **M3 done on 2026-11-04 with one marginal gate failure:** gate criteria A-38 (i), (ii), (iv) pass and (iii) fails marginally; the user kept the stereo route and the matcher settings of commit 044ee81 (option 3a, see §7). Resolution rule A-39 met (43.7 s per frame, 1280×720 kept). M4 is closed and M5 is stopped at the failed §5.11 sanity gate; [`STATUS.md`](STATUS.md) has the current state. The protocol (§5) is frozen at git tag `protocol-v1`; changes after that are deviations (§5.12).
- **Deadline:** Sun 2026-11-08 23:59 CET (A-02).
- **Budget:** about 6 h/day, Apple M2 with 8 GB, free software only.

---

## 1. Success criteria per requirement

| Requirement (task_description.md) | What counts as done | Evidence in the report |
|---|---|---|
| Commercial RGB-D reference camera | D415 chosen, with a documented rationale | §2 of the report, [S-01][S-05][S-06] |
| Labelled synthetic RGB-D pipeline | BOP-format output: RGB, ideal depth, instance masks, 6D poses, intrinsics, plus simulated D415 depth | Figure of example frames; README run command |
| Camera imperfections on these parts | Active-stereo simulation with metal materials; table of included/excluded effects with reasons | §4 table; anchor (a) plot; C3 vs C4 sensor metrics |
| One small experiment, quantitative, incl. what did not work | Pre-specified primary endpoint (§5.6), CIs, failure log | §6 results; "what did not work" subsection fed by DIARY.md |
| ≤1 page riskiest synthetic-to-real assumption + 6-month plan | Reflection section of the report | §8 of the report |
| AI-use note with one correction | Taken from AI_USE_LOG.md | §9 of the report |
| PDF ≤ 8 pages, runnable code | Everything fits in 8 pages incl. reflection and AI note (A-01); a quick-run configuration runs in minutes | PDF + repository README |

## 2. Approved decisions (2026-11-03)

| # | Decision | Rationale (short) | Sources |
|---|---|---|---|
| D1 | **Task A (main): CAD-based 6D pose estimation from depth.** **Task B (in parallel): suction grasp detection.** Parallel-jaw grasping is a stretch goal | No training needed, so depth input is the only variable; relevant to pick-and-assemble. B shares the same data and harness | — |
| D2 | **Parts:** 2–3 T-slot-like aluminium profile lengths and 1–2 L-brackets, procedurally generated | Scoping choice, *not* a researched convention (A-05) | — |
| D3 | **Toolchain:** BlenderProc 2.8; analysis in a separate Python env with Open3D/OpenCV. Fallback: Open3D raycasting. UTM/Ubuntu VM not used | Offers BOP output (depth, masks, poses), PBR metal and CPU stereo matching in one tool; Apple Silicon use evidenced by issue reports only (A-23) | [S-10][S-11] ✅ |
| D4 | **Camera: Intel RealSense D415** (active IR stereo, 55 mm baseline) | Real D415 data on metal parts exists (ROBI), plus a D415 metrology study (Carfagni) | [S-05][S-04][S-01][S-08] ✅ |
| D5 | **External anchors:** (a) sensor-level plane check vs. datasheet formula and Carfagni (mandatory); (c) BOP symmetry-aware metrics (mandatory); (b) ROBI comparison (first optional) | Results can be compared with published references even though our parts differ from published datasets | [S-02][S-04][S-07] |
| D6 | **Camera model: Route 3 hybrid.** Physics-based active stereo (left/right IR + projected pattern + PBR materials → OpenCV SGBM) is *the camera model*. A datasheet-noise layer is the naive baseline | Material-specific effects emerge from rendering rather than being hand-coded; precedent in [S-09] | [S-09][S-11] ✅ |
| D7 | **Fallback:** if the stereo route isn't plausible by the Wed 4 Nov gate, switch to Route 2, a rule-based image-space model (z² noise, occlusion invalidation, edge flying pixels, specular dropout) | Time risk | — |
| D8 | **Resolution and placement:** 1280×720; camera 0.65–0.95 m above the table; tilt ≤ 30°. Fallback: a lower resolution (848×480 is the D415's other native mode) **proposed to the user** if the projected full render exceeds 8 h (rule fixed 2026-11-04, A-39) | 1280×720 is Intel's recommended D415 resolution and matches ROBI. Datasheet Min-Z = 450 mm at 1280×720 (A-16) | [S-01][S-03][S-05] ✅ |
| D9 | **Experiment design:** as in §5, after an adversarial review. All review changes accepted; suggestions to use forum images and the MP6D dataset rejected | Avoids C2 being trivially null by construction, A1 sitting at its ceiling, and pseudo-replication | [S-04] |
| D10 | **Dev/test split:** the 5-scene M4 pilot is the dev split (disjoint seed range), excluded from the ~50 test scenes (§5.10) | Hyperparameters are never tuned on test scenes; no extra render cost | — |
| D11 | **Suction planarity tolerance = 1.0 mm** (A-19, §5.3) | Rejects T-slot openings and edges; tolerant of mesh tessellation | — |
| D12 | **C1 sanity check = zero-offset ICP test** (§5.11), replacing "A1 on C1 ≈ 0 error" | At the 10 mm/10° offset, C1 can fail for geometric reasons (ICP sliding along prisms, §5.9), so it cannot serve as a bug detector | — |
| D13 | **SGBM runs in the analysis env (`.venv`, OpenCV 5.0), not in Blender (option B).** Blender renders and exports the left/right IR pair once (linear 16-bit, no tone mapping); our own code adds IR noise/blur, runs SGBM and converts to depth. BlenderProc's `stereo_global_matching` is not used. This replaces the "CPU stereo matching in one tool" part of D3's rationale; D3 otherwise stands | The helper hard-codes the matcher (no left-right check or speckle filter, window 5 px), maps zero disparity to max depth and is not metric with WLS on [S-11]. Option B allows re-matching without re-rendering (§5.8 check, anchor tuning), shared seeds (§5.10) and unit-tested code | [S-11] ✅ |
| D14 | **BlenderProc env:** BlenderProc 2.8.0 in its own launcher env `.venv-bproc` (pins `requirements-bproc.txt`, lock `requirements-bproc.lock.txt`), with our local macOS patch (`patches/blenderproc-2.8.0-macos-app-bundle.patch`, applied by `scripts/setup_blenderproc.sh`) instead of granting the terminal App Management permission. Blender always via `scripts/bproc.sh` (repo-local `blender/`) | Keeps `.venv` equal to its lock; no OS permission change needed; reproducible on macOS. On Linux the patch is not applied | [S-10] ✅ |
| D15 | **M3 set-up, fixed before any M3 data:** projector field of projection 67° × 41° (A-36); static semi-random dot pattern, 30 000 dots by default (A-37); quantitative M3 gate pass criteria on a matte plane (A-38); resolution rule "1280×720 if the projected full render fits in 8 h" (A-39). If a gate criterion fails, the agent stops and presents the options (Route 2 per D7, or the patched-helper fallback per D13) to the user rather than switching | Makes the M3 go/no-go and the resolution choice pre-specified rather than judged after the results. The D415 dot pattern is not published, so its density follows Intel's projector guidance | [S-01][S-13] ✅ |

D10–D12 were decided by the user on 2026-11-03, before any data existed, to close gaps in the protocol. D13 and D14 were decided by the user on 2026-11-03 (D14 after M1); **its feasibility is re-checked at M3** (A-32): if the linear IR export fails or the round trip is too slow by the M3 gate, the fallback is the BlenderProc helper copied into our code and patched (left-right check on, zero disparity → invalid, no WLS), run inside Blender. D15 was decided by the user on 2026-11-04 (projector FOV, gate criteria and resolution rule as stated by the user; dot-pattern defaults and the operational details of the criteria proposed by the agent from the research, see A-37/A-38).

## 3. Scope

**Included effects** (camera model C3/C4)
- Stereo disparity noise that grows with z².
- Occlusion shadows: pixels seen by only one camera are invalid.
- Invalid band at the left image edge, and the minimum-range limit (disparity search range of 126 px).
- Edge fattening and flying pixels caused by the matching window.
- Dependence on incidence angle, emerging from rendering.
- Specular glare and dark regions on metal, together with how the projected pattern looks on metal.
- IR image sensor noise and blur before matching.

**Excluded effects, with reasons** (each is an assumption)
- Motion blur and rolling shutter: the scene is static (A-04).
- Intel post-processing filters: we model raw depth (A-08).
- Sunlight, ambient IR and temperature drift: indoor cell (A-03).
- Calibration bias and lens non-linearity: calibrated out per unit (A-09).
- RGB imperfections: both tasks use depth only.
- Explicit multipath: not modelled on purpose; some interreflection may emerge from path tracing (A-22).
- Temporal noise and multi-frame filtering: single-frame setting.
- Projector non-uniformity (central hot spot) and laser speckle: not quantified in any source we found; the pattern envelope is uniform (A-37).

**Non-goals**
- Object detection or segmentation (ground-truth masks are given, A-07).
- Grasp execution with physics, or a real robot.
- RGB-based methods.
- Replicating Intel's on-chip matcher (A-10).
- Training neural networks in the minimum deliverable.
- ROS2.

**Claim scope:** results apply to *"an active-stereo model with D415 geometry"*, not to the physical D415.

## 4. Pipeline (planned)

1. **Parts:** procedural meshes (profiles with T-slots, L-brackets) with known CAD and symmetries (A-20).
2. **Scenes:** a tray or table in a cell; 3–6 parts per scene placed with physics drop; ~50 test scenes × 2 views, scaled to measured render time, plus 5 dev scenes (§5.10).
3. **Renders per frame:**
   - RGB + ideal depth + instance masks (BOP writer);
   - left/right IR with projected pattern, metal materials;
   - left/right IR, matte materials with matched brightness;
   - IR pairs exported as linear 16-bit images (view transform "Standard", no tone mapping), so saturation is decided by our exposure model, not by Blender's display transform (D13, A-32).
4. **IR post-processing (in `.venv`, D13):** add sensor noise and blur, then run our own SGBM tuned to D415 geometry (baseline 55 mm; disparity search 126 px, implemented as `num_disparities=128` plus masking of d > 126, A-25). No WLS filtering and no depth completion; invalid pixels (including zero disparity) are 0. BlenderProc's stereo helper is not used [S-11]. Convert disparity to depth, taking care of units, z-depth vs ray distance, and OpenCV's ×16 disparity scaling.
5. **Datasheet noise layer for C2**, at two levels: the formula level and the Carfagni-matched level.

## 5. Experiment protocol (pre-specified)

### 5.1 Conditions
These are paired: same scenes, same poses.

| ID | Depth input | Role |
|---|---|---|
| C1 | Ideal rendered depth | Upper bound; also used for the zero-offset sanity check (§5.11) |
| C2a / C2b | Ideal depth + Gaussian noise, σ = z²·ε_d/(f·B) [S-02] with ε_d = 0.08 px [S-03] (C2a), and a level matched to Carfagni (C2b) [S-04] | **Naive baseline, not the camera model** |
| C3 | Stereo simulation, metal materials | **The camera model (headline)** |
| C4 | Stereo simulation, matte materials, brightness matched | Isolates the material effect (C3 vs C4) |

### 5.2 Task A: pose estimation
- Inputs: ground-truth instance mask → masked depth points → point-to-plane ICP against the CAD model.
- **A1 (primary):** start from the ground-truth pose with a 10 mm / 10° offset. Sweep the offset over 2/5/10/20 mm as a secondary result, with the rotation swept together (n mm and n°, A-30; confirmed by the user, to be re-checked when the sweep is implemented at M5).
- **Offset definition:** a translation of exactly the stated magnitude in a uniformly random direction, composed with a rotation of exactly the stated angle about a uniformly random axis. The offsets are drawn once per instance and are **identical across conditions** (§5.10).
- **A2 (optional):** global registration (FPFH + RANSAC) followed by ICP.
- Hyperparameters are fixed once on the dev split (§5.10) and are identical across conditions.

### 5.3 Task B: suction
- On the masked points, estimate normals and choose the flattest point that fits a cup of 10 mm radius.
- **Success** is checked against the ground-truth mesh. All three must hold:
  - the point is within 2 mm of the surface;
  - the normal error is under 15°;
  - the ground-truth surface within the cup disk is planar (the cup is not over a slot or edge): the whole 10 mm-radius disk lies on the same part, and every ground-truth surface point inside it is within **1.0 mm** of the tangent plane at the chosen point (D11, A-19).
- All suction parameters are fixed before running (A-19) and are in `configs/default.yaml`.

### 5.4 Metrics
- **A:** MSSD (symmetry-aware). Primary: recall at **absolute 5 mm**. Secondary: recall at 2 mm, translation and rotation error, error along the profile axis vs across it.
- **B:** success rate.
- **Sensor (cause → effect):** depth MAE vs ground truth, % invalid pixels, % of pixels with error > 5 mm. Each is split edge vs interior and metal vs matte.

### 5.5 Statistics
- Test scenes only; dev scenes are never part of the reported results.
- Bootstrap over **scenes** (not instances), 95% CIs on paired differences in success rate, 10 000 resamples.
- McNemar's test for paired success/failure outcomes.
- State the detectable effect size: roughly 10–15 percentage points with ~50 scenes (A-18; computed on the dev-split pilot at M4).
- Log seeds and compute times.

### 5.6 Primary endpoint
Fraction of parts with MSSD < 5 mm in A1 (10 mm / 10° offset), compared for **C1 vs C3** and **C3 vs C4**.

### 5.7 Hypotheses
- **H-1:** recall C1 ≥ C2 > C3.
- **H-2:** C3 ≠ C4.

Null results are reported as results.

### 5.8 Robustness checks
- Strict vs loose SGBM invalidation (uniqueness, left-right check, speckle filtering) on a 10-scene subset: does the ranking of conditions flip?
- Anchor (a): a flat matte plane at 0.3–1.0 m vs. the formula and Carfagni. This validates **only the stereo pipeline's noise floor (C4)**, not metal behaviour.

### 5.9 Expected failure modes (plan for them)
- **Simulated IR too clean:** C4 ≈ C1.
- **Metal fully dark or saturated.** Check Cycles caustics settings.
- **Unit or convention bugs:** units, z-depth vs ray distance, ×16 disparity scaling.
- **Physics drop goes wrong:** parts roll off the tray or stack unrealistically.
- **ICP slides along prisms:** this error comes from geometry, not the camera.
- **Wrong symmetry definitions.**
- **Suction check passes almost everywhere.**
- **A1 at ceiling, or A2 at floor.**

### 5.10 Dev/test split, seeds and pairing (D10)
- **Test scenes:** scene seeds 0–49. **Dev scenes:** scene seeds 1000–1004 (= the M4 pilot). The ranges are disjoint, and dev scenes are excluded from all reported results.
- **Master seed** 0, set in `configs/default.yaml`.
- Every random stream is derived from `(master, scene seed, view, stream)` via `numpy.random.SeedSequence` (`src/synthrgbd/seeds.py`). The streams are scene layout/physics, C2a noise, C2b noise, IR sensor noise, initial pose offset, and bootstrap.
- **Pairing:** C3 and C4 use the **same IR-noise realisation**, and all conditions use the **same initial pose offsets**, so paired differences come only from the depth input.
- Every generated dataset and experiment run logs its seeds and the commit hash.

### 5.11 Sanity check (D12)
- On C1, start ICP **at the ground-truth pose** (zero offset). At least **99%** of instances must stay at MSSD < **0.5 mm**.
- If the check fails, treat it as a bug: fix, rerun all conditions, and log it in DIARY.md. A failed check is not a result.
- C1 at the 10 mm / 10° offset is reported as the upper bound, whatever its value.
- Unit tests in `tests/` cover the known silent-bug risks (R5): ×16 disparity scaling, disparity ↔ depth, z-depth vs ray distance, MSSD with symmetries.

### 5.12 Protocol freeze and deviations
- The protocol (§5 and the thresholds in `configs/default.yaml`) is frozen at git tag `protocol-v1`, before any data exist.
- Any later change is a **deviation**: add a dated row below with the reason, and report it in the paper.

| Date | Deviation | Reason |
|---|---|---|
| 2026-11-03 | §5.3/§5.4 Task B: success rate is reported **per part type (profiles, brackets) in addition to** the pre-specified overall rate; definition, thresholds and cup radius unchanged. Approved by the user (option a) | With the frozen 10 mm cup no profile face can pass the planarity check (largest flat disk 5.5 mm side, 9.76 mm end face, A-33), so profiles fail for geometric reasons in every condition; the overall rate alone would mix this with the camera effect. Found at M2, before any Task B data |
| 2026-11-04 | **Editorial, no protocol value changed.** Commit 348d49c (2026-11-03) changed the comment of `task_a.offset_sweep` in `configs/default.yaml` (added "confirmed; re-check at M5") and the wording of the A1 line in §5.2 (added "confirmed by the user, to be re-checked when the sweep is implemented at M5", A-30). Commit b6c5b00 (2026-11-03) edited only PLAN §2 (D13) and §4, outside the frozen scope; listed for completeness. Approved by the user | Found in the post-M2 review; logged at the user's request so every post-tag edit of a frozen file is traceable. Thresholds, conditions, endpoints and statistics are unchanged |
| 2026-11-04 | **§5.5/§5.7, before any test data.** (i) H-1's "C2 > C3" contrast is tested with **C2b**: ε_d fitted to Carfagni's plane SD at 1 m (4.74 mm → ε_d = 4.74 mm × 55.25 px·m / (1 m)² ≈ 0.26 px). The 0.2 m point would imply 0.48 px, so a single z² law does not fit both points; the 1 m point is used because it lies in the range of our scenes (0.61–1.24 m). C2a is reported descriptively. (ii) "C1 ≥ C2" is reported descriptively; no non-inferiority test. (iii) Multiplicity: **fixed-sequence testing at α = 0.05 in the order C1 vs C3 → C2b vs C3 → C3 vs C4**. A comparison is confirmatory only if all earlier ones rejected; otherwise it and all later ones are exploratory. Bootstrap CIs and McNemar p-values are reported for all comparisons. (iv) The C2b value is written into `configs/default.yaml` at M4, as the frozen comment ("fitted at M4") anticipates. Endpoint, thresholds, conditions and Task B are unchanged. Approved by the user | Found in the pre-M4 design review: the protocol did not name the C2 level used for H-1 and had no multiplicity rule. C2b is the conservative (generous) naive baseline, so a C2b vs C3 difference cannot be explained by noise magnitude alone. Order: C2b vs C3 answers the task's question directly; C3 vs C4 depends most on the unsourced metal roughness, so it comes last |
| 2026-11-04 | **§5.4/§5.6 clarification, before any test data.** The unit of the primary endpoint ("fraction of parts with MSSD < 5 mm") and of the Task B success rate is the ground-truth instance-view. Instance-views with visib_fract < 0.1 are excluded from every task and condition, and their number is reported. An included instance-view with too few valid depth points, or with no ICP or suction result, counts as a failure in that condition, which keeps the pairing across conditions. No threshold, condition or endpoint changes; no effect on the dev scenes (minimum visib_fract 0.749). Approved by the user | §5.6 did not define which instances form the denominator (found at M4 step 1). The 10% threshold is the BOP convention [S-07]: BOP 2020 Table 1 counts instances with at least 10% of the projected surface visible; bop_toolkit's BOP'18 evaluation used visib_gt_min = 0.1 |
| 2026-11-05 | **§5.2/§5.10/§5.11, after the test render, before any recall at a real offset.** The Task A harness changed after test data existed: (i) ray-cast cache bug fixed (ade985f); (ii) CAD samples per model 50 000 → 200 000 (3ad09a2, `configs/harness.yaml`); (iii) harness re-selected on dev by the A-45 rule among the variants that passed §5.11: **H3** (H2 before). **Disclosed departure from §5.2 and D10:** the sample count was chosen after seeing zero-offset drift on C1 on the test scenes, and that same check decided which variants were eligible. Only C1 at zero offset was looked at on test scenes. The §5.11 threshold, conditions, endpoints, statistics, rendering and Task B are unchanged. Approved by the user (§5.11 takes precedence over A-53; fix steps; closing M5) | §5.11 failed with H2 (416/459, required ≥ 99%), and §5.11 says to treat that as a bug: fix and rerun all conditions. 36 of the 43 failures came from the cache bug, the other 7 from the coarse CAD sampling (A-62). No recall at a real offset had been computed on test scenes, so the fix cannot favour any condition. After the fix H0–H3 all reach 459/459 |

## 6. Minimum deliverable and optional work

**Minimum deliverable**
1. Pipeline producing a BOP dataset plus C2/C3/C4 depth.
2. Camera-model table and anchor (a).
3. A1 across C1–C4 with the sweep, MSSD and statistics.
4. Task B across the same conditions (unless frozen at the Friday gate).
5. Sensor metrics and the invalidation check.
6. Report ≤ 8 pages including reflection and AI note.
7. README with exact commands, a quick-run configuration, pinned versions and seeds.

**Optional work, in priority order**
1. ROBI comparison (b).
2. A2.
3. Per-effect ablation with the Route 2 model.
4. Parallel-jaw grasping.
5. Learned segmentation.
6. Video or sketches.

## 7. Milestones and gates (flexible)

Work proceeds as fast as it goes. Dates are **latest-by** gates, not planned slots.

| Milestone | Contents | Gate (latest by) → action if missed |
|---|---|---|
| M1 Environment | BlenderProc quickstart runs | 1 h of trying → Open3D fallback |
| M2 Scenes + labels | Procedural parts, physics scenes, BOP output | — |
| M3 Stereo route | IR pair + projector + SGBM; plane anchor; render benchmark per frame | **Wed 4 Nov end of day.** Pass criteria fixed in advance (A-38); if any fails, stop and present Route 2 (D7) or the patched helper (D13) to the user. Resolution rule A-39 (projected full render > 8 h → propose a lower resolution). **Outcome 2026-11-04: done with one marginal failure.** (i), (ii), (iv) pass; (iii) Min-Z fails: 5.03% / 5.07% valid at 0.42 / 0.43 m (limit ≤ 5%), out-of-range false matches in clumps of ≈ 120 px. User decision (option 3a): keep the stereo route and the matcher settings of 044ee81; report (iii) under "what did not work"; expected effect on the experiment nil (nearest scene pixel 0.609 m, A-16). Option 3b (speckle window 200 px) rejected. Not a §5.12 deviation (gate criteria are outside §5). A-39: 43.7 s/frame, 1280×720 kept |
| M4 Camera model done | Metal/matte, IR noise and blur, SGBM tuning, 5-scene pilot on the dev split (ceiling/floor check; power estimate A-18; tune hyperparameters; log any design change as a deviation, §5.12) | — |
| M5 Experiment | Full renders, A1 + B, sensor metrics, statistics, invalidation check | **A metrics by Fri 6 Nov end of day** → otherwise freeze B |
| M6 Report | Skeleton → figures → text → reflection → AI note; README | **Code freeze Sat 7 Nov 20:00. Target submission Sun 8 Nov 18:00** |

## 8. Risks

| ID | Risk | Mitigation / trigger |
|---|---|---|
| R1 | BlenderProc fails on this macOS version (known permission issue). This Mac runs **macOS 27.2**, newer than the 26.3 tested in PR #1231, so the risk is higher | Run M1 first; 1 h limit; grant terminal permission [S-10]; else Open3D fallback |
| R2 | Stereo simulation implausible | M3 gate → Route 2 |
| R3 | Render time / memory on 8 GB | Benchmark at M3; reduce resolution, then samples, then views, then scenes |
| R4 | Ceiling or floor effect in A1 or B | Pilot at M4; thresholds fixed in advance; offset sweep |
| R5 | Silent bugs (units, disparity scaling, symmetries) | Zero-offset sanity check (§5.11); plane test; unit tests in `tests/` |
| R6 | Report runs over time | Notes kept in DIARY.md continuously; skeleton early; code freeze |
| R7 | Reviewers can't run the code | Pinned environment, quick-run configuration, seeds, clear README |

## 9. Sources → [`SOURCES.md`](SOURCES.md)

Moved out on 2026-11-03. IDs `[S-xx]` are unchanged.

## 10–11. Report outline and reflection outline → [`REPORT_PLAN.md`](REPORT_PLAN.md)

Moved out on 2026-11-03.
