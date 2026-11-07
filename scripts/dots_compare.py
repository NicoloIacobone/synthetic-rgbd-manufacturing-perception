"""Control and denser pattern of the dot-density test on seeds 0-9 (A-76), descriptive.

Usage: .venv/bin/python scripts/dots_compare.py <test_root> --out <json>

Reads the primary results and the three dot runs, all paired on the same instance-views: (1) repeat, control at 30 000 minus primary; (2) density,
10 000 and 60 000 minus the control on the same path; (3) stereo against noise, C4 at each density minus C2b. The readings are fixed in A-76.
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
DENSITIES = (10000, 30000, 60000)


def load(path):
    lines = path.read_text().splitlines()
    return {(r["scene"], r["im_id"], r["gt_id"]): r for r in map(json.loads, lines[1:])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg = load_config()
    g = rng(cfg["seeds"]["master"], 0, 10, "bootstrap")
    runs = {c: load(args.root / "results" / f"A_{c}_10.jsonl") for c in ("C1", "C2b", "C3", "C4")}
    for n in DENSITIES:
        for m in ("C3", "C4"):
            c = f"{m}dots{n // 1000}k"
            runs[c] = load(args.root / f"results_dots{n}" / f"A_{c}_10.jsonl")
    keys = sorted(runs["C3dots30k"])
    if any(not set(keys) <= set(r) for r in runs.values()) or any(len(runs[c]) != len(keys) for c in runs if "dots" in c):
        raise ValueError("instance-views differ")
    scenes = np.array([k[0] for k in keys])
    hit = {c: np.array([r[k].get("mssd_mm") is not None and r[k]["mssd_mm"] < THR_MM for k in keys], bool) for c, r in runs.items()}

    def paired(b, a):
        """b minus a: difference in recall, interval over scenes, exact McNemar."""
        lo, hi = scene_bootstrap_ci(hit[b].astype(float) - hit[a].astype(float), scenes, cfg["statistics"]["bootstrap_resamples"], g)
        m = mcnemar_exact(hit[b], hit[a])
        return {"recall": float(hit[b].mean()), "against": a, "recall_against": float(hit[a].mean()), "diff": float(hit[b].mean() - hit[a].mean()), "ci95": [lo, hi], "p": m["p"],
                "n_up": m["n_a_only"], "n_down": m["n_b_only"], "excludes_zero": not lo <= 0.0 <= hi}

    out = {"n_instance_views": len(keys), "scenes": sorted({int(s) for s in scenes}), "recall_5mm": {c: float(v.mean()) for c, v in hit.items()},
           "repeat": {m: paired(f"{m}dots30k", m) for m in ("C3", "C4")},
           "density": {str(n): {m: paired(f"{m}dots{n // 1000}k", f"{m}dots30k") for m in ("C3", "C4")} for n in (10000, 60000)},
           "stereo_vs_noise": {"primary": paired("C4", "C2b"), **{str(n): paired(f"C4dots{n // 1000}k", "C2b") for n in DENSITIES}},
           "order_held": {str(n): bool(hit[f"C3dots{n // 1000}k"].mean() < hit[f"C4dots{n // 1000}k"].mean() < hit["C2b"].mean()) for n in DENSITIES}}

    def word(v):
        return "holds" if v["ci95"][1] < 0.0 else "reversed" if v["ci95"][0] > 0.0 else "not shown on ten scenes"

    out["reading"] = {"repeat": "a repeat render alone moves recall on these seeds" if any(v["excludes_zero"] for v in out["repeat"].values()) else "no detectable effect of a repeat render on these seeds",
                      "density": {n: {m: "this density moves recall on this material" if v["excludes_zero"] else "no detectable effect on this material against the control" for m, v in d.items()}
                                  for n, d in out["density"].items()},
                      "stereo_vs_noise": {n: word(out["stereo_vs_noise"][n]) for n in ("primary", *map(str, DENSITIES))}}
    out["note"] = "Descriptive, 10 scenes. Replaces no primary number. Reading fixed in advance in A-76."
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("n_instance_views", "recall_5mm", "order_held", "reading")}))


if __name__ == "__main__":
    main()
