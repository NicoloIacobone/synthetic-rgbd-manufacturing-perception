"""Statistics of the experiment (PLAN §5.5, §5.12) from the Task A and Task B result files.

Usage: .venv/bin/python scripts/stats_m5.py <results_dir> --out <json>

Reads <results_dir>/A_<condition>_<mm>.jsonl (scripts/pose_eval.py) and B_<condition>.jsonl (scripts/suction_eval.py).
The unit is the instance-view; a missing estimate is a failure (§5.12). Scene bootstrap: 10 000 resamples from the
"bootstrap" stream; A-31 stability is checked with a second stream. McNemar: exact, per instance-view; it ignores
scene clustering, so a comparison in the fixed sequence **rejects only if p < alpha and the scene-bootstrap CI excludes
0** (the stricter reading of §5.5, which lists both). Fixed sequence on A1 recall@5 mm: C1 vs C3, C2b vs C3, C3 vs C4.
MDE (A-18) from the observed discordance, for n = instance-views and for n = scenes.
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
from synthrgbd.stats import fixed_sequence, mcnemar_exact, mde_mcnemar, scene_bootstrap_ci  # noqa: E402

SEQUENCE = [("C1", "C3"), ("C2b", "C3"), ("C3", "C4")]
DESCRIPTIVE_PAIRS = [("C1", "C2a"), ("C1", "C2b"), ("C2a", "C3"), ("C4", "C4bright"), ("C3", "C3r02"), ("C3", "C3r04"), ("C3", "C3nogloss")]


def load(path):
    lines = path.read_text().splitlines()
    return json.loads(lines[0])["meta"], [json.loads(x) for x in lines[1:]]


def key(r):
    return r["scene"], r["im_id"], r["gt_id"]


def recall_table(rows, thr, n_boot, g):
    def block(sel):
        if not sel:
            return {"n": 0}
        x = np.array([r.get("mssd_mm") is not None and r["mssd_mm"] < thr for r in sel], float)
        s = np.array([r["scene"] for r in sel])
        lo, hi = scene_bootstrap_ci(x, s, n_boot, g)
        return {"n": len(sel), "recall": float(x.mean()), "ci95": [lo, hi]}
    return {"all": block(rows), "profile": block([r for r in rows if r["type"] == "profile"]),
            "bracket": block([r for r in rows if r["type"] == "bracket"])}


def compare(a_rows, b_rows, succ, n_boot, g):
    """a minus b, paired by instance-view; both files must hold the same instance-views."""
    if [key(r) for r in a_rows] != [key(r) for r in b_rows]:
        raise ValueError("instance-views differ between conditions: pairing broken")
    a, b = np.array([succ(r) for r in a_rows], bool), np.array([succ(r) for r in b_rows], bool)
    s = np.array([r["scene"] for r in a_rows])
    d = a.astype(float) - b.astype(float)
    lo, hi = scene_bootstrap_ci(d, s, n_boot, g)
    m = mcnemar_exact(a, b)
    return {"rate_a": float(a.mean()), "rate_b": float(b.mean()), "diff": float(d.mean()), "ci95": [lo, hi], **m,
            "n": len(a), "n_scenes": int(len(np.unique(s))),
            "mde_instance_views": mde_mcnemar(m["discordance"], len(a)), "mde_scenes": mde_mcnemar(m["discordance"], len(np.unique(s)))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg = load_config()
    n_boot, master = cfg["statistics"]["bootstrap_resamples"], cfg["seeds"]["master"]
    thr, thr2 = cfg["task_a"]["recall_threshold_mm"], cfg["task_a"]["secondary_threshold_mm"]
    alpha = 1 - cfg["statistics"]["ci"]
    g = rng(master, 0, 0, "bootstrap")
    A, metas = {}, {}
    for f in sorted(args.results.glob("A_*_*.jsonl")):
        _, cond, mm = f.stem.split("_")
        metas[f.stem], A[(cond, int(mm))] = load(f)
    B = {f.stem.split("_")[1]: load(f)[1] for f in sorted(args.results.glob("B_*.jsonl"))}
    out = {"n_bootstrap": n_boot, "alpha": alpha, "tables": {}}
    succ5 = lambda r: r.get("mssd_mm") is not None and r["mssd_mm"] < thr      # noqa: E731
    conds = sorted({c for c, _ in A})
    primary = {c: A[(c, 10)] for c in conds if (c, 10) in A}
    any_rows = next(iter(primary.values()))
    meta_any = next(iter(metas.values()))
    out["unit"] = {"instance_views": len(any_rows), "scenes": len({r["scene"] for r in any_rows}),
                   "excluded_visib_lt_0.1": len(meta_any["skipped"]),
                   "profile": sum(r["type"] == "profile" for r in any_rows), "bracket": sum(r["type"] == "bracket" for r in any_rows)}
    out["commits"] = sorted({m["commit"] for m in metas.values()})
    out["dirty_tree_any"] = any(m["dirty_tree"] for m in metas.values())

    out["A1_recall_5mm"] = {c: recall_table(primary[c], thr, n_boot, g) for c in primary}
    out["A1_recall_2mm"] = {c: recall_table(primary[c], thr2, n_boot, g) for c in primary}
    out["sweep_recall_5mm"] = {c: {str(mm): recall_table(A[(c, mm)], thr, n_boot, g)["all"] for mm in (2, 5, 10, 20) if (c, mm) in A} for c in conds}
    out["sweep_recall_5mm_by_type"] = {c: {str(mm): {t: recall_table(A[(c, mm)], thr, n_boot, g)[t] for t in ("profile", "bracket")}
                                           for mm in (2, 5, 10, 20) if (c, mm) in A} for c in conds}

    seq = [compare(primary[a], primary[b], succ5, n_boot, g) for a, b in SEQUENCE]
    rejected = [r["p"] < alpha and not (r["ci95"][0] <= 0 <= r["ci95"][1]) for r in seq]
    status = fixed_sequence(rejected)
    out["fixed_sequence"] = [{"a": a, "b": b, "status": st, "test_rejects": bool(rj), **r} for (a, b), r, rj, st in zip(SEQUENCE, seq, rejected, status)]
    g2 = rng(master, 0, 1, "bootstrap")
    out["ci_stability_second_stream"] = [{"a": a, "b": b, "ci95": compare(primary[a], primary[b], succ5, n_boot, g2)["ci95"]} for a, b in SEQUENCE]
    out["A1_descriptive_pairs"] = [{"a": a, "b": b, **compare(primary[a], primary[b], succ5, n_boot, g)} for a, b in DESCRIPTIVE_PAIRS if a in primary and b in primary]

    # Secondary: pose errors and the profile axis (§5.4, A-47)
    sec = {}
    for c, rows in primary.items():
        ok = [r for r in rows if r.get("mssd_mm") is not None]
        prof = [r for r in ok if r["type"] == "profile" and "centre_err_axial_mm" in r]
        sec[c] = {"failed_or_no_estimate": len(rows) - len(ok),
                  "median_mssd_mm": float(np.median([r["mssd_mm"] for r in ok])) if ok else None,
                  "median_t_err_mm": float(np.median([r["t_err_mm"] for r in ok])) if ok else None,
                  "median_R_err_deg": float(np.median([r["R_err_deg"] for r in ok])) if ok else None,
                  "profile_median_axial_mm": float(np.median([r["centre_err_axial_mm"] for r in prof])) if prof else None,
                  "profile_median_across_mm": float(np.median([r["centre_err_across_mm"] for r in prof])) if prof else None}
    out["A1_secondary"] = sec

    if B:
        succ = lambda r: bool(r["success"])          # noqa: E731
        tb = {}
        for c, rows in B.items():
            tb[c] = {}
            for t, sel in (("all", rows), ("profile", [r for r in rows if r["type"] == "profile"]), ("bracket", [r for r in rows if r["type"] == "bracket"])):
                x = np.array([succ(r) for r in sel], float)
                s = np.array([r["scene"] for r in sel])
                tb[c][t] = {"n": len(sel), "success": float(x.mean()), "ci95": list(scene_bootstrap_ci(x, s, n_boot, g)),
                            "has_grasp": float(np.mean([r["has_grasp"] for r in sel]))}
        out["B_success"] = tb
        out["B_pairs_bracket"] = []
        for a, b in SEQUENCE + DESCRIPTIVE_PAIRS:
            if a in B and b in B:
                aa = [r for r in B[a] if r["type"] == "bracket"]
                bb = [r for r in B[b] if r["type"] == "bracket"]
                out["B_pairs_bracket"].append({"a": a, "b": b, **compare(aa, bb, succ, n_boot, g)})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1))
    print("WROTE", args.out)


if __name__ == "__main__":
    main()
