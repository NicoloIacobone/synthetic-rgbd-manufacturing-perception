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
