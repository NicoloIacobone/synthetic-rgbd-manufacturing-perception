# M5 open items

Everything uncertain, unexplained or left undone when M5 was closed. The user asked for these to be written down rather than stopping for each (2026-11-05), so that a reviewer can check them after the milestone. Nothing here was hidden from the results: where an item affects a number, it says which.

**Sections 1–4 are history: their numbers come from the archived 65° run.** The primary run is now at 71°: its numbers, and what it closes, are in section 5. Results of the 65° run are in `data/m5/results_v2/stats.json`, `sensor.json` and `data/m5/results_v2_s58/robustness.json`, all from commit 26cd449 with a clean tree. Item numbers are stable identifiers, not a ranking. No item needs a decision any more.

**Triage by the review of 2026-11-06.** Test: if the outcome were different, would the 8 pages change? **Can change a conclusion:** 10, 20, 21, 23. **One line or a small fix is enough:** 1, 2, 4, 18, 19, 22, 24, 25, 26, 30, 31, 32. **Ignore until submission:** 3, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 27, 28, 29, 33. Items 34–37 were added by the review.

## 1. Could affect reported numbers

| # | Item | Evidence | Effect |
|---|---|---|---|
| 1 | **The H3 pick rests on one instance-view.** H3 beat H2 on the dev rule only because C3 recall was 0.05 vs 0.025, 2 vs 1 of 40 views, in the condition known to flip on tiny changes (A-59). H2 and H3 are identical at zero offset on the test scenes | `data/m5_dev/selection_fix/selection.json` | The harness choice is close to arbitrary between H2 and H3. Whether it matters on test data is unknown: H2 was not run at real offsets on test scenes, on purpose |
| 2 | **Sample count chosen after looking at test scenes.** 200 000 CAD samples was chosen after seeing zero-offset drift on C1 on the test scenes, a departure from §5.2 and D10 | PLAN §5.12, 2026-11-05 row | Only C1 at zero offset was seen, so it cannot favour a condition. To be disclosed in the report |
| 3 | **Bracket drift grew with more samples, unexplained.** H1 worst bracket 0.323 → 0.404 mm, p99 0.207 → 0.340 mm, while the median halved. Two views: scene 7 view 1 instance 4, scene 20 view 0 instance 0 | `data/m5/diag_sanity_fix`, ledger "second round: result" | Margin to the 0.5 mm sanity threshold is 0.096 mm. It suggests "drift is about one sample spacing" is not a general bound, so the cause of cause 2 is only partly understood |
| 4 | **C3 can flip per view** on numerically tiny changes (A-59), and its level moves with the IR noise draw. Seeds 0–9, 98 instance-views: C3 recall 0.143, redraws 0.133 and 0.071; 9 and 13 views change side of the 5 mm threshold. Only the sensor noise is redrawn, not the render | `data/m5/results_v2_s58/robustness.json` | C3−C4 stays negative on all three draws (−0.214, −0.224, −0.286), but C3's level on 10 scenes moves by a factor of 2. No redraw exists on all 50 scenes, so the 0.085 carries noise-draw uncertainty that its scene-bootstrap CI does not include. Seeds 0–9 also run higher than the 50 scenes (0.143 vs 0.085), so they are not a proxy for the level |
| 5 | **One odd H2 run in the first round, cause not shown.** 1 of 7 identical plain runs gave 33 failures instead of 43, up to 119 mm different. The inference that the cache assignment differed was not checked, because that run was not instrumented | `data/m5/diag_sanity/H2_omp1.jsonl` | After the fix, one replay matched within 4e-13 mm. One replay cannot prove it never recurs, but the `id()` reuse behind the bug is gone |
| 6 | **The across-axis pair of the residual failures was not traced.** Scene 15 view 0 instance 0 and scene 15 view 1 instance 3 drifted 0.36–0.41 mm across the axis at about 0.1° rotation | `logs/report.log` in `data/m5/diag_sanity` | Both pass after the sample increase, without a stated mechanism |
| 18 | **Closed 2026-11-06: re-run with the check really off, no flip (A-63).** The first §5.8 run did not turn the left-right check off: `disp12_max_diff: -1` does nothing in OpenCV 5.0.0: on a synthetic pair −1 and 0 give output identical to 1, while 1000 changes 2 880 pixels. All 20 `C3nolr` depth frames on disk equal C3. So `C3nolr` = C3, and `C3loose` / `C4loose` have only uniqueness and speckle off. PLAN §5.8 and the ledger row "SGBM loose" name all three filters. Found while checking the results, not by a test | `scripts/stereo_scene.py` line 39–40; test re-runnable from `make_sgbm` | **No primary number changes:** strict uses 1, so the check is on as A-43 says. **Re-run (user's decision, commit c44cd7a, `data/m5/results_s58_v2`):** value 1000, new folders. C1−C3 +0.561, C2b−C3 +0.337, C3−C4 −0.214, no flip; C3 0.153, C4 0.367. For the report: one line in "what did not work" and PLAN §5.12 |
| 19 | **§5.8, first run (two filters off): no ranking flip.** The re-run with all three off also shows none (item 18): correct part pixels on C3 only rise 61.3 → 62.4%, invalid falls to 0.0%, MAE rises 6.57 → 21.61 mm, and recall barely moves, so the filters remove mostly wrong pixels and ICP tolerates them. First run: signs of C1−C3 (+0.571), C2b−C3 (+0.347), C3−C4 (−0.214) are unchanged and the values are equal to the strict ones. The equality is cancellation, not a wiring fault: every one of the 98 views has a different MSSD (C3 median 0.12 mm, max 50 mm), C3 gains 2 and loses 2 views at 5 mm, C4 gains 1 and loses 1. Filled pixels are mostly wrong: C3 invalid falls 5.3% → 2.8%, correct only rises 61.3% → 62.1%, part-pixel MAE rises 6.57 → 10.35 mm | `data/m5/results_v2_s58/robustness.json`, `sensor.json` | Supports A-10 for relative comparisons, weakly: 10 scenes and a descriptive rule |
| 20 | **C3's level depends on an assumed roughness.** A1 recall@5 mm 0.085 at 0.15, 0.159 at 0.2, 0.288 at 0.4. Roughness 0.15 is a modelling choice (A-53) and has no check against a real D415 yet | `stats.json`, `A1_descriptive_pairs` | The confirmatory test is C3 as defined, so it stands, but C3's absolute recall is not a prediction for real parts. ROBI (A-55) is the first external check |
| 21 | **Reflections hardly change recall.** C3 0.085 vs reflections off 0.102: −1.7 points [−4.3, +0.8], p 0.26, and correct part pixels 54% vs 59%. The A-57 fix switched reflections on | `stats.json`, `sensor.json` | Most of C3's loss at this roughness comes from something other than interreflection. Mechanism wording in the report must not credit reflections alone. Absence of a detected difference, not proof of none |
| 22 | **C2a vs C1 hides opposite effects by part type.** All parts: −1.7 points [−3.5, +0.2], p 0.17. Profiles: C2a higher, 0.754 vs 0.713, discordant 17 vs 3, p 0.003. Brackets: C1 higher, 0.786 vs 0.735, discordant 6 vs 0, p 0.03. The sign holds at nearly every offset. Cause of the profile gain not traced | `stats.json` sweep by type; p values computed for this note | Subgroup tests chosen after seeing data, uncorrected: exploratory only. "Noise averages out" (A-15) is true of the total, not within part types |
| 23 | **C1 recall of 0.73 is largely a harness limit.** Zero offset 459/459, 2 mm 1.00, 5 mm 0.92, 10 mm 0.73, 20 mm 0.67, on ideal depth. 14% of C1 views end worse than they started. Profile axial error is bimodal: median 0.28 mm but median centre error 1.24 mm, consistent with end-face pinning and axial sliding (§5.9) | `stats.json`, `A_C1_10.jsonl` | C1−C3 is not a pure sensor effect at a real offset. On C3, 44% of views end worse than they started (median MSSD 15.5 → 13.0 mm); median rotation error 11.9° exceeds the 10° start. The sweep figure shows this; the text must say it. The profile explanation is an inference. **Review 2026-11-06:** at 2 mm / 2° every start is already < 5 mm, and after ICP C1 is 1.00, C2b 0.76, C4 0.52, C3 0.135, with C3 ending worse than it started in 95% of views. So the ICP limit explains C1's fall, not C3's level, and C1−C3 grows to +86.5 points [81.2, 91.2]: the 10 mm endpoint understates the gap. The order holds for thresholds from 5 to 30 mm |
| 24 | **Task B on C3 mixes "no grasp" and "wrong grasp".** Bracket success 0.145, a grasp planned on 0.444 of views, success given a grasp 0.327 (C1 0.897, C2b 0.667, C4 0.500) | `stats.json`, `B_success` | Report both rates. Task B is not in the fixed sequence |
| 25 | **Noise creates grasps on profiles.** Profile success is 0 in every condition, by geometry (A-33). But the planner proposes a grasp on 0.9% of views in C1, 48% in C2a, 97% in C2b, 93% in C3, 97% in C4. Mechanism not traced; the rim-gap test in `plan_suction` is the place to look | `stats.json`, `B_success` | All-part Task B rates mix in a zero by construction: report brackets, plus this as a false-positive result |
| 26 | **Scene-level MDE (minimum detectable effect) is far above A-18's estimate.** A1: 10.8 / 9.7 / 7.8 points with instance-views as n, 32.8 / 29.3 / 23.7 with scenes as n, against the 10–15 expected. Task B brackets: 21.5 / 19.0 / 15.3 and 35.9 / 31.7 / 25.6. Computed from observed discordance, so not independent of the effects | `stats.json` | All three confirmatory differences (+64.7, +50.5, −30.1) exceed both. Small effects cannot be claimed, such as C3 vs reflections off. **Review 2026-11-06:** n = scenes is a worst case; the bootstrap CI half-widths imply about 9 / 11 / 8 points (an inference: 2.8 × half-width / 1.96) |
| 27 | **Bootstrap CIs depend on what else is computed.** All tables share one stream, so adding the sweep moved C1−C3 from [0.579, 0.707] to [0.583, 0.708]; the second stream gives [0.582, 0.709] | `stats.json`, `ci_stability_second_stream` | Third decimal only (A-31). Quote the final `stats.json` |
| 28 | **Tray means are inflated by pixels past the tray.** 12 of 100 views have pixels with ideal depth > 2 m, reaching the 16-bit ceiling of 6553.5 mm. C2a tray MAE 5.56 mm vs median 0.7 mm; its error on pixels under 2 m is at most 14.6 mm | `sensor.json`, tray region (`scripts/sensor_metrics.py`) | Do not quote tray MAE; use medians or mask these pixels. Part regions, Task A and Task B use part masks and are not affected |
| 29 | **No-estimate counts at A1:** C1 1, C2a 4, C3r02 1, not traced | `stats.json`, `A1_secondary` | Counted as failures (§5.12). Too few to change a conclusion |

## 2. Not run

| # | Item | Why it matters |
|---|---|---|
| 7 | Cache fix at 50 000 samples | H2's gain from 416 to 459 mixes both changes; only H1's gain from 452 to 459 is attributable to the sample count alone |
| 8 | Dev pilot (`data/m5_dev/pilot`) not re-run after the fix | Stale, including its descriptive passes. `data/m5_dev/selection_fix` has the current dev numbers for the five protocol conditions |
| 9 | Descriptive passes at offsets other than 10 mm / 10° | Skipped to save about 1 h of machine time (ledger "M5 run scope"): no figure uses them |
| 10 | ROBI comparison (A-55) | A-55 places it after M5, so it is not part of closing M5. Still required for the report; time box 3 h |
| 30 | §5.8 with the left-right check really off | **Done 2026-11-06,** see item 18 |
| 31 | C4 noise redraws, and C3 redraws beyond seeds 0–9 | The ledger's redraws cover C3 on seeds 0–9 only, see item 4 |

## 3. Documentation and code to check

| # | Item |
|---|---|
| 11 | Ledger rows left stale on purpose, because they were not on the user's list: "Metal roughness" (10-scene subset, widened by A-51), "C4 part albedo" and "Exposure setpoint" (rule rows from before A-57), "Grasp point (done)" (covered by a later row, same pick) |
| 12 | Assumptions still marked open from M4: A-43, A-44, A-46. A-44 and A-46 have been decided by the ledger; their status column was not updated |
| 13 | PLAN §5.6 names two comparisons while §5.12 sets three in a fixed sequence. §5.6 is frozen; the §5.12 row is the record (user, 2026-11-05) |
| 14 | `solver: lm` remains in `pose.py` with no tests and is not used by any selected harness |
| 15 | Commit 52764a3 lists an AI-log "entry 12" it does not contain; added as entry 8 in 04faf51. History not rewritten |
| 16 | `scripts/sanity_diagnosis.py` documents a diagnosis made at commit 1887f8e. Its `static` and `report` steps rely on files from that state, so re-running them after the fix gives different numbers |
| 17 | Earlier open items carried over from STATUS: Cycles roughness → α = roughness² unverified (S-16 caveat); about a fifth of the dark-face pixels stay behind the surface under both cuts (A-58) |
| 32 | `data/m5/figures/results.png`: the titles of panels (a) and (b) run together. Panel (a) prints C3 as 0.08, correct rounding of 39/459 = 0.085 but different from the text's 0.085. Fix when the figure goes into the report at M6 |
| 33 | **Closed 2026-11-06.** No test covered the variant settings, which is why item 18 went unseen. `tests/test_stereo.py` now pins the OpenCV behaviour and the variants |

## 4. Added by the review of 2026-11-06

| # | Item | Evidence | Effect |
|---|---|---|---|
| 34 | **Distance is a strong moderator, not yet reported.** A1 recall@5 mm by part distance, < 0.7 m (47 views) and ≥ 0.9 m (142 views): C1 0.62 and 0.77, C4 0.68 and 0.24, C3 0.32 and 0.00. 5 mm is 0.34 px at 0.9 m and 2.15 px at ROBI's 0.34 m | `A_*_10.jsonl`, `scene_gt.json` | One panel in the results figure |
| 35 | **The simulated IR differs from real IR.** Part pixels, median DN and median 7 × 7 local SD: real ROBI Zigzag 21 and 4.6; C3 1.9 and 23; roughness 0.4 16.8 and 69 (seeds 0–9). Zero ambient (A-03) is not tested | `data/m5/robi/zigzag.json`, `scripts/ir_appearance.py` | Limitation, and evidence for the reflection |
| 36 | **ROBI must be read in pixels, not at 5 mm.** Disparity error p5 / p25 / p50: real D415 −2.07 / −0.71 / −0.19 px, C3 −2.44 / −0.72 / −0.23 px, roughness 0.4 −0.80 / −0.22 / −0.02 px. Invalid 21% vs 5%. "71% vs 54% correct" compares different tolerances in px. ROBI's ground-truth error is unknown | `data/m5/robi/zigzag.json`, `sensor.json` | Compatible, not a validation. Framing fixed in A-65 |
| 37 | **A third of the IR noise does not move C3.** C3 0.143 → 0.143, C4 0.357 → 0.408; the noise level, calibrated on the plane anchor, was therefore not what set C3's level at this value | A-64, `data/m5/results_s58_v2` | One line in the limitations. Anchor (a) cannot validate the noise level, since it calibrates it |

## 5. New numbers from the final run at 71° (2026-11-07)

Commit 7eca5f0, clean tree, 460 instance-views, `results/hfov71/`. The items keep their numbers; the text above stays as history. **Closed by this run:** 4 and 31 for C3, 10, 30, 32, 34.

| # | Item | New numbers |
|---|---|---|
| 2 | Sample count and earlier results seen | Disclosed as before. In addition the earlier **recall** results had been seen before this run was defined (A-66) |
| 4, 31 | **Closed for C3: noise redraws on all 50 scenes** | C3 0.070, redraws 0.061 and 0.063: spread 0.9 points, 24 and 21 of 460 views change side. C3−C4 −27.4, −28.3, −28.0 points. The primary draw is the highest of the three. C4 redraws were not run |
| 10 | **Closed: ROBI comparison done,** Zigzag only | `results/figures/robi.png`, A-55 |
| 19, 18, 30 | §5.8, seeds 0–9, all three filters off | C3 0.102 → 0.112, C4 0.265 → 0.245, no sign change. C3 correct part pixels 62.2 → 63.0%, invalid 2.7 → 0.0%, MAE 6.75 → 13.92 mm |
| 20 | C3 depends on the assumed roughness | 0.070 at 0.15, 0.139 at 0.2, 0.276 at 0.4 |
| 21 | Reflections hardly change recall | C3 0.070, reflections off 0.076: −0.7 points [−2.7, +1.5], p 0.68. Correct part pixels 55% and 60%. A-58 has the mechanism re-run; note the collapse of the "no texture" share |
| 22 | C2a vs C1 by part type | All parts −1.7 points [−4.1, +0.7], p 0.18. Profiles C2a higher, 0.737 and 0.696; brackets C1 higher, 0.780 and 0.729: same signs as at 65° |
| 23 | C1 largely a harness limit | Zero offset 460/460, 2 mm 1.00, 5 mm 0.90, 10 mm 0.717, 20 mm 0.633 |
| 24 | Task B on C3 | Bracket success 0.110, grasp planned on 0.441 of views, success given a grasp 0.250 (C1 0.901, C2b 0.656, C4 0.570) |
| 25 | Noise creates grasps on profiles | Grasp proposed on 0.3% of profile views in C1, 45.6% C2a, 97.1% C2b, 93.9% C3, 97.7% C4; success still 0 |
| 26 | MDE (minimum detectable effect) | A1: 11.0 / 9.7 / 7.3 points with instance-views as n, 33.2 / 29.3 / 22.2 with scenes as n. Task B brackets: 21.2 / 17.8 / 14.2 and 35.6 / 29.8 / 23.9 |
| 29 | No-estimate counts at A1 | C1 2, C2a 6, C3nogloss 1, others 0 |
| 32 | **Closed:** results figure | Titles apart, three decimals, labels read from the config. `results/figures/results.png` |
| 34 | **Closed:** distance panel in the results figure | A1 recall by part distance, < 0.7 m (46 views), 0.7–0.9 m (273), ≥ 0.9 m (141): C1 0.630, 0.714, 0.752; C2b 0.609, 0.586, 0.496; C4 0.565, 0.388, 0.184; C3 0.217, 0.070, 0.021. `results/hfov71/distance.json` |
| 35 | Simulated IR against real IR | Part pixels, median DN and median 7 × 7 local SD: real ROBI Zigzag 21 and 4.6; C3 5.05 and 22.5 (1.9 and 23 at 65°); C4 3.95 and 22.8; roughness 0.4 29.8 and 69. Zero ambient is now tested once (A-70): 22.05 and 17.2, so the mean can be matched but the local contrast not |
| 36 | ROBI in pixels | Disparity error p5 / p25 / p50: real −2.07 / −0.71 / −0.19 px; C3 −2.24 / −0.68 / −0.23 px; roughness 0.4 −0.98 / −0.22 / −0.04 px. Invalid 21% against 2.3% |
| 37 | Noise sensitivity | A smaller step than at 65°, since `e_per_dn` is now 0.42: C3 0.102 → 0.102, C4 0.265 → 0.286 (A-64) |

**New at 71°, for the report.**
- `e_per_dn` went from 0.087 to 0.42 on the same plane rule, because the no-noise plane floor rose from 0.053 to 0.0749 px (pixel locking), leaving less room for noise under the 0.09 px target. σ at 21 DN falls from 15.6 to 7.1 DN. A reader comparing the two runs needs this.
- Unlit part pixels: 0.064% (1 077 of 1 674 189), on 2 instance-views: a bracket in scene 19 view 1 at 85%, a profile in scene 35 at 1.6%. Unlit image share 13.6%. `results/hfov71/unlit_share.json`.
- ICP is not strictly repeatable on identical depth (A-72). Its effect on the recall of the test scenes is not measured; one repeat has been proposed and not run.
