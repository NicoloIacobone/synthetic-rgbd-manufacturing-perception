# Assumptions and hypotheses register

Every scoping, modelling or evaluation choice that is not a direct fact belongs here. Add a row when a new assumption is made, and update **Status** when it is tested.

**Columns**
- **Type:**
  - `doc` = a documented fact (with a source from PLAN.md §9);
  - `inf` = our inference;
  - `asm` = an unverified assumption or design choice;
  - `usr` = provided or decided by the user.
- **Test / justification:** how the item is checked, or why it is accepted without a check.
- **Status:** `open`, `tested-ok`, `tested-failed`, or `accepted` (a scoping choice, not tested).
- **Report:** the report section where it is discussed.

## Assumptions

| ID | Statement | Type | Source | Test / justification | Status | Report |
|---|---|---|---|---|---|---|
| A-01 | The reflection and AI note count toward the 8-page limit | usr | task_description.md is silent | Conservative reading | accepted | all |
| A-02 | Deadline is Sun 2026-11-08 23:59 CET | usr | User (not in task_description.md) | — | accepted | — |
| A-03 | Indoor cell: no sunlight or ambient-IR interference; constant temperature | asm | — | Scoping; listed as an excluded effect | accepted | §4, §7 |
| A-04 | Static scene at capture time, so motion blur and rolling shutter are irrelevant | asm | — | Scoping | accepted | §4 |
| A-05 | Procedural T-slot-like profiles and L-brackets are representative of the target parts | asm | Our scoping choice, not a researched convention | Discussed as a limitation | accepted | §3, §7 |
| A-06 | CAD models of the parts are known to the robot | inf | Typical for manufacturing (not sourced) | Scoping | accepted | §1 |
| A-07 | Detection/segmentation is solved (ground-truth instance masks given) | asm | Design choice to isolate the effect of depth quality | Limitation: real masks would also degrade at edges | accepted | §5, §7 |
| A-08 | Raw depth is modelled; Intel post-processing filters are not | asm | — | Scoping | accepted | §4 |
| A-09 | Per-unit calibration bias and lens non-linearity are calibrated out | asm | — | Scoping | accepted | §4 |
| A-10 | OpenCV SGBM tuned to D415 geometry approximates the D415 matcher well enough for **relative** comparisons | asm | [S-11] | Strict/loose invalidation sensitivity check (PLAN §5.8) | open | §4, §6 |
| A-11 | Cycles rendering of PBR metal (visible-light material parameters) approximates aluminium's appearance under the D415's 850 nm projector | asm | Wavelength is 850 nm ± 10 nm [S-01] ✅; IR reflectance of aluminium not sourced | Qualitative check against ROBI images (optional (b)) | open | §4, §7 |
| A-12 | Parameters of IR image noise and blur are plausible (values to be chosen) | asm | — | Tuned so the plane anchor matches the formula / Carfagni | open | §4 |
| A-13 | Disparity error ε_d = 0.08 px for D4xx on well-textured targets | doc | [S-03] ✅ (Intel tuning guide). [S-02] gives only the formula; its 0.08 px is for the R200 | Anchor (a) checks our pipeline against it | accepted | §4 |
| A-14 | Carfagni's plane SD (whole-scan deviation from a ground-truth plane, incl. systematic non-planarity and lens non-linearity) is an upper bound on per-pixel random noise | inf | [S-04] §3.3 ✅ | Used only as the upper level of the C2 sensitivity band (C2b) | accepted | §4 |
| A-15 | ICP averages out independent per-pixel noise, so we expect C1 ≈ C2 | inf | — | Measured directly (C1 vs C2) | open | §6 |
| A-16 | D415 Min-Z = 450 mm at 1280×720 (310 mm at 848×480), so the camera at 0.65–0.95 m keeps all parts above Min-Z | doc | [S-01] Table 4-11 ✅ (own estimate f·B/126 ≈ 440 mm agrees) | Check per frame that the nearest part depth > 0.45 m | accepted | §3 |
| A-17 | Instances within one scene are correlated, so scenes are the independent unit | inf | Reviewer judgement | Bootstrap over scenes | accepted | §5 |
| A-18 | About 50 scenes can detect differences of ~10–15 percentage points | inf | Reviewer judgement | Compute properly once pilot data exist | open | §5 |
| A-19 | Suction parameters: 10 mm cup radius, 15° normal tolerance, 2 mm on-surface, planarity tolerance TBD | asm | Design parameters | Fixed before the full run | open | §5 |
| A-20 | Symmetries: square profile = 4-fold about its axis × 2-fold end flip (assumes a symmetric cross-section and slots); equal-leg L-bracket = 2-fold | inf | Geometry of our procedural meshes | Unit test on symmetric poses (MSSD ≈ 0) | open | §5 |
| A-21 | 5 mm absolute pose error is a meaningful assembly-oriented threshold | asm | No source | 2 mm also reported; sweep shown | open | §5, §7 |
| A-22 | Multipath/interreflection is not modelled on purpose (some may emerge from path tracing) | asm | — | Listed as excluded/partial | accepted | §4 |
| A-23 | BlenderProc 2.8 runs on this macOS version on M2 | asm | [S-10] ✅ (issues only; no official macOS support statement) | M1 milestone | open | — |
| A-25 | OpenCV SGBM needs num_disparities divisible by 16, so the D415's 126 px search range is emulated with 128 plus masking of d > 126 | inf | [S-11] ✅ (divisible-by-16 constraint); 126 from [S-04] Eq. 3 | Check that Min-Z in the simulation ≈ 450 mm on the plane test | open | §4 |
| A-24 | Brightness matching between metal (C3) and matte (C4) isolates reflectance as the only change | asm | Reviewer recommendation | Compare mean IR intensity of the two conditions | open | §5 |

## Hypotheses

| ID | Statement | Test | Status |
|---|---|---|---|
| H-1 | A1 recall (MSSD < 5 mm): C1 ≥ C2 > C3 | Paired, scene bootstrap CI + McNemar | open |
| H-2 | A1 recall differs between C3 (metal) and C4 (matte) | Paired, scene bootstrap CI + McNemar | open |
