"""Report figure for the C3 mechanism check (A-54): left IR, C3 depth error and metal-part masks, for two renders.

Usage: .venv/bin/python scripts/fig_mechanism.py <root_a> <label_a> <root_b> <label_b> <scene> <view> --out <png> [--pass-a <pass>] [--pass-b <pass>]
       scene and view -1 -1: the dev view with the most part pixels (seeds 1000-1004)

Two renders or two passes of one render, e.g. the final dev render with --pass-a nogloss (reflections off) and the default metal.

The view is chosen by a rule that does not look at the outcome: the dev view with the most part pixels. Each row
reproduces the 8-bit SGBM input (auto exposure, shared noise draws). Same display scales in both rows.
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
sys.path.insert(0, str(REPO / "scripts"))
from mechanism_check import build_scenes, cast, pixel_rays  # noqa: E402
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.seeds import rng  # noqa: E402
from synthrgbd.stereo import auto_exposure_gain, exposed_pair_uint8, exposure_roi_x0  # noqa: E402

ERR_MM = 20.0
GREY, BLUE = "#9b9b9b", "#2a6fb0"     # mask classes; invalid depth is drawn black, non-part pixels stay white


def most_part_pixels(root):
    best = (-1, None, None)
    for seed in range(1000, 1005):
        sc = root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
        gts = json.loads((sc / "scene_gt.json").read_text())
        for im in sorted(gts, key=int):
            n = np.any([cv2.imread(str(sc / "mask_visib" / f"{int(im):06d}_{k:06d}.png"), 0) > 0 for k in range(len(gts[im]))], axis=0).sum()
            if n > best[0]:
                best = (int(n), seed, int(im))
    return best[1], best[2]


def load_row(root, seed, im, cfg, ir, pass_name="metal"):
    cam, sn = cfg["camera"], ir["sensor_noise"]
    pad = ir["ir_render"]["pad_px"]
    sc = root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
    f = f"{im:06d}"
    K = np.array(json.loads((sc / "scene_camera.json").read_text())[str(im)]["cam_K"]).reshape(3, 3)
    d = np.load(sc / "ir" / f"{f}_{pass_name}.npz")
    L, R = d["left"].astype(np.float32), d["right"].astype(np.float32)
    r = rng(cfg["seeds"]["master"], seed, im, "ir_noise")
    zl, zr = r.standard_normal(L.shape), r.standard_normal(L.shape)
    g = auto_exposure_gain(L[:, pad:], exposure_roi_x0(K[0, 0], cam["baseline_m"], cam["min_z_m"]), float(ir["exposure"]["setpoint_dn"]))
    l8, _ = exposed_pair_uint8(L, R, g, sn, zl, zr)
    z = cv2.imread(str(sc / f"depth_stereo_{pass_name}" / f"{f}.png"), cv2.IMREAD_UNCHANGED).astype(np.float64) * 0.1
    z_gt = cv2.imread(str(sc / "depth" / f"{f}.png"), cv2.IMREAD_UNCHANGED).astype(np.float64) * 0.1
    return l8[:, pad:], z, z_gt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root_a", type=Path)
    ap.add_argument("label_a")
    ap.add_argument("root_b", type=Path)
    ap.add_argument("label_b")
    ap.add_argument("scene", type=int)
    ap.add_argument("view", type=int)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pass-a", default="metal")
    ap.add_argument("--pass-b", default="metal")
    args = ap.parse_args()
    if args.scene < 0:
        args.scene, args.view = most_part_pixels(args.root_a)
        print("view with the most part pixels:", args.scene, args.view)
    cfg, ir = load_config(), load_config(REPO / "configs" / "camera_d415_ir.yaml")
    W, H = cfg["camera"]["width"], cfg["camera"]["height"]
    sc = args.root_a / "synthrgbd" / "train_pbr" / f"{args.scene:06d}"
    gt = json.loads((sc / "scene_gt.json").read_text())[str(args.view)]
    cc = json.loads((sc / "scene_camera.json").read_text())[str(args.view)]
    K = np.array(cc["cam_K"]).reshape(3, 3)
    masks = [cv2.imread(str(sc / "mask_visib" / f"{args.view:06d}_{k:06d}.png"), 0) > 0 for k in range(len(gt))]
    parts = np.any(masks, axis=0)

    # Does the mirror ray of each pixel see the scene? (first-order, planar faces)
    full, _ = build_scenes(gt, np.array(cc["cam_R_w2c"]).reshape(3, 3), np.array(cc["cam_t_w2c"], float))
    d = pixel_rays(K, W, H)
    ans = cast(full, np.zeros(3), d)
    n = ans["primitive_normals"].numpy().astype(np.float64)
    n[(n * d).sum(1) > 0] *= -1
    p = d * ans["t_hit"].numpy().astype(np.float64)[:, None]
    m = d - 2 * (d * n).sum(1, keepdims=True) * n
    import open3d as o3d
    hit = full.cast_rays(o3d.core.Tensor(np.hstack([p + 0.05 * n, m]).astype(np.float32)))["t_hit"].numpy()
    sees = np.isfinite(hit).reshape(H, W)

    ys, xs = np.nonzero(parts)
    m_px = 30
    y0, y1, x0, x1 = max(ys.min() - m_px, 0), min(ys.max() + m_px, H), max(xs.min() - m_px, 0), min(xs.max() + m_px, W)
    aspect = (y1 - y0) / (x1 - x0)
    fig, ax = plt.subplots(2, 3, figsize=(10.5, 2 * 3.05 * aspect + 0.9), constrained_layout=True)
    rows = [(args.root_a, args.label_a, args.pass_a), (args.root_b, args.label_b, args.pass_b)]
    for r, (root, label, pass_name) in enumerate(rows):
        dn, z, z_gt = load_row(root, args.scene, args.view, cfg, ir, pass_name)
        ax[r, 0].imshow(np.sqrt(np.clip(dn / 255.0, 0, 1)), cmap="gray", vmin=0, vmax=1)
        ax[r, 0].set_ylabel(label, fontsize=11)
        err = np.where(parts & (z > 0), z - z_gt, np.nan)
        im = ax[r, 1].imshow(np.where(parts & (z == 0), 0.0, np.nan), cmap="gray", vmin=0, vmax=1)  # invalid = black
        im = ax[r, 1].imshow(err, cmap="coolwarm", vmin=-ERR_MM, vmax=ERR_MM)
        c = fig.colorbar(im, ax=ax[r, 1], fraction=0.045, pad=0.02)
        c.set_label("z − z_GT (mm)", fontsize=9)
        lab = np.full((H, W, 3), 1.0)
        lab[parts & ~sees] = matplotlib.colors.to_rgb(GREY)
        lab[parts & sees] = matplotlib.colors.to_rgb(BLUE)
        ax[r, 2].imshow(lab)
        for a in ax[r]:
            a.contour(parts, levels=[0.5], colors="k", linewidths=0.5)
            a.set_xlim(x0, x1)
            a.set_ylim(y1, y0)
            a.set_xticks([])
            a.set_yticks([])
            for s in a.spines.values():
                s.set_visible(False)
    ax[0, 0].set_title("left IR, matcher input (√DN)", fontsize=10)
    ax[0, 1].set_title("depth error (black = invalid)", fontsize=10)
    ax[0, 2].set_title("metal-part masks", fontsize=10)
    ax[1, 2].legend(handles=[Patch(color=GREY, label="mirror ray sees nothing"), Patch(color=BLUE, label="mirror ray sees the scene")],
                    loc="lower center", bbox_to_anchor=(0.5, -0.14), ncols=2, frameon=False, fontsize=9)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150)
    print(args.out)


if __name__ == "__main__":
    main()
