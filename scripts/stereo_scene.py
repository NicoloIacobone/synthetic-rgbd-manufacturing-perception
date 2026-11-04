"""Stereo depth for a rendered scene (D13): IR pairs (scripts/bproc_render_scene.py --ir) -> SGBM -> depth.

Usage: .venv/bin/python scripts/stereo_scene.py <out_root> <scene_seed> [--sheet <png>]

For every view and IR pass (<scene>/ir/<im_id>_<pass>.npz) writes <scene>/depth_stereo_<pass>/<im_id>.png
(uint16 z-depth, BOP depth_scale 0.1 mm, invalid = 0, D415 left-imager pixels = the BOP camera) and
<scene>/stereo_meta.json with per-frame timings and quick sensor numbers against the ideal depth
(informative only; the M5 sensor metrics are computed separately). "metalproxy" uses the M2
placeholder material and exists only for the A-39 timing at M3.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.geometry import disparity_to_depth  # noqa: E402
from synthrgbd.seeds import rng  # noqa: E402
from synthrgbd.stereo import (auto_exposure_gain, depth_from_ir, expose_to_uint8, exposed_pair_uint8,  # noqa: E402
                              exposure_roi_x0, make_sgbm, match_extended)

DEPTH_SCALE_MM = 0.1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_root", type=Path)
    ap.add_argument("scene_seed", type=int)
    ap.add_argument("--ir-config", type=Path, default=REPO / "configs" / "camera_d415_ir.yaml")
    ap.add_argument("--sheet", type=Path)
    args = ap.parse_args()
    cam = load_config()["camera"]
    ir = load_config(args.ir_config)
    scene = args.out_root / "synthrgbd" / "train_pbr" / f"{args.scene_seed:06d}"
    cams = json.loads((scene / "scene_camera.json").read_text())
    seg_index = json.loads((scene / "segmap" / "index.json").read_text())
    cfg_all = load_config()
    sgbm = make_sgbm(ir["sgbm"])
    pad, gain = ir["ir_render"]["pad_px"], float(ir["exposure"]["gain"])
    auto = ir["exposure"].get("mode") == "auto"
    meta = {"commit": subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            "ir_config": str(args.ir_config.relative_to(REPO)), "exposure": ir["exposure"],
            "sensor_noise": ir.get("sensor_noise"), "frames": []}
    sheet = []
    for im_id in sorted(cams, key=int):
        K = np.array(cams[im_id]["cam_K"]).reshape(3, 3)
        gt = cv2.imread(str(scene / "depth" / f"{int(im_id):06d}.png"), cv2.IMREAD_UNCHANGED) * DEPTH_SCALE_MM * 1e-3
        seg = np.load(scene / "segmap" / f"{int(im_id):06d}.npz")["instance"]
        parts = np.isin(seg, [i for i in seg_index[im_id] if i >= 0])
        if auto:   # A-42: gain from the C3 (metal) left image, shared by C4 and the right image; A-12 noise, shared draws
            Lm = np.load(scene / "ir" / f"{int(im_id):06d}_metal.npz")["left"].astype(np.float32)
            g_frame = auto_exposure_gain(Lm[:, pad:], exposure_roi_x0(K[0, 0], cam["baseline_m"], cam["min_z_m"]),
                                         float(ir["exposure"]["setpoint_dn"]))
            r = rng(cfg_all["seeds"]["master"], args.scene_seed, int(im_id), "ir_noise")
            zl, zr = r.standard_normal(Lm.shape), r.standard_normal(Lm.shape)
        for name in ("metal", "metalproxy", "matte"):
            f = scene / "ir" / f"{int(im_id):06d}_{name}.npz"
            if not f.exists():
                continue
            t = time.perf_counter()
            d = np.load(f)
            L, R = d["left"].astype(np.float32), d["right"].astype(np.float32)
            t_load = time.perf_counter() - t
            t = time.perf_counter()
            if auto:
                l8, r8 = exposed_pair_uint8(L, R, g_frame, ir.get("sensor_noise"), zl, zr)
                disp = match_extended(l8, r8, pad, sgbm, cam["disparity_search_px"])
                z = disparity_to_depth(disp, K[0, 0], cam["baseline_m"], cam["disparity_search_px"])
                dn = l8[:, pad:]
            else:
                z, _ = depth_from_ir(L, R, gain, pad, sgbm, K[0, 0], cam["baseline_m"], cam["disparity_search_px"])
                dn = expose_to_uint8(L[:, pad:], gain)
            t_match = time.perf_counter() - t
            t = time.perf_counter()
            out = scene / f"depth_stereo_{name}"
            out.mkdir(exist_ok=True)
            cv2.imwrite(str(out / f"{int(im_id):06d}.png"), np.round(z * 1e3 / DEPTH_SCALE_MM).astype(np.uint16))
            t_write = time.perf_counter() - t
            v = (z > 0) & (gt > 0)
            err = np.abs(z - gt)
            meta["frames"].append({
                "im_id": int(im_id), "pass": name, "t_load_s": t_load, "t_sgbm_s": t_match, "t_write_s": t_write,
                "invalid_frac_all": float(1 - (z > 0).mean()), "invalid_frac_parts": float(1 - (z[parts] > 0).mean()),
                "mae_mm_parts": float(1e3 * err[v & parts].mean()) if (v & parts).any() else None,
                "frac_err_gt_5mm_parts": float((err[v & parts] > 5e-3).mean()) if (v & parts).any() else None,
                "dn_mean": float(dn.mean()), "dn_saturated_frac": float((dn == 255).mean()),
                "gain": float(g_frame) if auto else gain,
                "median_err_mm_parts": float(1e3 * np.median((z - gt)[v & parts])) if (v & parts).any() else None})
            if name == "matte":
                sheet.append((dn, gt, z, parts))
    (scene / "stereo_meta.json").write_text(json.dumps(meta, indent=1))
    for fr in meta["frames"]:
        print("STEREO", json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in fr.items()}))
    if args.sheet and sheet:
        contact_sheet(args.sheet, sheet)


def contact_sheet(path, rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(len(rows), 4, figsize=(16, 2.6 * len(rows)), squeeze=False)
    for r, (dn, gt, z, parts) in enumerate(rows):
        lo, hi = np.percentile(gt[gt > 0], [1, 99])
        ax[r, 0].imshow(dn, cmap="gray", vmin=0, vmax=255)
        ax[r, 0].set_title("left IR (8-bit), matte")
        ax[r, 1].imshow(np.where(gt > 0, gt, np.nan), vmin=lo, vmax=hi)
        ax[r, 1].set_title("ideal depth")
        ax[r, 2].imshow(np.where(z > 0, z, np.nan), vmin=lo, vmax=hi)
        ax[r, 2].set_title("stereo depth (invalid = white)")
        e = np.where((z > 0) & (gt > 0), 1e3 * (z - gt), np.nan)
        im = ax[r, 3].imshow(e, cmap="coolwarm", vmin=-10, vmax=10)
        ax[r, 3].contour(parts, levels=[0.5], colors="k", linewidths=0.4)
        ax[r, 3].set_title("stereo - ideal (mm), parts outlined")
        fig.colorbar(im, ax=ax[r, 3], fraction=0.03)
        for a in ax[r]:
            a.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=70)


if __name__ == "__main__":
    main()
