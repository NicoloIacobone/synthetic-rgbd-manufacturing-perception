"""Gate on the matte plane (A-67; A-38 is the 65-degree history) and the A-32 (i)-(iii) checks, in .venv.

Run after scripts/bproc_ir_plane.py:
  .venv/bin/python scripts/plane_gate.py <plane_dir>              # gate (needs exposure.gain set)
  .venv/bin/python scripts/plane_gate.py <plane_dir> --calibrate  # print the exposure gain only

Planes and limits: plane_gate in configs/camera_d415_ir.yaml. ROI = central 80% of width and height, minus the expected left
band f B / z and a border of half the SGBM window. No noise, fixed gain.
  (i) |mean(z_est - z)| < 1% z over valid ROI pixels; (ii') valid >= 95% of the ROI;
  (iv') first valid column, median over the ROI rows: within +-10% of f B / z where the band exceeds the lit edge; between
        0.9 f B / z and 1.1 max(f B / z, lit edge) elsewhere;
  (iii') Min-Z: >= 95% valid at 0.40-0.46 m, <= 5% valid at 0.37-0.38 m (5-10% = the accepted marginal failure, > 10% = stop).
The same criteria with auto exposure and sensor noise: scripts/anchor_a.py.
Noise (plane-fit residual, equivalent subpixel RMS) is reported, not gated (M4).
Writes <dir>/gate_results.json and <dir>/gate_figure.png.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.plane_gate import gate_roi, gate_verdict, lit_left_column, roi_rows  # noqa: E402
from synthrgbd.projector import make_pattern, plane_pattern_in_camera  # noqa: E402
from synthrgbd.stereo import depth_from_ir, expose_to_uint8, first_valid_column, make_sgbm  # noqa: E402


def load(d: Path, tag: str):
    f = np.load(d / f"plane_{tag}.npz")
    return f["left"].astype(np.float32), f["right"].astype(np.float32)


def corr(a, b):
    return float(np.corrcoef(a.ravel(), b.ravel())[0, 1])


def plane_fit_residual(z_est, valid):
    """Std of residuals of a least-squares plane z = a u + b v + c over valid pixels (m)."""
    v, u = np.nonzero(valid)
    A = np.c_[u, v, np.ones_like(u)].astype(np.float64)
    zz = z_est[valid]
    coef, *_ = np.linalg.lstsq(A, zz, rcond=None)
    return float(np.std(zz - A @ coef))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plane_dir", type=Path)
    ap.add_argument("--ir-config", type=Path, default=REPO / "configs" / "camera_d415_ir.yaml")
    ap.add_argument("--calibrate", action="store_true")
    args = ap.parse_args()
    cam = load_config()["camera"]
    ir = load_config(args.ir_config)
    meta = json.loads((args.plane_dir / "plane_meta.json").read_text())
    K, pad = np.array(meta["K"]), meta["pad_px"]
    W, H = cam["width"], cam["height"]
    f, B, dmax = K[0, 0], cam["baseline_m"], cam["disparity_search_px"]
    hw = ir["sgbm"]["block_size"] // 2
    ex = ir["exposure"]
    gc = ir["plane_gate"]
    GATE_Z, MINZ_Z = gc["gate_z_m"], gc["minz_z_m"]
    px_proj, hfov_proj = ir["projector"]["position_x_m"], ir["projector"]["fov_deg"][0]
    lit_edge = lambda z: lit_left_column(f, K[0, 2], px_proj, hfov_proj, z)   # noqa: E731
    y0, y1 = roi_rows(H, gc["roi_frac"])

    if args.calibrate or ex["gain"] is None:
        L, _ = load(args.plane_dir, f"minz{ex['calib_z_m']:.2f}")
        p = float(np.percentile(L[:, pad:], 99.9))
        gain = ex["calib_target_dn"] / p
        print(json.dumps({"calib_plane": f"minz{ex['calib_z_m']:.2f}", "p99.9_radiance": p, "gain": gain}))
        if ex["gain"] is None:
            print("exposure.gain is null: write the value into the IR config, then rerun the gate")
        return
    gain = float(ex["gain"])
    sgbm = make_sgbm(ir["sgbm"])

    def evaluate(z, tag):
        L, R = load(args.plane_dir, tag)
        t = time.perf_counter()
        zest, d = depth_from_ir(L, R, gain, pad, sgbm, f, B, dmax)
        t_match = time.perf_counter() - t
        valid = zest > 0
        band = f * B / z
        roi = gate_roi(W, H, band, hw, gc["roi_frac"])
        roi_area = gate_roi(W, H, band, hw, float(np.sqrt(gc["roi_frac"])))      # the area reading of "80%", descriptive (A-67)
        vr = valid & roi
        first = first_valid_column(valid[y0:y1])
        err = zest[vr] - z
        r = {"z_m": z, "band_expected_px": band, "lit_edge_px": lit_edge(z), "roi_px": int(roi.sum()),
             "valid_frac_roi": float(vr.sum() / roi.sum()),
             "valid_frac_roi_area_reading": float((valid & roi_area).sum() / roi_area.sum()),
             "band_measured_px": float(np.median(first)),
             "t_sgbm_s": t_match,
             "dn_p99.9": float(np.percentile(expose_to_uint8(L[:, pad:], gain), 99.9)),
             "dn_saturated_frac": float((expose_to_uint8(L[:, pad:], gain) == 255).mean())}
        if vr.any():
            res = plane_fit_residual(zest, vr)
            r.update({"bias_m": float(err.mean()), "bias_rel": float(abs(err.mean()) / z),
                      "rmse_mm": float(1e3 * np.sqrt((err**2).mean())), "mae_mm": float(1e3 * np.abs(err).mean()),
                      "frac_err_gt_5mm": float((np.abs(err) > 5e-3).mean()),
                      "planefit_std_mm": 1e3 * res, "eps_d_equiv_px": res * f * B / z**2,
                      "c2a_sigma_mm": 1e3 * z**2 * 0.08 / (f * B)})
        return r, L, zest, d

    gate, imgs = [], {}
    for z in GATE_Z:
        r, L, zest, d = evaluate(z, f"z{z:.2f}")
        gate.append(r)
        imgs[z] = (L, zest, d)
    minz = [evaluate(z, f"minz{z:.2f}")[0] for z in MINZ_Z]
    verdict = gate_verdict(gate + minz, gc, f, B, lit_edge)

    # Projector geometry: rendered left IR vs numpy forward model of the pattern on the plane.
    pattern, geo, _ = make_pattern(cam, ir)
    px = ir["projector"]["position_x_m"]
    geom = []
    for z in (0.5, 0.7, 1.0):
        L = imgs[z][0][:, pad:]
        sl = (slice(40, H - 40), slice(200, W - 40))
        pred = plane_pattern_in_camera(pattern, geo, K, W, H, z, px)
        pred0 = plane_pattern_in_camera(pattern, geo, K, W, H, z, 0.0)
        predm = plane_pattern_in_camera(pattern[:, ::-1], geo, K, W, H, z, px)
        colmean = L.mean(axis=0)
        lit = colmean > 0.05 * np.median(colmean)
        geom.append({"z_m": z, "corr_model": corr(L[sl], pred[sl]), "corr_no_offset": corr(L[sl], pred0[sl]),
                     "corr_mirrored": corr(L[sl], predm[sl]),
                     "unlit_cols_left": int(np.argmax(lit)), "unlit_cols_left_predicted": lit_edge(z), "unlit_cols_right": int(np.argmax(lit[::-1])),
                     "unlit_rows": int((~(L.mean(axis=1) > 0.05 * np.median(L.mean(axis=1)))).sum())})

    # A-32 (i): linearity in projector power, and 1/z^2 falloff of a Lambertian plane.
    L1, _ = load(args.plane_dir, "z0.70")
    L2, _ = load(args.plane_dir, "lin0.70")
    m = L1 > 0.1 * L1.max()
    ratio = L2[m] / L1[m]
    c = (slice(H // 2 - 100, H // 2 + 100), slice(pad + W // 2 - 100, pad + W // 2 + 100))
    means = [float(imgs[z][0][c].mean()) for z in GATE_Z]
    slope = float(np.polyfit(np.log(GATE_Z), np.log(means), 1)[0])
    lin = {"power_ratio_median": float(np.median(ratio)), "power_ratio_p1": float(np.percentile(ratio, 1)),
           "power_ratio_p99": float(np.percentile(ratio, 99)), "loglog_slope_mean_vs_z": slope}

    # A-32 (ii): metal highlight is unclipped in the export; saturation only from our exposure.
    mf = np.load(args.plane_dir / "plane_metal_f32.npz")["left"][:, pad:]
    m16 = np.load(args.plane_dir / "plane_metal0.60.npz")["left"].astype(np.float32)[:, pad:]
    pl = imgs[0.6][0][:, pad:]
    dn = expose_to_uint8(mf, gain)
    metal = {"max_radiance": float(mf.max()), "matte_plane_max_radiance": float(pl.max()),
             "max_over_matte_max": float(mf.max() / pl.max()), "frac_radiance_gt_1": float((mf > 1).mean()),
             "n_px_saturated_after_exposure": int((dn == 255).sum()),
             "n_px_saturated_matte_plane": int((expose_to_uint8(pl, gain) == 255).sum()),
             "float16_max_rel_err": float(np.max(np.abs(m16 - mf) / np.maximum(mf, 1e-3)))}

    t_sgbm = float(np.median([r["t_sgbm_s"] for r in gate]))
    out = {"commit": subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
           "gain": gain, "sgbm": ir["sgbm"], "gate": gate, "minz": minz, "pass": verdict,
           "projector_geometry": geom, "linearity": lin, "metal": metal,
           "timing": {"sgbm_median_s_per_pair": t_sgbm, "render_s_per_image": meta["timings"]["render_planes_s_per_image"]}}
    (args.plane_dir / "gate_results.json").write_text(json.dumps(out, indent=1))

    print(f"{'z':>5} {'band exp':>8} {'band meas':>9} {'valid%':>7} {'bias mm':>8} {'bias%':>6} {'rmse mm':>7} "
          f"{'fit sd mm':>9} {'eps_d px':>8} {'C2a sd':>7}")
    for r in gate + minz:
        print(f"{r['z_m']:5.2f} {r['band_expected_px']:8.1f} {r['band_measured_px']:9.1f} {100 * r['valid_frac_roi']:7.2f} "
              f"{1e3 * r.get('bias_m', np.nan):8.3f} {100 * r.get('bias_rel', np.nan):6.3f} {r.get('rmse_mm', np.nan):7.3f} "
              f"{r.get('planefit_std_mm', np.nan):9.3f} {r.get('eps_d_equiv_px', np.nan):8.4f} {r.get('c2a_sigma_mm', np.nan):7.3f}")
    print("PASS", json.dumps(out["pass"]))
    print("GEOM", json.dumps(geom))
    print("LIN", json.dumps(lin))
    print("METAL", json.dumps(metal))
    print("TIMING", json.dumps(out["timing"]))

    figure(args.plane_dir / "gate_figure.png", imgs, gate, minz, pad, gain, f, B, cam["disparity_search_px"], cam["min_z_m"])
    if verdict["stop"]:
        raise SystemExit("gate failed (A-67): stop and present the options to the user")


def figure(path, imgs, gate, minz, pad, gain, f, B, dmax, min_z_m):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(2, 3, figsize=(13, 6.2))
    L, _, _ = imgs[0.7]
    ax[0, 0].imshow(expose_to_uint8(L[200:330, pad + 560:pad + 780], gain), cmap="gray", vmin=0, vmax=255)
    ax[0, 0].set_title("left IR, z = 0.70 m (crop, 8-bit)")
    for a, z in ((ax[0, 1], 0.5), (ax[0, 2], 1.0)):
        d = imgs[z][2]
        im = a.imshow(np.where(d > 0, d, np.nan), cmap="viridis")
        a.axvline(f * B / z, color="r", lw=0.8)
        a.set_title(f"disparity, z = {z:.2f} m (red: f B / z)")
        fig.colorbar(im, ax=a, fraction=0.03)
    zs = [r["z_m"] for r in gate]
    ax[1, 0].plot(zs, [100 * r["bias_m"] / r["z_m"] for r in gate], "o-", label="bias (% z)")
    ax[1, 0].plot(zs, [100 - 100 * r["valid_frac_roi"] for r in gate], "s-", label="invalid (% ROI)")
    ax[1, 0].axhline(1, color="k", ls=":", lw=0.8)
    ax[1, 0].axhline(-1, color="k", ls=":", lw=0.8)
    ax[1, 0].set_xlabel("z (m)")
    ax[1, 0].legend()
    ax[1, 0].set_title("gate (i), (ii'): limits +-1% bias, 5% invalid")
    ax[1, 1].plot(zs, [r["band_expected_px"] for r in gate], "k--", label="f B / z")
    ax[1, 1].plot(zs, [r["band_measured_px"] for r in gate], "o", label="measured")
    ax[1, 1].set_xlabel("z (m)")
    ax[1, 1].set_ylabel("left invalid band (px)")
    ax[1, 1].legend()
    ax[1, 1].set_title("gate (iv')")
    ax[1, 2].plot([r["z_m"] for r in minz], [100 * r["valid_frac_roi"] for r in minz], "o-")
    ax[1, 2].axvline(f * B / dmax, color="r", lw=0.8, label=f"f B / {dmax}")
    ax[1, 2].axvline(min_z_m, color="k", ls=":", lw=0.8, label="datasheet Min-Z")
    ax[1, 2].set_xlabel("z (m)")
    ax[1, 2].set_ylabel("valid (% ROI)")
    ax[1, 2].legend()
    ax[1, 2].set_title("gate (iii') Min-Z")
    fig.tight_layout()
    fig.savefig(path, dpi=110)


if __name__ == "__main__":
    main()
