"""Build the sample scene of the quick run, and its expected numbers from a finished experiment (A-71). No upload.

Usage: .venv/bin/python scripts/make_sample_archive.py <dataset_root> <results_dir> --seed 0 --archive dist/sample_scene_seed0.tar.gz
           --expected results/quick_run_expected_seed0.json

Archive: only what the quick run needs: IR metal and matte, ideal depth, masks, annotations, segmentation, RGB and the BOP models. It is
byte-reproducible (sorted names, zeroed times and owners). Expected: per instance-view MSSD and Task B outcome of the full run at 10 mm / 10 deg, and
a hash of the pixels of each computed depth image, which unlike the ICP result repeats exactly (A-72), and a summary of each, for the rule off the reference platform (A-77).
"""

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.conditions import DEPTH_DIRS  # noqa: E402
from synthrgbd.stats import depth_summary  # noqa: E402

CONDITIONS = ("C1", "C2a", "C2b", "C3", "C4")
FOLDERS = ("depth", "mask", "mask_visib", "segmap", "rgb")
FILES = ("scene_camera.json", "scene_gt.json", "scene_gt_info.json")


def rows(path, seed):
    lines = path.read_text().splitlines()
    return json.loads(lines[0])["meta"], [r for r in map(json.loads, lines[1:]) if r["scene"] == seed]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("results", type=Path)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--expected", type=Path, required=True)
    args = ap.parse_args()
    base = args.root / "synthrgbd"
    sc = base / "train_pbr" / f"{args.seed:06d}"
    names = [base / "camera.json"] + sorted((base / "models").glob("*"))
    names += [sc / f for f in FILES]
    for folder in FOLDERS:
        names += sorted(p for p in (sc / folder).glob("*") if p.is_file())
    names += sorted(p for pattern in ("*_metal.npz", "*_matte.npz") for p in (sc / "ir").glob(pattern))

    def clean(info):
        info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""
        return info

    args.archive.parent.mkdir(parents=True, exist_ok=True)
    with open(args.archive, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as gz, tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for p in names:
            tar.add(p, arcname=str(p.relative_to(args.root)), recursive=False, filter=clean)
    sha = hashlib.sha256(args.archive.read_bytes()).hexdigest()

    expected = {"seed": args.seed, "archive": args.archive.name, "archive_sha256": sha, "archive_bytes": args.archive.stat().st_size, "offset_mm_deg": 10, "conditions": {}}
    commits = set()
    for c in CONDITIONS:
        ma, ra = rows(args.results / f"A_{c}_10.jsonl", args.seed)
        mb, rb = rows(args.results / f"B_{c}.jsonl", args.seed)
        commits |= {ma["commit"], mb.get("commit", ma["commit"])}
        expected["conditions"][c] = {"A": [{"im_id": r["im_id"], "gt_id": r["gt_id"], "type": r["type"], "mssd_mm": r.get("mssd_mm")} for r in ra],
                                     "B": [{"im_id": r["im_id"], "gt_id": r["gt_id"], "type": r["type"], "success": bool(r["success"]), "has_grasp": bool(r["has_grasp"])} for r in rb]}
    expected["depth_pixels_sha256"] = {c: {p.stem: hashlib.sha256(cv2.imread(str(p), cv2.IMREAD_UNCHANGED).tobytes()).hexdigest() for p in sorted((sc / DEPTH_DIRS[c]).glob("*.png"))}
                                       for c in ("C2a", "C2b", "C3", "C4")}
    expected["depth_summary"] = {c: {p.stem: depth_summary(cv2.imread(str(p), cv2.IMREAD_UNCHANGED)) for p in sorted((sc / DEPTH_DIRS[c]).glob("*.png"))} for c in ("C2a", "C2b", "C3", "C4")}
    expected["run_commits"] = sorted(commits)
    expected["built_at_commit"] = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    args.expected.parent.mkdir(parents=True, exist_ok=True)
    args.expected.write_text(json.dumps(expected, indent=1) + "\n")
    print(json.dumps({"archive": str(args.archive), "bytes": expected["archive_bytes"], "files": len(names), "sha256": sha, "instance_views": len(expected["conditions"]["C1"]["A"])}))


if __name__ == "__main__":
    main()
