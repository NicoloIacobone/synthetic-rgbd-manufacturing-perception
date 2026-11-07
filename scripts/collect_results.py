"""Copy the final results into the tracked results/ folder, with a manifest of commits and seeds (A-71).

Usage: .venv/bin/python scripts/collect_results.py <hfov71_root> <archive_65_root> --out results

<hfov71_root> holds test/, dev/, plane/, intrinsics/; <archive_65_root> holds the 65-degree run (results_v2, results_s58_v2, robi). A missing optional
file (the ambient test, if it was skipped) is listed in the manifest rather than failing.
"""

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.config import load_config  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("archive", type=Path)
    ap.add_argument("--out", type=Path, default=REPO / "results")
    args = ap.parse_args()
    t, d = args.root / "test", args.root / "dev"
    new = {"stats.json": t / "results" / "stats.json", "sensor.json": t / "results" / "sensor.json", "distance.json": t / "results" / "distance.json",
           "s58_robustness.json": t / "results_s58" / "robustness.json", "s58_sensor.json": t / "results_s58" / "sensor.json",
           "redraw.json": t / "results_redraw" / "redraw.json", "redraw_sensor.json": t / "results_redraw" / "sensor.json",
           "ambient.json": t / "results_ambient" / "ambient.json", "ambient_sensor.json": t / "results_ambient" / "sensor.json",
           "icp_repeat.json": t / "results_repeat" / "icp_repeat.json", "error_structure.json": t / "results_structure" / "error_structure.json",
           "brightness_match.json": t / "brightness_match.json", "depth_wrap.json": t / "depth_wrap.json",
           "dots.json": t / "results_dots10000" / "dots.json", "dots_sensor.json": t / "results_dots10000" / "sensor.json",
           "ambient_level.json": d / "ambient_level.json", "unlit_share.json": t / "unlit_share.json", "mechanism_dev.json": t / "mechanism" / "dev_final.json",
           "ir_appearance.json": t / "robi_sim" / "ir_appearance.json", "robi_zigzag_real.json": args.archive / "robi" / "zigzag.json",
           "plane_gate_no_noise.json": args.root / "plane" / "gate_results.json", "anchor_a.json": args.root / "plane" / "anchor_a.json",
           "anchor_a_calibration.json": args.root / "plane" / "anchor_a_calibration.json", "intrinsics_check.json": args.root / "intrinsics" / "intrinsics_check.json",
           "rgb_light_rule.json": args.root / "rgb_sweep" / "e12" / "rule.json"}
    old = {"stats.json": args.archive / "results_v2" / "stats.json", "sensor.json": args.archive / "results_v2" / "sensor.json",
           "s58_robustness.json": args.archive / "results_s58_v2" / "robustness.json", "s58_sensor.json": args.archive / "results_s58_v2" / "sensor.json"}
    figures = {"results.png": t / "figures" / "results.png", "robi.png": t / "figures" / "robi.png", "examples.png": t / "figures" / "examples.png", "mechanism.png": t / "figures" / "mechanism.png"}
    files, missing = {}, []
    for sub, table in (("hfov71", new), ("archive_hfov65", old), ("figures", figures)):
        (args.out / sub).mkdir(parents=True, exist_ok=True)
        for name, src in table.items():
            if not src.exists():
                missing.append(str(src))
                continue
            dst = args.out / sub / name
            shutil.copyfile(src, dst)
            files[f"{sub}/{name}"] = hashlib.sha256(dst.read_bytes()).hexdigest()
    cfg = load_config()
    stats = json.loads((args.out / "hfov71" / "stats.json").read_text())
    git = lambda *a: subprocess.check_output(["git", "-C", str(REPO), *a], text=True).strip()   # noqa: E731
    manifest = {"written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "collected_at_commit": git("rev-parse", "HEAD"),
                "primary_run_commits": stats["commits"], "primary_run_dirty_tree": stats["dirty_tree_any"], "unit": stats["unit"],
                "seeds": cfg["seeds"], "camera": cfg["camera"], "noise": cfg["noise"], "platform": platform.platform(), "python": platform.python_version(),
                "archive_hfov65_note": "Descriptive sensitivity to the focal length only; commit 26cd449. Never compared to choose settings (A-66).",
                "missing_optional": missing, "sha256": files}
    (args.out / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps({"copied": len(files), "missing": missing}))


if __name__ == "__main__":
    main()
