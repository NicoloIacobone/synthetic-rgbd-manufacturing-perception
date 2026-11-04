"""Run Task A and Task B over the conditions, a few jobs at a time (8 GB machine); finished result files are kept.

Usage: .venv/bin/python scripts/run_eval.py <dataset_root> <results_dir> <first_seed> <last_seed>
           [--conditions C1 C2a ...] [--offsets 2 5 10 20] [--no-task-b] [--jobs 3] [--harness <yaml>]

The §5.11 zero-offset check on C1 runs first; if it fails nothing else runs (a failed check is treated as a bug).
Results: <results_dir>/sanity_C1_zero.jsonl, A_<condition>_<mm>.jsonl, B_<condition>.jsonl; logs: <results_dir>/logs/.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.conditions import PROTOCOL_CONDITIONS  # noqa: E402

PY = str(REPO / ".venv" / "bin" / "python")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("results", type=Path)
    ap.add_argument("first", type=int)
    ap.add_argument("last", type=int)
    ap.add_argument("--conditions", nargs="+", default=list(PROTOCOL_CONDITIONS))
    ap.add_argument("--offsets", type=int, nargs="+", default=[2, 5, 10, 20])
    ap.add_argument("--no-task-b", action="store_true")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--harness", type=Path, default=REPO / "configs" / "harness.yaml")
    args = ap.parse_args()
    (args.results / "logs").mkdir(parents=True, exist_ok=True)
    seeds = [str(s) for s in range(args.first, args.last + 1)]
    env = dict(os.environ, OMP_NUM_THREADS="2")

    def run(name, cmd):
        out = args.results / f"{name}.jsonl"
        if out.exists():
            return name, "kept", 0.0
        tmp = out.with_suffix(".tmp")
        t = time.perf_counter()
        with open(args.results / "logs" / f"{name}.log", "w") as log:
            subprocess.run([PY, *cmd, "--harness", str(args.harness), "--out", str(tmp)], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        tmp.rename(out)
        return name, "done", time.perf_counter() - t

    pose, suction = str(REPO / "scripts" / "pose_eval.py"), str(REPO / "scripts" / "suction_eval.py")
    print(run("sanity_C1_zero", [pose, str(args.root), *seeds, "--condition", "C1", "--offset", "0", "0"]), flush=True)
    rows = [json.loads(x) for x in (args.results / "sanity_C1_zero.jsonl").read_text().splitlines()[1:]]
    frac = sum(r["mssd_mm"] is not None and r["mssd_mm"] < 0.5 for r in rows) / len(rows)
    print(f"SANITY n={len(rows)} frac_lt_0.5mm={frac:.4f}", flush=True)
    if frac < 0.99:
        raise SystemExit("§5.11 sanity check failed: treat as a bug, stop")
    jobs = [(f"A_{c}_{mm}", [pose, str(args.root), *seeds, "--condition", c, "--offset", str(mm), str(mm)])
            for mm in sorted(args.offsets, key=lambda m: m != 10) for c in args.conditions]
    if not args.no_task_b:
        jobs += [(f"B_{c}", [suction, str(args.root), *seeds, "--condition", c]) for c in args.conditions]
    with ThreadPoolExecutor(args.jobs) as ex:
        for res in ex.map(lambda j: run(*j), jobs):
            print(res, flush=True)
    print("ALL_DONE", flush=True)


if __name__ == "__main__":
    main()
