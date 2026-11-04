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
