"""Surrogate depth for the error structure check (A-73): C3 with the errors of each part shuffled, or with random signs.

Usage: .venv/bin/python scripts/error_structure_depth.py <dataset_root> <scene_seed>...
Writes depth_stereo_metal_shuf/ and depth_stereo_metal_sym/ in each scene. Seeds from the stream error_structure of (master, scene, view).
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.conditions import DEPTH_DIRS  # noqa: E402
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.error_structure import scramble_errors  # noqa: E402
from synthrgbd.seeds import rng  # noqa: E402

OUT = {"shuffle": DEPTH_DIRS["C3shuf"], "sign": DEPTH_DIRS["C3sym"]}


def main():
    root, seeds = Path(sys.argv[1]), [int(s) for s in sys.argv[2:]]
    master = load_config()["seeds"]["master"]
    for seed in seeds:
        sc = root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
        gt = json.loads((sc / "scene_gt.json").read_text())
        for d in OUT.values():
            (sc / d).mkdir(exist_ok=True)
        for im, insts in gt.items():
            f = f"{int(im):06d}"
            z = cv2.imread(str(sc / DEPTH_DIRS["C3"] / f"{f}.png"), cv2.IMREAD_UNCHANGED)
            z_true = cv2.imread(str(sc / DEPTH_DIRS["C1"] / f"{f}.png"), cv2.IMREAD_UNCHANGED)
            g = rng(master, seed, int(im), "error_structure")
            for mode, d in OUT.items():
                out = z.copy()
                for k in range(len(insts)):
                    mask = cv2.imread(str(sc / "mask_visib" / f"{f}_{k:06d}.png"), 0) > 0
                    out = scramble_errors(out, z_true, mask, g, mode)
                cv2.imwrite(str(sc / d / f"{f}.png"), out.astype(np.uint16))
        print("scene", seed, "done", flush=True)


if __name__ == "__main__":
    main()
