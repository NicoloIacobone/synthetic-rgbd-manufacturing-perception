"""A-28 check, analysis side (.venv): compare BlenderProc's plane depth with the analytic depth.

Usage: .venv/bin/python scripts/check_intrinsics.py <out_dir of bproc_check_intrinsics.py>

Reports (i) K as BlenderProc reports it vs ours, (ii) the residual rendered - analytic z-depth for
our K, (iii) the best-fitting principal-point shift and focal scale (grid search), and (iv) the
residual if the render were ray distance instead of z-depth. Writes intrinsics_check.json.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from synthrgbd.geometry import plane_depth, z_to_ray_distance

out = Path(sys.argv[1])
depth = np.load(out / "depth.npy")
plane = json.load(open(out / "plane.json"))
kinfo = json.load(open(out / "K_blenderproc.json"))
K = np.array(kinfo["K_set"])
K_bp = np.array(kinfo["K_blenderproc"])
H, W = depth.shape
n, p = np.array(plane["normal_cv"]), np.array(plane["point_cv"])


def resid(Kc):
    z = plane_depth(Kc, n, p, H, W)
    m = (depth > 0) & (depth < 1e3) & (z > 0)
    return (depth - z)[m], m


r, m = resid(K)
res = {
    "K_set": K.tolist(),
    "K_blenderproc_max_abs_diff": float(np.abs(K_bp - K).max()),
    "valid_fraction": float(m.mean()),
    "z_residual_mm": {"mean": 1e3 * float(r.mean()), "std": 1e3 * float(r.std()),
                      "max_abs": 1e3 * float(np.abs(r).max())},
}
# Ray-distance hypothesis: would the render match the ray distance better than z-depth?
zr = z_to_ray_distance(plane_depth(K, n, p, H, W), K)
res["ray_distance_hypothesis_max_abs_mm"] = 1e3 * float(np.abs((depth - zr)[m]).max())

# Grid search: principal-point shift (px) and focal scale.
best = None
for dcx in np.arange(-1.0, 1.01, 0.25):
    for dcy in np.arange(-1.0, 1.01, 0.25):
        for s in (0.998, 0.999, 1.0, 1.001, 1.002):
            Kc = K.copy()
            Kc[0, 0] *= s
            Kc[1, 1] *= s
            Kc[0, 2] += dcx
            Kc[1, 2] += dcy
            rc, _ = resid(Kc)
            rms = float(np.sqrt((rc ** 2).mean()))
            if best is None or rms < best[0]:
                best = (rms, float(dcx), float(dcy), s)
res["best_fit"] = {"rms_mm": 1e3 * best[0], "dcx_px": best[1], "dcy_px": best[2], "f_scale": best[3]}
json.dump(res, open(out / "intrinsics_check.json", "w"), indent=1)
print(json.dumps(res, indent=1))
