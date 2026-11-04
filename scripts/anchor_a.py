"""Anchor (a) under the M4 camera model: auto exposure (A-42) + sensor noise (A-12) on the matte planes.

Usage:
  .venv/bin/python scripts/anchor_a.py data/m3/plane --calibrate   # grid over sensor_noise.e_per_dn
  .venv/bin/python scripts/anchor_a.py data/m3/plane               # anchor with the config values

Planes: scripts/bproc_ir_plane.py renders (matte albedo 0.5, no metal, so the C3 left image = the plane).
Gain per plane from its own left image (mean DN over columns >= ceil(f B / Min-Z) = setpoint). Noise draws
from seeds.rng(master, 7000 + z in cm, 0, "ir_noise") (plane seeds, disjoint from test 0-49 / dev 1000-1004).
Noise metric ([S-13]): RMS residual of a least-squares plane fitted to the *disparity* (px) over the valid
pixels of a central ROI covering 15% of the image area; calibration target = median over z = 0.5 ... 1.0 m
equal to 0.09 px (A-12). Gate criteria (i), (ii), (iv), (iii) as in A-38, re-run under the same rule.
Writes <dir>/anchor_a.json.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.geometry import disparity_to_depth  # noqa: E402
from synthrgbd.seeds import rng  # noqa: E402
from synthrgbd.stereo import (auto_exposure_gain, exposed_pair_uint8, exposure_roi_x0, first_valid_column,  # noqa: E402
                              make_sgbm, match_extended)

GATE_Z = [0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
MINZ_Z = [0.42, 0.43, 0.44, 0.45, 0.46]
ROI_AREA = 0.15


def plane_rms(img: np.ndarray, valid: np.ndarray) -> float:
    v, u = np.nonzero(valid)
    A = np.c_[u, v, np.ones_like(u)].astype(np.float64)
    y = img[valid]
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(np.sqrt(np.mean((y - A @ coef) ** 2)))


def run(plane_dir, cam, ir, master, noise, setpoint):
    meta = json.loads((plane_dir / "plane_meta.json").read_text())
    K, pad = np.array(meta["K"]), meta["pad_px"]
    W, H = cam["width"], cam["height"]
    f, B, dmax = K[0, 0], cam["baseline_m"], cam["disparity_search_px"]
    hw = ir["sgbm"]["block_size"] // 2
    sgbm = make_sgbm(ir["sgbm"])
    x0 = exposure_roi_x0(f, B, cam["min_z_m"])
    cw, ch = int(round(W * np.sqrt(ROI_AREA))), int(round(H * np.sqrt(ROI_AREA)))
    croi = np.zeros((H, W), bool)
    croi[(H - ch) // 2:(H + ch) // 2, (W - cw) // 2:(W + cw) // 2] = True
    out = []
    for z in GATE_Z + MINZ_Z:
        tag = f"z{z:.2f}" if z in GATE_Z else f"minz{z:.2f}"
        d = np.load(plane_dir / f"plane_{tag}.npz")
        L, R = d["left"].astype(np.float32), d["right"].astype(np.float32)
        gain = auto_exposure_gain(L[:, pad:], x0, setpoint)
        r = rng(master, 7000 + int(round(z * 100)), 0, "ir_noise")
        l8, r8 = exposed_pair_uint8(L, R, gain, noise, r.standard_normal(L.shape), r.standard_normal(L.shape))
        disp = match_extended(l8, r8, pad, sgbm, dmax)
        zest = disparity_to_depth(disp, f, B, dmax)
        valid = zest > 0
        band = f * B / z
        roi = np.zeros((H, W), bool)
        roi[hw:H - hw, int(np.ceil(band)) + hw:W - hw] = True
        vr = valid & roi
        row = {"z_m": z, "gain": gain, "valid_frac_roi": float(vr.sum() / roi.sum()),
               "band_expected_px": band, "band_measured_px": float(np.median(first_valid_column(valid[hw:H - hw]))),
               "dn_saturated_frac": float((l8[:, pad:] == 255).mean())}
        if z in GATE_Z and vr.any():
            err = zest[vr] - z
            vc = valid & croi
            row.update(bias_rel=float(abs(err.mean()) / z), bias_mm=float(1e3 * err.mean()),
                       subpixel_rms_px=plane_rms(disp, vc), planefit_rms_mm=1e3 * plane_rms(zest, vc),
                       median_abs_err_mm=float(1e3 * np.median(np.abs(err))), frac_err_gt_5mm=float((np.abs(err) > 5e-3).mean()))
        out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plane_dir", type=Path)
    ap.add_argument("--ir-config", type=Path, default=REPO / "configs" / "camera_d415_ir.yaml")
    ap.add_argument("--calibrate", action="store_true")
    args = ap.parse_args()
    cfg = load_config()
    cam, ir = cfg["camera"], load_config(args.ir_config)
    setpoint = float(ir["exposure"]["setpoint_dn"])
    noise = dict(ir["sensor_noise"])
    if args.calibrate:
        res = []
        for e in [None] + [2.0 ** (k / 2) for k in range(-8, 13)]:
            noise["e_per_dn"] = e
            rows = run(args.plane_dir, cam, ir, cfg["seeds"]["master"], noise, setpoint)
            med = float(np.median([r["subpixel_rms_px"] for r in rows if "subpixel_rms_px" in r]))
            res.append({"e_per_dn": e, "median_subpixel_rms_px": med})
            print(json.dumps(res[-1]))
        (args.plane_dir / "anchor_a_calibration.json").write_text(json.dumps(res, indent=1))
        return
    rows = run(args.plane_dir, cam, ir, cfg["seeds"]["master"], noise, setpoint)
    gate = [r for r in rows if r["z_m"] in GATE_Z]
    vf = {round(r["z_m"], 2): r["valid_frac_roi"] for r in rows if r["z_m"] in MINZ_Z}
    summary = {
        "pass_i_bias": all(r["bias_rel"] < 0.01 for r in gate),
        "pass_ii_valid": all(r["valid_frac_roi"] >= 0.95 for r in gate),
        "pass_iv_band": all(abs(r["band_measured_px"] - r["band_expected_px"]) <= 0.1 * r["band_expected_px"] for r in gate),
        "pass_iii_minz": bool(vf[0.45] >= 0.95 and vf[0.42] <= 0.05 and vf[0.43] <= 0.05),
        "median_subpixel_rms_px": float(np.median([r["subpixel_rms_px"] for r in gate]))}
    commit = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    (args.plane_dir / "anchor_a.json").write_text(json.dumps({"commit": commit, "setpoint_dn": setpoint, "noise": noise,
                                                              "summary": summary, "rows": rows}, indent=1))
    for r in rows:
        print("ROW", json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}))
    print("SUMMARY", json.dumps(summary))


if __name__ == "__main__":
    main()
