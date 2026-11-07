"""Dot-density test on seeds 0-9 (A-74), descriptive: recall with 10 000 dots against the primary 30 000 on the same instance-views.

Usage: .venv/bin/python scripts/dots_summary.py <results_dir> <dots_dir> --out <json>

The two sides come from separate renders, and renders are not bit-reproducible, so a difference mixes dot density with render repeat.
The reading is fixed in advance in A-74 of docs/ASSUMPTIONS.md.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.seeds import rng  # noqa: E402
from synthrgbd.stats import mcnemar_exact, scene_bootstrap_ci  # noqa: E402

THR_MM = 5.0


def load(path):
    lines = path.read_text().splitlines()
    return json.loads(lines[0])["meta"], {(r["scene"], r["im_id"], r["gt_id"]): r for r in map(json.loads, lines[1:])}


def ok(r):
    return r.get("mssd_mm") is not None and r["mssd_mm"] < THR_MM


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("dots", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg = load_config()
    g = rng(cfg["seeds"]["master"], 0, 7, "bootstrap")
    metas, runs = {}, {}
    for c in ("C3dots10k", "C4dots10k"):
        metas[c], runs[c] = load(args.dots / f"A_{c}_10.jsonl")
    keys = sorted(runs["C3dots10k"])
    if sorted(runs["C4dots10k"]) != keys:
        raise ValueError("instance-views differ")
    base = {c: load(args.results / f"A_{c}_10.jsonl")[1] for c in ("C1", "C2b", "C3", "C4")}
    scenes = np.array([k[0] for k in keys])
    types = np.array([base["C3"][k]["type"] for k in keys])
    sensor = json.loads((args.dots / "sensor.json").read_text())["conditions"]
    out = {"dots": 10000, "n_instance_views": len(keys), "scenes": sorted({int(s) for s in scenes}),
           "recall_5mm": {c: float(np.mean([ok(base[c][k]) for k in keys])) for c in base}, "against_baseline": {},
           "part_pixel_classes": {c: {**v["classes"], "invalid_frac": v["parts"]["invalid_frac"], "frac_gt_5mm": v["parts"]["frac_gt_5mm"], "median_signed_mm": v["parts"].get("median_signed_mm")}
                                  for c, v in sensor.items()},
           "ir_appearance": json.loads((args.dots / "ir_appearance.json").read_text()),
           "commits": sorted({m["commit"] for m in metas.values()}), "dirty_tree_any": any(m["dirty_tree"] for m in metas.values())}
    for c, b0 in (("C3dots10k", "C3"), ("C4dots10k", "C4")):
        a = np.array([ok(base[b0][k]) for k in keys], bool)
        b = np.array([ok(runs[c][k]) for k in keys], bool)
        lo, hi = scene_bootstrap_ci(b.astype(float) - a.astype(float), scenes, cfg["statistics"]["bootstrap_resamples"], g)
        m = mcnemar_exact(b, a)
        out["recall_5mm"][c] = float(b.mean())
        out["against_baseline"][c] = {"baseline": b0, "diff": float(b.mean() - a.mean()), "ci95": [lo, hi], "p": m["p"], "n_up": m["n_a_only"], "n_down": m["n_b_only"], "excludes_zero": not lo <= 0.0 <= hi,
                                      "profile": float(b[types == "profile"].mean()), "bracket": float(b[types == "bracket"].mean())}
    d3, d4 = out["against_baseline"]["C3dots10k"], out["against_baseline"]["C4dots10k"]
    out["order_held"] = out["recall_5mm"]["C3dots10k"] < out["recall_5mm"]["C4dots10k"] < out["recall_5mm"]["C2b"]
    out["reading"] = "dot density moves recall on these seeds" if d3["excludes_zero"] or d4["excludes_zero"] else "no detectable effect of dot density on these seeds"
    out["note"] = "Descriptive, 10 scenes. Replaces no primary number. New render, so the difference also holds render repeat. Reading fixed in advance in A-74."
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("n_instance_views", "recall_5mm", "against_baseline", "order_held", "reading")}))


if __name__ == "__main__":
    main()
