"""Quick run: one sample scene, no Blender, a few minutes. Computes depth, runs pose and suction evaluation, compares with the committed numbers.

Usage: .venv/bin/python scripts/quick_run.py [--sample <path or URL>] [--expected <json>] [--jobs 3]

Without --sample: dist/sample_scene_seed0.tar.gz if it exists, otherwise SAMPLE_SCENE_URL below. The archive is checked against the SHA-256 in
the expected file before it is opened. Everything is written to outputs/quick_run/, which is wiped first; the repository is not touched.
For conditions C1, C2a, C2b, C3, C4: depth from the stored IR images (stereo, C3 and C4) or from the ideal depth (C2), then ICP at
10 mm / 10 deg and the suction planner, compared with the committed numbers of the full run.
PASS (A-71, A-72) if, for every condition: the depth pixels are identical; every suction outcome matches; and for ICP the median |delta MSSD| over
the instance-views is at most 0.01 mm and at most one instance-view changes side of 5 mm. ICP is not strictly repeatable on identical depth: on unstable
views, mostly brackets that have already failed, repeated runs differ by tens of mm, so an exact per-view rule would fail by construction.
Exit code 0 on PASS, 1 on FAIL, 2 if the sample cannot be found.
"""

import argparse
import hashlib
import json
import os
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

# >>> The one place for the sample's address. Empty until the owner publishes the archive. <<<
SAMPLE_SCENE_URL = ""

LOCAL_SAMPLE = REPO / "dist" / "sample_scene_seed0.tar.gz"
EXPECTED = REPO / "results" / "quick_run_expected_seed0.json"
WORK = REPO / "outputs" / "quick_run"
TOL_MEDIAN_MM = 0.01
MAX_SIDE_CHANGES = 1
THR_MM = 5.0


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample")
    ap.add_argument("--expected", type=Path, default=EXPECTED)
    ap.add_argument("--jobs", type=int, default=3)
    args = ap.parse_args()
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
    depth_same = {c: all(hashlib.sha256(cv2.imread(str(scene / DEPTH_DIRS[c] / f"{stem}.png"), cv2.IMREAD_UNCHANGED).tobytes()).hexdigest() == h for stem, h in v.items())
                  for c, v in exp["depth_pixels_sha256"].items()}
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
        same = depth_same.get(c, True)
        good = same and flips <= MAX_SIDE_CHANGES and med <= TOL_MEDIAN_MM and b_diff == 0 and len(got_a) == len(e["A"]) and len(got_b) == len(e["B"])
        ok &= good
        rec = lambda rows: sum(r["mssd_mm"] is not None and r["mssd_mm"] < THR_MM for r in rows)   # noqa: E731
        got_rec = sum(v is not None and v < THR_MM for v in got_a.values())
        succ = sum(r["success"] for r in got_b.values())
        lines.append(f"{c:4} depth {'identical' if same else 'DIFFERENT'}; A1 recall {got_rec}/{len(got_a)} (expected {rec(e['A'])}/{len(e['A'])}), |dMSSD| median {med:.1e}, max {worst:.1e} mm, side changes {flips}; "
                     f"suction {succ}/{len(got_b)} (expected {sum(r['success'] for r in e['B'])}/{len(e['B'])}), differences {b_diff}: {'ok' if good else 'DIFFERS'}")
    print("\n".join(lines))
    print(f"time {time.perf_counter() - t0:.0f} s")
    print("QUICK_RUN_PASS" if ok else "QUICK_RUN_FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
