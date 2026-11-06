"""Ambient-IR test on seeds 0-9 (A-70), descriptive, next to the baseline on the same seeds and instance-views.

Usage: .venv/bin/python scripts/ambient_summary.py <results_dir> <ambient_dir> --out <json>
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.config import load_config  # noqa: E402

THR_MM = 5.0


def load(path, scenes=None):
    rows = [json.loads(x) for x in path.read_text().splitlines()[1:]]
    return {(r["scene"], r["im_id"], r["gt_id"]): r.get("mssd_mm") is not None and r["mssd_mm"] < THR_MM for r in rows if scenes is None or r["scene"] in scenes}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("ambient", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    amb = {c: load(args.ambient / f"A_{c}_10.jsonl") for c in ("C3amb", "C4amb")}
    scenes = {k[0] for k in amb["C3amb"]}
    base = {c: load(args.results / f"A_{c}_10.jsonl", scenes) for c in ("C1", "C2b", "C3", "C4")}
    for c, d in {**base, **amb}.items():
        assert d.keys() == base["C3"].keys(), f"instance-views differ for {c}"
    rec = {c: float(np.mean(list(d.values()))) for c, d in {**base, **amb}.items()}
    sensor = json.loads((args.ambient / "sensor.json").read_text())["conditions"]
    out = {"scenes": sorted(scenes), "n_instance_views": len(base["C3"]), "recall_5mm": rec,
           "views_changed": {"C3": sum(amb["C3amb"][k] != base["C3"][k] for k in base["C3"]), "C4": sum(amb["C4amb"][k] != base["C4"][k] for k in base["C4"])},
           "level": load_config(REPO / "configs" / "camera_d415_ir.yaml")["ambient_test"]["level"],
           "part_pixel_classes": {c: {**v["classes"], "invalid_frac": v["parts"]["invalid_frac"], "median_abs_mm": v["parts"].get("median_abs_mm")} for c, v in sensor.items()},
           "ir_appearance": json.loads((args.ambient / "ir_appearance.json").read_text()),
           "note": "Descriptive. Level and spectrum not sourced; no surface texture in the scene (A-70)."}
    args.out.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("n_instance_views", "recall_5mm", "views_changed", "level")}))


if __name__ == "__main__":
    main()
