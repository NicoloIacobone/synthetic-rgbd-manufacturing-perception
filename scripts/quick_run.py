"""Quick run: one sample scene, no Blender, a few minutes. Computes depth, runs pose and suction evaluation, compares with the committed numbers.

Usage: .venv/bin/python scripts/quick_run.py [--sample <path or URL>] [--expected <json>] [--jobs 3] [--rule auto|exact|tolerance]

Without --sample: dist/sample_scene_seed0.tar.gz if it exists, otherwise SAMPLE_SCENE_URL below. The archive is checked against the SHA-256 in
the expected file before it is opened. Everything is written to outputs/quick_run/, which is wiped first; the repository is not touched.
For conditions C1, C2a, C2b, C3, C4: depth from the stored IR images (stereo, C3 and C4) or from the ideal depth (C2), then ICP at
10 mm / 10 deg and the suction planner, compared with the committed numbers of the full run.
On macOS arm64, where the expected numbers were computed, PASS (A-71, A-72) if, for every condition: the depth pixels are identical; every suction outcome matches; and for ICP the median |delta MSSD| over
the instance-views is at most 0.01 mm and at most one instance-view changes side of 5 mm. ICP is not strictly repeatable on identical depth: on unstable
views, mostly brackets that have already failed, repeated runs differ by tens of mm, so an exact per-view rule would fail by construction.
Elsewhere OpenCV and Open3D can take other code paths, so identical pixels are not promised, and PASS (A-77) if, for every condition: each view's share of valid depth
pixels is within 0.5 points and its 5th, 50th and 95th depth percentiles within 1 mm; recall and suction successes are within one instance-view; the median |delta MSSD| is at most 0.5 mm.
Exit code 0 on PASS, 1 on FAIL, 2 if the sample cannot be found.
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median

import cv2

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.conditions import DEPTH_DIRS  # noqa: E402
from synthrgbd.stats import depth_summary  # noqa: E402

# >>> The one place for the sample's address: an asset of the GitHub release submission-2026-11-08. <<<
SAMPLE_SCENE_URL = "https://github.com/NicoloIacobone/synthetic-rgbd-manufacturing-perception/releases/download/submission-2026-11-08/sample_scene_seed0.tar.gz"

LOCAL_SAMPLE = REPO / "dist" / "sample_scene_seed0.tar.gz"
EXPECTED = REPO / "results" / "quick_run_expected_seed0.json"
WORK = REPO / "outputs" / "quick_run"
TOL_MEDIAN_MM = 0.01
MAX_SIDE_CHANGES = 1
THR_MM = 5.0
REFERENCE = ("Darwin", "arm64")     # where the expected numbers were computed
TOL_VALID_FRAC = 0.005              # the tolerance off that platform, fixed before the first Linux run (A-77)
TOL_DEPTH_MM = 1.0
TOL_VIEWS = 1
TOL_OFF_MEDIAN_MM = 0.5


def locate(sample):
    src = sample or (str(LOCAL_SAMPLE) if LOCAL_SAMPLE.exists() else SAMPLE_SCENE_URL)
    if not src:
        print(f"ERROR: no sample scene. Pass --sample <path or URL>, put the archive at {LOCAL_SAMPLE.relative_to(REPO)} or set SAMPLE_SCENE_URL in this script.", file=sys.stderr)
        sys.exit(2)
    if src.startswith(("http://", "https://")):
        dst = WORK / "sample.tar.gz"
        print(f"downloading {src}", flush=True)
        urllib.request.urlretrieve(src, dst)
        return dst
    p = Path(src)
    if not p.exists():
        print(f"ERROR: {p} does not exist", file=sys.stderr)
        sys.exit(2)
    return p


def run(cmd, log):
    env = dict(os.environ, OMP_NUM_THREADS="2")
    with open(log, "w") as f:
        subprocess.run([sys.executable, *map(str, cmd)], env=env, stdout=f, stderr=subprocess.STDOUT, check=True)


def read(path):
    return [json.loads(x) for x in path.read_text().splitlines()[1:]]


def depth_close(got, want):
    """A depth image's summary against the expected one, for the rule off the reference platform (A-77)."""
    return abs(got["valid_frac"] - want["valid_frac"]) <= TOL_VALID_FRAC and all(abs(got[k] - want[k]) <= TOL_DEPTH_MM for k in ("p5_mm", "p50_mm", "p95_mm"))


def passes(rule, m):
    """Does one condition pass? `m` holds its measures against the expected numbers (see main)."""
    if not m["complete"]:
        return False
    if rule == "exact":
        return m["depth_same"] and m["side_changes"] <= MAX_SIDE_CHANGES and m["median_mm"] <= TOL_MEDIAN_MM and m["suction_differences"] == 0
    return m["depth_close"] and abs(m["recall_diff"]) <= TOL_VIEWS and abs(m["suction_diff"]) <= TOL_VIEWS and m["median_mm"] <= TOL_OFF_MEDIAN_MM


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample")
    ap.add_argument("--expected", type=Path, default=EXPECTED)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--rule", choices=("auto", "exact", "tolerance"), default="auto", help="auto: exact on macOS arm64, tolerance elsewhere")
    args = ap.parse_args()
    here = (platform.system(), platform.machine())
    rule = args.rule if args.rule != "auto" else "exact" if here == REFERENCE else "tolerance"
    t0 = time.perf_counter()
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / "logs").mkdir(parents=True)
    exp = json.loads(args.expected.read_text())
    seed = exp["seed"]
    archive = locate(args.sample)
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    if sha != exp["archive_sha256"]:
        print(f"ERROR: {archive} has SHA-256 {sha}, expected {exp['archive_sha256']}", file=sys.stderr)
        sys.exit(2)
    root = WORK / "data"
    with tarfile.open(archive) as tar:
        tar.extractall(root, filter="data")
    print(f"sample ok: {archive} ({archive.stat().st_size / 1e6:.1f} MB), scene {seed}", flush=True)

    s = REPO / "scripts"
    run([s / "c2_depth.py", root, seed], WORK / "logs" / "c2.log")
    run([s / "stereo_scene.py", root, seed, "--passes", "metal", "matte"], WORK / "logs" / "stereo.log")
    print(f"depth ready, {time.perf_counter() - t0:.0f} s; running ICP and suction", flush=True)
    jobs = [(WORK / f"A_{c}.jsonl", [s / "pose_eval.py", root, seed, "--condition", c, "--offset", 10, 10]) for c in exp["conditions"]]
    jobs += [(WORK / f"B_{c}.jsonl", [s / "suction_eval.py", root, seed, "--condition", c]) for c in exp["conditions"]]
    with ThreadPoolExecutor(args.jobs) as ex:
        list(ex.map(lambda j: run([*j[1], "--out", j[0]], WORK / "logs" / f"{j[0].stem}.log"), jobs))

    scene = root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
    def depth(c, stem):
        return cv2.imread(str(scene / DEPTH_DIRS[c] / f"{stem}.png"), cv2.IMREAD_UNCHANGED)

    depth_same = {c: all(hashlib.sha256(depth(c, stem).tobytes()).hexdigest() == h for stem, h in v.items()) for c, v in exp["depth_pixels_sha256"].items()}
    close = {c: all(depth_close(depth_summary(depth(c, stem)), s) for stem, s in v.items()) for c, v in exp["depth_summary"].items()}
    print(f"rule: {rule} ({here[0]} {here[1]}; the expected numbers come from {REFERENCE[0]} {REFERENCE[1]})")
    ok, lines = True, []
    for c, e in exp["conditions"].items():
        got_a = {(r["im_id"], r["gt_id"]): r.get("mssd_mm") for r in read(WORK / f"A_{c}.jsonl")}
        got_b = {(r["im_id"], r["gt_id"]): r for r in read(WORK / f"B_{c}.jsonl")}
        deltas, flips = [], 0
        for r in e["A"]:
            g, w = got_a.get((r["im_id"], r["gt_id"])), r["mssd_mm"]
            flips += (g is not None and g < THR_MM) != (w is not None and w < THR_MM)
            if g is not None and w is not None:
                deltas.append(abs(g - w))
            elif (g is None) != (w is None):
                deltas.append(float("inf"))
        med, worst = (median(deltas), max(deltas)) if deltas else (0.0, 0.0)
        b_diff = sum(bool(got_b[(r["im_id"], r["gt_id"])]["success"]) != r["success"] or bool(got_b[(r["im_id"], r["gt_id"])]["has_grasp"]) != r["has_grasp"] for r in e["B"])
        same, near = depth_same.get(c, True), close.get(c, True)
        rec = lambda rows: sum(r["mssd_mm"] is not None and r["mssd_mm"] < THR_MM for r in rows)   # noqa: E731
        got_rec = sum(v is not None and v < THR_MM for v in got_a.values())
        succ = sum(r["success"] for r in got_b.values())
        good = passes(rule, {"complete": len(got_a) == len(e["A"]) and len(got_b) == len(e["B"]), "depth_same": same, "depth_close": near, "side_changes": flips, "median_mm": med, "suction_differences": b_diff,
                             "recall_diff": got_rec - rec(e["A"]), "suction_diff": succ - sum(r["success"] for r in e["B"])})
        ok &= good
        lines.append(f"{c:4} depth {'identical' if same else 'close' if near else 'DIFFERENT'}; A1 recall {got_rec}/{len(got_a)} (expected {rec(e['A'])}/{len(e['A'])}), |dMSSD| median {med:.1e}, max {worst:.1e} mm, side changes {flips}; "
                     f"suction {succ}/{len(got_b)} (expected {sum(r['success'] for r in e['B'])}/{len(e['B'])}), differences {b_diff}: {'ok' if good else 'DIFFERS'}")
    print("\n".join(lines))
    print(f"time {time.perf_counter() - t0:.0f} s")
    if ok and rule == "tolerance":
        print("Passed on the tolerance for other platforms (A-77): conclusions match, pixels need not.")
    print("QUICK_RUN_PASS" if ok else "QUICK_RUN_FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
