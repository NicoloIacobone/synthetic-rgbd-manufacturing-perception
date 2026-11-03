# Project plan

Synthetic RGB-D of aluminium profiles and brackets with a RealSense D415 camera model, and the effect on downstream pose estimation and suction grasping.

Authoritative requirements are in [`task_description.md`](../task_description.md). This file records **decisions and how they will be evaluated**. Assumptions live in [`ASSUMPTIONS.md`](ASSUMPTIONS.md) (IDs `A-xx`, `H-x`), and sources in §9 (IDs `[S-xx]`).

- **Status:** Phase 0 (planning) is complete as of 2026-11-03. No code yet.
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
| D8 | **Resolution and placement:** 1280×720; camera 0.65–0.95 m above the table; tilt ≤ 30°. Fallback: 848×480 if the day-1 render benchmark is too slow | 1280×720 is Intel's recommended D415 resolution and matches ROBI. Datasheet Min-Z = 450 mm at 1280×720 (A-16) | [S-01][S-03][S-05] ✅ |
| D9 | **Experiment design:** as in §5, after an adversarial review. All review changes accepted; suggestions to use forum images and the MP6D dataset rejected | Avoids C2 being trivially null by construction, A1 sitting at its ceiling, and pseudo-replication | [S-04] |

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
2. **Scenes:** a tray or table in a cell; 3–6 parts per scene placed with physics drop; ~50 scenes × 2 views, scaled to measured render time.
3. **Renders per frame:**
   - RGB + ideal depth + instance masks (BOP writer);
   - left/right IR with projected pattern, metal materials;
   - left/right IR, matte materials with matched brightness.
4. **IR post-processing:** add sensor noise and blur, then run SGBM tuned to D415 geometry (baseline 55 mm; disparity search 126 px, implemented as `num_disparities=128` plus masking of d > 126, A-25). The BlenderProc defaults for WLS filtering and depth completion are **off** [S-11]. Convert disparity to depth, taking care of units, z-depth vs ray distance, and OpenCV's ×16 disparity scaling.
5. **Datasheet noise layer for C2**, at two levels: the formula level and the Carfagni-matched level.

## 5. Experiment protocol (pre-specified)

### 5.1 Conditions
These are paired: same scenes, same poses.

| ID | Depth input | Role |
|---|---|---|
| C1 | Ideal rendered depth | Upper bound; also a sanity check (A1 on C1 must give ≈0 error) |
| C2a / C2b | Ideal depth + Gaussian noise, σ = z²·ε_d/(f·B) [S-02] with ε_d = 0.08 px [S-03] (C2a), and a level matched to Carfagni (C2b) [S-04] | **Naive baseline, not the camera model** |
| C3 | Stereo simulation, metal materials | **The camera model (headline)** |
| C4 | Stereo simulation, matte materials, brightness matched | Isolates the material effect (C3 vs C4) |

### 5.2 Task A: pose estimation
- Inputs: ground-truth instance mask → masked depth points → point-to-plane ICP against the CAD model.
- **A1 (primary):** start from the ground-truth pose with a 10 mm / 10° offset. Sweep the offset over 2/5/10/20 mm as a secondary result.
- **A2 (optional):** global registration (FPFH + RANSAC) followed by ICP.
- Hyperparameters are fixed once on a small dev split and are identical across conditions.

### 5.3 Task B: suction
- On the masked points, estimate normals and choose the flattest point that fits a cup of 10 mm radius.
- **Success** is checked against the ground-truth mesh. All three must hold:
  - the point is within 2 mm of the surface;
  - the normal error is under 15°;
  - the ground-truth surface within the cup disk is planar (the cup is not over a slot or edge).
- The planarity tolerance is fixed **before** running (A-19).

### 5.4 Metrics
- **A:** MSSD (symmetry-aware). Primary: recall at **absolute 5 mm**. Secondary: recall at 2 mm, translation and rotation error, error along the profile axis vs across it.
- **B:** success rate.
- **Sensor (cause → effect):** depth MAE vs ground truth, % invalid pixels, % of pixels with error > 5 mm. Each is split edge vs interior and metal vs matte.

### 5.5 Statistics
- Bootstrap over **scenes** (not instances), 95% CIs on paired differences in success rate.
- McNemar's test for paired success/failure outcomes.
- State the detectable effect size: roughly 10–15 percentage points with ~50 scenes (A-18, to be computed).
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
| M3 Stereo route | IR pair + projector + SGBM; plane anchor; render benchmark per frame | **Wed 4 Nov end of day** → Route 2 if implausible; 848×480 if too slow |
| M4 Camera model done | Metal/matte, IR noise and blur, SGBM tuning, 5-scene pilot (ceiling/floor check; document any design change) | — |
| M5 Experiment | Full renders, A1 + B, sensor metrics, statistics, invalidation check | **A metrics by Fri 6 Nov end of day** → otherwise freeze B |
| M6 Report | Skeleton → figures → text → reflection → AI note; README | **Code freeze Sat 7 Nov 20:00. Target submission Sun 8 Nov 18:00** |

## 8. Risks

| ID | Risk | Mitigation / trigger |
|---|---|---|
| R1 | BlenderProc fails on this macOS version (known permission issue) | 1 h limit; grant terminal permission [S-10]; else Open3D fallback |
| R2 | Stereo simulation implausible | M3 gate → Route 2 |
| R3 | Render time / memory on 8 GB | Benchmark at M3; reduce resolution, then samples, then views, then scenes |
| R4 | Ceiling or floor effect in A1 or B | Pilot at M4; thresholds fixed in advance; offset sweep |
| R5 | Silent bugs (units, disparity scaling, symmetries) | Sanity check: A1 on C1 ≈ 0 error; plane test; unit checks |
| R6 | Report runs over time | Notes kept in DIARY.md continuously; skeleton early; code freeze |
| R7 | Reviewers can't run the code | Pinned environment, quick-run configuration, seeds, clear README |

## 9. Sources

Status legend:
- ✅ = the lead agent read the primary source and confirmed the specific claim.
- 🔶 = reported by a subagent or a search summary; **verify before citing in the report**.
- ⚠️ = partially verified; the caveat is stated.

| ID | Source | Claims used | Status |
|---|---|---|---|
All entries below were checked by the lead agent on 2026-11-03 against the primary source (datasheet, paper and PDF text extracted locally; official pages fetched). The verification notes record corrections to earlier claims.

| ID | Source | Verified claims | Status and notes |
|---|---|---|---|
| S-01 | Intel RealSense D400 Series Datasheet, Rev 013, April 2022 (doc 337029-013), third-party copy: https://docs.clearpathrobotics.com/assets/files/clearpath_robotics_017103-TDS2-80efb31ac3e573ef412db1cbfe285e63.pdf | D415 baseline 55 mm and depth FOV H65°/V40° (HD) (Table 3-11); D41x projector 850 nm ± 10 nm, static pattern, VCSEL (Table 3-16); **Min-Z D415: 450 mm @1280×720, 310 mm @848×480** (Table 4-11); invalid left band = B·F/Z px (§4.5); spec (≤2 m, 80% ROI, HD, 150 mW, auto exposure): Z-accuracy ±2%, fill ≥99%, RMS (spatial noise vs best-fit plane) ≤2%, temporal ≤1% (Tables 4-12, 4-14) | ✅. **Correction:** "specular reflections may cause image saturation" (Table 3-49) is a *D435 vs D435f* comparison, not a D415 statement. Do not cite it for the D415 |
| S-02 | Keselman, Woodfill, Grunnet-Jepsen, Bhowmik, "Intel RealSense Stereoscopic Depth Cameras", CVPR 2017 Workshops (CCD), https://arxiv.org/abs/1705.05548 | Eq. 1 z = f·B/d; eq. 2 ε_z = z²·ε_d/(f·B); ε_d "≈ 0.1" treated as constant | ✅. **Correction:** the 0.08 px disparity RMS in this paper is measured on the **R200**, not the D400. Cite it for the formula only |
| S-03 | Intel/RealSense, "Tuning depth cameras for best performance", https://dev.realsenseai.com/docs/tuning-depth-cameras-for-best-performance | Theoretical RMS curve uses subpixel 0.08 (well-textured targets < 0.1, approaching 0.05); RMS measured as a plane fit; **recommended resolution D415 = 1280×720**; invalid pixels have depth = 0; poor exposure is the main cause of bad depth; glossy surfaces worse than matte textured ones; laser power 150 mW nominal | ✅ (the formula itself appears only as an image on the page). The BKMs PDF suggested by the reviewer was not checked and is not used |
| S-04 | Carfagni et al., "Metrological and Critical Characterization of the Intel D415 Stereo Depth Camera", *Sensors* 19(3):489, 2019, https://pmc.ncbi.nlm.nih.gov/articles/PMC6387018/ (PDF: https://flore.unifi.it/retrieve/e398c381-ea32-179a-e053-3705fe0a4cff/sensors-19-00489-v2.pdf) | §3.3: whole-scan deviation from a certified ground-truth plane (labelled "systematic non-planarity errors"): mean 0.004 mm / SD 0.345 mm @200 mm, mean 0.237 mm / SD 4.74 mm @1 m; max 1.6 → 26.5 mm; "noise tends to be distributed locally"; lens non-linearity noted; near-zero depth offset; Default preset; Eq. 3 MinZ = f·B/(shift+126); no fitted noise model; no reflective targets | ✅. Note: the paper states "maximum IR camera resolution (1920 × 1080)" while its own spec table gives depth up to 1280×720, an internal inconsistency |
| S-05 | Yang, Gao, Li, Waslander, "ROBI: A Multi-View Dataset for Reflective Objects in Robotic Bin-Picking", IROS 2021, https://arxiv.org/abs/2105.04112 (full text https://ar5iv.labs.arxiv.org/html/2105.04112); project page https://www.trailab.utias.utoronto.ca/robi | D415 at 1280×720 + Ensenso N35; 7 metallic parts; 63 scenes; GT 6D poses; GT depth from the Ensenso with anti-reflective spray; RealSense depth "higher level of completeness" but "significant degradation of depth accuracy (e.g., loss of geometric details)"; license CC BY-NC-SA 4.0; downloads via Google Drive + ROBI_Toolkit | ✅ (download size unknown) |
| S-06 | Ahn, Chae, Noh, Nam, Hong, "Analysis and Noise Modeling of the Intel RealSense D435 for Mobile Robots", 16th Int. Conf. on Ubiquitous Robots (UR) 2019, https://ucla.box.com/shared/static/gqxwr2vvqsf22oi9dqtn50hr0xkruzie.pdf | Gaussian axial and lateral noise model vs distance and incidence angle for the D435 | ⚠️ Existence and scope verified. **Coefficients unverified** (PDF behind a Box redirect; constants not found elsewhere). Not used; do not cite numbers |
| S-07 | Hodaň et al., "BOP Challenge 2020 on 6D Object Localization", ECCVW 2020, https://arxiv.org/abs/2009.07378 | MSSD eq. 2: e = min over symmetries S of max over vertices x of ‖P̂x − P̄Sx‖₂; "MSSD is relevant for robotic grasping"; symmetries are those with Hausdorff distance < max(15 mm, 0.1·diameter); AR_MSSD averages recall over thresholds of 5–50% of diameter | ✅ (PDF text extracted) |
| S-08 | RealSense spin-out (Intel Capital, 11 July 2025): https://www.intelcapital.com/realsense-completes-spin-out-from-intel-raises-50-million-to-accelerate-ai-powered-vision-for-robotics-and-biometrics/ ; products page https://realsenseai.com/products/ | Spin-out completed; will "continue to support its existing customer base and product roadmap"; D415 listed as a current product (65°×40°, rolling shutter, ideal range 0.4–3 m) | ✅. The product page shows no stock, price or EOL information, so claim only "listed as a current product" |
| S-09 | Zhang et al., "Close the Optical Sensing Domain Gap by Physics-Grounded Active Stereo Sensor Simulation", arXiv 2201.11924 (v4, Jan 2023; listed as to appear in IEEE T-RO) | Physics-grounded active-stereo simulation: material acquisition, ray-traced IR rendering, IR noise simulation, depth estimation | ✅ (abstract). The DOI and the specific sensor model simulated were not verified |
| S-10 | BlenderProc: PyPI https://pypi.org/project/blenderproc/ ; issue #768 https://github.com/DLR-RM/BlenderProc/issues/768 ; PR #1231 https://github.com/DLR-RM/BlenderProc/pull/1231 ; issue #1070 https://github.com/DLR-RM/BlenderProc/issues/1070 | v2.8.0 latest (PyPI dates inconsistent); BOP annotation writer; #768 (open): "Operation not permitted" inside Blender.app on macOS, workaround = allow the terminal to perform updates in macOS settings; PR #1231 (open, unmerged): fixes this on macOS 26.3 / M4 Pro / Blender 4.2.1; #1070 (open): M2 Pro quickstart error with BlenderProc 2.7.0 / Blender 3.5.1, not reproduced by the maintainer | ✅. No official macOS support statement found; Apple Silicon use is evidenced only by these issues |
| S-11 | BlenderProc stereo matching source https://raw.githubusercontent.com/DLR-RM/BlenderProc/main/blenderproc/python/postprocessing/StereoGlobalMatching.py ; projector example https://dlr-rm.github.io/BlenderProc/examples/advanced/stereo_matching_with_projector/README.html | `stereo_global_matching(color_images, depth_max, window_size=7, num_disparities=32, min_disparity=0, disparity_filter=True, depth_completion=True)` → (depths, disparities); CPU `cv2.StereoSGBM_create` (MODE_HH) + optional `ximgproc` WLS filter; **num_disparities must be divisible by 16**. Projector = SPOT light with `setup_as_projector(fov, ratio, pattern_img)` and a random dot pattern; stereo via `set_stereo_parameters(interocular_distance, convergence_mode="PARALLEL")` | ✅. Defaults (WLS filter, depth completion) would hide artifacts and must be disabled for our use. The example needs SUNCG, so we adapt rather than run it |
| S-12 | Open3D ray casting tutorial https://www.open3d.org/docs/latest/tutorial/geometry/ray_casting.html | `RaycastingScene.cast_rays` → t_hit, geometry_ids, primitive_ids, primitive_uvs, primitive_normals; `create_rays_pinhole` helper | ✅. t_hit is distance along the ray, not z-depth (convert if used) |

Not used, and not verified: the camera alternatives from the research subagent (Orbbec Femto Bolt, Gemini 335, Zivid 2+). Verify them if the report's camera-choice section compares against them.

## 10. Report outline (≤ 8 pages total)

| § | Content | Pages |
|---|---|---|
| 1 | Problem, scope, non-goals | 0.5 |
| 2 | Reference camera: why the D415 | 0.5 |
| 3 | Synthetic data pipeline | 1.0 |
| 4 | Camera model: active stereo simulation, included/excluded table, anchor (a) | 1.5 |
| 5 | Experiment design and pre-specified endpoint | 0.75 |
| 6 | Results, incl. what did not work | 1.5 |
| 7 | Limitations | 0.5 |
| 8 | Synthetic-to-real reflection (≤ 1 page) | 1.0 |
| 9 | AI-use note | 0.25 |
| — | References | ~0.5 |

## 11. Reflection outline (tentative until results)

**Riskiest assumption candidates**
- **(a) Preferred:** the simulated sensor reproduces how the real sensor errs on reflective metal. Links to the C3 vs C4 result; ROBI suggests the real D415 smooths metal rather than leaving holes [S-05].
- **(b)** Randomised appearance in simulation covers real factory surfaces.
- **(c)** Pose error in simulation predicts real pick or assembly success.

**Six-month plan for (a)**
1. **Months 1–2:** collect a small real calibration set with the target camera on real parts; ground-truth depth from spray-coated scanning (ROBI protocol).
2. **Months 2–3:** measure the simulation-to-reality gap effect by effect.
3. **Months 3–4:** fit the sensor-model parameters or learn a residual correction; randomise what remains unmodelled.
4. **Months 5–6:** closed-loop pick and assembly validation, with success criteria and go/no-go thresholds fixed in advance.
