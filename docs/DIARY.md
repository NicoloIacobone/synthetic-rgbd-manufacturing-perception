# Project diary (append-only)

This is a working log of what was done, measured, decided, and what failed. It feeds the report, especially "what did not work".

**Rules**
- **Append only.** Agents do **not** read this file unless the user asks, or during report writing.
- **How to append:** use the shell, e.g. `cat >> docs/DIARY.md <<'EOF' ... EOF`, so the file is never loaded into context.
- **Entry format:**

```
## YYYY-MM-DD HH:MM — <milestone/topic>
- Done: ...
- Numbers: ... (with units, seeds, commit hash if any)
- Decided: ... (link PLAN D-x / ASSUMPTIONS A-xx if changed)
- Failed / surprised: ...
- Report note: ... (what to say in which section)
```

---

## 2026-11-03 ~11:30 — Phase 0 (planning) complete

**Done**
- Read-only repo inspection.
- Research: two subagents (camera documentation; renderer feasibility on M2) and one adversarial review of the experiment design.
- The lead agent verified the key sources itself: ROBI, Carfagni, Ahn (existence only).

**Decided** (PLAN §2, D1–D9)
- Tasks: A (pose estimation) as primary, B (suction) in parallel.
- Toolchain: BlenderProc.
- Camera: D415, with a hybrid camera model (active stereo + datasheet-noise baseline).
- Conditions: C1–C4. Primary endpoint: MSSD < 5 mm recall in A1, comparing C1 vs C3 and C3 vs C4.

**Numbers**
- D415 plane SD: 0.345 mm @0.2 m → 4.74 mm @1 m (Carfagni, measured), vs ~1.5 mm @1 m from the stereo formula at 1280 px.
- z_min ≈ 440 mm at 1280×720 (own calculation).

**Failed / surprised**
- The Ahn et al. coefficients could not be verified (Box PDF redirect).
- My first error figure underestimated the measured error by ~3×.
- ROBI shows the real D415 *smooths* metal rather than leaving holes, which changes what the camera model must reproduce.

**Report note**
- §2: camera rationale (ROBI + Carfagni).
- §4: Carfagni SD vs formula, and what each one measures.
- §9: AI-use example #2.

## 2026-11-03 ~12:15 — Source verification before first commit (user request)
- Done: every 🔶 source in PLAN §9 checked against primary text. Datasheet, Carfagni, Keselman and BOP PDFs were text-extracted locally with pdftotext; official pages fetched.
- Numbers: D415 Min-Z = 450 mm @1280×720 and 310 mm @848×480 (datasheet Table 4-11); projector 850 nm; spec RMS ≤ 2% at ≤ 2 m, 80% ROI.
- Failed / surprised:
  - Keselman's 0.08 px is for the R200; the D4xx value 0.08 comes from Intel's tuning guide.
  - The "specular saturation" datasheet row is D435 vs D435f, not D415.
  - Ahn's coefficients are still unverifiable, so they are not used.
  - SGBM needs num_disparities divisible by 16, so 126 px is emulated as 128 plus masking (A-25).
  - BlenderProc defaults (WLS filter, depth completion) would hide artifacts, so they must be off.
- Report note:
  - §4 cite Keselman for the formula only, tuning guide for ε_d.
  - §9 AI note: verification caught misattributions (AI_USE_LOG A#4).

## 2026-11-03 — Pre-Phase-1 setup and protocol freeze
- Done: protocol frozen at tag `protocol-v1` (commit 4f52c67), before any data. User decisions: D10 dev split = 5-scene pilot (seeds 1000–1004; test 0–49), D11 suction planarity 1.0 mm, D12 zero-offset C1 sanity check (≥99% at MSSD < 0.5 mm).
- Agent-chosen, awaiting confirmation: A-30 offset sweep moves mm and degrees together (2/2, 5/5, 10/10, 20/20).
- Env: `.venv` Python 3.11.6, OpenCV 5.0.0.93, Open3D 0.20.0, numpy 2.4.6 (commit 69acb7d). 13 unit tests pass.
- Surprise: pip resolved OpenCV **5.0**, not 4.x. Checked that StereoSGBM still returns int16 ×16 (a 10 px shift reads as 10.0 px). Also, fx from the 65° HFOV gives an implied VFOV of 39.4°, not the 40° in the datasheet (A-28).
- Context: PLAN §9 sources moved to SOURCES.md, §10–11 to REPORT_PLAN.md; PLAN 21.9 KB → 16.2 KB despite the new §5.10–5.12. Older diary entries citing "PLAN §9" now mean SOURCES.md.
- Report notes: §5 can state "endpoint, thresholds and dev/test split pre-registered at tag protocol-v1"; D12 rationale (geometry failures vs bugs) is a good judgement example.

## 2026-11-03 — A-30 confirmed; BlenderProc SGBM source read
- A-30 (offset sweep moves mm and degrees together) confirmed by the user; re-check when the sweep is implemented at M5 (noted in ASSUMPTIONS, PLAN §5.2, config, STATUS). No protocol change, so no deviation.
- Read BlenderProc `StereoGlobalMatching.py` (main branch) for the M3 decision. Surprises: `blockSize=5` hard-coded (the `window_size` argument only sets P1/P2); left-right check and speckle filter hard-coded off; zero disparity → depth_max instead of invalid; with WLS on, the disparity is min-max normalised to 0–255 before /16, so the depth is not metric. Recorded in SOURCES S-11. Relevant for the report: "why we did not use the stock helper".
- User declined automating skills with hooks (AI_USE_LOG A#5).

## 2026-11-03 — D13: SGBM in .venv (option B)
- User chose option B: Blender renders and exports the IR pair (linear 16-bit, no tone mapping); noise, SGBM and depth conversion run in `.venv`. BlenderProc's stereo helper is not used (hard-coded matcher, zero disparity → max depth, non-metric WLS path; SOURCES S-11).
- Feasibility not yet tested: A-32 lists three checks for M3 (linearity, saturation only through our exposure model, export + matching time). Fallback: copy the helper and patch it, run inside Blender.
- Pipeline §4 is not part of the frozen protocol §5, so this is not a deviation.
- Phase 1 readiness reviewed: nothing blocking; research items deferred to M3/M4/M6 (STATUS.md).

## 2026-11-03 — M1 BlenderProc environment (Phase 1 start)

- Started 16:59 CET; quickstart passing at ≈ 17:35 (≈ 35 min of the 1 h time box).
- `blenderproc==2.8.0` would add only blenderproc, h5py 3.16.0 and progressbar 2.5 to `.venv` (no version conflict), but would break `.venv` == `requirements.lock.txt`. Installed it instead into a separate, gitignored launcher env `.venv-bproc` (Python 3.11.6). No requirements file changed.
- Blender 4.2.1 macos-arm64 downloaded by BlenderProc into repo-local `blender/` (≈ 4.5 min download).
- **Failure 1 (unpatched):** exit 2 after 272 s. Two writes into the signed `Blender.app` bundle are blocked by macOS 27.2 ("Operation not permitted", issue #768): (a) `pip install --upgrade pip` uninstalls the bundled pip 23.2.1, cannot install the new one and cannot roll back, so the bundled Python is left **without pip**; (b) `os.mkdir(.../Blender.app/Contents/Resources/custom-python-packages)`. Upstream PR #1231 fixes (b) but recovers from (a) by re-running `ensurepip` inside the bundle, which cannot work when the bundle is read-only, as here.
- **Fix:** local patch `patches/blenderproc-2.8.0-macos-app-bundle.patch` to `SetupUtility.py` in `.venv-bproc`: (b) as in PR #1231 (packages dir next to the bundle: `blender/blender-4.2.1-macos-arm64/custom-python-packages`), and (a) skip the pip self-upgrade when Blender's site-packages is not writable. Deleted the broken Blender copy and let BlenderProc re-download it. `scripts/setup_blenderproc.sh` reproduces the env + patch.
- **Result:** quickstart exit 0, wall 293 s including the re-download and package installs (pyrender 0.1.45, PyOpenGL 3.1.0, pyyaml 6.0.1, …); render 55.3 s for one 512×512 frame of the quickstart scene. Cycles uses "Apple M2 (GPU - 8 cores)" METAL + CPU. Output image looks correct (Suzanne).
- No terminal permission (App Management) was granted; the patch avoids the need for it.

## 2026-11-03 — M2a procedural parts and symmetry tests

- `src/synthrgbd/parts.py`: profiles (30 mm square, 4 T-slots, lengths 60/100/150 mm) and an equal-leg L-bracket (40×40×30 mm, 4 mm thick), as CCW 2D polygons extruded along z; ear-clipping caps; unshared vertices (flat shading); PLY writer (mm). Model frames as in A-20. numpy only, so the module also runs inside Blender's Python.
- `tests/test_parts.py`: 22 new tests (36 in total, all pass, 17 s). Vertex-set and surface invariance under all 8 profile and 2 bracket symmetries; wrong transforms rejected (> 1 mm); closed 2-manifold with outward winding (signed volume = analytic prism volume); model frames; MSSD = 0 for symmetric poses on the generated meshes.
- **Surprise:** Open3D 0.20 `RaycastingScene.compute_distance` (float32) reports up to 0.02 mm for points that lie exactly on the profile mesh (identity transform), so it cannot verify symmetries at a 1e-3 mm tolerance. Replaced it in the test with an exact float64 closest-point-on-triangle routine (Ericson), with its own unit test.
- Also `geometry.plane_depth` (analytic z-depth of a plane for a given K) + test, for the A-28 check.
- **Finding for Task B:** with these dimensions the largest flat disk is 5.5 mm radius on profile side strips and 9.76 mm on end faces, both below the frozen 10 mm cup (A-19). Suction can only succeed on brackets (≤ 15 mm). Recorded in A-33; decision left to the user.

## 2026-11-03 — M2b K-matrix check against A-28

- `scripts/bproc_check_intrinsics.py` (Blender) renders the depth of a 4 m plane at 0.8 m, tilted 30° about x and 15° about y, camera K = intrinsics_from_hfov(1280, 720, 65°) = fx = fy = 1004.599 px, cx = 639.5, cy = 359.5. `scripts/check_intrinsics.py` (.venv) compares it to the analytic depth.
- K read back from BlenderProc: max |Δ| = 4.2e-5 px. Depth residual: mean −0.0004 mm, std 0.0002 mm, max 0.0016 mm over 100% of pixels. Grid search (Δc ±1 px in 0.25 px steps, f ×0.998–1.002): best at Δcx = Δcy = 0, f ×1.000. Ray-distance hypothesis: off by up to 325 mm, so the output is z-depth. Render 10.1 s (1 sample, depth only).
- A-28 → tested-ok.

## 2026-11-03 — Correction and a slip: M1 timing, stray ~/blender download

- **Correction to the M1 entry above:** from file timestamps, the unpatched quickstart failed at 17:05:38 and the patched one passed at 17:12:11, so M1 took ≈ 13 min of the 1 h box (not "≈ 35 min", which was an estimate).
- **Slip (agent):** the first K-check run (17:16) used plain `blenderproc run` without `--blender-install-path`; BlenderProc's default then downloaded a second Blender 4.2.1 (1.4 GB) into `~/blender`, outside the repo, against the instruction to keep it in `blender/`. Also a first scene-1000 attempt started there and was stopped during package install. Fix: `scripts/bproc.sh` wrapper (always `--blender-install-path <repo>/blender`, temp dir `data/tmp`); `~/blender` removed at 17:22 (it did not exist before this session: the K-check log shows the download). K check re-run on the repo-local Blender: identical numbers (max |Δ| 0.0016 mm, Δc = 0 px). `--custom-blender-path` pointing at `Blender.app` fails ("Could not determine major blender version"), so the wrapper uses the install path.

## 2026-11-03 — M2c physics scenes and BOP output (dev seeds 1000, 1001)

- Pipeline: `scripts/render_scenes.sh <out> <seeds>` = `bproc_render_scene.py` (Blender: tray + table, 3–6 parts, Bullet drop, 2 views, RGB 64 samples + z-depth without AA + instance segmentation, BOP writer) → `bop_gt_info.py` (.venv: mask_visib PNGs from the segmentation, ray-cast amodal masks, scene_gt_info.json) → `check_bop_scene.py` (.venv: back-projection consistency, K vs A-28, Min-Z). Models: `export_models.py` (PLY in mm + models_info.json with symmetries_discrete).
- **Failure 1:** BlenderProc's BOP writer with `calc_mask_info_coco=True` pip-installs bop_toolkit (which also downgraded Blender-side numpy to 1.26.4) and starts a `multiprocessing.Pool` for pyrender; on macOS (spawn) each worker re-runs our script without `blenderproc` on its path, dies, and is respawned. The run hung for 10 min with a 194k-line log; killed. Fix: `calc_mask_info_coco=False`, masks computed by us (A-35).
- **Failure 2:** visible masks written inside Blender with OpenImageIO came out as diagonal stripes (wrong stride), which the consistency check caught (visib_fract up to 345, median back-projection error 390 mm). Fix: Blender saves the raw instance map (.npz) + k→index table; PNGs are written by OpenCV in .venv.
- **Failure 3:** with BlenderProc's default 1 mm collision margin, all parts rested 2 mm above the floor (profile centre z = 17 mm instead of 15 mm). Collision margin 0.1 mm → lowest vertex 0.2 mm above the support for every part (A-34).
- **Results (dev seed 1000, 4 parts; dev seed 1001, 6 parts; master seed 0; Blender 4.2.1, Metal GPU + CPU, 1280×720):** physics 0.11–0.12 s; RGB + depth + segmentation render 8.4–8.6 s/frame at 64 samples; BOP writer 0.2 s; full scene wall time 25.3 s for 2 frames including Blender start-up and .venv post-steps (≈ 12.6 s/frame end to end); 2.0 MB/scene on disk. All parts in the tray; one stacked part in 1001 (lowest vertex 30.4 mm); visib_fract 0.79–1.00; nearest part depth 0.609–0.952 m (> 0.45 m, A-16).
- **Consistency (20 instance-views):** masked depth back-projected through scene_gt poses lies on the CAD surface: worst median 0.023 mm, worst p95 0.047 mm (≈ the 0.1 mm depth quantisation), 0% > 1 mm; 0 visible pixels outside amodal masks; unoccluded visib_fract = 1.000 (Blender segmentation and Open3D ray casting agree to the pixel); scene_camera K = A-28 K within 4e-5 px.
- **Determinism:** re-rendering seed 1001 gives identical scene_gt poses (max |Δ| = 0) and bit-identical depth; RGB differs by ≤ 1 grey level in 0.002% of pixels (GPU sampling).
- Projection for 55 scenes (50 test + 5 dev) RGB/depth only: ≈ 23 min. IR stereo renders (M3) will dominate; not measured yet.

## 2026-11-03 — M2 close

- Re-rendered dev scenes 1000 and 1001 from the clean commit 81e583b (earlier sample renders recorded `7a7c4d0-dirty`): 4 and 6 parts, 8.36 / 8.43 s per frame, worst p95 back-projection error 0.047 mm, 0% > 1 mm, Min-Z OK. Stopped after M2 as instructed; M3 not started.

## 2026-11-03 — User decisions after M2

- A-33 / Task B: option (a), keep part geometry and the 10 mm cup; report Task B per part type in addition to the overall rate. Logged as the first deviation in PLAN §5.12 (no data existed yet).
- Keep the local BlenderProc macOS patch rather than granting App Management permission: recorded as D14.
- Pin BlenderProc: `requirements-bproc.txt` (blenderproc==2.8.0) + `requirements-bproc.lock.txt` (pip freeze of `.venv-bproc`, 21 packages); `scripts/setup_blenderproc.sh` now installs from the lock.

## 2026-11-03 — D415 projector details from the datasheet [S-01]

- Full-text search of the D400 datasheet Rev 013 (153 pages). Table 3-16 (p. 40): static pattern, VCSEL + optics, PWM, 360 mW average optical power, 850 ± 10 nm, field of projection H 64° ± 3° / V 41° ± 3° / D 72° ± 3°. Tables 3-11 (p. 37) and 3-48 (p. 64) give H 67 / V 41 / D 75 instead: an internal inconsistency. Laser power 0–360 mW in 30 mW steps (p. 88); specs measured at 150 mW, auto exposure (p. 81). Dot count, size, density and layout are not given anywhere in the datasheet; another source is needed for the projector model at M3.

## 2026-11-03 — End-of-session review before handoff

- Re-checked: 38 tests pass; all scripts compile (`py_compile`, `bash -n`); no leftovers of removed options; the macOS patch applies to a freshly downloaded blenderproc-2.8.0 wheel; `requirements-bproc.lock.txt` resolves in a fresh venv (pip dry run); no generated data, Blender, venvs or .DS_Store tracked; `protocol-v1` tag unchanged (4f52c67).
- **Inconsistency found:** since `protocol-v1`, commits 348d49c and b6c5b00 (earlier session) edited comments only in frozen files (`configs/default.yaml` offset_sweep comment; PLAN §5.2 A1 line, "A-30 confirmed") without a §5.12 row. No value changed. Not logged unilaterally; raised in STATUS for the user.
- Stale docs fixed: CLAUDE.md Environment now names `.venv-bproc` and the `scripts/bproc.sh` rule; PLAN status line; A-16 (Min-Z check implemented, OK on dev scenes); STATUS adds the projector-FOV choice (64° vs 67°) for M3.

## 2026-11-03 — protocol-v1 tag published

- At the user's request, pushed the annotated tag `protocol-v1` (tag object 35ca9bf → commit 4f52c67, tagged 2026-11-03 16:35:08 +0100) to origin, so the pre-data protocol freeze is visible on GitHub. The tag was not moved.

## 2026-11-04 — Pre-M3 open points closed (D15)
- User decisions: projector FOV 67° × 41° (A-36); M3 gate criteria (A-38); resolution rule "1280×720 if the projected full render ≤ 8 h" (A-39); editorial row for commits 348d49c / b6c5b00 logged in PLAN §5.12. Checking the diffs showed that only 348d49c touched frozen content (config comment + §5.2 wording); b6c5b00 edited PLAN §2/§4 only.
- Dot-pattern research (A-37): no verifiable D415 dot count. Datasheet Rev 013 is silent; Intel projector white paper Rev 1.0 [S-13] gives the D435 count (~5000), says the D415 uses two Heptagon projectors emitting at 68 × 43°, and gives density guidance (1–10% of image resolution near-ideal; D435 test: > 10K dots desirable, diminishing after 30K). Default chosen: 30 000 dots → ~27 700 in the 1280×720 image (3.0% of pixels, spacing ≈ 5.8 px). Rejected: a 30K-dot figure from an iPhone X teardown (different product).
- Surprise: OpenCV 5.0.0 StereoSGBM leaves the first num_disparities = 128 columns invalid even when the true disparity is 55 px, so the D415 band B·f/Z (55 px at 1 m) would come out at 128 px. Synthetic test (random texture, d = 55/110 px, blockSize 7, LR check 1): padding the left image by 128 px + a right image 128 px wider + masking x − d < 0 gives first valid column 55/110, 99.9–100% valid right of the band (A-40). StereoSGBM.compute also rejects non-8-bit input.
- Derived numbers: f = 1004.6 px, f·B = 55.25 px·m, Min-Z by 126 px search = 438.5 mm; per-frame budget 8 h / 110 frames = 262 s.

## 2026-11-04 — M3 stereo route: implementation, plane gate (A-38), benchmark (A-39)

**Code (commit 044ee81).** New non-frozen camera config `configs/camera_d415_ir.yaml`. `synthrgbd.projector` (30 000 Poisson-disk dots, seed 415, σ = 0.7 px, pattern 2660 × 1502 texels over 67° × 41°), `synthrgbd.bproc_ir` (own spot-light projector at the baseline midpoint, shadows on, linear float pattern; IR pair rendered 1408 px wide with cx + 128; EXR, no denoiser/adaptive sampling/clamping, 32 samples), `synthrgbd.stereo` (fixed exposure → 8 bit, SGBM on the extended pair, invalidate no-match / d > 126 / x − d < 0, z = fB/d). Scripts: `bproc_ir_plane.py`, `plane_gate.py`, `stereo_scene.py`, `benchmark_m3.sh`, `--ir` in `bproc_render_scene.py`. Tests 38 → 54 pass.
- BlenderProc's `setup_as_projector` not used: it copies the camera pose and FOV, sets `use_shadow = False` and loads the pattern into an 8-bit sRGB image.
- Pitfall: a second `render()` with OPEN_EXR fails ("Can not have two output entries with the same key/path") after the PNG RGB pass; fixed with its own output key/prefix (`ir_`).
- Pitfall (shell): `rm -rf data/m3/_tmp_*` with no match aborts the zsh `&&` chain, so the first benchmark rerun never started.
- Exposure gain calibrated once: p99.9 radiance of the albedo-0.5 plane at 0.45 m = 0.04037 → gain 5700 (230 DN).

**Plane gate A-38** (z 0.50…1.00 m, matte albedo 0.5, no IR noise; clean rerun at 044ee81 reproduces the first run to 1e-4 mm):
- (i) bias −0.19 / +0.24 / −0.59 / +0.33 / +2.60 / +2.25 mm = max 0.29% z ✅; (ii) 100.00% valid at every z ✅; (iv) band 111 / 93 / 79 / 70 / 62 / 56 px vs fB/z 110.5 / 92.1 / 78.9 / 69.1 / 61.4 / 55.3 ✅.
- **(iii) ❌:** valid 5.03% (0.42 m), 5.07% (0.43 m), 100% at 0.44 / 0.45 / 0.46 m. Limit ≤ 5% at ≤ 0.43 m, so the gate fails by 0.03–0.07 pp. The step is where designed (fB/126 = 438.5 mm). Valid pixels below Min-Z are false matches: ~310 connected blobs, median 120 px, disparities 1–124 px; they survive the 100 px speckle window. Not a pipeline bug.
- Diagnostics only (not adopted, `data/m3/logs/gate_variants_diagnostic.log`): our SGBM with speckle window 200 → (iii) 0.34 / 0.41%, (i)/(ii)/(iv) unchanged; uniqueness 15 → 3.09 / 3.12%; BlenderProc helper matcher (block 5, HH, uniqueness 15, no speckle) with the LR check on → (iii) 16.5 / 16.2%, and without the A-40 fix its band is 128 px at every z (fails iv) and valid drops to 94.3–94.8% at 0.9–1.0 m (fails ii). So the patched-helper fallback would not fix the failure.
- Noise-free plane: SGBM pixel-locking, plane-fit residual 0.10–1.02 mm (equivalent ε_d 0.011–0.23 px depending on the fractional disparity). Not gated (M4).
- Projector geometry: rendered left IR vs numpy forward model r = 0.980 / 0.980 / 0.968 (0.5 / 0.7 / 1.0 m); r ≈ 0.003 without the offset or mirrored. Unlit left strip 30 / 14 / 2 px, inside the invalid band.
- A-32: (i) power ×2 → summed radiance ×1.9997; mean radiance ∝ z^−2.003; (ii) metal sphere peak 28.8 = 1159× matte max, unclipped, 15 px saturate only after exposure; float16 rel. err ≤ 4.9e-4.

**Benchmark A-39** (dev scenes 1000–1001, 2 views each, RGB 64 + IR 32 samples, metal pass = M2 placeholder aluminium as timing proxy). Per scene wall time: first run (uncommitted tree) 66.9 / 69.3 s; clean run at 044ee81 103.0 / 71.9 s (Blender 98.5 / 66.8 s; RGB 15.8 / 13.7 s per frame vs 8.4 at M2; same code, so machine load/thermal). Per frame median 43.7 s (clean run) ≤ 262 s → 110 frames ≈ 1.3–1.6 h, keep 1280×720. SGBM 0.2–0.4 s per pair; IR ≈ 5 MB per scene.

**Surprises for M4 (scene stereo, matte pass, informative only):**
- Scenes are dark with the fixed gain: mean 3.6–8.6 DN (tray albedo 0.3, z up to 1.24 m).
- Pixel-locking dominates the scene error: 58–64% of stereo disparities within ±0.125 px of an integer (uniform would be 25%); disparity error MAD 0.12 px, p95 0.28–0.30 px; striped ±5–10 mm depth error on the tilted view 1 of scene 1000; part MAE 1.95–4.29 mm matte, 2.30–8.64 mm metal proxy; part pixels invalid 0.15–6.5%.

**Status:** M3 gate not passed on (iii). Per D15, stopped and presented the options to the user; no route switch, no matcher change.

## 2026-11-04 — M3 closed: user decision on gate (iii)

- **User decision (option 3a):** keep the stereo route and the matcher settings of commit 044ee81. A-38 (iii) is recorded as a marginal failure: 5.03% / 5.07% valid at 0.42 / 0.43 m against ≤ 5%. Cause: out-of-range false matches (true disparity 131.6 / 128.5 px > 126 px search range) in clumps of ≈ 120 px that pass the 100 px speckle window. Expected effect on the experiment nil: nearest scene pixel 0.609 m (A-16), camera 0.65–0.95 m. **REPORT §6 "what did not work".**
- **Option 3b rejected by the user:** speckle window 200 px was tried as a diagnostic only (`data/m3/logs/gate_variants_diagnostic.log`: (iii) 0.34 / 0.41% valid, (i)/(ii)/(iv) unchanged) and not adopted. Reason: tuned after seeing the gate result, and it may remove small true surfaces such as bracket edges. Speckle window stays 100 px.
- Placement: not a PLAN §5.12 deviation (the gate criteria are in A-38 / D15 / PLAN §7, outside the frozen §5 and `configs/default.yaml`); recorded in ASSUMPTIONS A-38, PLAN §7 (M3 row) and here.
- Open for M4, nothing chosen: dark IR at fixed exposure (mean 3.6–8.6 DN on dev scenes); SGBM pixel-locking (58–64% of disparities within ±0.125 px of an integer). M4 waits for the user's design review.
- Process note: the user asked that at a gate the agent stops there and proposes further measurements instead of running them (the A-39 benchmark had been run after the gate failure).

## 2026-11-04 evening — Pre-M4 design review (external reviewer claims tested)
- Done: tested 7 claims from an external Claude review (docs only, commit 5706022) against docs, sources, code and the dev data. One fresh adversarial subagent reviewed the lead agent's conclusions. Memo given in chat; decisions recorded in ASSUMPTIONS / SOURCES (commit below).
- Numbers (dev 1000–1001, commit 044ee81, matte pass, own analysis):
  - pixel-locking: 65% of disparities within ±2/16 px of an integer (31% uniform at OpenCV's 1/16 px step; A-43's 25% is the continuous baseline);
  - sawtooth of the mean disparity error vs the true fractional disparity, −0.11 to +0.18 px; half-integer bin 1%;
  - matte mean error per part (interior pixels): median |·| ≈ 0.4 mm, worst 2.7 mm;
  - metal proxy (roughness 0.3): invalid on parts 0–8% (no holes); brackets in 1000 view 1 +5/+10/+13 mm interior mean; other views: medians ≈ 0, heavy tails (21–30% of interior pixels > 5 mm);
  - left IR median 0–2 DN, p99 30–60 DN.
- Sources:
  - ROBI's D415 working distance is 243–638 mm (S-05, verified in the PDF), against our 0.61–1.24 m;
  - Intel subpixel-linearity white paper (S-14, read in full): D4 ASIC pixel-locking ±0.5% at ~1 m (D435, High Density), D415 "almost identical", default A = 0. Our locking is of comparable magnitude, so it is kept.
- Decided (user):
  - 1(b): keep §5.6. Fixed-sequence order C1–C3 → C2b–C3 → C3–C4; C2b at 0.26 px; "C1 ≥ C2" descriptive. The §5.12 row text awaits the user's OK;
  - 2(b): ROBI after Friday;
  - 3(c): keep pixel-locking;
  - 4(a): per-frame AE on the C3 left image, gain shared with C4; A-24 defined first;
  - Task B: no deviation; grasp point fixed on dev;
  - roughness by rationale + 0.2/0.4 robustness check;
  - tuning ledger (A-45); ICP normals from the CAD model, pooled worst-case rule (A-46); reporting additions (A-47).
  - M4 order changed by the user: harness first.
- Failed / surprised:
  - the metal proxy gives biased or heavy-tailed depth, not holes, so the "holes vs smoothing" framing was wrong;
  - S-13's 0.07–0.11 px is a plane-fit RMS and cannot see locking.
- Report note:
  - §4: locking "comparable magnitude to D4 at default firmware" [S-14];
  - §5: fixed-sequence testing and the tuning ledger as judgement examples;
  - §6: ROBI range mismatch.

## 2026-11-04 late — M4 step 1: ICP harness, C1 sanity check, suction code
- Done:
  - `synthrgbd.pose` (point-to-plane ICP, normals from the CAD model, back-face culling in an outer loop; offsets per A-30/A-48);
  - `synthrgbd.suction` (planner + GT check per §5.3);
  - `scripts/pose_eval.py`, `scripts/suction_eval.py`;
  - non-frozen `configs/harness.yaml` (all values PROVISIONAL);
  - tests 54 → 73 pass. Commits 0ebdbac, 11cfe42.
- Numbers:
  - **§5.11 sanity, C1, dev 1000–1001, zero offset: 20/20 < 0.5 mm, median 0.032 mm, max 0.28 mm → pass** (same at both commits);
  - ICP ≈ 0.02 s per instance;
  - Task B smoke run on C1 dev: brackets 5/8 succeed (1 without a grasp, 2 fail check 3(b)), profiles 0/12 (A-33).
- Failed / surprised:
  - 6 000 CAD samples gave 0.07–0.10 mm drift from the GT pose on ideal synthetic views (point-to-plane against a sparse target), so 50 000 are used (0.006–0.019 mm with 60 000);
  - Task B check 3(b) without a height cap also fails grasps on parts far along the approach axis (193 mm), which goes beyond §5.3: cap left to the user (A-50).
- Open, for the user: A-48 offset pivot (bounding-box centre) and directions shared across sweep levels; A-49 instance inclusion (visib_fract ≥ 0.1, source unverified); A-50 cylinder cap. §5.12 row text still awaits OK.
- Report note:
  - §5: back-face culling and CAD normals;
  - "what did not work": sparse-target drift; the over-broad suction check caught by the smoke run.

## 2026-11-04 night — M4 step 1 follow-ups (user answers)
- Decided (user):
  - A-48 pivot confirmed (bounding-box centre, directions shared by conditions and sweep levels);
  - A-49 visibility ≥ 0.1 approved in principle (§5.12 row drafted, awaiting approval);
  - A-50 option (a), cap = cup radius, all parts, two-sided.
- Verified: the BOP 10% rule in the BOP 2020 paper, Table 1 caption ("at least 10% of the projected surface area is visible"); bop_toolkit default now −1, with the filtering in the test targets (S-07).
- Code (2723650, 880bf32):
  - suction check 3 is now a first-surface two-sided ray-cast over the disk (A-50). A literal "every surface point in the cylinder" check would fail every bracket on its own back face 4 mm below, so the first-surface reading is flagged to the user;
  - planner cup-fit is now a rim test (32 points, gap ≤ 1.5 mm). 8 sectors / 0.7 let the disk overhang 0.83 mm on an ideal view; 16 sectors / 0.9 found no fit on tilted dev faces;
  - pose_eval adds axial / across-axis centre error;
  - 75 tests pass.
- Numbers (dev 1000–1001, C1, commit 2723650 for Task A, 880bf32 for Task B; master seed 0):
  - sanity unchanged (20/20 < 0.5 mm, max 0.28 mm);
  - **A1 10 mm/10° on C1, report-only: recall@5 mm 8/20 = 40% (brackets 4/8, profiles 4/12); @2 mm 5/20 = 25% (brackets 2/8, profiles 3/12).** Profile failures: 2 axial slides (axial 9.0/9.5 mm, across < 0.5 mm), 6 wrong-minimum across the axis (across 12–24 mm, rotation 10–35°). Brackets: 1 no correspondences, 1 in-plane slide (t 9.8 mm, R 0°), 2 at 5.7 and 52.8 mm;
  - Task B C1 smoke run: brackets 5/8 succeed (6 with a grasp), profiles 0/12.
- Failed / surprised: **C1 is far from the ceiling at the frozen 10/10 offset (40%)**, mostly from wrong-minimum convergence, not sliding. Hypothesis (untested): Tukey k = 5 mm discards most correspondences at the start of a 10 mm offset. No harness change made (user: tuning waits for the pooled rule).
- Report note: "what did not work": the over-broad suction check and the overhanging planner, both caught by tests or the smoke run; C1 at 40% under A1 (§6).

## 2026-11-04 night — M4 step 2 started; stopped at the roughness choice
- Done:
  - order changed to roughness → A-24 → exposure → noise, because A-24 and the exposure gain depend on the C3 metal image (flagged to the user);
  - code 90c3595: C3 "metal" pass from `materials_metal` (render refuses to run while roughness is null); auto-exposure gain over columns ≥ ceil(f·B/Min-Z) = 123; shot + read noise with shared draws; 77 tests pass.
- Sources:
  - Al reflectance at 848 nm = 0.868 from Rakić 1998 n, k (S-15), against 0.915 at 550 nm;
  - MERL "aluminium" GGX α = 0.0044 / 0.0218 / 0.0201 / 0.0164 (Bieron & Peers 2020 supplement, S-16), i.e. roughness ≈ 0.13–0.15 for the non-L2 fits;
  - no source for extruded or anodised profiles; the TU Delft supplement host refused connections; the Bieron PDF is 99 MB at ~110 KB/s.
- Open for the user: the roughness value, which lies below the pre-declared 0.2 / 0.4 pair; then the noise-model free parameters.

## 2026-11-05 ~00:30 — M4 steps 2–3 on dev; STOP (b): C3 at floor
- Decided by the agent (ledger rows):
  - setpoint 10 DN;
  - e_per_dn 0.12 (effective);
  - A-24 albedo 0.085 by mean matching;
  - metal diffuse lobe D = 0.015 (S-16);
  - ICP H3 by leximin;
  - grasp point plane_fit.
- Numbers (dev 1000–1004, master 0, commits 08eeb9a…):
  - anchor (a): (i), (ii), (iv) pass; median subpixel RMS 0.090 px; (iii) 6.35 / 6.59% valid below Min-Z (accepted 3a);
  - locking 64% within ±2/16 px vs 31% uniform; sawtooth −0.08…+0.13 px;
  - part errors, median signed: C4 profiles +1.1 mm, brackets +4.3 mm; C3 profiles +4.1 mm, brackets +19 mm;
  - A1 recall@5 mm, H3, 40 instance-views per condition: C1 0.70, C2a 0.78, C2b 0.55, **C3 0.00**, C4 0.23;
  - sweep C1 0.975 / 0.875 / 0.60 at 2 / 5 / 20; C3 0.05 / 0.00 / 0.00 (median MSSD 22–30 mm); C4 0.35 / 0.25 / 0.15;
  - Task B brackets: C1 0.75, **C3 0.00**, C4 0.25.
- Failed / surprised: C3 metal (roughness 0.15) biases depth far by ~+19 mm on brackets, so ICP fails from every offset. C4 is weak because brightness-matched parts are dark (0.085) and noisy. Stop criterion (b).

## 2026-11-04 ~16:45 CET — M4 closed; first M5 start stopped and undone
- M4 done: camera model (roughness 0.15 + D 0.015, albedo 0.085, setpoint 10 DN, e_per_dn 0.12), harness H3 + plane-fit grasp, dev pilot (C3 at floor). Details in the entries above and the ASSUMPTIONS ledger.
- Correction: the previous entry's heading "2026-11-05 ~00:30" is wrong. That work happened on Wednesday 2026-11-04, early afternoon CET; the agent misstated the date and time.
- User decisions for M5 (A-51…A-56): (B) roughness 0.2 / 0.4 on all 50 test scenes as a dose–response curve; (D) a bright-matte pass at albedo 0.5, descriptive; (C) rejected; nothing changes once test data exist; a pre-render check figure; ROBI mandatory after M5; operating mode.
- **M5 start stopped by the user (to continue in a fresh session) and undone.** No commits had been made after c18ea50 and no test scene was rendered. Removed:
  - uncommitted edits (`stereo_scene.py --suffix`, `pose_eval.py` / `suction_eval.py --depth-dir`);
  - the new `scripts/fig_specular_check.py` (a copy is kept outside the repo in the agent scratchpad);
  - `data/m4/figs/specular_*.png` (4);
  - `depth_stereo_{metal,matte}_nonoise/` and `stereo_meta_nonoise.json` in dev scenes 1000–1004;
  - `data/tmp/{diag_depth_stereo_metal_nonoise.jsonl, ir_nonoise.yaml, spec_small.png}`.
  - The noise-off diagnostic was deleted unread.
- Preliminary, not a result (to redo in M5, A-54): on dev views the metal parts were near-black in the left IR image, and 83–89% of biased C3 pixels lay between the true surface and the tray behind it. A mirror-image prediction explained only 15–28% of them (C4 control 9–13%). This points to texture loss + SGBM fill more than to reflected dots; no sign of a bug.

## 2026-11-04 (M5 Step 1, stopped on a bug)
**Surprise:** BlenderProc 2.8.0 defaults to Cycles `glossy_bounces = 0` and our IR code never overrode it. Printed live in Blender at IR render time: glossy 0, diffuse 3, max 3. Every IR render so far (M3 proxy, M4 dev at 185aa1a) therefore has no reflected image on metal. The check was meant to choose between reflected dots (i) and SGBM fill (ii); (i) cannot occur in that data.
**Run:** dev seeds 1000–1004 re-rendered with `--glossy-bounces 3` at abbae3d + uncommitted flag, into `data/m5_diag/gb3`, 46–64 s/scene (same as glossy 0). Poses identical; ideal depth differs by ≤ 0.1 mm on ≤ 5.4e-6 of pixels; matte IR relative difference ≤ 2.5e-5. Metal: zero-radiance part pixels 78.5 → 56.9%, mean part radiance × 22.4 (glints; top 1% of pixels hold up to 87% of the sum). A1 and Task B not run on it, so the decision does not see the outcome (A-45).
**Mechanism (142 284 metal-part pixels, 10 views):** glossy 0: correct 49.6%, behind the surface 40.2%, in front 6.8%, invalid 2.6%; blanked metal stays 98.5% valid with 2.5% correct; background cut moves behind/in-front from 40.2/6.8% to 17.6/13.0%; ±3 px shift slope 0.27–0.37 (blanked control 0.87–0.99). So fill, as a pull rather than a copy: median 0.52 of the way from surface to tray. Glossy 3: correct 42.6%, behind 46.0%, P(correct | SNR > 5) 92.9 → 49.6%; on faces whose mirror ray hits the scene, behind survives the cut (51.0 → 39.5%) and slope is 0.00–0.01, so mirror images act there. Details: A-58.
**What did not work:** the ±8 px background shift lacks power (blanked control slope 0.54–0.60), replaced by ±3 px. The mirror-prediction match is weak evidence on its own: 12.7% of biased pixels match where no mirror image exists. The shifted-pixel null (0.8%) badly understates that floor. A-24 mean matching breaks with glints (albedo 1.90).
**Unexplained:** at glossy 3, biased pixels on faces whose first-order mirror ray sees nothing also stop following the background (slope 0.02–0.07).
**State:** stopped for the user's decision; no test data; Steps 2–5 not started. Seeds: master 0, ir_noise stream as in M4.

## 2026-11-04 (M5, user decisions after the Step 1 stop)
User accepted all three suggestions: (1) enable reflections, re-run the dev rules, new pilot, then M5, with reflections off as a descriptive pass; (2) C4 albedo 0.317 by clipped-at-saturation matching (0.3169 when C4's own clipping is included); (3) run both convergence checks first. Rules for the checks written into the ledger and committed before any check render.

## 2026-11-04 (M5, dev rules re-run after the reflection fix)
Convergence (rules in the ledger, committed at 2e5a374 before the runs): 128 samples +1.95 points correct on scene 1001 (limit 2), keep 32, though lit metal radiance differs by a median 47-53%; max 12 -2.26 points, use it; glossy 1 +2.89, informative. The max 12 trigger was one view, 1002/1. **Surprise:** the same view flips between two renders with identical settings and seeds (79.4% of metal pixels move > 5 mm, frame radiance differs by <= 7e-5). So fill on dark parts is bistable and C3 is not bit-reproducible from a re-render (A-59).
**Re-derived on dev, in this order, radiance/saturation/plane only:** setpoint 10 -> 20 DN; e_per_dn 0.12 -> 0.087 (median RMS 0.0898 px); C4 albedo 0.247 (clipping couples it with the setpoint: 0.32 at 10 DN -> 20 DN -> 0.247 -> 20 DN; the user approved the rule and 0.317 at 10 DN). Harness H3 -> H2 by leximin; plane_fit stays.
**Dev pilot, final settings, data/m5_dev/pilot, 40 instance-views:** A1 recall@5 mm C1 0.70, C2a 0.80, C2b 0.55, C3 0.05, C4 0.325; C3 reflections off 0.025, roughness 0.2 / 0.4 0.075 / 0.325, bright matte 0.425. Task B brackets (n = 12): C1 0.75, C2b 0.58, C3 0, C4 0.50. Sensor, part pixels: C3 MAE 8.94 mm, > 5 mm 50.5%, invalid 6.7%; C4 3.44 mm, 18.0%, 2.3%.
**Refuted:** the agent's idea that dark faces are filled from the reflecting faces next to them (blanking those faces moves behind-the-surface only 32.7 -> 29.3%).

## 2026-11-04 (M5 paused by the user, ~18:55 CET)
Stopped at a scene boundary to shut the computer down: scenes 0-2 rendered (104-130 s each, commit 73f0305, all parts in the tray), the render loop and the ROBI fetch stopped, nothing left running, no test metric computed. ROBI: whole-file Drive downloads return "Quota exceeded" for the 4 GB archives; HTTP range requests on the uncompressed zip work, so only a subset is fetched (24 Zigzag files so far). D415 data exist only in scenes 4, 5, 8, 9 of each object. Resume steps in STATUS. Later scenes will record the docs-only commit of this note; the code is identical.

## 2026-11-04, evening: test render done; §5.11 sanity gate FAILED, stopped
Test render finished at commit 8ccbd95 (scenes 3-49; scenes 0-2 at 73f0305, code identical): 50 scenes, 2 views each, 9 depth conditions, C2 depth, all counts verified. Scripts committed e293e31 (adds stereo_scene.py --noise-redraw, A-59; protocol depth unchanged by hash on scene 0; 94 tests pass). run_eval.py stopped itself at the sanity check, clean tree at e293e31.
**Result, C1 ideal depth, ICP started at GT, harness H2: 416/459 = 90.63% at MSSD < 0.5 mm; required ≥ 99% (≤ 4 failures, got 43).** Dev was 40/40 for H0-H3 (p50 0.03, max 0.28 mm), which at this failure rate has about a 2% chance if independent: n = 40 was too small to see it.
Failures: 10 at ≥ 5 mm (9 at 40-119 mm, fitness median 0.39, 8 of them with R error about 90°; 1 at 7.0 mm); 33 at 0.5-5 mm (median R 0.72°, t 0.18 mm, fitness 0.97). All profiles: obj 1 (60 mm) 23/104, obj 2 (100 mm) 14/124, obj 3 (150 mm) 6/114, bracket obj 4 0/117. Not occlusion (42 of 43 at visib ≥ 0.9), not few points (n_pts ≥ 1277), spread over 27 of 50 scenes.
Untested inference: near-planar views make the point-to-plane normal matrix near-singular. H2 has no step clamp, and the code comment on H3's clamp says "near-planar views diverge". The clamp cannot explain the 0.5-5 mm band, and short profiles failing most is the opposite of a lever-arm effect. H2 beat H3 on dev by one instance-view in three of five conditions.
No recall at a real offset has been computed: data/m5/results holds only the sanity file. §5.8 variant and redraw depth for seeds 0-9 exists but no metric was computed; the quick sensor line of one redraw view (scene 0 view 0) was seen while testing the option. Rendering is not affected, ICP runs on existing depth; Task B does not use ICP. Awaiting the user's decision; nothing further run, per stop-at-gates.

## 2026-11-04, ~21:15: read-only recount of the §5.11 failure; glossary added
User asked for a personal orientation guide (`docs/personal/GUIDA_PROGETTO.md`, not in git) and a code dictionary (`docs/GLOSSARY.md`), after losing track of the codes in agent replies. CLAUDE.md now requires codes to be written with their meaning and new codes to be added to the glossary. No ICP or experiment was run; the decision on the failed gate is still the user's.
**Recount of `data/m5/results/sanity_C1_zero.jsonl` (commit e293e31, clean tree), existing fields only:** every number in the stop report is confirmed (416/459, 10 + 33 failures, per-part counts, 27 scenes). H2 settings are identical on dev and test. P(dev 40/40) is 1.96% pooled, 3.1% from per-object rates, assuming independence; dev has 4 of 40 instance-views on the 60 mm profile.
**Not in the stop report:** (1) removing all 10 large jumps still gives only 92.8%, so at least 29 of the 33 small drifts must also go. (2) The 33 are two groups: 7 with R < 0.1° (5 on 150 mm, 2 on 100 mm; 6 slide along the axis, fitness 1.00: §5.9 prism sliding) and 26 small rotations (18 on 60 mm, 7 on 100 mm, 1 on 150 mm; median 1.04°, max 4.2°, fitness median 0.96). (3) Profiles by final fitness: < 0.90, 18 of 18 fail; 0.90-0.99, 11 of 29; >= 0.99, 14 of 295. Example: 60 mm profile, MSSD 0.55 mm, fitness 0.86, so 14% of points lose their 5 mm correspondence although no vertex moved more than 0.55 mm. Untested inference: the visibility filters remove surface the camera really sees. (4) R p90 excluding jumps: 1.08° / 0.14° / 0.06° at 60 / 100 / 150 mm, so short profiles failing most is compatible with weak rotation constraints, against the stop report's remark. (5) 97.82% stay below 5 mm at zero offset, so relaxing the threshold to 5 mm would still fail. (6) `run_eval.py` keeps existing result files, so a re-run needs a new results folder. (7) `solver: lm` is not a `select_harness.py` candidate and has no tests.
**Report note:** §6 "what did not work": the sanity gate caught an ICP robustness problem that dev (n = 40) could not see.

## 2026-11-05: §5.11 diagnosis (option 1, A-62): no candidate passes; ray-cast cache bug found; stopped
Docs fixes 87560d1; candidates and rule pre-declared 52764a3 (its message says "entry 12" for an AI-log row it does not contain; the insert had failed, added as entry 8 in 04faf51); runner 99e122c. All runs at 04faf51, C1, zero offset, test scenes 0-49, master seed 0, 459 instance-views; failed run untouched in data/m5/results, new runs in data/m5/diag_sanity. No recall at a real offset. Reproduce: scripts/sanity_candidates.py, then scripts/sanity_diagnosis.py (replay, static, trace, report); output logs/report.log.
**Pass/fail, MSSD < 0.5 mm, at least 455 needed:** H0 452 (98.47%), H1 452 (98.47%), solver lm 453 (98.69%), H3 421 (91.72%, 1 no estimate), H2 control 416 (90.63%). None passes. H0, H1, lm: no failure at or above 5 mm, max 0.853 mm. Wall time 14-70 s per run.
**Repeat and threads:** 7 plain H2 runs. 6 match the failed run, same 43, |ΔMSSD| < 1.3e-12 mm (2 threads x3, default x1, 1 thread x2). The first 1-thread run gave 33 failures, 25 shared, 122 views differ, up to 119 mm. So it is not the thread count: two more 1-thread runs and an instrumented 1-thread replay reproduce the 43. H1 has no cache and agrees at 1, 2 and default threads within 2.9e-13 mm. Inference, not shown: the odd run had another cache assignment (memory layout); that run was not instrumented. Extra control runs beyond the ledger, to answer the thread question: H2 2 x 2 threads, 2 x 1 thread; H1 at 1 and default; replays (dirty_tree true from the then untracked diagnosis script; src and configs unchanged).
**Bug (found by reading the code before the runs, then measured):** pose.py _model_scene keys its cache on (id(tri), shape); pose_eval.py passes m["mesh"].triangles, a new array per instance; the 3 profile lengths share a triangle count (140), brackets differ (20). Replay: 221 of 342 profile views got the wrong mesh. Failures: wrong mesh 43/221, right mesh 0/121, brackets 0/117. The contrast alone overstates it: the 7 failures that remain without ray cast also sit on wrong-mesh views, so the causal evidence is the comparison below.
**Mechanism:** a longer mesh encloses the part's end faces, rays hit its side first and the samples are culled. Target end-face share 13.5% → 0.4%; median 85% of measured end-face points have no end-face target within 1 mm. Views with a measured end face: 35/80 fail on a longer mesh, 0/76 on the right mesh; no measured end face on a longer mesh: 1/50. First Gauss-Newton step from GT at stage 20 mm: small rotations 1.83° with the used mesh vs 0.016° with the own mesh; jumps 3.05° vs 0.031°.
**Fitness:** the 18 of 18 profiles with fitness < 0.9 are all wrong-mesh; at the GT pose, used mesh: fit@5 mm 0.875, 33% of measured points have their nearest sample culled; own mesh: fit 1.000, 1.3%. On the part's own mesh the filters do remove nearest samples (median 1.6% of points on profiles, back-face alone 0.7%, max 2.8%) but no point loses its correspondence (min fit@5 mm 1.000), so they are not the cause. Worst case with the wrong mesh: 69%.
**Conditioning (lambda max/min of the 6x6 normal matrix, centred, rotation scaled by 30 mm):** does not explain the 43. Failures per quartile, low to high: 17/86, 16/85, 8/85, 2/86, the opposite of the 2026-11-04 inference. The top quartile (about 1e30) is exactly singular: no end-face correspondence, so no axial force either.
**The 33 small drifts:** R < 0.1° group 7 (9/0/0, 9/1/0, 15/0/0, 22/0/0, 33/1/3, 34/0/0, 47/1/1): six axial, 15/0/0 is across-axis at R 0.098°. Rest 26 (25 used a longer mesh). H1 cures 25 of the 26 and 1 of the 7; the 10 jumps too. So 36 of 43 go away without the ray cast.
**The 7 that remain in H0 and H1** (lm passes 15/0/0 at 0.404 mm): 9/1/0, 22/0/0, 33/1/3, 34/0/0, 47/1/1 axial 0.49-0.83 mm; 15/0/0, 15/1/3 across 0.36-0.41 mm. All fitness 1.000. Trace: the axial move happens entirely in the first stage (20 mm). Profiles with no measured end-face point: 0 side-to-end matches (n = 131) axial max 0.001 mm; 1-4 matches (n = 6) axial median 0.60, max 0.83 mm. So 1-4 points of 4000-10 000 fix the axial pose. Max H1 MSSD vs mean sample spacing: 60 mm 0.356/0.522, 100 mm 0.673/0.663, 150 mm 0.853/0.804, bracket 0.323/0.329: about one spacing (4 parts, association). 50 000 samples per model makes long parts coarser. The across-axis pair is not traced.
**Not run:** H2 with the cache fixed, denser sampling, anything on dev. So "H2 fixed gives about 7 failures" and "200 000 samples gives about 0.43 mm" are predictions. Why the existing test missed it: it exercises one profile length only.
**Report note:** §6 "what did not work": the sanity gate caught a real bug in AI-written code that dev (n = 40) and 94 unit tests had missed; the user's request to explain fitness on ideal depth pointed to it, while the conditioning inference was wrong.

## 2026-11-05: §5.11 second round: H0, H1, H2, H3 all pass; stopped before the dev selection
User approved steps 1-3. Cache fix ade985f (an entry keeps its array alive; one long-lived triangle array per part; regression test fails on the old code at the visibility check; _model_tree left alone, cKDTree keeps its array alive, my first test of it never failed). Rule pre-declared be3a99c. CAD samples 200 000 and runner 3ad09a2. All runs at 3ad09a2, clean tree, C1, zero offset, test scenes 0-49, master seed 0, data/m5/diag_sanity_fix.
**Result, MSSD < 0.5 mm:** H0, H1, H2, H3 each 459/459; worst 0.427, 0.404, 0.404, 0.404 mm; median 0.011 mm (was 0.033-0.049); no estimate 0. Wall time 39, 96, 81, 178 s (first round 14-70 s). Rule: two or more pass, so the A-45 dev rule is proposed to the user; nothing run on dev.
**Control:** H2 replay at 1 thread, instrumented: 0 of 459 views off their own mesh, 4 cache entries (52 before), same MSSD as plain H2 at 2 threads within 4.1e-13 mm. One replay; it cannot show that the 1-in-7 odd run of the first round can no longer happen, but the code path that allowed it is gone.
**Attribution:** H1 has no ray cast, so 452 → 459 is the sample count alone. H2's 416 → 459 is both changes; cache fix at 50 000 samples was not run. Zero offset cannot separate the four: views differing from H2 by > 0.01 mm: H3 0, H1 1, H0 2.
**My prediction vs result:** predicted worst about 0.43 mm on the 150 mm profile; got 0.309 mm there and 0.404 mm on a bracket. H1 max by part, 50 000 → 200 000 samples: 60 mm 0.356 → 0.314, 100 mm 0.673 → 0.238, 150 mm 0.853 → 0.309, bracket 0.323 → 0.404 mm; bracket p99 0.207 → 0.340 mm while its median goes 0.011 → 0.005 mm. Max / spacing on the bracket goes 0.98 → 2.46, so "about one sample spacing" is not a general bound. Two views drive it: 7/1/4 (0.323 → 0.404 mm, R 0.29°, 760 points) and 20/0/0 (0.07 → 0.37 mm, R 0.53°, 976 points). Not explained; margin to the threshold 0.096 mm (H0 0.073 mm).
**Stale until re-run:** all H2 and H3 numbers on dev, the pilot and the H2 pick. Next step needs approval: dev selection in a new folder. run_eval.py needs a new results folder too: in data/m5/results it would keep the failed sanity file and stop.

## 2026-11-05, evening: M5 closed

Run `scripts/run_m5.sh`, commit 26cd449, clean tree, ended 19:49 CET. Relaunched detached at 17:28 after the session end killed it at about 17:26; it resumed from finished files. Seeds 0–49 (§5.10), 459 instance-views (342 profile, 117 bracket), 1 excluded. Harness H3 (stages 20/10/5 mm, ray-cast visibility, 5 mm / 5° step clamp), 200 000 CAD samples. Sanity on C1 at zero offset: 459/459 < 0.5 mm.

A1 recall@5 mm (10 mm / 10°): C1 0.732 [0.682, 0.779], C2a 0.749 [0.697, 0.799], C2b 0.590 [0.521, 0.657], C3 0.085 [0.054, 0.118], C4 0.386 [0.327, 0.444]. Descriptive: reflections off 0.102, roughness 0.2 0.159, roughness 0.4 0.288, bright matte 0.444.

Fixed sequence, all three reject (McNemar p < 0.05 and CI excludes 0): C1−C3 +0.647 [0.583, 0.708], p 2e-78; C2b−C3 +0.505 [0.429, 0.580], p 7e-59; C3−C4 −0.301 [−0.356, −0.244], p 6e-31. Second bootstrap stream agrees to the third decimal. MDE 7.8–10.8 points on instance-views, 23.7–32.8 on scenes.

Sweep, recall@5 mm at 2 / 5 / 10 / 20 mm: C1 1.000, 0.919, 0.732, 0.667; C2a 0.989, 0.917, 0.749, 0.669; C2b 0.760, 0.708, 0.590, 0.523; C3 0.135, 0.111, 0.085, 0.072; C4 0.516, 0.464, 0.386, 0.316. The ordering C1 ≈ C2a > C2b > C4 > C3 holds at every offset.

Task B brackets, n = 117: C1 0.821, C2a 0.761, C2b 0.615, C3 0.145, C4 0.359. Grasp planned: C1 0.915, C3 0.444, C4 0.718. Profiles 0 everywhere, by geometry (A-33), while the planner proposes grasps on 0.9% of C1 views and 97% of C2b views.

Part pixels, C1 / C2a / C2b / C3 / C4: median |error| 0 / 0.6 / 2.0 / 4.1 / 2.2 mm; invalid 0 / 0 / 0 / 5.2% / 1.8%; C3 correct 53.7%, behind the surface 33.6%.

**Surprise: the §5.8 loose variants never turned the left-right check off.** `C3nolr` matched C3 exactly in the sensor metrics. Tested on OpenCV 5.0.0: `disp12MaxDiff` −1 and 0 are identical to 1 on a synthetic pair, 1000 changes 2 880 pixels, and all 20 `C3nolr` frames on disk equal C3. No primary number is affected. The ranking does not flip under the two filters that were off. Not re-run; the user decides (open item 18).

Checked and harmless: strict and loose recall are equal by cancelling flips (C3 2 up, 2 down; C4 1 up, 1 down); all 98 views differ. C1 median translation error 1.24 mm against axial 0.28 mm on profiles comes from a bimodal axial error. Tray MAE is inflated by pixels past the tray (12 of 100 views, up to the 6553.5 mm ceiling); parts unaffected.

C3 noise redraws, seeds 0–9: 0.143, 0.133, 0.071; 9 and 13 of 98 views change side. C3−C4 stays negative. 33 open items in `docs/M5_OPEN_ITEMS.md`. Nothing pushed.

## 2026-11-06: independent review of M5; §5.8 re-run; noise sensitivity

Review (read-only agent, user's prompt): all STATUS numbers recomputed from the raw files and confirmed; 96 tests passed; result files from 26cd449, clean tree; IR and depth from 73f0305 / 8ccbd95, and the difference touches only the redraw option. Findings new to the docs: distance is a strong moderator (C3 0.32 below 0.7 m, 0.00 at 0.9 m and beyond; C4 0.68 and 0.24; C1 0.62 and 0.77); at 2 mm / 2° every start is already under 5 mm and C3 ends at 0.135, so the ICP limit explains C1's fall, not C3's level; simulated IR differs from real ROBI IR (part median 1.9 vs 21 DN, local SD 23 vs 4.6 DN). M6 not started: no skeleton, README or quick-run.

User decisions: item 18 re-run first, disclose only if it fails (the agent had recommended disclosing); the other four as recommended (A-64, A-65).

§5.8 re-run (commit c44cd7a, clean tree, seeds 0–9, 98 instance-views, master seed 0, `data/m5/results_s58_v2`, about 21 min wall time for the four ICP runs). OpenCV 5.0.0: disp12MaxDiff −1, 0, 1 identical; 127, 128, 1000, 100 000 identical; 4 524 px differ between the groups on scene 0 view 0. `C3nolr1000` differs from C3 in 20 of 20 views. Sanity 98/98. **No flip:** C1−C3 +0.571 → +0.561, C2b−C3 +0.347 → +0.337, C3−C4 −0.214 → −0.214; C3 0.143 → 0.153, C4 0.357 → 0.367; 5 and 3 views change side. All filters off: part invalid 5.3 → 0.0% on C3, correct only 61.3 → 62.4%, MAE 6.57 → 21.61 mm. The filters remove mostly wrong pixels, and ICP tolerates them.

Noise sensitivity (same commit and folder, e_per_dn 1.0 vs 0.087, about 30% of the noise at 21 DN): C3 0.143 → 0.143 (+0.0 points [−4.0, +4.0], 4 views each way); C4 0.357 → 0.408 (+5.1 points [−1.0, +11.1], p 0.27); C4−C3 +21.4 → +26.5 points. **Surprise:** the review agent expected noise could matter for the metal; it does not at this value. Ambient light stays untested.

Report notes: "what did not work" gets the −1 pitfall, found only by checking results, and pinned by a test now. Limitations get distance, ROBI in pixels, simulated IR vs real.

## 2026-11-06, audit against the invitation mail

Read-only audit at f6a2ffe, no code or frozen value changed. Tests: 98 pass. `stats.json` matches STATUS (C1 0.732, C2b 0.590, C3 0.085, C4 0.386; commit 26cd449, clean tree). Not yet existing: PDF, report source, README, quick-run, `.venv` setup script. Surprises: the GitHub repo is private; RGB on the 100 test frames is overexposed (part pixels with all channels ≥ 250: median 36%, max 92%; median grey 242; no task reads RGB, so no result is affected); the Sat 12:00 and Sat 20:00 dates need 11.25 h and 15.25 h against at most 12 h at 6 h/day. Ambient-IR sensitivity and C3 redraws on 50 scenes proposed to the user, not run.
