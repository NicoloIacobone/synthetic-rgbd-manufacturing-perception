"""Task A (PLAN §5.2): ICP from an offset initial pose on one depth condition; per-instance MSSD.

Usage:
  .venv/bin/python scripts/pose_eval.py <dataset_root> <scene_seed>... --condition C1 --offset 0 0 --out <jsonl>

<dataset_root> holds synthrgbd/train_pbr/<scene>/ (BOP). Conditions map to depth folders (uint16, BOP depth
scale 0.1 mm): C1 = depth/ (ideal); the others are added at M4 (C2a/C2b noise, C3/C4 stereo). --offset is
[mm deg]; 0 0 is the §5.11 zero-offset sanity check. Instances below instances.min_visib_fract
(configs/harness.yaml) are skipped and listed. The pass/fail summary of the sanity check uses
configs/default.yaml sanity.* (≥ 99% of instances at MSSD < 0.5 mm).
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
from synthrgbd.mssd import equal_leg_bracket_symmetries, mssd, profile_symmetries  # noqa: E402
from synthrgbd.parts import PART_CATALOGUE, ProfileSpec, make_part  # noqa: E402
from synthrgbd.pose import (IcpParams, apply_offset, backproject, draw_offset_directions,  # noqa: E402
                            erode_mask, icp_refine, rotation_error_deg, sample_with_normals,
                            unique_vertices)
from synthrgbd.seeds import rng  # noqa: E402

DEPTH_DIRS = {"C1": "depth"}
DEPTH_SCALE_MM = 0.1


def load_models(n_pts: int, seed: int) -> dict:
    models = {}
    for obj_id, (name, spec) in PART_CATALOGUE.items():
        mesh = make_part(spec)
        pts, nrm = sample_with_normals(mesh, n_pts, np.random.default_rng([seed, obj_id]))
        verts = unique_vertices(mesh)
        models[obj_id] = {
            "name": name, "pts": pts, "nrm": nrm, "verts": verts,
            "centre": (verts.min(0) + verts.max(0)) / 2,          # bounding-box centre (offset pivot)
            "syms": profile_symmetries() if isinstance(spec, ProfileSpec) else equal_leg_bracket_symmetries(),
            "axis": np.array([0.0, 0.0, 1.0]) if isinstance(spec, ProfileSpec) else None}
    return models


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("scenes", type=int, nargs="+")
    ap.add_argument("--condition", default="C1", choices=sorted(DEPTH_DIRS))
    ap.add_argument("--offset", type=float, nargs=2, default=[0.0, 0.0], metavar=("MM", "DEG"))
    ap.add_argument("--harness", type=Path, default=REPO / "configs" / "harness.yaml")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg, hcfg = load_config(), load_config(args.harness)
    p = IcpParams.from_cfg(hcfg["icp"])
    models = load_models(hcfg["model_sampling"]["points_per_model"], hcfg["model_sampling"]["seed"])
    min_vis = hcfg["instances"]["min_visib_fract"]
    commit = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "-C", str(REPO), "status", "--porcelain", "src", "scripts",
                                          "configs"], text=True).strip())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows, skipped = [], []
    for seed in args.scenes:
        sc = args.root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
        gt_all = json.loads((sc / "scene_gt.json").read_text())
        info_all = json.loads((sc / "scene_gt_info.json").read_text())
        cams = json.loads((sc / "scene_camera.json").read_text())
        for im in sorted(gt_all, key=int):
            K = np.array(cams[im]["cam_K"]).reshape(3, 3)
            depth = cv2.imread(str(sc / DEPTH_DIRS[args.condition] / f"{int(im):06d}.png"),
                               cv2.IMREAD_UNCHANGED).astype(np.float64) * DEPTH_SCALE_MM
            dirs = draw_offset_directions(rng(cfg["seeds"]["master"], seed, int(im), "init_offset"),
                                          len(gt_all[im]))
            for k, (g, gi) in enumerate(zip(gt_all[im], info_all[im])):
                if gi["visib_fract"] < min_vis:
                    skipped.append({"scene": seed, "im_id": int(im), "gt_id": k, "visib_fract": gi["visib_fract"]})
                    continue
                m = models[g["obj_id"]]
                T_gt = np.eye(4)
                T_gt[:3, :3] = np.array(g["cam_R_m2c"]).reshape(3, 3)
                T_gt[:3, 3] = g["cam_t_m2c"]
                T0 = apply_offset(T_gt, dirs[k, 0], dirs[k, 1], args.offset[0], args.offset[1], m["centre"])
                mask = cv2.imread(str(sc / "mask_visib" / f"{int(im):06d}_{k:06d}.png"), cv2.IMREAD_GRAYSCALE) > 0
                pts = backproject(depth, erode_mask(mask, p.mask_erosion_px), K)
                t = time.perf_counter()
                T_est, info = icp_refine(pts, m["pts"], m["nrm"], T0, p)
                row = {"scene": seed, "im_id": int(im), "gt_id": k, "obj_id": g["obj_id"],
                       "visib_fract": gi["visib_fract"], "n_pts": info["n_scene"], "status": info["status"],
                       "t_icp_s": time.perf_counter() - t,
                       "mssd_init_mm": mssd(T0, T_gt, m["verts"], m["syms"])}
                if T_est is not None:
                    row["mssd_mm"] = mssd(T_est, T_gt, m["verts"], m["syms"])
                    row["t_err_mm"] = float(np.linalg.norm(T_est[:3, 3] - T_gt[:3, 3]))
                    row["R_err_deg"] = rotation_error_deg(T_est[:3, :3], T_gt[:3, :3])
                    row["fitness"] = info["fitness"]
                else:
                    row["mssd_mm"] = None
                rows.append(row)
    meta = {"commit": commit, "dirty_tree": dirty, "condition": args.condition, "offset": args.offset,
            "harness": hcfg, "scenes": args.scenes, "master_seed": cfg["seeds"]["master"], "skipped": skipped}
    with open(args.out, "w") as f:
        f.write(json.dumps({"meta": meta}) + "\n")
        for r in rows:
            f.write(json.dumps(r) + "\n")
    ms = np.array([r["mssd_mm"] if r["mssd_mm"] is not None else np.inf for r in rows])
    s = cfg["sanity"]
    frac = float((ms < s["c1_zero_offset_max_mssd_mm"]).mean()) if len(ms) else float("nan")
    summary = {"n": len(rows), "skipped": len(skipped), "frac_mssd_lt_sanity": frac,
               "frac_mssd_lt_5mm": float((ms < cfg["task_a"]["recall_threshold_mm"]).mean()),
               "max_mssd_mm": float(ms.max()), "median_mssd_mm": float(np.median(ms))}
    if args.offset == [0.0, 0.0] and args.condition == "C1":
        summary["sanity_pass"] = frac >= s["c1_zero_offset_min_fraction"]
    print("SUMMARY", json.dumps(summary))


if __name__ == "__main__":
    main()
