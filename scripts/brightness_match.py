"""How well the matte albedo matches metal brightness: clipped exposed DN on part pixels, C4 against C3 (A-24, A-42).

Usage: .venv/bin/python scripts/brightness_match.py <dev_root> <test_root> --out <json>

The albedo rule works on the development scenes. This reports the same measure on them and on the test scenes: linear radiance times the
gain of the C3 left image, clipped to 8 bits, no noise, left-image part pixels. Means are weighted by pixel; ratios are per view.
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
from synthrgbd.stereo import auto_exposure_gain, exposure_roi_x0  # noqa: E402


def measure(root, seeds, cam, pad, setpoint):
    sum_c4 = sum_c3 = n = 0.0
    ratio = []
    for seed in seeds:
        sc = root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
        cams = json.loads((sc / "scene_camera.json").read_text())
        gt = json.loads((sc / "scene_gt.json").read_text())
        for im in sorted(cams, key=int):
            f = f"{int(im):06d}"
            K = np.array(cams[im]["cam_K"]).reshape(3, 3)
            metal = np.load(sc / "ir" / f"{f}_metal.npz")["left"].astype(np.float64)[:, pad:]
            matte = np.load(sc / "ir" / f"{f}_matte.npz")["left"].astype(np.float64)[:, pad:]
            gain = auto_exposure_gain(metal, exposure_roi_x0(K[0, 0], cam["baseline_m"], cam["min_z_m"]), setpoint)
            parts = np.zeros(metal.shape, bool)
            for k in range(len(gt[im])):
                parts |= cv2.imread(str(sc / "mask_visib" / f"{f}_{k:06d}.png"), 0) > 0
            c4, c3 = np.clip(matte[parts] * gain, 0, 255), np.clip(metal[parts] * gain, 0, 255)
            sum_c4, sum_c3, n = sum_c4 + c4.sum(), sum_c3 + c3.sum(), n + parts.sum()
            ratio.append(float(c4.mean() / c3.mean()))
    q = np.percentile(ratio, [5, 50, 95])
    return {"n_views": len(ratio), "n_part_pixels": int(n), "c3_dn_mean": sum_c3 / n, "c4_dn_mean": sum_c4 / n, "ratio_pixel_weighted": sum_c4 / sum_c3,
            "ratio_per_view": {"p5": float(q[0]), "p50": float(q[1]), "p95": float(q[2]), "min": min(ratio), "max": max(ratio)}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dev", type=Path)
    ap.add_argument("test", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg, ir = load_config(), load_config(REPO / "configs" / "camera_d415_ir.yaml")
    pad, setpoint = ir["ir_render"]["pad_px"], float(ir["exposure"]["setpoint_dn"])
    out = {"measure": "clipped exposed DN on left-image part pixels, gain of the C3 left image, no noise",
           "dev": measure(args.dev, range(1000, 1005), cfg["camera"], pad, setpoint),
           "test": measure(args.test, range(50), cfg["camera"], pad, setpoint)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
