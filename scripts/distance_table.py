"""A1 recall@5 mm by part distance (open item 34, ledger "Distance panel"), descriptive, at 10 mm / 10 deg.

Usage: .venv/bin/python scripts/distance_table.py <dataset_root> <results_dir> --out <json>

Distance = camera-frame z of the part's bounding-box centre at the ground-truth pose. Bands < 0.7, 0.7-0.9, >= 0.9 m. Same
instance-views and failures as the primary endpoint; 95% CI by scene bootstrap, from its own stream.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.pose import load_part_models  # noqa: E402
from synthrgbd.seeds import rng  # noqa: E402
from synthrgbd.stats import scene_bootstrap_ci  # noqa: E402

BANDS = [("< 0.7 m", 0.0, 0.7), ("0.7-0.9 m", 0.7, 0.9), (">= 0.9 m", 0.9, np.inf)]
CONDITIONS = ("C1", "C2a", "C2b", "C3", "C4")
THR_MM = 5.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("results", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg = load_config()
    centres = {i: m["centre"] for i, m in load_part_models(1000, 0).items()}
    g = rng(cfg["seeds"]["master"], 0, 2, "bootstrap")
    gts = {}

    def distance(r):
        key = r["scene"]
        if key not in gts:
            gts[key] = json.loads((args.root / "synthrgbd" / "train_pbr" / f"{key:06d}" / "scene_gt.json").read_text())
        inst = gts[key][str(r["im_id"])][r["gt_id"]]
        R, t = np.array(inst["cam_R_m2c"]).reshape(3, 3), np.array(inst["cam_t_m2c"], float)
        return float((R @ centres[inst["obj_id"]] + t)[2]) * 1e-3

    out = {"bands": [b[0] for b in BANDS], "threshold_mm": THR_MM, "conditions": {}}
    out["part_centre_z_m"] = None
    for c in CONDITIONS:
        rows = [json.loads(x) for x in (args.results / f"A_{c}_10.jsonl").read_text().splitlines()[1:]]
        dist = np.array([distance(r) for r in rows])
        ok = np.array([r.get("mssd_mm") is not None and r["mssd_mm"] < THR_MM for r in rows], float)
        sc = np.array([r["scene"] for r in rows])
        res = []
        for name, lo, hi in BANDS:
            m = (dist >= lo) & (dist < hi)
            ci = scene_bootstrap_ci(ok[m], sc[m], cfg["statistics"]["bootstrap_resamples"], g)
            res.append({"band": name, "n": int(m.sum()), "n_scenes": int(len(np.unique(sc[m]))), "recall": float(ok[m].mean()), "ci95": list(ci)})
        out["conditions"][c] = res
        out["part_centre_z_m"] = [float(dist.min()), float(dist.max())]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1))
    print(json.dumps({c: [round(b["recall"], 3) for b in v] for c, v in out["conditions"].items()}), [b["n"] for b in out["conditions"]["C1"]])


if __name__ == "__main__":
    main()
