"""Real D415 depth on metal vs ground truth, ROBI [S-05] (A-55). Time-boxed comparison, not an endpoint.

Usage: .venv/bin/python -I scripts/robi_compare.py <subset_dir> <cad_dir> <cam_dir> <object> --out <json> [--overlay <png>]

Ground truth at the D415 left-imager pixels comes from ray-casting the CAD model at every annotated pose (GT_world2obj.json,
camera pose from the per-view JSON), as on our own scenes. On visible object pixels (no erosion), three things are measured:
- D415: the camera's own depth (RealSense/Depth, depth_unit from the toolkit's camera file);
- SGBM: our strict matcher, unchanged, on the real stereo pair (RealSense/StereoPattern). The stored pair has disparity
  f B / z - disparity_shift (measured -77.9 px against the D415 depth, as the toolkit's formula says), so 78 px is added
  back after matching; no noise or exposure model, these are real images;
- IR appearance: median DN and 7 x 7 local SD on object vs other pixels of the left image.
Errors are z - z_GT in mm and d - d_GT in px, classes as in A-58 without an upper bound for "behind" (no bin model).
The bin is not modelled, so "towards the background" can only be read as "behind the surface".
"""

import argparse
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import open3d as o3d
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.stereo import make_sgbm  # noqa: E402

TOL_MM = 5.0
QUANTILES = (5, 25, 50, 75, 95)


def local_sd(img, w=7):
    d = img.astype(np.float32)
    m = cv2.boxFilter(d, -1, (w, w), borderType=cv2.BORDER_REFLECT)
    m2 = cv2.boxFilter(d * d, -1, (w, w), borderType=cv2.BORDER_REFLECT)
    return np.sqrt(np.maximum(m2 - m * m, 0))


def summarise(err_mm, err_px, n_mask, z_gt_vals=None):
    out = {"n_px": int(n_mask), "invalid_frac": 1 - len(err_mm) / max(n_mask, 1)}
    if len(err_mm):
        out.update(mae_mm=float(np.abs(err_mm).mean()), median_signed_mm=float(np.median(err_mm)), median_abs_mm=float(np.median(np.abs(err_mm))),
                   frac_gt_5mm=float((np.abs(err_mm) > TOL_MM).mean()),
                   quantiles_mm={str(q): float(np.percentile(err_mm, q)) for q in QUANTILES},
                   quantiles_px={str(q): float(np.percentile(err_px, q)) for q in QUANTILES},
                   classes={"correct": float((np.abs(err_mm) <= TOL_MM).sum() / n_mask), "behind": float((err_mm > TOL_MM).sum() / n_mask),
                            "in_front": float((err_mm < -TOL_MM).sum() / n_mask), "invalid": 1 - len(err_mm) / max(n_mask, 1)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subset", type=Path)
    ap.add_argument("cad", type=Path)
    ap.add_argument("cam", type=Path)
    ap.add_argument("object")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--overlay", type=Path)
    args = ap.parse_args()
    cam = yaml.safe_load((args.cam / "RealSense_DEPTH.yml").read_text())
    fx, fy, cx, cy, W, H = cam["fx"], cam["fy"], cam["cx"], cam["cy"], cam["width"], cam["height"]
    unit, B, shift = cam["depth_unit"], cam["baseline"], cam["disparity_shift"]
    mesh = o3d.io.read_triangle_mesh(str(args.cad / f"{args.object}.stl"))
    verts, tris = np.asarray(mesh.vertices), np.asarray(mesh.triangles)
    extent = (verts.max(0) - verts.min(0)).tolist()
    ir = load_config(REPO / "configs" / "camera_d415_ir.yaml")
    sgbm = make_sgbm(ir["sgbm"])
    max_d = load_config()["camera"]["disparity_search_px"]
    u, v = np.meshgrid(np.arange(W), np.arange(H))
    rays = np.stack([(u - cx) / fx, (v - cy) / fy, np.ones(u.shape)], -1).reshape(-1, 3)
    rays /= np.linalg.norm(rays, axis=1, keepdims=True)
    zfac = rays[:, 2].reshape(H, W)
    coll = {k: {"mm": [], "px": [], "n": 0} for k in ("d415", "sgbm")}
    zvals, ir_rows, per_view = [], [], []
    scenes = sorted(p for p in (args.subset / args.object).glob("Scene_*") if (p / "RealSense" / "Depth").is_dir())
    overlay = None
    for sc in scenes:
        gt = json.loads((sc / "GT_world2obj.json").read_text())
        T_world = {k: np.array(val).reshape(4, 4) for k, val in gt.items()}
        for f in sorted((sc / "RealSense" / "Depth").glob("DEPTH_view_*.png"), key=lambda p: int(re.search(r"(\d+)\.png", p.name).group(1))):
            view = int(re.search(r"(\d+)\.png", f.name).group(1))
            # First line: {"cam_pose": [...]}; the following lines hold per-object visibility scores.
            left_file = sc / "RealSense" / "StereoPattern" / f"LEFT_view_{view}.bmp"
            right_file = sc / "RealSense" / "StereoPattern" / f"RIGHT_view_{view}.bmp"
            if not left_file.exists() or not right_file.exists():
                continue                            # subset fetch stopped by the Drive quota part-way through a view
            cam_pose = np.array(json.loads(f.with_suffix(".json").read_text().splitlines()[0])["cam_pose"]).reshape(4, 4)
            T_c_w = np.linalg.inv(cam_pose)
            scene = o3d.t.geometry.RaycastingScene()
            for T in T_world.values():
                T_c_o = T_c_w @ T
                vc = verts @ T_c_o[:3, :3].T + T_c_o[:3, 3]
                scene.add_triangles(o3d.core.Tensor(vc.astype(np.float32)), o3d.core.Tensor(tris.astype(np.uint32)))
            ans = scene.cast_rays(o3d.core.Tensor(np.hstack([np.zeros_like(rays), rays]).astype(np.float32)))
            t = ans["t_hit"].numpy().reshape(H, W).astype(np.float64)
            mask = np.isfinite(t)
            z_gt = np.where(mask, t * zfac, 0.0)
            if mask.sum() < 500:
                continue
            z_d = cv2.imread(str(f), cv2.IMREAD_ANYDEPTH).astype(np.float64) * unit
            L = cv2.imread(str(left_file), cv2.IMREAD_GRAYSCALE)
            R = cv2.imread(str(right_file), cv2.IMREAD_GRAYSCALE)
            raw = sgbm.compute(L, R).astype(np.float64) / 16.0
            d_s = np.where((raw >= 0) & (raw <= max_d), raw + shift, 0.0)
            z_s = np.where(d_s > 0, fx * B / np.maximum(d_s, 1e-6), 0.0)
            d_gt = fx * B / np.maximum(z_gt, 1e-6)
            row = {"scene": sc.name, "view": view, "n_px": int(mask.sum()), "z_gt_median_mm": float(np.median(z_gt[mask]))}
            for name, z in (("d415", z_d), ("sgbm", z_s)):
                ok = mask & (z > 0)
                e = z[ok] - z_gt[ok]
                p = fx * B / z[ok] - d_gt[ok]
                coll[name]["mm"].append(e.astype(np.float32))
                coll[name]["px"].append(p.astype(np.float32))
                coll[name]["n"] += int(mask.sum())
                row[name] = {"invalid": 1 - ok.sum() / mask.sum(), "median_signed_mm": float(np.median(e)) if len(e) else None,
                             "frac_gt_5mm": float((np.abs(e) > TOL_MM).mean()) if len(e) else None}
            per_view.append(row)
            zvals.append(z_gt[mask].astype(np.float32))
            sd = local_sd(L)
            back = ~cv2.dilate(mask.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
            ir_rows.append({"obj_dn_median": float(np.median(L[mask])), "back_dn_median": float(np.median(L[back])), "obj_dn_p99": float(np.percentile(L[mask], 99)),
                            "back_dn_p99": float(np.percentile(L[back], 99)), "obj_local_sd_median": float(np.median(sd[mask])), "back_local_sd_median": float(np.median(sd[back])),
                            "obj_saturated": float((L[mask] == 255).mean()), "back_saturated": float((L[back] == 255).mean()),
                            "obj_local_sd_lt_2dn": float((sd[mask] < 2).mean()), "back_local_sd_lt_2dn": float((sd[back] < 2).mean())})
            if overlay is None and args.overlay:
                overlay = (L.copy(), mask.copy(), z_d.copy(), z_gt.copy(), sc.name, view)
    z = np.concatenate(zvals)
    out = {"object": args.object, "n_views": len(per_view), "scenes": [s.name for s in scenes], "cad_extent_mm": extent, "n_instances_example": len(T_world),
           "z_gt_mm_quantiles": {str(q): float(np.percentile(z, q)) for q in (5, 50, 95)}, "camera": cam,
           "ir_appearance_mean_over_views": {k: float(np.mean([r[k] for r in ir_rows])) for k in ir_rows[0]}, "per_view": per_view}
    for name, c in coll.items():
        out[name] = summarise(np.concatenate(c["mm"]), np.concatenate(c["px"]), c["n"])
    far = [r for r in per_view if r["z_gt_median_mm"] >= 450]
    out["views_z_ge_450mm"] = {"n_views": len(far), **{k: {"median_invalid": float(np.median([r[k]["invalid"] for r in far])) if far else None,
                                                            "median_of_median_signed_mm": float(np.median([r[k]["median_signed_mm"] for r in far if r[k]["median_signed_mm"] is not None])) if far else None}
                                                        for k in ("d415", "sgbm")}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("object", "n_views", "cad_extent_mm", "z_gt_mm_quantiles", "ir_appearance_mean_over_views", "views_z_ge_450mm")}))
    print("D415", json.dumps(out["d415"]))
    print("SGBM", json.dumps(out["sgbm"]))
    if overlay is not None:
        L, m, zd, zg, sn, vw = overlay
        rgb = cv2.cvtColor(L, cv2.COLOR_GRAY2BGR)
        rgb[m] = (0.6 * rgb[m] + 0.4 * np.array([0, 140, 255])).astype(np.uint8)
        err = np.where(m & (zd > 0), np.clip((zd - zg) / 20.0, -1, 1), 0.0)
        vis = np.zeros_like(rgb)
        vis[..., 2] = np.where(err > 0, err * 255, 0)
        vis[..., 0] = np.where(err < 0, -err * 255, 0)
        vis[m & (zd == 0)] = (255, 255, 255)
        args.overlay.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(args.overlay), np.hstack([rgb, vis]))


if __name__ == "__main__":
    main()
