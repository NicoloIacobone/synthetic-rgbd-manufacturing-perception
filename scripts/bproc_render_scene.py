import blenderproc as bproc  # noqa: I001  (BlenderProc requires this to be the first import)

"""Render one physics scene of procedural parts in a tray, in BOP format (milestone M2).

Run (one scene per process; one render process at a time on this machine):
  scripts/bproc.sh scripts/bproc_render_scene.py --scene-seed 1000 --out data/m2

Output: <out>/synthrgbd/{camera.json, train_pbr/<scene_seed:06d>/...} in BOP format (RGB, z-depth
in units of 0.1 mm, visible instance masks, 6D poses, intrinsics), plus scene_meta.json in the scene folder
with seeds, commit, versions, layout and per-stage timings.

With --ir: after the BOP output, the IR stereo pair with the dot projector (synthrgbd.bproc_ir,
configs/camera_d415_ir.yaml) is rendered for every view, twice: parts metal ("metal", C3; materials_metal,
A-11) and parts matte ("matte", C4; materials_matte.part_albedo, A-24). Tray and table are matte in both.
--metal-roughness / --matte-part-albedo override the config (pre-declared robustness check, A-11).
Output: <scene>/ir/<im_id:06d>_<metal|matte>.npz (left, right: float16 linear radiance, both extended by
pad px on the left, A-40). M3 renders used the M2 RGB placeholder instead of "metal" ("metalproxy").

Conventions:
- Units are metres in Blender; BOP annotations are written in mm (annotation_unit="mm").
- Part meshes come from synthrgbd.parts, in the model frames of A-20, so the object pose in
  Blender is the BOP model-to-world pose.
- The tray floor is the plane z = 0; camera height is measured from it (D8, A-34).
- All randomness comes from one generator, seeds.rng(master, scene_seed, 0, "scene"), drawn in a
  fixed order: layout, then camera pose of view 0, view 1, ... (PLAN §5.10).
- Camera K from geometry.intrinsics_from_hfov (A-28).
- Visible masks (mask_visib/) come from Blender's instance segmentation of the same render
  (saved raw in segmap/; PNGs written by scripts/bop_gt_info.py). The
  BOP writer's own mask/gt_info step is not used: on macOS its multiprocessing pool ("spawn")
  re-imports this script in workers without blenderproc and hangs. Amodal masks (mask/) and
  scene_gt_info.json are added afterwards in .venv by scripts/bop_gt_info.py (A-35).
"""

import argparse
import json
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

import bpy
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.geometry import intrinsics_from_hfov  # noqa: E402
from synthrgbd.parts import PART_CATALOGUE, BracketSpec, ProfileSpec, diameter, make_part, signed_volume  # noqa: E402
from synthrgbd.seeds import rng as make_rng  # noqa: E402

ALUMINIUM_DENSITY = 2700.0          # kg/m^3, for rigid-body masses only

# Tray (A-34): inner 0.50 x 0.35 m, walls 0.04 m high; table plane 2 cm below the tray floor.
TRAY_INNER = (0.50, 0.35)
TRAY_WALL_H, TRAY_WALL_T, TRAY_FLOOR_T = 0.04, 0.01, 0.02
DROP_XY = (0.12, 0.07)              # half-extents of the drop region (m), keeps parts off the walls
DROP_Z = (0.08, 0.30)               # drop heights of part centres (m)
# Bullet keeps convex shapes apart by the sum of their collision margins (BlenderProc default
# 1 mm each -> parts rested 2 mm above the floor). A 0.1 mm margin brings that to ~0.2 mm (A-34).
COLLISION_MARGIN = 1e-4


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene-seed", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--config", type=Path, default=REPO / "configs" / "default.yaml")
    ap.add_argument("--samples", type=int, default=64, help="Cycles max samples for RGB")
    ap.add_argument("--ir", action="store_true", help="also render the IR stereo pairs (M3)")
    ap.add_argument("--ir-config", type=Path, default=REPO / "configs" / "camera_d415_ir.yaml")
    ap.add_argument("--metal-roughness", type=float, help="override materials_metal.roughness (A-11)")
    ap.add_argument("--matte-part-albedo", type=float, help="override materials_matte.part_albedo (A-24)")
    return ap.parse_args()


def git_commit() -> str:
    try:
        sha = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.call(["git", "-C", str(REPO), "diff", "--quiet", "HEAD"]) != 0
        return sha + ("-dirty" if dirty else "")
    except Exception:  # noqa: BLE001
        return "unknown"


def random_rotation(g: np.random.Generator) -> np.ndarray:
    q = g.normal(size=4)
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def make_box(name, size, location, material):
    box = bproc.object.create_primitive("CUBE")      # 2 x 2 x 2 m cube centred at the origin
    box.set_name(name)
    box.set_scale([s / 2 for s in size])
    box.set_location(location)
    box.persist_transformation_into_mesh()
    box.replace_materials(material)
    return box


def make_part_object(obj_id, name, spec, material):
    mesh = make_part(spec)
    obj = bproc.object.create_with_empty_mesh(name)
    v = (mesh.vertices * 1e-3).tolist()                       # mm -> m
    obj.get_mesh().from_pydata(v, [], mesh.faces.tolist())
    obj.get_mesh().validate()
    obj.replace_materials(material)
    obj.set_cp("category_id", obj_id)
    mass = ALUMINIUM_DENSITY * signed_volume(mesh) * 1e-9
    if isinstance(spec, BracketSpec):
        # Convex hull would fill the inside of the L. Use a compound of two boxes (one per leg),
        # as BlenderProc does for V-HACD decompositions: hidden children, COMPOUND parent.
        L, t, w = spec.leg * 1e-3, spec.thickness * 1e-3, spec.width * 1e-3
        for i, (size, centre) in enumerate([((L, t, w), (L / 2, t / 2, 0.0)),
                                           ((t, L, w), (t / 2, L / 2, 0.0))]):
            leg = make_box(f"{name}_collision_{i}", size, centre, material)
            leg.set_parent(obj)
            leg.enable_rigidbody(True, "CONVEX_HULL", collision_margin=COLLISION_MARGIN)
            leg.hide()
        obj.enable_rigidbody(True, "COMPOUND", mass=mass, collision_margin=COLLISION_MARGIN)
    else:
        obj.enable_rigidbody(True, "CONVEX_HULL", mass=mass, collision_margin=COLLISION_MARGIN)
    return obj, mesh


def sample_layout(g, n_parts):
    """Part ids and non-overlapping drop poses (rejection sampling on bounding spheres)."""
    ids = sorted(PART_CATALOGUE)
    chosen = [int(g.choice(ids)) for _ in range(n_parts)]
    radii = [diameter(make_part(PART_CATALOGUE[i][1])) / 2e3 for i in chosen]
    centres = []
    for r in radii:
        for _ in range(10000):
            c = np.array([g.uniform(-DROP_XY[0], DROP_XY[0]), g.uniform(-DROP_XY[1], DROP_XY[1]),
                          g.uniform(*DROP_Z)])
            if c[2] - r > 0.005 and all(np.linalg.norm(c - c2) > r + r2 + 0.005
                                        for c2, r2 in zip(centres, radii)):
                break
        else:
            raise RuntimeError("could not place parts without overlap")
        centres.append(c)
    rotations = [random_rotation(g) for _ in chosen]
    return chosen, centres, rotations


def sample_camera(g, cfg):
    """Look-at pose: height above the tray floor, tilt from vertical, random azimuth and roll (D8)."""
    h = g.uniform(*cfg["scene"]["camera_height_m"])
    tilt = np.deg2rad(g.uniform(0.0, cfg["scene"]["max_tilt_deg"]))
    azim = g.uniform(0.0, 2 * np.pi)
    roll = g.uniform(-np.pi, np.pi)
    poi = np.array([g.uniform(-0.05, 0.05), g.uniform(-0.05, 0.05), 0.0])
    pos = poi + (h / np.cos(tilt)) * np.array([np.sin(tilt) * np.cos(azim),
                                              np.sin(tilt) * np.sin(azim), np.cos(tilt)])
    R = bproc.camera.rotation_from_forward_vec(poi - pos, inplane_rot=roll)
    return bproc.math.build_transformation_mat(pos, R), {
        "height_m": float(h), "tilt_deg": float(np.rad2deg(tilt)), "azimuth_deg": float(np.rad2deg(azim)),
        "roll_deg": float(np.rad2deg(roll)), "poi_m": poi.tolist(), "position_m": pos.tolist()}


def render_ir_passes(cfg, ir, area_light, mats, T_cams, K, scene_dir):
    """IR stereo pairs for all views, metal then matte parts (see module docstring)."""
    from synthrgbd.bproc_ir import add_ir_frames, extended_K, ir_render_settings, make_projector, matte, metal, render_ir
    from synthrgbd.projector import make_pattern

    out = {}
    t = time.perf_counter()
    area_light.delete()
    ir_render_settings(ir)
    W, H, pad = cfg["camera"]["width"], cfg["camera"]["height"], ir["ir_render"]["pad_px"]
    pattern, _, _ = make_pattern(cfg["camera"], ir)
    proj = make_projector(pattern, ir["projector"]["fov_deg"], ir["projector"]["power_w"])
    mm = ir["materials_matte"]
    matte(mats["tray"], mm["tray_albedo"])
    matte(mats["table"], mm["table_albedo"])
    add_ir_frames(T_cams, cfg["camera"]["baseline_m"], ir["projector"]["position_x_m"], proj,
                  extended_K(K, pad), W + pad, H)
    (scene_dir / "ir").mkdir(exist_ok=True)
    out["ir_setup_s"] = time.perf_counter() - t
    mt = ir["materials_metal"]
    if mt.get("roughness") is None:
        raise SystemExit("materials_metal.roughness is not set (A-11): pass --metal-roughness or set it in the IR config")
    for name in ("metal", "matte"):
        if name == "metal":
            metal(mats["parts"], mt["base_reflectance"], mt["roughness"])
        else:
            matte(mats["parts"], mm["part_albedo"])
        t = time.perf_counter()
        imgs = render_ir()
        out[f"ir_render_{name}_s"] = time.perf_counter() - t
        t = time.perf_counter()
        for v in range(len(T_cams)):
            np.savez_compressed(scene_dir / "ir" / f"{v:06d}_{name}.npz", left=imgs[2 * v].astype(np.float16),
                                right=imgs[2 * v + 1].astype(np.float16))
        out[f"ir_export_{name}_s"] = time.perf_counter() - t
    return out


def main():
    args = parse_args()
    cfg = load_config(args.config)
    master = cfg["seeds"]["master"]
    t0 = time.perf_counter()
    timings = {}

    bproc.init()
    g = make_rng(master, args.scene_seed, 0, "scene")

    # Materials (RGB only; IR materials are M3/M4, A-11).
    alu = bproc.material.create("aluminium")
    alu.set_principled_shader_value("Base Color", [0.91, 0.92, 0.92, 1.0])
    alu.set_principled_shader_value("Metallic", 1.0)
    alu.set_principled_shader_value("Roughness", 0.3)
    grey = bproc.material.create("tray")
    grey.set_principled_shader_value("Base Color", [0.18, 0.18, 0.2, 1.0])
    grey.set_principled_shader_value("Roughness", 0.8)
    table_mat = bproc.material.create("table")
    table_mat.set_principled_shader_value("Base Color", [0.45, 0.42, 0.38, 1.0])
    table_mat.set_principled_shader_value("Roughness", 0.7)

    # Table and tray (passive rigid bodies).
    ix, iy = TRAY_INNER
    statics = [make_box("table", (2.0, 2.0, 0.02), (0, 0, -TRAY_FLOOR_T - 0.01), table_mat),
               make_box("tray_floor", (ix + 2 * TRAY_WALL_T, iy + 2 * TRAY_WALL_T, TRAY_FLOOR_T),
                        (0, 0, -TRAY_FLOOR_T / 2), grey)]
    wz = TRAY_WALL_H / 2
    for name, size, loc in [
        ("wall_px", (TRAY_WALL_T, iy + 2 * TRAY_WALL_T, TRAY_WALL_H), (ix / 2 + TRAY_WALL_T / 2, 0, wz)),
        ("wall_nx", (TRAY_WALL_T, iy + 2 * TRAY_WALL_T, TRAY_WALL_H), (-ix / 2 - TRAY_WALL_T / 2, 0, wz)),
        ("wall_py", (ix, TRAY_WALL_T, TRAY_WALL_H), (0, iy / 2 + TRAY_WALL_T / 2, wz)),
        ("wall_ny", (ix, TRAY_WALL_T, TRAY_WALL_H), (0, -iy / 2 - TRAY_WALL_T / 2, wz)),
    ]:
        statics.append(make_box(name, size, loc, grey))
    for s in statics:
        s.enable_rigidbody(False, "CONVEX_HULL", collision_margin=COLLISION_MARGIN)

    # Parts: layout, drop, settle.
    lo, hi = cfg["scene"]["parts_per_scene"]
    n_parts = int(g.integers(lo, hi + 1))
    chosen, centres, rotations = sample_layout(g, n_parts)
    parts, part_meshes = [], []
    for k, (obj_id, c, R) in enumerate(zip(chosen, centres, rotations)):
        name, spec = PART_CATALOGUE[obj_id]
        obj, mesh = make_part_object(obj_id, f"{name}_{k}", spec, alu)
        part_meshes.append(mesh)
        obj.set_local2world_mat(bproc.math.build_transformation_mat(c, R))
        parts.append(obj)

    t = time.perf_counter()
    bproc.object.simulate_physics_and_fix_final_poses(
        min_simulation_time=2.0, max_simulation_time=10.0, check_object_interval=1.0,
        substeps_per_frame=20, solver_iters=20)
    timings["physics_s"] = time.perf_counter() - t

    layout = []
    for obj, mesh in zip(parts, part_meshes):
        T = np.asarray(obj.get_local2world_mat())
        x, y, z = T[:3, 3]
        lowest = float((mesh.vertices * 1e-3 @ T[:3, :3].T + T[:3, 3])[:, 2].min())
        layout.append({"name": obj.get_name(), "obj_id": int(obj.get_cp("category_id")),
                       "position_m": [float(x), float(y), float(z)],
                       "lowest_vertex_z_mm": 1e3 * lowest,
                       "in_tray": bool(abs(x) < ix / 2 and abs(y) < iy / 2 and -0.001 < z < TRAY_WALL_H + 0.1)})

    # Light: one area light above the tray, plus dim ambient.
    light = bproc.types.Light(light_type="AREA")
    light.set_location([0.3, -0.2, 1.5])
    light.set_energy(150)
    light.blender_obj.data.size = 0.5
    bproc.renderer.set_world_background([0.05, 0.05, 0.05], strength=1.0)

    # Camera.
    W, H = cfg["camera"]["width"], cfg["camera"]["height"]
    K = intrinsics_from_hfov(W, H, cfg["camera"]["hfov_deg"])
    bproc.camera.set_intrinsics_from_K_matrix(K, W, H)
    cams, T_cams = [], []
    for _ in range(cfg["scene"]["views_per_scene"]):
        T_cam, info = sample_camera(g, cfg)
        bproc.camera.add_camera_pose(T_cam)
        cams.append(info)
        T_cams.append(np.asarray(T_cam))

    # Render RGB + z-depth (no antialiasing on depth) + instance segmentation.
    bproc.renderer.set_max_amount_of_samples(args.samples)
    bproc.renderer.enable_depth_output(activate_antialiasing=False)
    bproc.renderer.enable_segmentation_output(map_by=["instance", "category_id", "name"],
                                           default_values={"category_id": 0})
    t = time.perf_counter()
    data = bproc.renderer.render()
    timings["render_s"] = time.perf_counter() - t
    timings["render_s_per_frame"] = timings["render_s"] / len(cams)

    # A-16: nearest part pixel must be beyond Min-Z.
    for info, depth, seg in zip(cams, data["depth"], data["category_id_segmaps"]):
        part_px = (seg > 0) & np.isfinite(depth)
        info["min_part_depth_m"] = float(depth[part_px].min()) if part_px.any() else None
        info["part_pixel_fraction"] = float(part_px.mean())

    # BOP output into a scratch dataset dir, then moved to train_pbr/<scene_seed>.
    root = args.out / "synthrgbd"
    tmp = args.out / f"_tmp_{args.scene_seed:06d}"
    if tmp.exists():
        shutil.rmtree(tmp)
    t = time.perf_counter()
    bproc.writer.write_bop(str(tmp), target_objects=parts, depths=data["depth"], colors=data["colors"],
                           color_file_format="PNG", dataset="synthrgbd", depth_scale=0.1,
                           annotation_unit="mm", append_to_existing_output=False,
                           calc_mask_info_coco=False)
    timings["bop_writer_s"] = time.perf_counter() - t
    src_scene = tmp / "synthrgbd" / "train_pbr" / "000000"
    dst_scene = root / "train_pbr" / f"{args.scene_seed:06d}"
    dst_scene.parent.mkdir(parents=True, exist_ok=True)
    if dst_scene.exists():
        shutil.rmtree(dst_scene)
    shutil.move(str(src_scene), str(dst_scene))
    shutil.copy(tmp / "synthrgbd" / "camera.json", root / "camera.json")
    shutil.rmtree(tmp)

    # Raw instance segmentation per frame + the k -> segmentation-index table; scripts/bop_gt_info.py
    # turns these into mask_visib/<im_id>_<k>.png. k = index in scene_gt, which the BOP writer fills
    # in the order of target_objects (checked against obj_id here).
    gt = json.loads((dst_scene / "scene_gt.json").read_text())
    (dst_scene / "segmap").mkdir(exist_ok=True)
    seg_index = {}
    for im_id, (segmap, attrs) in enumerate(zip(data["instance_segmaps"], data["instance_attribute_maps"])):
        idx_by_name = {a["name"]: int(a["idx"]) for a in attrs}
        assert len(gt[str(im_id)]) == len(parts)
        for obj, inst in zip(parts, gt[str(im_id)]):
            assert inst["obj_id"] == obj.get_cp("category_id"), (inst, obj.get_name())
        seg_index[str(im_id)] = [idx_by_name.get(obj.get_name(), -1) for obj in parts]
        np.savez_compressed(dst_scene / "segmap" / f"{im_id:06d}.npz", instance=np.asarray(segmap, np.int32))
    (dst_scene / "segmap" / "index.json").write_text(json.dumps(seg_index))

    ir_meta = None
    if args.ir:
        ir_cfg = load_config(args.ir_config)
        if args.metal_roughness is not None:
            ir_cfg["materials_metal"]["roughness"] = args.metal_roughness
        if args.matte_part_albedo is not None:
            ir_cfg["materials_matte"]["part_albedo"] = args.matte_part_albedo
        timings.update(render_ir_passes(cfg, ir_cfg, light, {"parts": alu, "tray": grey, "table": table_mat},
                                        T_cams, K, dst_scene))
        ir_meta = {"config": str(args.ir_config.relative_to(REPO)), "samples": ir_cfg["ir_render"]["samples"],
                   "pad_px": ir_cfg["ir_render"]["pad_px"], "dot_seed": ir_cfg["dots"]["seed"],
                   "passes": ["metal", "matte"], "frame_order": "L0 R0 L1 R1 ...",
                   "materials_metal": ir_cfg["materials_metal"], "materials_matte": ir_cfg["materials_matte"]}

    timings["total_s"] = time.perf_counter() - t0
    meta = {
        "scene_seed": args.scene_seed, "master_seed": master, "rng_stream": "scene (view 0)",
        "commit": git_commit(), "blender": bpy.app.version_string, "numpy": np.__version__,
        "platform": platform.platform(), "cycles_device": bpy.context.scene.cycles.device,
        "samples": args.samples, "resolution": [W, H], "K": K.tolist(),
        "n_parts": n_parts, "layout": layout, "cameras": cams, "timings": timings,
        "mask_visib_source": "blender instance segmentation", "ir": ir_meta,
    }
    (dst_scene / "scene_meta.json").write_text(json.dumps(meta, indent=1))
    print("SCENE_META", json.dumps({"scene_seed": args.scene_seed, "timings": timings,
                                    "in_tray": [p["in_tray"] for p in layout],
                                    "lowest_vertex_z_mm": [round(p["lowest_vertex_z_mm"], 3) for p in layout],
                                    "min_part_depth_m": [c["min_part_depth_m"] for c in cams]}))


main()
