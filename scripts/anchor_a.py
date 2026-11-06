"""Anchor (a) under the M4 camera model: auto exposure (A-42) + sensor noise (A-12) on the matte planes.

Usage:
  .venv/bin/python scripts/anchor_a.py <plane_dir> --calibrate   # grid over sensor_noise.e_per_dn, then bisection to 0.09 +- 0.001 px
  .venv/bin/python scripts/anchor_a.py <plane_dir>               # anchor with the config values; exit 1 if the gate says stop

Planes: scripts/bproc_ir_plane.py renders (matte albedo 0.5, no metal, so the C3 left image = the plane).
Gain per plane from its own left image (mean DN over columns >= ceil(f B / Min-Z) = setpoint). Noise draws
from seeds.rng(master, 7000 + z in cm, 0, "ir_noise") (plane seeds, disjoint from test 0-49 / dev 1000-1004).
Noise metric ([S-13]): RMS residual of a least-squares plane fitted to the *disparity* (px) over the valid
pixels of a central ROI covering 15% of the image area; calibration target = median over z = 0.5 ... 1.0 m
equal to 0.09 px (A-12). Gate criteria (i), (ii'), (iv'), (iii') as in A-67, re-run under the same rule.
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
from synthrgbd.plane_gate import gate_roi, gate_verdict, lit_left_column, roi_rows  # noqa: E402
from synthrgbd.seeds import rng  # noqa: E402
from synthrgbd.stereo import (auto_exposure_gain, exposed_pair_uint8, exposure_roi_x0, first_valid_column,  # noqa: E402
                              make_sgbm, match_extended)

ROI_AREA = 0.15
TARGET_PX, TARGET_TOL_PX = 0.09, 0.001    # A-12, ledger "IR noise (71°)"


def plane_rms(img: np.ndarray, valid: np.ndarray) -> float:
    v, u = np.nonzero(valid)
    A = np.c_[u, v, np.ones_like(u)].astype(np.float64)
    y = img[valid]
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(np.sqrt(np.mean((y - A @ coef) ** 2)))


def run(plane_dir, cam, ir, master, noise, setpoint, gate_only=False):
    gc = ir["plane_gate"]
    GATE_Z, MINZ_Z = gc["gate_z_m"], gc["minz_z_m"]
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
    y0, y1 = roi_rows(H, gc["roi_frac"])
    out = []
    for z in GATE_Z + ([] if gate_only else MINZ_Z):
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
        roi = gate_roi(W, H, band, hw, gc["roi_frac"])
        vr = valid & roi
        row = {"z_m": z, "gain": gain, "valid_frac_roi": float(vr.sum() / roi.sum()),
               "band_expected_px": band, "band_measured_px": float(np.median(first_valid_column(valid[y0:y1]))),
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

        def rms(e):
            noise["e_per_dn"] = e
            rows = run(args.plane_dir, cam, ir, cfg["seeds"]["master"], noise, setpoint, gate_only=True)
            res.append({"e_per_dn": e, "median_subpixel_rms_px": float(np.median([r["subpixel_rms_px"] for r in rows]))})
            print(json.dumps(res[-1]), flush=True)
            return res[-1]["median_subpixel_rms_px"]

        rms(None)
        grid = [2.0 ** (k / 2) for k in range(-8, 13)]
        vals = [rms(e) for e in grid]
        # RMS falls as e_per_dn grows (less noise): bisect the first interval that brackets the target, in log space.
        hit = next(i for i in range(len(grid) - 1) if vals[i] >= TARGET_PX >= vals[i + 1])
        lo, hi = grid[hit], grid[hit + 1]
        best = min(zip(vals, grid), key=lambda t: abs(t[0] - TARGET_PX))
        for _ in range(12):
            if abs(best[0] - TARGET_PX) <= TARGET_TOL_PX:
                break
            mid = float(np.sqrt(lo * hi))
            v = rms(mid)
            best = min(best, (v, mid), key=lambda t: abs(t[0] - TARGET_PX))
            lo, hi = (mid, hi) if v > TARGET_PX else (lo, mid)
        print("CHOSEN", json.dumps({"e_per_dn": best[1], "median_subpixel_rms_px": best[0]}))
        (args.plane_dir / "anchor_a_calibration.json").write_text(json.dumps({"chosen": {"e_per_dn": best[1], "median_subpixel_rms_px": best[0]}, "runs": res}, indent=1))
        return
    rows = run(args.plane_dir, cam, ir, cfg["seeds"]["master"], noise, setpoint)
    gc = ir["plane_gate"]
    gate = [r for r in rows if r["z_m"] in gc["gate_z_m"]]
    K = np.array(json.loads((args.plane_dir / "plane_meta.json").read_text())["K"])
    lit_edge = lambda z: lit_left_column(K[0, 0], K[0, 2], ir["projector"]["position_x_m"], ir["projector"]["fov_deg"][0], z)   # noqa: E731
    summary = {**gate_verdict(rows, gc, K[0, 0], cam["baseline_m"], lit_edge),
               "median_subpixel_rms_px": float(np.median([r["subpixel_rms_px"] for r in gate]))}
    commit = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    (args.plane_dir / "anchor_a.json").write_text(json.dumps({"commit": commit, "setpoint_dn": setpoint, "noise": noise,
                                                              "summary": summary, "rows": rows}, indent=1))
    for r in rows:
        print("ROW", json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}))
    print("SUMMARY", json.dumps(summary))
    if summary["stop"]:
        raise SystemExit("gate failed (A-67): stop and present the options to the user")


if __name__ == "__main__":
    main()
