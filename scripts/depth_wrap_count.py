"""Count the pixels whose stereo depth wraps around when stored as uint16 at 0.1 mm (A-75), by re-matching the stored IR pairs.

Usage: .venv/bin/python scripts/depth_wrap_count.py <test_root> --out <json>

scripts/stereo_scene.py casts z / 0.1 mm to uint16, so z > 6.5535 m wraps to a false value. Counts on seeds 0-49 for C3 and C4 as stored, and on
seeds 0-9 for the metal pass with all three filters off (§5.8, C3looselr). Also the depth these pixels end up with in C3 on seeds 0-9.
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
from synthrgbd.geometry import disparity_to_depth  # noqa: E402
from synthrgbd.seeds import rng  # noqa: E402
from synthrgbd.stereo import SGBM_VARIANTS, auto_exposure_gain, exposed_pair_uint8, exposure_roi_x0, make_sgbm, match_extended  # noqa: E402

LIMIT = 65535  # uint16, in units of 0.1 mm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg, ir = load_config(), load_config(REPO / "configs" / "camera_d415_ir.yaml")
    cam, sn = cfg["camera"], ir["sensor_noise"]
    pad, setpoint = ir["ir_render"]["pad_px"], float(ir["exposure"]["setpoint_dn"])
    strict, loose = make_sgbm(ir["sgbm"]), make_sgbm({**ir["sgbm"], **SGBM_VARIANTS["looselr"]})
    keys = ("frame_px", "frame_wrapped", "part_px", "part_wrapped")
    tot = {name: dict.fromkeys(keys, 0) for name in ("C3", "C4", "C3looselr_seeds_0_9")}
    values_mm, identical, views = [], 0, 0

    def depth(l8, r8, K, matcher):
        return disparity_to_depth(match_extended(l8, r8, pad, matcher, cam["disparity_search_px"]), K[0, 0], cam["baseline_m"], cam["disparity_search_px"])

    def count(name, z, parts):
        over, t = z * 1e4 > LIMIT, tot[name]
        t["frame_px"] += int(z.size)
        t["frame_wrapped"] += int(over.sum())
        t["part_px"] += int(parts.sum())
        t["part_wrapped"] += int((over & parts).sum())
        return over

    for seed in range(50):
        sc = args.root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
        cams = json.loads((sc / "scene_camera.json").read_text())
        gt = json.loads((sc / "scene_gt.json").read_text())
        for im in sorted(cams, key=int):
            f = f"{int(im):06d}"
            K = np.array(cams[im]["cam_K"]).reshape(3, 3)
            d = np.load(sc / "ir" / f"{f}_metal.npz")
            Lm, Rm = d["left"].astype(np.float32), d["right"].astype(np.float32)
            gain = auto_exposure_gain(Lm[:, pad:], exposure_roi_x0(K[0, 0], cam["baseline_m"], cam["min_z_m"]), setpoint)
            r = rng(cfg["seeds"]["master"], seed, int(im), "ir_noise")
            zl, zr = r.standard_normal(Lm.shape), r.standard_normal(Lm.shape)
            parts = np.zeros((cam["height"], cam["width"]), bool)
            for k in range(len(gt[im])):
                parts |= cv2.imread(str(sc / "mask_visib" / f"{f}_{k:06d}.png"), 0) > 0
            l8, r8 = exposed_pair_uint8(Lm, Rm, gain, sn, zl, zr)
            z = depth(l8, r8, K, strict)
            over = count("C3", z, parts)
            stored = cv2.imread(str(sc / "depth_stereo_metal" / f"{f}.png"), cv2.IMREAD_UNCHANGED)
            views += 1
            identical += int(np.array_equal(np.round(z * 1e4).astype(np.uint16), stored))
            if seed < 10:
                if over.any():
                    values_mm.append(stored[over] * 0.1)
                count("C3looselr_seeds_0_9", depth(l8, r8, K, loose), parts)
            d = np.load(sc / "ir" / f"{f}_matte.npz")
            l8, r8 = exposed_pair_uint8(d["left"].astype(np.float32), d["right"].astype(np.float32), gain, sn, zl, zr)
            count("C4", depth(l8, r8, K, strict), parts)
    v = np.concatenate(values_mm)
    out = {"limit_m": LIMIT * 1e-4, "disparity_below_px": float(K[0, 0]) * cam["baseline_m"] / (LIMIT * 1e-4), "counts": tot,
           "c3_stored_mm_of_wrapped_pixels_seeds_0_9": {"n": int(v.size), "min": float(v.min()), "median": float(np.median(v)), "max": float(v.max()), "share_below_500mm": float((v < 500).mean())},
           "c3_views_reproducing_the_stored_depth": {"identical": identical, "views": views},
           "note": "Not fixed: recall and part metrics of C3 and C4 do not change, and a fix changes the quick run's expected hashes."}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
