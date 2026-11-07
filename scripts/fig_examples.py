"""Report figure with one labelled example frame: RGB, ideal depth, C3 depth, C4 depth, instance masks and a pose overlay.

Usage: .venv/bin/python scripts/fig_examples.py <dataset_root> <results_dir> --out <png>

The scene is chosen without looking at outcomes (ledger "Figure scenes"): the lowest test seed with at least one profile and one
bracket in scene_gt.json, view 0. The overlay re-runs C3 ICP for that view from the stored depth with the seeded offsets, since the result files
do not store the estimated pose. ICP is not strictly repeatable on identical depth (A-72), so it prints the MSSD against the stored one per instance.
Displays are cropped to the parts.
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.conditions import DEPTH_SCALE_MM  # noqa: E402
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.mssd import mssd  # noqa: E402
from synthrgbd.parts import PART_CATALOGUE, ProfileSpec  # noqa: E402
from synthrgbd.pose import IcpParams, apply_offset, backproject, draw_offset_directions, erode_mask, icp_refine, load_part_models  # noqa: E402
from synthrgbd.seeds import rng  # noqa: E402

INK, MUTED = "#0b0b0b", "#52514e"
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
GT_COL, EST_COL, INVALID = "#2a78d6", "#eda100", "#eb6834"
MARGIN_PX = 40


def choose_scene(root, first=0, last=49):
    is_profile = {i: isinstance(spec, ProfileSpec) for i, (_, spec) in PART_CATALOGUE.items()}
    for seed in range(first, last + 1):
        gt = json.loads((root / "synthrgbd" / "train_pbr" / f"{seed:06d}" / "scene_gt.json").read_text())["0"]
        kinds = {is_profile[g["obj_id"]] for g in gt}
        if kinds == {True, False}:
            return seed
    raise SystemExit("no scene with both part types")


def project(pts, T, K):
    p = pts @ T[:3, :3].T + T[:3, 3]
    return K[0, 0] * p[:, 0] / p[:, 2] + K[0, 2], K[1, 1] * p[:, 1] / p[:, 2] + K[1, 2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("results", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg, hcfg = load_config(), load_config(REPO / "configs" / "harness.yaml")
    seed, im = choose_scene(args.root), 0
    sc = args.root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
    f = f"{im:06d}"
    gt = json.loads((sc / "scene_gt.json").read_text())[str(im)]
    info = json.loads((sc / "scene_gt_info.json").read_text())[str(im)]
    K = np.array(json.loads((sc / "scene_camera.json").read_text())[str(im)]["cam_K"]).reshape(3, 3)
    rgb = cv2.cvtColor(cv2.imread(str(sc / "rgb" / f"{f}.png")), cv2.COLOR_BGR2RGB)
    read = lambda folder: cv2.imread(str(sc / folder / f"{f}.png"), cv2.IMREAD_UNCHANGED).astype(np.float64) * DEPTH_SCALE_MM   # noqa: E731
    z1, z3, z4 = read("depth"), read("depth_stereo_metal"), read("depth_stereo_matte")
    masks = [cv2.imread(str(sc / "mask_visib" / f"{f}_{k:06d}.png"), 0) > 0 for k in range(len(gt))]
    parts = np.any(masks, axis=0)
    ys, xs = np.nonzero(parts)
    H, W = parts.shape
    y0, y1, x0, x1 = max(ys.min() - MARGIN_PX, 0), min(ys.max() + MARGIN_PX, H), max(xs.min() - MARGIN_PX, 0), min(xs.max() + MARGIN_PX, W)

    # C3 ICP on this view, exactly as scripts/pose_eval.py at 10 mm / 10 deg, to get the estimated poses.
    p = IcpParams.from_cfg(hcfg["icp"])
    models = load_part_models(hcfg["model_sampling"]["points_per_model"], hcfg["model_sampling"]["seed"])
    stored = {(r["scene"], r["im_id"], r["gt_id"]): r.get("mssd_mm") for r in map(json.loads, (args.results / "A_C3_10.jsonl").read_text().splitlines()[1:])}
    dirs = draw_offset_directions(rng(cfg["seeds"]["master"], seed, im, "init_offset"), len(gt))
    overlays = []
    for k, (g, gi) in enumerate(zip(gt, info)):
        if gi["visib_fract"] < hcfg["instances"]["min_visib_fract"]:
            continue
        m = models[g["obj_id"]]
        T_gt = np.eye(4)
        T_gt[:3, :3], T_gt[:3, 3] = np.array(g["cam_R_m2c"]).reshape(3, 3), g["cam_t_m2c"]
        T0 = apply_offset(T_gt, dirs[k, 0], dirs[k, 1], 10.0, 10.0, m["centre"])
        pts = backproject(z3, erode_mask(masks[k], p.mask_erosion_px), K)
        T_est, _ = icp_refine(pts, m["pts"], m["nrm"], T0, p, m["tri"])
        if T_est is not None:
            print(f"instance {k}: MSSD {mssd(T_est, T_gt, m['verts'], m['syms']):.3f} mm here, {stored[(seed, im, k)]:.3f} mm in the run")
        overlays.append((m["pts"][::60], T_gt, T_est))

    aspect = (y1 - y0) / (x1 - x0)
    # One row at full text width in the report: fixed grid, so all six panels align; a thin row below holds the colour bar and the legend.
    fig = plt.figure(figsize=(7.0, 1.13 * aspect + 0.62))
    gs = fig.add_gridspec(2, 6, height_ratios=[1.13 * aspect, 0.09], left=0.004, right=0.996, top=0.945, bottom=0.135, wspace=0.05, hspace=0.04)
    ax = np.array([fig.add_subplot(gs[0, k]) for k in range(6)])
    show = lambda a, img, **kw: a.imshow(img, aspect="auto", **kw)   # noqa: E731
    title = lambda a, text: a.set_title(text, fontsize=7.5, color=INK, loc="left", pad=2)   # noqa: E731
    show(ax[0], rgb)
    title(ax[0], "RGB")
    lo, hi = np.percentile(z1[y0:y1, x0:x1][z1[y0:y1, x0:x1] > 0], [1, 99])
    cmap = plt.get_cmap("Blues_r").copy()
    cmap.set_bad(INVALID)
    for a, z, name in ((ax[1], z1, "ideal depth, C1"), (ax[2], z3, "stereo, metal, C3"), (ax[3], z4, "stereo, matte, C4")):
        im_ = show(a, np.where(z > 0, z, np.nan), cmap=cmap, vmin=lo, vmax=hi)
        title(a, name)
    cb = fig.colorbar(im_, cax=fig.add_subplot(gs[1, 1:4]), orientation="horizontal")
    cb.set_label("z (mm); orange = invalid", fontsize=7, color=MUTED, labelpad=1)
    cb.ax.tick_params(labelsize=6.5, length=2, pad=1)
    lab = np.full((H, W, 3), 1.0)
    for k, m_ in enumerate(masks):
        lab[m_] = matplotlib.colors.to_rgb(SLOTS[k % len(SLOTS)])
    show(ax[4], lab)
    title(ax[4], "instance masks")
    show(ax[5], cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), cmap="gray", vmin=0, vmax=255, alpha=0.55)
    for pts, T_gt, T_est in overlays:
        u, v = project(pts, T_gt, K)
        ax[5].scatter(u, v, s=0.25, color=GT_COL, linewidths=0)
        if T_est is not None:
            u, v = project(pts, T_est, K)
            ax[5].scatter(u, v, s=0.25, color=EST_COL, linewidths=0)
    title(ax[5], "poses, ICP on C3")
    leg = fig.add_subplot(gs[1, 4:6])
    leg.axis("off")
    leg.legend(handles=[Patch(color=GT_COL, label="true pose"), Patch(color=EST_COL, label="estimate on C3")], frameon=False, fontsize=7, ncols=2, loc="center right", labelcolor=INK,
               handlelength=1, columnspacing=0.8, handletextpad=0.3, borderaxespad=0)
    for a in ax.ravel():
        a.set_xlim(x0, x1)
        a.set_ylim(y1, y0)
        a.set_xticks([])
        a.set_yticks([])
        for s in a.spines.values():
            s.set_visible(False)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=300, facecolor="white")
    print(args.out, "scene", seed, "view", im)


if __name__ == "__main__":
    main()
