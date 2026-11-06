"""RGB light rule (A-69) on one rendered sweep folder: saturated part pixels and part grey, per view and pooled. No IR, depth or recall.

Usage: .venv/bin/python scripts/select_rgb_light.py <root> <seed>... --out <json> [--sheet <jpg>]

Saturated = all three channels >= 250, on the union of the visible part masks. Pass: median <= 1% and maximum <= 5% over views.
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

SAT = 250
MEDIAN_MAX, WORST_MAX, GREY_MIN = 0.01, 0.05, 40.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("seeds", type=int, nargs="+")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sheet", type=Path)
    args = ap.parse_args()
    rows, tiles = [], []
    for seed in args.seeds:
        sc = args.root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
        gt = json.loads((sc / "scene_gt.json").read_text())
        for im in sorted(gt, key=int):
            f = f"{int(im):06d}"
            img = cv2.imread(str(sc / "rgb" / f"{f}.png"))
            parts = np.zeros(img.shape[:2], bool)
            for k in range(len(gt[im])):
                parts |= cv2.imread(str(sc / "mask_visib" / f"{f}_{k:06d}.png"), 0) > 0
            sat = (img >= SAT).all(axis=2)
            grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            rows.append({"scene": seed, "im_id": int(im), "saturated_part_share": float(sat[parts].mean()), "median_part_grey": float(np.median(grey[parts])),
                         "median_image_grey": float(np.median(grey))})
            tiles.append(cv2.resize(img, (320, 180), interpolation=cv2.INTER_AREA))
    s = [r["saturated_part_share"] for r in rows]
    out = {"n_views": len(rows), "median_saturated": float(np.median(s)), "max_saturated": float(np.max(s)), "median_part_grey": float(np.median([r["median_part_grey"] for r in rows])),
           "passes": bool(np.median(s) <= MEDIAN_MAX and np.max(s) <= WORST_MAX), "grey_ok": bool(np.median([r["median_part_grey"] for r in rows]) >= GREY_MIN), "per_view": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "per_view"}))
    if args.sheet:
        args.sheet.parent.mkdir(parents=True, exist_ok=True)
        cols = 5
        grid = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
        cv2.imwrite(str(args.sheet), np.vstack(grid), [cv2.IMWRITE_JPEG_QUALITY, 80])


if __name__ == "__main__":
    main()
