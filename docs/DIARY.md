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
