"""Naive datasheet-noise baselines C2a / C2b (PLAN §5.1): ideal depth + Gaussian noise, σ = z²·ε_d/(f·B).

Usage: .venv/bin/python scripts/c2_depth.py <dataset_root> <scene_seed>...

ε_d = noise.c2a_eps_d_px (0.08 px, [S-03]) and noise.c2b_eps_d_px (0.262 px, Carfagni 1 m point, A-14) from
configs/default.yaml. Noise is added to every valid pixel of the ideal depth (depth/, uint16, 0.1 mm),
independently per pixel, from the seed streams c2a_noise / c2b_noise of (master, scene, view) (§5.10).
Writes depth_c2a/ and depth_c2b/ (uint16, 0.1 mm; invalid stays 0; negative values clipped to 0).
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.seeds import rng  # noqa: E402

DEPTH_SCALE_MM = 0.1


def main():
    root, seeds = Path(sys.argv[1]), [int(s) for s in sys.argv[2:]]
    cfg = load_config()
    B, master = cfg["camera"]["baseline_m"], cfg["seeds"]["master"]
    levels = {"c2a": cfg["noise"]["c2a_eps_d_px"], "c2b": cfg["noise"]["c2b_eps_d_px"]}
    for seed in seeds:
        sc = root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
        cams = json.loads((sc / "scene_camera.json").read_text())
        for im in sorted(cams, key=int):
            fx = np.array(cams[im]["cam_K"]).reshape(3, 3)[0, 0]
            z = cv2.imread(str(sc / "depth" / f"{int(im):06d}.png"), cv2.IMREAD_UNCHANGED).astype(np.float64) * DEPTH_SCALE_MM
            valid = z > 0
            for name, eps in levels.items():
                sigma = (z * 1e-3) ** 2 * eps / (fx * B) * 1e3            # mm
                n = rng(master, seed, int(im), f"{name}_noise").standard_normal(z.shape)
                zn = np.where(valid, np.clip(z + sigma * n, 0, None), 0.0)
                out = sc / f"depth_{name}"
                out.mkdir(exist_ok=True)
                cv2.imwrite(str(out / f"{int(im):06d}.png"), np.round(zn / DEPTH_SCALE_MM).astype(np.uint16))
        print(f"scene {seed}: C2a/C2b written")


if __name__ == "__main__":
    main()
