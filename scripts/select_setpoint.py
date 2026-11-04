"""Auto-exposure setpoint (A-42) by the tuning-ledger rule (A-45): saturation only.

Usage: .venv/bin/python scripts/select_setpoint.py <dataset_root> <dev_seed>...

For setpoints 10, 20, ..., 250 DN: per dev frame, gain from the C3 (metal) left image (mean over columns
>= ceil(f B / Min-Z)); C4 (matte) left image exposed with the same gain, before noise; saturated = DN >= 255
(after rounding). The chosen setpoint is the highest one at which every dev frame has <= 0.1% saturated
C4 pixels. C3 saturation is reported but does not constrain (metal highlights saturate on the real camera).
"""

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.stereo import auto_exposure_gain, exposure_roi_x0  # noqa: E402

MAX_SAT = 0.001


def main():
    root, seeds = Path(sys.argv[1]), [int(s) for s in sys.argv[2:]]
    cam, ir = load_config()["camera"], load_config(REPO / "configs" / "camera_d415_ir.yaml")
    pad = ir["ir_render"]["pad_px"]
    frames = []
    for seed in seeds:
        sc = root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
        cams = json.loads((sc / "scene_camera.json").read_text())
        for im in sorted(cams, key=int):
            fx = np.array(cams[im]["cam_K"]).reshape(3, 3)[0, 0]
            Lm = np.load(sc / "ir" / f"{int(im):06d}_metal.npz")["left"][:, pad:].astype(np.float64)
            La = np.load(sc / "ir" / f"{int(im):06d}_matte.npz")["left"][:, pad:].astype(np.float64)
            frames.append((exposure_roi_x0(fx, cam["baseline_m"], cam["min_z_m"]), Lm, La, f"{seed}/{im}"))
    rows, chosen = [], None
    for sp in range(10, 260, 10):
        sat_c4, sat_c3 = [], []
        for x0, Lm, La, _ in frames:
            g = auto_exposure_gain(Lm, x0, sp)
            sat_c4.append(float((np.rint(La * g) >= 255).mean()))
            sat_c3.append(float((np.rint(Lm * g) >= 255).mean()))
        ok = max(sat_c4) <= MAX_SAT
        rows.append({"setpoint_dn": sp, "max_sat_c4": max(sat_c4), "max_sat_c3": max(sat_c3), "ok": ok})
        if ok:
            chosen = sp
        print(json.dumps(rows[-1]))
    print("CHOSEN", json.dumps({"setpoint_dn": chosen, "rule": "highest setpoint with max C4 saturation <= 0.1%",
                                "frames": len(frames)}))


if __name__ == "__main__":
    main()
