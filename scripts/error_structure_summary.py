"""Error structure check (A-73): recall of the surrogates against C3 on the same instance-views, with the reading fixed in the ledger.

Usage: .venv/bin/python scripts/error_structure_summary.py <results_dir> <check_dir> --out <json>
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
    ap.add_argument("check", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg = load_config()
    g = rng(cfg["seeds"]["master"], 0, 6, "bootstrap")
    metas, runs = {}, {}
    for c in ("C3shuf", "C3sym"):
        metas[c], runs[c] = load(args.check / f"A_{c}_10.jsonl")
    keys = sorted(runs["C3shuf"])
    if sorted(runs["C3sym"]) != keys:
        raise ValueError("instance-views differ")
    _, base = load(args.results / "A_C3_10.jsonl")
    _, c4 = load(args.results / "A_C4_10.jsonl")
    scenes = np.array([k[0] for k in keys])
    types = np.array([base[k]["type"] for k in keys])
    a = np.array([ok(base[k]) for k in keys], bool)
    out = {"n_instance_views": len(keys), "scenes": sorted(set(int(s) for s in scenes)), "recall_5mm": {"C3": float(a.mean()), "C4": float(np.mean([ok(c4[k]) for k in keys]))},
           "median_mssd_mm": {"C3": float(np.median([1e9 if base[k].get("mssd_mm") is None else base[k]["mssd_mm"] for k in keys]))}, "against_C3": {},
           "commits": sorted({m["commit"] for m in metas.values()}), "dirty_tree_any": any(m["dirty_tree"] for m in metas.values())}
    for c, run in runs.items():
        b = np.array([ok(run[k]) for k in keys], bool)
        lo, hi = scene_bootstrap_ci(b.astype(float) - a.astype(float), scenes, cfg["statistics"]["bootstrap_resamples"], g)
        m = mcnemar_exact(b, a)
        out["recall_5mm"][c] = float(b.mean())
        out["median_mssd_mm"][c] = float(np.median([1e9 if run[k].get("mssd_mm") is None else run[k]["mssd_mm"] for k in keys]))
        out["against_C3"][c] = {"diff": float(b.mean() - a.mean()), "ci95": [lo, hi], "p": m["p"], "n_up": m["n_a_only"], "n_down": m["n_b_only"], "excludes_zero": not lo <= 0.0 <= hi,
                                "profile": float(b[types == "profile"].mean()), "bracket": float(b[types == "bracket"].mean())}
    shuf, sym = out["against_C3"]["C3shuf"], out["against_C3"]["C3sym"]
    up = lambda x: x["excludes_zero"] and x["diff"] > 0   # noqa: E731
    out["reading"] = ("coherence matters" if up(shuf) else "one-sidedness matters" if up(sym) else "claim refuted: the size of the error is enough")
    out["note"] = "Descriptive, 10 scenes. Replaces no primary number. Reading fixed in advance in the ledger, row Error structure check (A-73)."
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("recall_5mm", "median_mssd_mm", "against_C3", "reading")}))


if __name__ == "__main__":
    main()
