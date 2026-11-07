"""One repeat of the ICP on identical depth (A-72, ledger "ICP repeat"): how much of the primary result is ICP repeatability? Descriptive.

Usage: .venv/bin/python scripts/icp_repeat_summary.py <results_dir> <repeat_dir> --out <json>

Same stored depth, offsets and harness; only the ICP is run again. Per condition: recall in both runs, instance-views that change
side of 5 mm, instance-views whose MSSD moves more than 0.01 mm. Then the fixed sequence on the repeat, by the rule of the primary run
(exact McNemar p < 0.05 and scene-bootstrap CI excluding 0). Replaces no primary number.
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

CONDITIONS = ("C1", "C2b", "C3", "C4")
SEQUENCE = (("C1", "C3"), ("C2b", "C3"), ("C3", "C4"))
THR_MM = 5.0
MOVED_MM = 0.01


def load(path):
    lines = path.read_text().splitlines()
    return json.loads(lines[0])["meta"], [json.loads(x) for x in lines[1:]]


def key(r):
    return r["scene"], r["im_id"], r["gt_id"]


def ok(rows):
    return np.array([r.get("mssd_mm") is not None and r["mssd_mm"] < THR_MM for r in rows], bool)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("repeat", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg = load_config()
    n_boot = cfg["statistics"]["bootstrap_resamples"]
    g = rng(cfg["seeds"]["master"], 0, 4, "bootstrap")
    out = {"threshold_mm": THR_MM, "moved_mm": MOVED_MM, "conditions": {}, "commits": set(), "dirty_tree_any": False}
    rows_rep = {}
    for c in CONDITIONS:
        _, a = load(args.results / f"A_{c}_10.jsonl")
        meta, b = load(args.repeat / f"A_{c}_10.jsonl")
        if [key(r) for r in a] != [key(r) for r in b]:
            raise ValueError(f"{c}: instance-views differ between the runs")
        out["commits"].add(meta["commit"])
        out["dirty_tree_any"] |= bool(meta["dirty_tree"])
        rows_rep[c] = b
        oa, ob = ok(a), ok(b)
        ma = np.array([np.nan if r.get("mssd_mm") is None else r["mssd_mm"] for r in a], float)
        mb = np.array([np.nan if r.get("mssd_mm") is None else r["mssd_mm"] for r in b], float)
        one_missing = np.isnan(ma) != np.isnan(mb)
        moved = one_missing | (np.abs(np.nan_to_num(ma) - np.nan_to_num(mb)) > MOVED_MM)
        out["conditions"][c] = {"n": len(a), "recall_primary": float(oa.mean()), "recall_repeat": float(ob.mean()),
                                "side_changes": int((oa != ob).sum()), "up": int((ob & ~oa).sum()), "down": int((oa & ~ob).sum()),
                                "moved_gt_0.01mm": int(moved.sum()), "max_abs_d_mssd_mm": float(np.nanmax(np.abs(ma - mb))),
                                "no_estimate_primary": int(np.isnan(ma).sum()), "no_estimate_repeat": int(np.isnan(mb).sum())}
    out["fixed_sequence_repeat"] = []
    for x, y in SEQUENCE:
        a, b = ok(rows_rep[x]), ok(rows_rep[y])
        s = np.array([r["scene"] for r in rows_rep[x]])
        lo, hi = scene_bootstrap_ci(a.astype(float) - b.astype(float), s, n_boot, g)
        m = mcnemar_exact(a, b)
        out["fixed_sequence_repeat"].append({"a": x, "b": y, "diff": float(a.mean() - b.mean()), "ci95": [lo, hi], "p": m["p"],
                                             "rejects": bool(m["p"] < 0.05 and not lo <= 0.0 <= hi)})
    out["commits"] = sorted(out["commits"])
    out["note"] = "Descriptive. Same depth, offsets and harness as the primary run; only the ICP is repeated. Replaces no primary number."
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out)[:1200])


if __name__ == "__main__":
    main()
