"""§5.8 robustness check on seeds 0-9 (ledger "§5.8 flip rule", fixed before any recall on test scenes). Descriptive, no test.

Usage: .venv/bin/python scripts/robustness_s58.py <results_dir> <s58_dir> --out <json> [--loose C3looselr C4looselr] [--redraw-dir <dir>]

A1 recall@5 mm with strict SGBM (C1, C2b, C3, C4 from <results_dir>, restricted to the scenes of <s58_dir>) and with loose
SGBM (C1, C2b unchanged, C3loose for C3, C4loose for C4, or the two conditions given with --loose). The ranking flips if the
sign of C1-C3, C2b-C3 or C3-C4 differs between strict and loose; a zero on one side only counts as a flip. C3redraw1/2 (from
--redraw-dir, default <s58_dir>): same IR and matcher, new sensor noise (A-59), to show how much C3 recall moves. Sensor
classes (filled vs invalid) from <s58_dir>/sensor.json when present.
"""

import argparse
import json
from pathlib import Path

import numpy as np

THR_MM = 5.0
PAIRS = [("C1", "C3"), ("C2b", "C3"), ("C3", "C4")]


def load(path: Path, scenes=None) -> dict:
    rows = [json.loads(x) for x in path.read_text().splitlines()[1:]]
    return {(r["scene"], r["im_id"], r["gt_id"]): r.get("mssd_mm") is not None and r["mssd_mm"] < THR_MM
            for r in rows if scenes is None or r["scene"] in scenes}


def flips(a: float, b: float) -> bool:
    return np.sign(a) != np.sign(b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("s58", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--loose", nargs=2, default=["C3loose", "C4loose"], metavar=("C3_VARIANT", "C4_VARIANT"))
    ap.add_argument("--redraw-dir", type=Path)
    args = ap.parse_args()
    c3l, c4l = args.loose
    loose = {c: load(args.s58 / f"A_{c}_10.jsonl") for c in (c3l, c4l)}
    loose |= {c: load((args.redraw_dir or args.s58) / f"A_{c}_10.jsonl") for c in ("C3redraw1", "C3redraw2")}
    scenes = {k[0] for k in loose[c3l]}
    strict = {c: load(args.results / f"A_{c}_10.jsonl", scenes) for c in ("C1", "C2a", "C2b", "C3", "C4")}
    for c, d in {**strict, **loose}.items():
        assert d.keys() == strict["C1"].keys(), f"instance-views differ for {c}"
    recall = {c: float(np.mean(list(d.values()))) for c, d in {**strict, **loose}.items()}
    rec_loose = {"C1": recall["C1"], "C2b": recall["C2b"], "C3": recall[c3l], "C4": recall[c4l]}
    pairs = [{"a": a, "b": b, "strict": recall[a] - recall[b], "loose": rec_loose[a] - rec_loose[b],
              "flip": bool(flips(recall[a] - recall[b], rec_loose[a] - rec_loose[b]))} for a, b in PAIRS]
    out = {"scenes": sorted(scenes), "n_instance_views": len(strict["C1"]), "loose_conditions": [c3l, c4l], "recall_5mm": recall,
           "pairs": pairs, "ranking_flips": any(p["flip"] for p in pairs),
           "views_changed_strict_vs_loose": {"C3": sum(loose[c3l][k] != strict["C3"][k] for k in strict["C3"]),
                                             "C4": sum(loose[c4l][k] != strict["C4"][k] for k in strict["C4"])},
           "C3_redraw": {c: {"recall": recall[c], "views_changed_vs_C3": sum(loose[c][k] != strict["C3"][k] for k in strict["C3"])}
                         for c in ("C3redraw1", "C3redraw2")}}
    sensor = args.s58 / "sensor.json"
    if sensor.exists():
        s = json.loads(sensor.read_text())["conditions"]
        out["part_pixel_classes"] = {c: {**v["classes"], "invalid_frac": v["parts"]["invalid_frac"], "median_abs_mm": v["parts"].get("median_abs_mm")}
                                     for c, v in s.items()}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("n_instance_views", "recall_5mm", "pairs", "ranking_flips", "views_changed_strict_vs_loose", "C3_redraw")}, indent=1))


if __name__ == "__main__":
    main()
