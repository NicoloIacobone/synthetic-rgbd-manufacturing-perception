"""Compare two renders of the same scenes that differ only in a Cycles setting (mechanism check, A-54).

Usage: .venv/bin/python scripts/mechanism_compare_render.py <root_a> <root_b> <scene_seed>... --out <json>

Checks that the scenes are the same (poses, ideal depth, matte IR) and reports how the metal IR image changes on part
pixels: zero-radiance fraction, mean radiance, and the C4 albedo and exposure gain that the frozen rules (A-24, A-42)
would give. Radiance statistics only: no pose, grasp or depth-error outcome is computed here (A-45).
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.stereo import auto_exposure_gain, exposure_roi_x0  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root_a", type=Path)
    ap.add_argument("root_b", type=Path)
    ap.add_argument("scenes", type=int, nargs="+")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg, ir = load_config(), load_config(REPO / "configs" / "camera_d415_ir.yaml")
    cam = cfg["camera"]
    pad, albedo = ir["ir_render"]["pad_px"], ir["materials_matte"]["part_albedo"]
    setpoint = float(ir["exposure"]["setpoint_dn"])
    rows = []
    num = {"a": 0.0, "b": 0.0}
    den, n_part_tot = 0.0, 0
    clip = {"a": 0.0, "b": 0.0, "matte_a": 0.0, "matte_b": 0.0}
    frame_ratio = {"a": [], "b": []}
    for seed in args.scenes:
        sa = args.root_a / "synthrgbd" / "train_pbr" / f"{seed:06d}"
        sb = args.root_b / "synthrgbd" / "train_pbr" / f"{seed:06d}"
        same_gt = json.loads((sa / "scene_gt.json").read_text()) == json.loads((sb / "scene_gt.json").read_text())
        cams = json.loads((sa / "scene_camera.json").read_text())
        n_inst = len(json.loads((sa / "scene_gt.json").read_text())["0"])
        for im in sorted(cams, key=int):
            f = f"{int(im):06d}"
            K = np.array(cams[im]["cam_K"]).reshape(3, 3)
            same_depth = bool(np.array_equal(cv2.imread(str(sa / "depth" / f"{f}.png"), cv2.IMREAD_UNCHANGED),
                                             cv2.imread(str(sb / "depth" / f"{f}.png"), cv2.IMREAD_UNCHANGED)))
            ma, mb = np.load(sa / "ir" / f"{f}_matte.npz"), np.load(sb / "ir" / f"{f}_matte.npz")
            same_matte = bool(np.array_equal(ma["left"], mb["left"]) and np.array_equal(ma["right"], mb["right"]))
            parts = np.zeros((cam["height"], cam["width"]), bool)
            for k in range(n_inst):
                parts |= cv2.imread(str(sa / "mask_visib" / f"{f}_{k:06d}.png"), 0) > 0
            La = np.load(sa / "ir" / f"{f}_metal.npz")["left"][:, pad:].astype(np.float64)
            Lb = np.load(sb / "ir" / f"{f}_metal.npz")["left"][:, pad:].astype(np.float64)
            Lm = ma["left"][:, pad:].astype(np.float64)
            x0 = exposure_roi_x0(K[0, 0], cam["baseline_m"], cam["min_z_m"])
            ga, gb = auto_exposure_gain(La, x0, setpoint), auto_exposure_gain(Lb, x0, setpoint)
            row = {"scene": seed, "im_id": int(im), "same_poses": same_gt, "same_depth": same_depth, "same_matte_ir": same_matte,
                   "zero_radiance_frac_a": float((La[parts] == 0).mean()), "zero_radiance_frac_b": float((Lb[parts] == 0).mean()),
                   "part_mean_radiance_a": float(La[parts].mean()), "part_mean_radiance_b": float(Lb[parts].mean()),
                   "gain_a": ga, "gain_b": gb,
                   "dn_ge_1_frac_a": float((La[parts] * ga >= 1).mean()), "dn_ge_1_frac_b": float((Lb[parts] * gb >= 1).mean()),
                   "dn_ge_10_frac_a": float((La[parts] * ga >= 10).mean()), "dn_ge_10_frac_b": float((Lb[parts] * gb >= 10).mean()),
                   "saturated_frac_a": float((La[parts] * ga >= 255).mean()), "saturated_frac_b": float((Lb[parts] * gb >= 255).mean())}
            rows.append(row)
            num["a"] += La[parts].sum()
            num["b"] += Lb[parts].sum()
            den += Lm[parts].sum()
            n_part_tot += int(parts.sum())
            # Robust to glints: means of the exposed image clipped at saturation (what the sensor records)
            clip["a"] += np.minimum(La[parts] * ga, 255).sum()
            clip["b"] += np.minimum(Lb[parts] * gb, 255).sum()
            clip["matte_a"] += np.minimum(Lm[parts] * ga, 255).sum()
            clip["matte_b"] += np.minimum(Lm[parts] * gb, 255).sum()
            frame_ratio["a"].append(float(La[parts].mean() / Lm[parts].mean()))
            frame_ratio["b"].append(float(Lb[parts].mean() / Lm[parts].mean()))
    keys = [k for k in rows[0] if k.endswith(("_a", "_b"))]
    w = np.array([1.0 for _ in rows])
    summary = {"n_views": len(rows), "all_same_poses": all(r["same_poses"] for r in rows),
               "all_same_depth": all(r["same_depth"] for r in rows), "all_same_matte_ir": all(r["same_matte_ir"] for r in rows),
               "mean_over_views": {k: float(np.average([r[k] for r in rows], weights=w)) for k in keys},
               "rule_A24_albedo_a": float(albedo * num["a"] / den), "rule_A24_albedo_b": float(albedo * num["b"] / den),
               "rule_A24_albedo_clipped_a": float(albedo * clip["a"] / clip["matte_a"]),
               "rule_A24_albedo_clipped_b": float(albedo * clip["b"] / clip["matte_b"]),
               "per_frame_metal_over_C4_a": {"median": float(np.median(frame_ratio["a"])), "min": min(frame_ratio["a"]), "max": max(frame_ratio["a"])},
               "per_frame_metal_over_C4_b": {"median": float(np.median(frame_ratio["b"])), "min": min(frame_ratio["b"]), "max": max(frame_ratio["b"])},
               "part_mean_radiance_ratio_b_over_a": float(num["b"] / num["a"]), "n_part_px": n_part_tot}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"summary": summary, "per_view": rows}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
