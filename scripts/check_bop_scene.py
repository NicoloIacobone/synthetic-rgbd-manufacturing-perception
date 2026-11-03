"""End-to-end consistency check of one rendered BOP scene (.venv).

Usage: .venv/bin/python scripts/check_bop_scene.py <out_root> <scene_seed> [--sheet out.png]

For every frame and annotated instance, the depth pixels inside mask_visib are back-projected with
the K in scene_camera.json, mapped into the model frame with the inverse of the scene_gt pose, and
their exact distance to the CAD surface is measured. If K, depth scale, pose convention, masks and
model frames are all consistent, the distances are a fraction of a millimetre (at the silhouette,
mask pixels may see the background: reported as a separate fraction above 1 mm). Also checks
K against A-28 and the A-16 Min-Z condition. Writes bop_check.json next to the scene.
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.geometry import intrinsics_from_hfov  # noqa: E402
from synthrgbd.meshdist import surface_distance  # noqa: E402
from synthrgbd.parts import PART_CATALOGUE, make_part  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("out_root", type=Path)
ap.add_argument("scene_seed", type=int)
ap.add_argument("--sheet", type=Path, help="write a downscaled RGB/depth/mask contact sheet")
ap.add_argument("--max-points", type=int, default=3000, help="per instance, for speed")
args = ap.parse_args()

cfg = load_config()
scene = args.out_root / "synthrgbd" / "train_pbr" / f"{args.scene_seed:06d}"
gt = json.loads((scene / "scene_gt.json").read_text())
cams = json.loads((scene / "scene_camera.json").read_text())
gt_info = json.loads((scene / "scene_gt_info.json").read_text()) if (scene / "scene_gt_info.json").exists() else None
K_a28 = intrinsics_from_hfov(cfg["camera"]["width"], cfg["camera"]["height"], cfg["camera"]["hfov_deg"])
tris = {i: make_part(spec).triangles for i, (_, spec) in PART_CATALOGUE.items()}
rng = np.random.default_rng(0)

report = {"scene_seed": args.scene_seed, "frames": []}
tiles = []
for im_id in sorted(gt, key=int):
    cam = cams[im_id]
    K = np.array(cam["cam_K"]).reshape(3, 3)
    depth = cv2.imread(str(scene / "depth" / f"{int(im_id):06d}.png"), cv2.IMREAD_UNCHANGED)
    depth_mm = depth.astype(np.float64) * cam["depth_scale"]
    frame = {"im_id": int(im_id), "K_max_abs_diff_vs_A28": float(np.abs(K - K_a28).max()),
             "depth_dtype": str(depth.dtype), "instances": []}
    union = np.zeros(depth.shape, bool)
    for k, inst in enumerate(gt[im_id]):
        R = np.array(inst["cam_R_m2c"]).reshape(3, 3)
        t = np.array(inst["cam_t_m2c"], dtype=np.float64)
        mpath = scene / "mask_visib" / f"{int(im_id):06d}_{k:06d}.png"
        mask = cv2.imread(str(mpath), cv2.IMREAD_GRAYSCALE) > 0 if mpath.exists() else None
        entry = {"obj_id": inst["obj_id"], "t_mm": t.tolist()}
        if gt_info is not None:
            entry["visib_fract"] = gt_info[im_id][k]["visib_fract"]
        if mask is not None and mask.any():
            union |= mask
            v, u = np.nonzero(mask & (depth > 0))
            if len(u) > args.max_points:
                sel = rng.choice(len(u), args.max_points, replace=False)
                u, v = u[sel], v[sel]
            z = depth_mm[v, u]
            X = np.stack([(u - K[0, 2]) / K[0, 0] * z, (v - K[1, 2]) / K[1, 1] * z, z], -1)
            Xm = (X - t) @ R                                   # R^T (X - t), row vectors
            d = surface_distance(tris[inst["obj_id"]], Xm)
            entry.update({"mask_px": int(mask.sum()), "dist_median_mm": float(np.median(d)),
                          "dist_p95_mm": float(np.percentile(d, 95)),
                          "frac_over_1mm": float((d > 1.0).mean())})
        frame["instances"].append(entry)
    part_depth = depth_mm[union & (depth > 0)]
    frame["min_part_depth_mm"] = float(part_depth.min()) if part_depth.size else None
    frame["min_z_ok_A16"] = bool(part_depth.size and part_depth.min() > 1e3 * cfg["camera"]["min_z_m"])
    report["frames"].append(frame)

    if args.sheet:
        rgb = cv2.imread(str(scene / "rgb" / f"{int(im_id):06d}.png"))
        valid = depth > 0
        dn = np.zeros(depth.shape, np.uint8)
        lo, hi = np.percentile(depth_mm[valid], [1, 99])
        dn[valid] = np.clip(255 * (depth_mm[valid] - lo) / (hi - lo), 0, 255).astype(np.uint8)
        dc = cv2.applyColorMap(dn, cv2.COLORMAP_TURBO)
        ov = rgb.copy()
        for k in range(len(gt[im_id])):
            mpath = scene / "mask_visib" / f"{int(im_id):06d}_{k:06d}.png"
            if mpath.exists():
                m = cv2.imread(str(mpath), cv2.IMREAD_GRAYSCALE) > 0
                col = np.array(cv2.applyColorMap(np.uint8([[40 * k + 30]]), cv2.COLORMAP_HSV)[0, 0], float)
                ov[m] = (0.5 * ov[m] + 0.5 * col).astype(np.uint8)
        row = np.hstack([cv2.resize(x, (427, 240), interpolation=cv2.INTER_AREA) for x in (rgb, dc, ov)])
        tiles.append(row)

all_inst = [i for f in report["frames"] for i in f["instances"] if "dist_median_mm" in i]
report["summary"] = {
    "n_frames": len(report["frames"]), "n_instances_with_mask": len(all_inst),
    "worst_median_dist_mm": max(i["dist_median_mm"] for i in all_inst) if all_inst else None,
    "worst_p95_dist_mm": max(i["dist_p95_mm"] for i in all_inst) if all_inst else None,
    "worst_frac_over_1mm": max(i["frac_over_1mm"] for i in all_inst) if all_inst else None,
    "K_max_abs_diff_vs_A28": max(f["K_max_abs_diff_vs_A28"] for f in report["frames"]),
    "min_z_ok_A16": all(f["min_z_ok_A16"] for f in report["frames"]),
}
(scene / "bop_check.json").write_text(json.dumps(report, indent=1))
print(json.dumps(report["summary"], indent=1))
if args.sheet:
    cv2.imwrite(str(args.sheet), np.vstack(tiles))
    print("sheet:", args.sheet)
