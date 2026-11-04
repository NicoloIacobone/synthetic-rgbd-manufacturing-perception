"""Sensor metrics (PLAN §5.4, A-47): depth error against the ideal depth, per condition and image region.

Usage: .venv/bin/python scripts/sensor_metrics.py <dataset_root> <scene_seed>... --conditions C1 C3 ... --out <json>

Regions: parts (visible masks of the included instance-views, not eroded), edge (< 5 px from the mask edge: the 7 px
matching window's half-width 3 + the 2 px harness erosion), interior (the rest), profile, bracket, and tray (non-part
pixels, every 8th pixel in each direction). Metal vs matte is C3 vs C4 on the part regions.
Per region: invalid fraction; over valid pixels MAE, median signed and absolute error, % with |error| > 5 mm, signed
quantiles in mm and in px. On part pixels also the classes of A-58 (correct / behind the surface up to the tray / in
front / beyond the tray / invalid), which give "filled vs invalid" for §5.8. Pixels are pooled over views.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))
from mechanism_check import build_scenes, cast, classes, pixel_rays  # noqa: E402
from synthrgbd.conditions import DEPTH_DIRS, DEPTH_SCALE_MM  # noqa: E402
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.parts import PART_CATALOGUE, ProfileSpec  # noqa: E402

EDGE_PX = 5.0
TRAY_STEP = 8
QUANTILES = (5, 25, 50, 75, 95)


def region_masks(masks, types, H, W):
    parts = np.zeros((H, W), bool)
    dist = np.zeros((H, W), np.float32)
    prof, brk = np.zeros((H, W), bool), np.zeros((H, W), bool)
    for m, t in zip(masks, types):
        parts |= m
        dist = np.maximum(dist, cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5))
        if t == "profile":
            prof |= m
        else:
            brk |= m
    return {"parts": parts, "edge": parts & (dist < EDGE_PX), "interior": parts & (dist >= EDGE_PX), "profile": prof, "bracket": brk}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("scenes", type=int, nargs="+")
    ap.add_argument("--conditions", nargs="+", required=True, choices=sorted(DEPTH_DIRS))
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg, hcfg = load_config(), load_config(REPO / "configs" / "harness.yaml")
    W, H = cfg["camera"]["width"], cfg["camera"]["height"]
    B = cfg["camera"]["baseline_m"]
    min_vis = hcfg["instances"]["min_visib_fract"]
    is_profile = {i: isinstance(spec, ProfileSpec) for i, (_, spec) in PART_CATALOGUE.items()}
    err_mm, err_px, n_total = defaultdict(lambda: defaultdict(list)), defaultdict(lambda: defaultdict(list)), defaultdict(lambda: defaultdict(int))
    cls_sum, cls_n = defaultdict(lambda: defaultdict(int)), defaultdict(int)
    for seed in args.scenes:
        sc = args.root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
        gt_all = json.loads((sc / "scene_gt.json").read_text())
        info_all = json.loads((sc / "scene_gt_info.json").read_text())
        cams = json.loads((sc / "scene_camera.json").read_text())
        for im in sorted(gt_all, key=int):
            gt, cc = gt_all[im], cams[im]
            K = np.array(cc["cam_K"]).reshape(3, 3)
            fx = K[0, 0]
            z_gt = cv2.imread(str(sc / "depth" / f"{int(im):06d}.png"), cv2.IMREAD_UNCHANGED).astype(np.float64) * DEPTH_SCALE_MM
            masks, types = [], []
            for k, (g, gi) in enumerate(zip(gt, info_all[im])):
                if gi["visib_fract"] >= min_vis:
                    masks.append(cv2.imread(str(sc / "mask_visib" / f"{int(im):06d}_{k:06d}.png"), 0) > 0)
                    types.append("profile" if is_profile[g["obj_id"]] else "bracket")
            reg = region_masks(masks, types, H, W)
            all_parts = np.zeros((H, W), bool)
            for k in range(len(gt)):
                all_parts |= cv2.imread(str(sc / "mask_visib" / f"{int(im):06d}_{k:06d}.png"), 0) > 0
            tray = np.zeros((H, W), bool)
            tray[::TRAY_STEP, ::TRAY_STEP] = True
            reg["tray"] = tray & ~all_parts & (z_gt > 0)
            _, bg = build_scenes(gt, np.array(cc["cam_R_w2c"]).reshape(3, 3), np.array(cc["cam_t_w2c"], float))
            d = pixel_rays(K, W, H)
            z_bg = (d * cast(bg, np.zeros(3), d)["t_hit"].numpy()[:, None])[:, 2].reshape(H, W)
            d_gt = fx * B * 1e3 / np.maximum(z_gt, 1e-6)
            for cond in args.conditions:
                f = sc / DEPTH_DIRS[cond] / f"{int(im):06d}.png"
                if not f.exists():
                    continue
                z = cv2.imread(str(f), cv2.IMREAD_UNCHANGED).astype(np.float64) * DEPTH_SCALE_MM
                for name, m in reg.items():
                    n_total[cond][name] += int(m.sum())
                    ok = m & (z > 0) & (z_gt > 0)
                    err_mm[cond][name].append((z - z_gt)[ok].astype(np.float32))
                    err_px[cond][name].append((fx * B * 1e3 / np.maximum(z, 1e-6) - d_gt)[ok].astype(np.float32))
                for name, c in classes(z, z_gt, z_bg, reg["parts"]).items():
                    cls_sum[cond][name] += int(c.sum())
                cls_n[cond] += int(reg["parts"].sum())
        print(f"scene {seed} done", flush=True)
    out = {"scenes": args.scenes, "edge_px": EDGE_PX, "tray_step": TRAY_STEP, "conditions": {}}
    for cond in args.conditions:
        if cond not in n_total:
            continue
        res = {}
        for name in n_total[cond]:
            e = np.concatenate(err_mm[cond][name]) if err_mm[cond][name] else np.zeros(0)
            p = np.concatenate(err_px[cond][name]) if err_px[cond][name] else np.zeros(0)
            res[name] = {"n_px": n_total[cond][name], "invalid_frac": 1 - len(e) / max(n_total[cond][name], 1)}
            if len(e):
                res[name].update(mae_mm=float(np.abs(e).mean()), median_signed_mm=float(np.median(e)), median_abs_mm=float(np.median(np.abs(e))),
                                 frac_gt_5mm=float((np.abs(e) > 5).mean()),
                                 quantiles_mm={str(q): float(np.percentile(e, q)) for q in QUANTILES},
                                 quantiles_px={str(q): float(np.percentile(p, q)) for q in QUANTILES})
        res["classes"] = {k: v / max(cls_n[cond], 1) for k, v in cls_sum[cond].items()}
        out["conditions"][cond] = res
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1))
    print("WROTE", args.out)


if __name__ == "__main__":
    main()
