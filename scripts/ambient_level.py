"""One ambient level on the dev views (A-70): total = projector + a x ambient, so that the median left-image DN on C3 part pixels is 21 DN.

Usage: .venv/bin/python scripts/ambient_level.py <dev_root> <seed>... --out <json>

Statistic: mean over views of the per-view median, on the 8-bit left image the matcher receives (auto exposure on the total image,
noise after exposure), as in scripts/ir_appearance.py and in ROBI's obj_dn_median. Bisection in log space, one level, no grid.
The level goes into configs/camera_d415_ir.yaml (ambient_test.level) before any ambient pass on a test seed. Exit 0 in both cases:
if the target cannot be reached, the JSON says reachable: false and the test is skipped (A-70).
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.seeds import rng  # noqa: E402
from synthrgbd.stereo import auto_exposure_gain, exposed_pair_uint8, exposure_roi_x0  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("seeds", type=int, nargs="+")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg, ir = load_config(), load_config(REPO / "configs" / "camera_d415_ir.yaml")
    cam, sn, at = cfg["camera"], ir["sensor_noise"], ir["ambient_test"]
    pad, sp = ir["ir_render"]["pad_px"], float(ir["exposure"]["setpoint_dn"])
    views = []
    for seed in args.seeds:
        sc = args.root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
        cams = json.loads((sc / "scene_camera.json").read_text())
        gt = json.loads((sc / "scene_gt.json").read_text())
        for im in sorted(cams, key=int):
            f = f"{int(im):06d}"
            K = np.array(cams[im]["cam_K"]).reshape(3, 3)
            parts = np.zeros((cam["height"], cam["width"]), bool)
            for k in range(len(gt[im])):
                parts |= cv2.imread(str(sc / "mask_visib" / f"{f}_{k:06d}.png"), 0) > 0
            p, a = np.load(sc / "ir" / f"{f}_metal.npz"), np.load(sc / "ir_ambient" / f"{f}_metal.npz")
            r = rng(cfg["seeds"]["master"], seed, int(im), "ir_noise")
            L = p["left"].astype(np.float64)
            views.append({"x0": exposure_roi_x0(K[0, 0], cam["baseline_m"], cam["min_z_m"]), "parts": parts, "L": L, "La": a["left"].astype(np.float64),
                          "zl": r.standard_normal(L.shape), "zr": r.standard_normal(L.shape), "id": f"{seed}/{im}"})

    def stat(level):
        med = []
        for v in views:
            T = v["L"] + level * v["La"]
            g = auto_exposure_gain(T[:, pad:], v["x0"], sp)
            l8 = exposed_pair_uint8(T, T, g, sn, v["zl"], v["zr"])[0][:, pad:]
            med.append(float(np.median(l8[v["parts"]])))
        return float(np.mean(med)), med

    target, tol = float(at["target_dn"]), float(at["tol_dn"])
    lo, hi = 1e-6, 100.0
    base, _ = stat(0.0)
    top, _ = stat(hi)
    trace = [{"level": 0.0, "dn": base}, {"level": hi, "dn": top}]
    level, achieved, per_view, reachable = None, None, None, False
    if base <= target <= top:
        for _ in range(40):
            mid = float(np.sqrt(lo * hi))
            v, med = stat(mid)
            trace.append({"level": mid, "dn": v})
            if abs(v - target) <= tol:
                level, achieved, per_view, reachable = mid, v, med, True
                break
            lo, hi = (mid, hi) if v < target else (lo, mid)
    out = {"reachable": reachable, "level": level, "achieved_dn": achieved, "target_dn": target, "tol_dn": tol, "dn_without_ambient": base,
           "dn_pure_ambient_limit": top, "per_view_median_dn": dict(zip([v["id"] for v in views], per_view or [])), "trace": trace}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("trace", "per_view_median_dn")}))


if __name__ == "__main__":
    main()
