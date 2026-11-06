"""Share of part pixels outside the projector's field (A-36, A-66), from geometry alone: no depth condition and no recall is read.

Usage: .venv/bin/python scripts/unlit_share.py <dataset_root> <first_seed> <last_seed> --out <json>

A part pixel is unlit if its surface point, from the ideal depth, falls outside the 67 x 41 degree field of the projector at the
baseline midpoint. Instance-views as in the experiment (visib_fract >= instances.min_visib_fract). Direct light only.
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.conditions import DEPTH_SCALE_MM  # noqa: E402
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.parts import PART_CATALOGUE, ProfileSpec  # noqa: E402
from synthrgbd.projector import lit_mask  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("first", type=int)
    ap.add_argument("last", type=int)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    ir, hcfg = load_config(REPO / "configs" / "camera_d415_ir.yaml"), load_config(REPO / "configs" / "harness.yaml")
    min_vis = hcfg["instances"]["min_visib_fract"]
    is_profile = {i: isinstance(spec, ProfileSpec) for i, (_, spec) in PART_CATALOGUE.items()}
    rows, image_unlit = [], []
    for seed in range(args.first, args.last + 1):
        sc = args.root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
        gt_all = json.loads((sc / "scene_gt.json").read_text())
        info_all = json.loads((sc / "scene_gt_info.json").read_text())
        cams = json.loads((sc / "scene_camera.json").read_text())
        for im in sorted(gt_all, key=int):
            K = np.array(cams[im]["cam_K"]).reshape(3, 3)
            z = cv2.imread(str(sc / "depth" / f"{int(im):06d}.png"), cv2.IMREAD_UNCHANGED).astype(np.float64) * DEPTH_SCALE_MM * 1e-3
            lit = lit_mask(z, K, ir["projector"]["position_x_m"], ir["projector"]["fov_deg"])
            image_unlit.append(float(1 - lit[z > 0].mean()))
            for k, (g, gi) in enumerate(zip(gt_all[im], info_all[im])):
                if gi["visib_fract"] < min_vis:
                    continue
                m = cv2.imread(str(sc / "mask_visib" / f"{int(im):06d}_{k:06d}.png"), 0) > 0
                rows.append({"scene": seed, "im_id": int(im), "gt_id": k, "type": "profile" if is_profile[g["obj_id"]] else "bracket",
                             "n_px": int(m.sum()), "n_unlit": int((m & ~lit).sum())})
    n, u = np.array([r["n_px"] for r in rows]), np.array([r["n_unlit"] for r in rows])
    frac = u / np.maximum(n, 1)
    out = {"n_instance_views": len(rows), "part_px": int(n.sum()), "part_px_unlit": int(u.sum()), "part_px_unlit_share": float(u.sum() / n.sum()),
           "instance_views_any_unlit": int((u > 0).sum()), "instance_views_unlit_gt_10pct": int((frac > 0.1).sum()),
           "instance_views_unlit_gt_50pct": int((frac > 0.5).sum()), "image_unlit_share_mean_over_views": float(np.mean(image_unlit)),
           "by_type": {t: float(sum(r["n_unlit"] for r in rows if r["type"] == t) / max(sum(r["n_px"] for r in rows if r["type"] == t), 1)) for t in ("profile", "bracket")},
           "worst": sorted(({**r, "share": r["n_unlit"] / max(r["n_px"], 1)} for r in rows), key=lambda r: -r["share"])[:5]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "worst"}))


if __name__ == "__main__":
    main()
