"""§5.11 diagnosis (A-62, ledger): zero-offset ICP on C1 for the pre-declared candidates and the H2 controls.

Usage: .venv/bin/python scripts/sanity_candidates.py <dataset_root> <out_dir> <first_seed> <last_seed>

Calls scripts/pose_eval.py directly, one process at a time. It does not use run_eval.py, which goes on to recall
at real offsets as soon as a sanity check passes. Existing outputs are kept and the failed run in
<dataset_root>/results is refused as a target. Per run: <out_dir>/<name>.jsonl and <out_dir>/logs/<name>.log;
<out_dir>/runs.json records thread settings and wall time.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from select_harness import C2F, CANDIDATES

REPO = Path(__file__).resolve().parents[1]
PY = str(REPO / ".venv" / "bin" / "python")
H2 = CANDIDATES["H2_c2f_raycast"]
LM = {"solver": "lm", "stages": C2F, "visibility": "backface", "o3d_step_clamp": False}
# name, ICP override over configs/harness.yaml, OMP_NUM_THREADS (None = not set, as select_harness.py ran on dev).
RUNS = [
    ("H2_repeat_omp2", H2, "2"),
    ("H2_omp1", H2, "1"),
    ("H2_ompdefault", H2, None),
    ("H0", CANDIDATES["H0_single_15_5"], "2"),
    ("H1", CANDIDATES["H1_c2f"], "2"),
    ("H3", CANDIDATES["H3_c2f_raycast_clamp"], "2"),
    ("lm", LM, "2"),
]


def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    first, last = int(sys.argv[3]), int(sys.argv[4])
    if out.resolve() == (root / "results").resolve():
        raise SystemExit("refusing to write into the folder of the failed run")
    (out / "logs").mkdir(parents=True, exist_ok=True)
    seeds = [str(s) for s in range(first, last + 1)]
    index = out / "runs.json"
    runs = json.loads(index.read_text()) if index.exists() else {}
    for name, override, omp in RUNS:
        target = out / f"{name}.jsonl"
        if target.exists():
            print(name, "kept", flush=True)
            continue
        env = {k: v for k, v in os.environ.items() if k != "OMP_NUM_THREADS"}
        if omp is not None:
            env["OMP_NUM_THREADS"] = omp
        tmp = target.with_suffix(".tmp")
        t = time.perf_counter()
        with open(out / "logs" / f"{name}.log", "w") as log:
            subprocess.run([PY, str(REPO / "scripts" / "pose_eval.py"), str(root), *seeds, "--condition", "C1",
                            "--offset", "0", "0", "--icp-override", json.dumps(override), "--out", str(tmp)],
                           env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        tmp.rename(target)
        runs[name] = {"override": override, "OMP_NUM_THREADS": omp, "wall_s": time.perf_counter() - t}
        index.write_text(json.dumps(runs, indent=1))
        print(name, f"done in {runs[name]['wall_s']:.0f} s", flush=True)
    print("ALL_DONE", flush=True)


if __name__ == "__main__":
    main()
