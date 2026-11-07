# Synthetic RGB-D of aluminium parts with a D415 camera model

This repository generates labelled synthetic RGB-D images of aluminium T-slot profiles and L-brackets in a tray, and simulates how an Intel RealSense D415 would see them. It then runs one experiment: does the camera model change the outcome of CAD-based pose estimation and suction grasping, compared with ideal depth and with a naive noise model?

The camera model renders the left and right infrared images with the projected dot pattern in Cycles, and adds sensor noise. It then runs OpenCV SGBM stereo matching tuned to the D415's geometry. It is not Intel's matcher. Results apply to this ICP and this simulated camera, not to a physical D415.

The report explains the method and the results. This file covers how to run the code.

## Install

Requires Python 3.11. Blender is not needed unless you want to render new scenes.

```bash
git clone <this repository>
cd synthetic-rgbd-manufacturing-perception
scripts/setup.sh
```

`scripts/setup.sh` checks for Python 3.11, creates `.venv` from `requirements.lock.txt` and runs the tests. It takes about 1.5 minutes (50 s to install without pip's cache, 45 s of tests), and `.venv` takes 720 MB.

**Tested only on macOS with Apple Silicon (Apple M2, 8 GB RAM, macOS 27.2). Linux is untested.**

## Quick run

One sample scene, no Blender, about 2 minutes. It computes depth from the stored infrared images, runs pose and suction evaluation at the primary offset, compares with the committed numbers for that scene, and prints `QUICK_RUN_PASS` or `QUICK_RUN_FAIL`.

```bash
.venv/bin/python scripts/quick_run.py --sample <path to sample_scene_seed0.tar.gz>
```

**The sample scene is not published yet.** The archive (6.5 MB, seed 0, chosen without looking at outcomes) is not in git. Once it has a public address, that address goes into `SAMPLE_SCENE_URL` at the top of `scripts/quick_run.py`, and `--sample` can be left out. With the full dataset you can rebuild it with `scripts/make_sample_archive.py`.

Stereo depth must match the committed numbers pixel for pixel, and suction outcomes must match exactly. ICP is compared more loosely, on the median difference and on at most one instance-view changing side of 5 mm, because it is not strictly repeatable on identical depth (see Known limits).

## Expected results

Committed in [`results/`](results/): statistics, sensor metrics, robustness, redraws, the ambient test, the plane gate and the figures, with a manifest of commits and seeds. Primary endpoint: A1 recall at MSSD < 5 mm, starting 10 mm / 10° from the true pose, seeds 0–49, 95% confidence intervals over scenes.

| Condition | A1 recall | 95% CI | Task B, brackets |
|---|---|---|---|
| C1 ideal depth | 0.717 | 0.671–0.761 | 0.771 |
| C2a ideal + noise, 0.08 px | 0.735 | 0.684–0.783 | 0.737 |
| C2b ideal + noise, 0.234 px | 0.561 | 0.498–0.621 | 0.534 |
| C3 metal, stereo camera model | 0.070 | 0.046–0.095 | 0.110 |
| C4 matte, stereo camera model | 0.343 | 0.287–0.400 | 0.381 |

Fixed-sequence test at α 0.05, on 460 instance-views in 50 scenes: C1 − C3 +0.648 (0.596–0.700), C2b − C3 +0.491 (0.425–0.559), C3 − C4 −0.274 (−0.330 to −0.217). All three reject. Two further noise draws of C3 give 0.061 and 0.063.

An earlier run with a 65° field of view is kept in [`results/archive_hfov65/`](results/archive_hfov65/) as a descriptive sensitivity to the focal length. It was seen before this run was defined, and the report discloses this.

## Full pipeline

Rendering needs BlenderProc, which `scripts/setup_blenderproc.sh` installs separately (it also downloads Blender on first use). Always run Blender scripts through `scripts/bproc.sh`.

```bash
scripts/setup_blenderproc.sh
.venv-bproc/bin/blenderproc quickstart --blender-install-path blender   # first use downloads Blender

# Intrinsics: rendered depth of a tilted plane against our K
scripts/bproc.sh scripts/bproc_check_intrinsics.py data/hfov71/intrinsics
.venv/bin/python scripts/check_intrinsics.py data/hfov71/intrinsics

# Planes: gate on the matte plane, without and with noise
scripts/bproc.sh scripts/bproc_ir_plane.py --out data/hfov71/plane
.venv/bin/python scripts/plane_gate.py data/hfov71/plane
.venv/bin/python scripts/anchor_a.py data/hfov71/plane

# Dev scenes, then the whole experiment; resumes from the last finished stage and stops on a stop rule
scripts/render_test.sh data/hfov71/dev 1000 1004
scripts/run_final.sh data/hfov71/test data/hfov71/dev

# Figures and the tracked results (data/m5 is the archived 65-degree run; anything missing is listed in the manifest)
scripts/make_figures.sh data/hfov71/test data/hfov71/dev results/hfov71/robi_zigzag_real.json
.venv/bin/python scripts/collect_results.py data/hfov71 data/m5 --out results
```

Measured on the machine above, one process at a time:

| Job | Time |
|---|---|
| BlenderProc env | 10 s |
| Blender download and first-use setup (`quickstart`), 1.4 GB | 2.5 min |
| Intrinsics check | 13 s |
| Planes: render and both gates | 2 min |
| Dev scenes, 5, all passes (`render_test.sh`) | 16 min |
| Test render, 50 scenes, all passes | 2 h 28 (median 178 s per scene) |
| A1 and Task B on nine conditions, offset sweep, statistics, sensor metrics | 5 h 36 |
| Left-right check off and lower noise, seeds 0–9 | 16 min |
| Two noise redraws of C3, 50 scenes | 58 min |
| Mechanism check and IR appearance | 46 s |
| Ambient test, seeds 0–9: render, match, evaluate | 18 min |
| **`run_final.sh`, everything above from the test render** | **9 h 38** |
| Figures | 1 min |

The test set takes 1.4 GB. The values that depend on image formation were derived on the dev scenes before the test render, with `scripts/derive_dev_exposure.sh`, `scripts/rgb_sweep.sh` and `scripts/ambient_level.py`; they are fixed in `configs/camera_d415_ir.yaml`, so you do not need to run these to reproduce the experiment.

**Renders are not bit-reproducible** (see Known limits), so a new render gives a statistically similar dataset, not the same numbers. The committed numbers come from the dataset rendered at the commit in `results/MANIFEST.json`.

## Seeds

All randomness derives from `(master, scene, view, stream)` through `numpy.random.SeedSequence` (`src/synthrgbd/seeds.py`). Master seed 0, test scenes 0–49, dev scenes 1000–1004 (`configs/default.yaml`). The dot pattern has its own constant seed, 415. Every dataset and result file records its commit.

## Where things are

| Path | What it is |
|---|---|
| `configs/default.yaml` | Protocol parameters, frozen at tag `protocol-v1`; deviations are in `docs/PLAN.md` §5.12 |
| `configs/camera_d415_ir.yaml` | Camera model: projector, dots, IR rendering, exposure, noise, matcher |
| `configs/harness.yaml` | ICP and suction settings |
| `src/synthrgbd/` | Package: parts, projector, stereo, pose, suction, statistics. Tests are in `tests/` |
| `scripts/bproc_render_scene.py`, `bproc_ir_plane.py` | Rendering inside Blender: scenes in BOP format, planes |
| `scripts/stereo_scene.py`, `c2_depth.py` | Depth conditions: stereo from IR images, ideal depth plus noise |
| `scripts/pose_eval.py`, `suction_eval.py`, `run_eval.py` | Task A, Task B, and running them over conditions |
| `scripts/stats_m5.py`, `sensor_metrics.py`, `distance_table.py` | Statistics with the fixed sequence, sensor metrics, recall by distance |
| `scripts/plane_gate.py`, `anchor_a.py` | Gate on the plane without and with noise |
| `scripts/run_m5.sh`, `run_m5_followup.sh`, `run_final.sh`, `check_stop.py` | Experiment, descriptive follow-ups, orchestrator, stop rules |
| `scripts/mechanism_check.py`, `robi_compare.py`, `ir_appearance.py`, `ambient_level.py`, `ambient_summary.py`, `redraw_summary.py`, `icp_repeat_summary.py`, `error_structure_depth.py`, `error_structure_summary.py`, `run_dots_test.sh`, `dots_summary.py`, `brightness_match.py`, `depth_wrap_count.py` | Diagnostics and descriptive comparisons |
| `scripts/fig_*.py`, `make_figures.sh` | Figures |
| `scripts/setup.sh`, `quick_run.py`, `make_sample_archive.py`, `collect_results.py` | Install, quick run, sample scene, tracked results |
| `report/` | The report: LaTeX source, PDF, and `check_numbers.py`, which checks the printed numbers against `results/` |
| `docs/` | Plan and frozen protocol, assumptions register, sources, working diary, AI-use log |

## Known limits

- **Not a physical D415.** The matcher is OpenCV SGBM, not Intel's chip. The metal is a material model with an assumed roughness, and C3's level depends on it: 0.070 at roughness 0.15, 0.139 at 0.2, 0.276 at 0.4 (`results/hfov71/stats.json`).
- **The dot density is assumed.** The D415's pattern is not published. The primary run uses 30 000 dots, 3.76% of lit pixels, inside the band in Intel's guidance. One descriptive test on seeds 0–9 with 10 000 dots, a new render, gives 0.041 on metal and 0.184 on matte, against 0.102 and 0.265 on the same seeds (`results/hfov71/dots.json`, A-74 in `docs/ASSUMPTIONS.md`). Denser patterns are untested.
- **The stereo search range and the datasheet's minimum range disagree at this focal length.** With a 126 px search the depth transition is at 392 mm, against the datasheet's 450 mm. No scene pixel is that close.
- **The imager is wider than the projector** (71° against 67°), so the image has unlit margins. The matcher fills narrow unlit strips with depth.
- **Depth wraps around beyond 6.55 m.** `scripts/stereo_scene.py` stores depth as uint16 at 0.1 mm, so a match beyond 6.5535 m (disparity below 7.5 px) wraps to a false value, as low as 26 mm. On the test scenes this is 0.09% of image pixels and none of the part pixels in C3 and C4, so recall and part metrics do not change. With all matcher filters off it is 0.04% of part pixels on seeds 0–9 (`results/hfov71/depth_wrap.json`). Not fixed: a fix changes pixels outside the parts and the quick run's expected hashes.
- **Zero ambient light in the primary run.** The simulated metal is far darker than the real camera on ROBI: 5 DN against 21 DN. `results/hfov71/ambient.json` holds one descriptive test with ambient light, at an unsourced level and spectrum.
- **Renders are not bit-reproducible.** Stereo depth repeats exactly from stored IR images, but the IR images differ slightly between renders.
- **ICP is not strictly repeatable on identical depth.** On unstable views, already failed, repeated runs differ by tens of millimetres. A full repeat of C1, C2b, C3 and C4 on the 50 test scenes moves no view across 5 mm, so recall does not change (`results/hfov71/icp_repeat.json`, A-72 in `docs/ASSUMPTIONS.md`).
- **The sample count, the harness and the focal length were changed after earlier test results had been seen.** All of this is logged in `docs/PLAN.md` §5.12 and disclosed in the report.
