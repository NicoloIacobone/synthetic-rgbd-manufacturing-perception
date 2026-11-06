"""C3 noise redraws on all test scenes (A-59, ledger "Noise redraws, all scenes"), descriptive: the spread next to the primary number.

Usage: .venv/bin/python scripts/redraw_summary.py <results_dir> <redraw_dir> --out <json>
"""

import argparse
import json
from pathlib import Path

import numpy as np

THR_MM = 5.0


def load(path):
    rows = [json.loads(x) for x in path.read_text().splitlines()[1:]]
    return {(r["scene"], r["im_id"], r["gt_id"]): r.get("mssd_mm") is not None and r["mssd_mm"] < THR_MM for r in rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("redraw", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    d = {c: load(args.results / f"A_{c}_10.jsonl") for c in ("C3", "C4")} | {c: load(args.redraw / f"A_{c}_10.jsonl") for c in ("C3redraw1", "C3redraw2")}
    for c, v in d.items():
        assert v.keys() == d["C3"].keys(), f"instance-views differ for {c}"
    rec = {c: float(np.mean(list(v.values()))) for c, v in d.items()}
    draws = ["C3", "C3redraw1", "C3redraw2"]
    out = {"n_instance_views": len(d["C3"]), "recall_5mm": rec,
           "C3_range": [min(rec[c] for c in draws), max(rec[c] for c in draws)], "C3_spread_points": 100 * (max(rec[c] for c in draws) - min(rec[c] for c in draws)),
           "C3_minus_C4_per_draw": {c: rec[c] - rec["C4"] for c in draws},
           "views_changed_vs_primary": {c: sum(d[c][k] != d["C3"][k] for k in d["C3"]) for c in draws[1:]},
           "note": "Only the sensor noise is redrawn; the render and the C4 draw stay."}
    args.out.write_text(json.dumps(out, indent=1))
    print(json.dumps(out))


if __name__ == "__main__":
    main()
