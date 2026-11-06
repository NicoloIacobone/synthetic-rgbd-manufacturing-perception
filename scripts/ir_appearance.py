"""IR appearance of parts vs background on our renders, with the same measures as scripts/robi_compare.py on real images.

Usage: .venv/bin/python scripts/ir_appearance.py <dataset_root> <scene_seed>... --passes metal matte r02 r04 --out <json> [--ambient]

Per view, on the 8-bit left image the matcher receives (auto exposure and sensor noise as in scripts/stereo_scene.py):
median DN, 99th percentile, 7 x 7 local SD and saturation on part pixels vs background pixels (non-part pixels at least 7 px
from a part). Means over views, as for ROBI.
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
from synthrgbd.seeds import rng  # noqa: E402
from synthrgbd.stereo import auto_exposure_gain, exposed_pair_uint8, exposure_roi_x0  # noqa: E402


def local_sd(img, w=7):
    d = img.astype(np.float32)
    m = cv2.boxFilter(d, -1, (w, w), borderType=cv2.BORDER_REFLECT)
    m2 = cv2.boxFilter(d * d, -1, (w, w), borderType=cv2.BORDER_REFLECT)
    return np.sqrt(np.maximum(m2 - m * m, 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("scenes", type=int, nargs="+")
    ap.add_argument("--passes", nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--ambient", action="store_true", help="add ambient_test.level x the ambient-only passes to metal and matte (A-70)")
    args = ap.parse_args()
    cfg, ir = load_config(), load_config(REPO / "configs" / "camera_d415_ir.yaml")
    cam, sn = cfg["camera"], ir["sensor_noise"]
    pad, sp = ir["ir_render"]["pad_px"], float(ir["exposure"]["setpoint_dn"])
    amb = ir["ambient_test"]["level"] if args.ambient else None
    rows = {p: [] for p in args.passes}
    for seed in args.scenes:
        sc = args.root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
        cams = json.loads((sc / "scene_camera.json").read_text())
        gt = json.loads((sc / "scene_gt.json").read_text())
        for im in sorted(cams, key=int):
            f = f"{int(im):06d}"
            K = np.array(cams[im]["cam_K"]).reshape(3, 3)
            x0 = exposure_roi_x0(K[0, 0], cam["baseline_m"], cam["min_z_m"])
            parts = np.zeros((cam["height"], cam["width"]), bool)
            for k in range(len(gt[im])):
                parts |= cv2.imread(str(sc / "mask_visib" / f"{f}_{k:06d}.png"), 0) > 0
            back = ~cv2.dilate(parts.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
            back[:, :x0] = False
            r = rng(cfg["seeds"]["master"], seed, int(im), "ir_noise")
            metal = np.load(sc / "ir" / f"{f}_metal.npz")
            zl, zr = r.standard_normal(metal["left"].shape), r.standard_normal(metal["left"].shape)
            lm = metal["left"].astype(np.float64)
            if args.ambient:
                lm = lm + amb * np.load(sc / "ir_ambient" / f"{f}_metal.npz")["left"].astype(np.float64)
            g_c3 = auto_exposure_gain(lm[:, pad:], x0, sp)
            for p in args.passes:
                d = np.load(sc / "ir" / f"{f}_{p}.npz")
                L, R = d["left"].astype(np.float32), d["right"].astype(np.float32)
                if args.ambient:
                    da = np.load(sc / "ir_ambient" / f"{f}_{p}.npz")
                    L, R = L + amb * da["left"].astype(np.float32), R + amb * da["right"].astype(np.float32)
                g = g_c3 if p in ("metal", "matte") else auto_exposure_gain(L[:, pad:].astype(np.float64), x0, sp)
                l8 = exposed_pair_uint8(L, R, g, sn, zl, zr)[0][:, pad:]
                sd = local_sd(l8)
                rows[p].append({"obj_dn_median": float(np.median(l8[parts])), "back_dn_median": float(np.median(l8[back])),
                                "obj_dn_p99": float(np.percentile(l8[parts], 99)), "back_dn_p99": float(np.percentile(l8[back], 99)),
                                "obj_local_sd_median": float(np.median(sd[parts])), "back_local_sd_median": float(np.median(sd[back])),
                                "obj_saturated": float((l8[parts] == 255).mean()), "back_saturated": float((l8[back] == 255).mean()),
                                "obj_local_sd_lt_2dn": float((sd[parts] < 2).mean()), "back_local_sd_lt_2dn": float((sd[back] < 2).mean())})
    out = {p: {k: float(np.mean([x[k] for x in v])) for k in v[0]} for p, v in rows.items()}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1))
    print(json.dumps({p: {k: round(x, 3) for k, x in v.items()} for p, v in out.items()}))


if __name__ == "__main__":
    main()
