"""Task B (PLAN §5.3): suction grasp per instance on one depth condition, checked against the GT mesh.

Usage:
  .venv/bin/python scripts/suction_eval.py <dataset_root> <scene_seed>... --condition C1 --out <jsonl>

Same dataset layout, condition folders and instance inclusion rule as scripts/pose_eval.py. Planner
settings: configs/harness.yaml `suction` (A-44/A-45); cup and thresholds: configs/default.yaml
task_b (frozen, A-19). Reported per part type as well as overall (§5.12 row 1).
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
from synthrgbd.conditions import DEPTH_DIRS, DEPTH_SCALE_MM  # noqa: E402
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.pose import backproject, erode_mask, load_part_models  # noqa: E402
from synthrgbd.suction import SuctionParams, check_success, plan_suction  # noqa: E402



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("scenes", type=int, nargs="+")
    ap.add_argument("--condition", default="C1", choices=sorted(DEPTH_DIRS))
    ap.add_argument("--harness", type=Path, default=REPO / "configs" / "harness.yaml")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg, hcfg = load_config(), load_config(args.harness)
    cfg_b, p = cfg["task_b"], SuctionParams.from_cfg(hcfg["suction"])
    models = load_part_models(hcfg["model_sampling"]["points_per_model"], hcfg["model_sampling"]["seed"])
    min_vis = hcfg["instances"]["min_visib_fract"]
    commit = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "-C", str(REPO), "status", "--porcelain", "src", "scripts",
                                          "configs"], text=True).strip())
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
            poses = [(np.array(g["cam_R_m2c"]).reshape(3, 3), np.array(g["cam_t_m2c"], float)) for g in gt_all[im]]
            view_tris = [models[g["obj_id"]]["mesh"].triangles @ R.T + t for g, (R, t) in zip(gt_all[im], poses)]
            for k, (g, gi) in enumerate(zip(gt_all[im], info_all[im])):
                if gi["visib_fract"] < min_vis:
                    skipped.append({"scene": seed, "im_id": int(im), "gt_id": k, "visib_fract": gi["visib_fract"]})
                    continue
                m = models[g["obj_id"]]
                mask = cv2.imread(str(sc / "mask_visib" / f"{int(im):06d}_{k:06d}.png"), cv2.IMREAD_GRAYSCALE) > 0
                pts = backproject(depth, erode_mask(mask, p.mask_erosion_px), K)
                t0 = time.perf_counter()
                grasp = plan_suction(pts, cfg_b["cup_radius_mm"], p)
                res = check_success(grasp, view_tris, k, cfg_b)
                row = {"scene": seed, "im_id": int(im), "gt_id": k, "obj_id": g["obj_id"], "type": m["type"],
                       "visib_fract": gi["visib_fract"], "n_pts": int(len(pts)), "t_s": time.perf_counter() - t0}
                row.update({kk: (float(v) if isinstance(v, (np.floating, float)) else v) for kk, v in res.items()})
                if grasp is not None:
                    row["plan_rms_mm"] = grasp["rms_mm"]
                rows.append(row)
    meta = {"commit": commit, "dirty_tree": dirty, "condition": args.condition, "harness": hcfg,
            "task_b": cfg_b, "scenes": args.scenes, "skipped": skipped}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        f.write(json.dumps({"meta": meta}) + "\n")
        for r in rows:
            f.write(json.dumps(r) + "\n")
    summ = {"n": len(rows), "skipped": len(skipped)}
    for typ in ("bracket", "profile", None):
        rr = [r for r in rows if typ is None or r["type"] == typ]
        key = typ or "all"
        summ[key] = {"n": len(rr), "success": sum(r["success"] for r in rr), "has_grasp": sum(r["has_grasp"] for r in rr)}
    print("SUMMARY", json.dumps(summ))


if __name__ == "__main__":
    main()
