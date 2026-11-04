"""Pooled worst-case harness selection on the dev split (tuning ledger A-45), Task A and Task B.

Usage: .venv/bin/python scripts/select_harness.py <dataset_root> <dev_seed>... --out <dir>

Task A: for every ICP candidate in CANDIDATES, run scripts/pose_eval.py on each condition C1, C2a, C2b, C3, C4
at the primary offset (10 mm / 10 deg) and the zero-offset C1 sanity check (§5.11). The chosen candidate
maximises the MINIMUM recall@5 mm over the five conditions among candidates that pass the sanity check;
ties -> the earlier candidate in the list (simpler first).
Task B: the same rule over GRASP_POINTS on bracket success.
Candidates and the grid are fixed here before the run (ledger). Results: <out>/selection.json.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONDITIONS = ["C1", "C2a", "C2b", "C3", "C4"]
C2F = [[20, 20], [10, 10], [5, 5]]
CANDIDATES = {          # simpler first
    "H0_single_15_5": {},
    "H1_c2f": {"stages": C2F},
    "H2_c2f_raycast": {"stages": C2F, "visibility": "raycast"},
    "H3_c2f_raycast_clamp": {"stages": C2F, "visibility": "raycast", "o3d_step_clamp": True},
}
GRASP_POINTS = ["plane_fit", "raw"]   # tie -> plane_fit (ledger)


def summary(path: Path) -> dict:
    rows = [json.loads(l) for l in path.read_text().splitlines()[1:]]
    ok = [r["mssd_mm"] is not None and r["mssd_mm"] < 5.0 for r in rows]
    return {"n": len(rows), "recall5": sum(ok) / len(rows) if rows else float("nan"),
            "recall_sanity": sum(r["mssd_mm"] is not None and r["mssd_mm"] < 0.5 for r in rows) / len(rows)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("seeds", nargs="+")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    py = str(REPO / ".venv" / "bin" / "python")
    res = {"task_a": {}, "task_b": {}}
    for name, ov in CANDIDATES.items():
        r = {}
        for cond, off in [("C1_zero", ["0", "0"])] + [(c, ["10", "10"]) for c in CONDITIONS]:
            c = "C1" if cond == "C1_zero" else cond
            out = args.out / f"A_{name}_{cond}.jsonl"
            subprocess.run([py, str(REPO / "scripts" / "pose_eval.py"), str(args.root), *args.seeds, "--condition", c,
                            "--offset", *off, "--icp-override", json.dumps(ov), "--out", str(out)],
                           check=True, capture_output=True)
            r[cond] = summary(out)
        r["sanity_pass"] = r["C1_zero"]["recall_sanity"] >= 0.99
        r["min_recall5"] = min(r[c]["recall5"] for c in CONDITIONS)
        res["task_a"][name] = r
        print(name, json.dumps({c: round(r[c]["recall5"], 3) for c in CONDITIONS}), "min", round(r["min_recall5"], 3),
              "sanity", r["sanity_pass"], flush=True)
    ok = [n for n in CANDIDATES if res["task_a"][n]["sanity_pass"]]
    best = max(ok, key=lambda n: (res["task_a"][n]["min_recall5"], -list(CANDIDATES).index(n)))
    res["task_a_chosen"] = best
    for gp in GRASP_POINTS:
        r = {}
        for cond in CONDITIONS:
            out = args.out / f"B_{gp}_{cond}.jsonl"
            hc = json.loads(json.dumps(__import__("yaml").safe_load(open(REPO / "configs" / "harness.yaml"))))
            hc["suction"]["grasp_point"] = gp
            tmp = args.out / f"harness_{gp}.yaml"
            tmp.write_text(__import__("yaml").safe_dump(hc))
            subprocess.run([py, str(REPO / "scripts" / "suction_eval.py"), str(args.root), *args.seeds, "--condition",
                            cond, "--harness", str(tmp), "--out", str(out)], check=True, capture_output=True)
            rows = [json.loads(l) for l in out.read_text().splitlines()[1:]]
            br = [x for x in rows if x["type"] == "bracket"]
            r[cond] = {"n_bracket": len(br), "bracket_success": sum(x["success"] for x in br) / max(len(br), 1)}
        r["min_bracket_success"] = min(r[c]["bracket_success"] for c in CONDITIONS)
        res["task_b"][gp] = r
        print("B", gp, json.dumps({c: round(r[c]["bracket_success"], 3) for c in CONDITIONS}), flush=True)
    res["task_b_chosen"] = max(GRASP_POINTS, key=lambda g: (res["task_b"][g]["min_bracket_success"],
                                                            -GRASP_POINTS.index(g)))
    (args.out / "selection.json").write_text(json.dumps(res, indent=1))
    print("CHOSEN", res["task_a_chosen"], res["task_b_chosen"])


if __name__ == "__main__":
    main()
