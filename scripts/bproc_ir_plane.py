import blenderproc as bproc  # noqa: I001  (BlenderProc requires this to be the first import)

"""M3 plane renders (A-38 gate, A-32 checks): IR stereo pairs of a fronto-parallel matte plane.

Run:  scripts/bproc.sh scripts/bproc_ir_plane.py --out <plane_dir>
Then: .venv/bin/python scripts/plane_gate.py <plane_dir>

Frames (left + right, both extended by pad px on the left, A-40), camera straight down at height z
above a 6 x 6 m Lambertian plane (albedo from configs/camera_d415_ir.yaml), projector on, no ambient:
- gate planes and Min-Z planes (plane_gate in the IR config, A-67), power P;
- linearity (A-32 i): z = 0.70 m at power 2P;
- metal (A-32 ii): a polished metal sphere (r = 3 cm) on the plane, z = 0.60 m, power P.
Output: <out>/plane_<tag>.npz (left, right: float16 linear radiance), <out>/plane_meta.json.
"""

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import bpy
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.bproc_ir import add_ir_frames, extended_K, ir_render_settings, make_projector, matte, render_ir  # noqa: E402
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.geometry import intrinsics_from_hfov  # noqa: E402
from synthrgbd.projector import make_pattern  # noqa: E402

LIN_Z, METAL_Z = 0.70, 0.60


def git_commit() -> str:
    try:
        sha = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.call(["git", "-C", str(REPO), "diff", "--quiet", "HEAD"]) != 0
        return sha + ("-dirty" if dirty else "")
    except Exception:  # noqa: BLE001
        return "unknown"


def down_pose(z):
    """Blender camera at height z looking straight down (-Z), x axis = world x."""
    T = np.eye(4)
    T[2, 3] = z
    return T


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--ir-config", type=Path, default=REPO / "configs" / "camera_d415_ir.yaml")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cam = load_config()["camera"]
    ir = load_config(args.ir_config)
    t0 = time.perf_counter()
    GATE_Z, MINZ_Z = ir["plane_gate"]["gate_z_m"], ir["plane_gate"]["minz_z_m"]

    bproc.init()
    ir_render_settings(ir)
    W, H, pad = cam["width"], cam["height"], ir["ir_render"]["pad_px"]
    K = intrinsics_from_hfov(W, H, cam["hfov_deg"])
    Ke = extended_K(K, pad)

    plane = bproc.object.create_primitive("PLANE", size=6.0)
    mat = bproc.material.create("plane_matte")
    matte(mat, ir["materials_matte"]["plane_albedo"])
    plane.replace_materials(mat)

    t = time.perf_counter()
    pattern, geo, pts = make_pattern(cam, ir)
    t_pattern = time.perf_counter() - t
    P = ir["projector"]["power_w"]
    light = make_projector(pattern, ir["projector"]["fov_deg"], P)

    tags = [f"z{z:.2f}" for z in GATE_Z] + [f"minz{z:.2f}" for z in MINZ_Z] + [f"lin{LIN_Z:.2f}"]
    zs = GATE_Z + MINZ_Z + [LIN_Z]
    powers = [P] * (len(GATE_Z) + len(MINZ_Z)) + [2 * P]
    n_frames = add_ir_frames([down_pose(z) for z in zs], cam["baseline_m"], ir["projector"]["position_x_m"],
                             light, Ke, W + pad, H, energies=powers)
    t = time.perf_counter()
    imgs = render_ir()
    t_render = time.perf_counter() - t
    assert len(imgs) == n_frames == 2 * len(zs)
    for k, tag in enumerate(tags):
        np.savez_compressed(args.out / f"plane_{tag}.npz", left=imgs[2 * k].astype(np.float16),
                            right=imgs[2 * k + 1].astype(np.float16))

    # A-32 (ii): polished metal sphere on the plane.
    sphere = bproc.object.create_primitive("SPHERE", radius=0.03, location=[0.0, 0.0, 0.03])
    sphere.set_shading_mode("SMOOTH")
    metal = bproc.material.create("metal_test")
    metal.set_principled_shader_value("Base Color", [0.91, 0.92, 0.92, 1.0])
    metal.set_principled_shader_value("Metallic", 1.0)
    metal.set_principled_shader_value("Roughness", 0.1)
    sphere.replace_materials(metal)
    add_ir_frames([down_pose(METAL_Z)], cam["baseline_m"], ir["projector"]["position_x_m"], light, Ke, W + pad, H,
                  energies=[P])
    t = time.perf_counter()
    m = render_ir()
    t_metal = time.perf_counter() - t
    np.savez_compressed(args.out / f"plane_metal{METAL_Z:.2f}.npz", left=m[0].astype(np.float16),
                        right=m[1].astype(np.float16))
    np.savez_compressed(args.out / "plane_metal_f32.npz", left=m[0], right=m[1])   # float32 copy for (ii)

    meta = {
        "frames": [{"tag": t_, "z_m": z, "power_w": p} for t_, z, p in zip(tags, zs, powers)]
        + [{"tag": f"metal{METAL_Z:.2f}", "z_m": METAL_Z, "power_w": P, "sphere_radius_m": 0.03}],
        "K": K.tolist(), "K_ext": Ke.tolist(), "pad_px": pad, "width_ext": W + pad, "height": H,
        "pattern": {"width": geo.width, "height": geo.height, "dots": int(len(pts)),
                    "seed": ir["dots"]["seed"], "time_s": t_pattern},
        "timings": {"render_planes_s": t_render, "render_planes_s_per_image": t_render / n_frames,
                    "render_metal_s": t_metal, "total_s": time.perf_counter() - t0},
        "samples": ir["ir_render"]["samples"], "commit": git_commit(), "blender": bpy.app.version_string,
        "platform": platform.platform(), "cycles_device": bpy.context.scene.cycles.device,
    }
    (args.out / "plane_meta.json").write_text(json.dumps(meta, indent=1))
    print("PLANE_META", json.dumps(meta["timings"]))


main()
