"""§5.11 diagnosis (A-62, ledger): zero-offset ICP on C1 for the pre-declared candidates and the H2 controls.

Usage: .venv/bin/python scripts/sanity_candidates.py <dataset_root> <out_dir> <first_seed> <last_seed> <round>

<round>: "first" (data/m5/diag_sanity, commit 04faf51) or "second" (data/m5/diag_sanity_fix, after the cache fix and with
200 000 CAD samples). The second round also replays H2 instrumented, at 1 thread, to check the fix.

Calls scripts/pose_eval.py directly, one process at a time. It does not use run_eval.py, which goes on to recall
at real offsets as soon as a sanity check passes. Existing outputs are kept and the failed run in
<dataset_root>/results is refused as a target. Per run: <out_dir>/<name>.jsonl and <out_dir>/logs/<name>.log;
<out_dir>/runs.json records thread settings and wall time, <out_dir>/summary.json the pass/fail table.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from select_harness import C2F, CANDIDATES

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.config import load_config  # noqa: E402

PY = str(REPO / ".venv" / "bin" / "python")
H2 = CANDIDATES["H2_c2f_raycast"]
LM = {"solver": "lm", "stages": C2F, "visibility": "backface", "o3d_step_clamp": False}
# name, ICP override over configs/harness.yaml, OMP_NUM_THREADS (None = not set, as select_harness.py ran on dev).
H0, H1, H3 = CANDIDATES["H0_single_15_5"], CANDIDATES["H1_c2f"], CANDIDATES["H3_c2f_raycast_clamp"]
ROUNDS = {
    "first": [("H2_repeat_omp2", H2, "2"), ("H2_omp1", H2, "1"), ("H2_ompdefault", H2, None),
              ("H0", H0, "2"), ("H1", H1, "2"), ("H3", H3, "2"), ("lm", LM, "2")],
    "second": [("H0", H0, "2"), ("H1", H1, "2"), ("H2", H2, "2"), ("H3", H3, "2")],
}
OWN_EXTENT_MM = {1: 60.0, 2: 100.0, 3: 150.0, 4: 30.0}


def load_rows(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines()[1:]]


def key(r: dict) -> tuple:
    return r["scene"], r["im_id"], r["gt_id"]


def mssd_of(r: dict) -> float:
    return r["mssd_mm"] if r["mssd_mm"] is not None else np.inf


def summarise(root: Path, out: Path, names: list[str]) -> None:
    """Pass/fail by the frozen §5.11 threshold, plus overlap with the failed run. Nothing here ranks candidates."""
    s = load_config()["sanity"]
    max_mm, min_frac = s["c1_zero_offset_max_mssd_mm"], s["c1_zero_offset_min_fraction"]
    failed_run = {key(r) for r in load_rows(root / "results" / "sanity_C1_zero.jsonl") if mssd_of(r) >= max_mm}
    table = {}
    for name in names:
        rows = load_rows(out / f"{name}.jsonl")
        ms = np.array([mssd_of(r) for r in rows])
        fails = [r for r, m in zip(rows, ms) if m >= max_mm]
        table[name] = {"n": len(rows), "ok": int((ms < max_mm).sum()), "frac": float((ms < max_mm).mean()),
                       "pass": bool((ms < max_mm).mean() >= min_frac), "fail_ge5": int((ms >= 5).sum()),
                       "no_estimate": int(np.isinf(ms).sum()), "median_mm": float(np.median(ms)), "max_mm": float(ms.max()),
                       "fails_by_obj": {str(o): sum(r["obj_id"] == o for r in fails) for o in OWN_EXTENT_MM},
                       "fails_also_in_failed_run": sum(key(r) in failed_run for r in fails),
                       "fails": [{"key": key(r), "obj": r["obj_id"], "mssd": r["mssd_mm"], "axial": r.get("centre_err_axial_mm"),
                                  "across": r.get("centre_err_across_mm"), "R": r.get("R_err_deg"), "fit": r.get("fitness")} for r in fails]}
        print(name, json.dumps({k: v for k, v in table[name].items() if k != "fails"}), flush=True)
    if (out / "H2_replay_meshes.json").exists():
        rows = load_rows(out / "H2_replay.jsonl")
        used = [c[0][1] for c in json.loads((out / "H2_replay_meshes.json").read_text())]
        a, b = np.array([mssd_of(r) for r in rows]), np.array([mssd_of(r) for r in load_rows(out / "H2.jsonl")])
        table["H2_replay_control"] = {
            "instance_views": len(rows), "not_on_own_mesh": sum(u != OWN_EXTENT_MM[r["obj_id"]] for u, r in zip(used, rows)),
            "n_differ_gt_1e-9mm_from_H2": int((np.abs(a - b) > 1e-9).sum()), "max_abs_diff_mm": float(np.abs(a - b).max())}
        print("H2_replay_control", json.dumps(table["H2_replay_control"]), flush=True)
    (out / "summary.json").write_text(json.dumps(table, indent=1))


def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    first, last, round_ = int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    if out.resolve() == (root / "results").resolve():
        raise SystemExit("refusing to write into the folder of the failed run")
    (out / "logs").mkdir(parents=True, exist_ok=True)
    seeds = [str(s) for s in range(first, last + 1)]
    index = out / "runs.json"
    runs = json.loads(index.read_text()) if index.exists() else {}
    for name, override, omp in ROUNDS[round_]:
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
    if round_ == "second" and not (out / "H2_replay.jsonl").exists():
        with open(out / "logs" / "H2_replay.log", "w") as log:
            subprocess.run([PY, str(REPO / "scripts" / "sanity_diagnosis.py"), "replay", str(root), str(out), str(first), str(last)],
                           env=dict(os.environ, OMP_NUM_THREADS="1"), stdout=log, stderr=subprocess.STDOUT, check=True)
    summarise(root, out, [name for name, _, _ in ROUNDS[round_]])
    print("ALL_DONE", flush=True)


if __name__ == "__main__":
    main()
