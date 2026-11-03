"""Add BOP amodal masks (mask/) and scene_gt_info.json to a rendered scene (.venv, A-35).

Usage: .venv/bin/python scripts/bop_gt_info.py <out_root> <scene_seed>

Amodal masks are ray-cast from the CAD models (synthrgbd.bop); visible masks (mask_visib/) are the
ones from Blender's instance segmentation (segmap/*.npz + segmap/index.json, written by the
Blender script) and are written here as PNGs. Reports how much of each visible mask lies
outside its amodal mask (should be ~0; non-zero only at silhouette pixels).
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from synthrgbd.bop import gt_info_entry, render_object_depth  # noqa: E402
from synthrgbd.parts import PART_CATALOGUE, make_part  # noqa: E402

root, seed = Path(sys.argv[1]), int(sys.argv[2])
scene = root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
gt = json.loads((scene / "scene_gt.json").read_text())
cams = json.loads((scene / "scene_camera.json").read_text())
tris = {i: make_part(spec).triangles for i, (_, spec) in PART_CATALOGUE.items()}
seg_index = json.loads((scene / "segmap" / "index.json").read_text())
(scene / "mask").mkdir(exist_ok=True)
(scene / "mask_visib").mkdir(exist_ok=True)

gt_info, worst_outside = {}, 0.0
for im_id in sorted(gt, key=int):
    K = np.array(cams[im_id]["cam_K"]).reshape(3, 3)
    depth = cv2.imread(str(scene / "depth" / f"{int(im_id):06d}.png"), cv2.IMREAD_UNCHANGED)
    H, W = depth.shape
    segmap = np.load(scene / "segmap" / f"{int(im_id):06d}.npz")["instance"]
    assert segmap.shape == depth.shape
    entries = []
    for k, inst in enumerate(gt[im_id]):
        R = np.array(inst["cam_R_m2c"]).reshape(3, 3)
        t = np.array(inst["cam_t_m2c"], dtype=np.float64)
        m_all = render_object_depth(tris[inst["obj_id"]], R, t, K, H, W) > 0
        idx = seg_index[im_id][k]
        m_vis = (segmap == idx) if idx >= 0 else np.zeros((H, W), bool)
        cv2.imwrite(str(scene / "mask_visib" / f"{int(im_id):06d}_{k:06d}.png"), m_vis.astype(np.uint8) * 255)
        cv2.imwrite(str(scene / "mask" / f"{int(im_id):06d}_{k:06d}.png"), m_all.astype(np.uint8) * 255)
        e = gt_info_entry(m_all, m_vis, depth)
        e["visib_px_outside_amodal"] = int((m_vis & ~m_all).sum())
        if m_vis.any():
            worst_outside = max(worst_outside, e["visib_px_outside_amodal"] / m_vis.sum())
        entries.append(e)
    gt_info[im_id] = entries
(scene / "scene_gt_info.json").write_text(json.dumps(gt_info, indent=1))
print(json.dumps({"scene_seed": seed, "worst_visib_fraction_outside_amodal": worst_outside,
                  "visib_fract": {i: [round(e["visib_fract"], 3) for e in v] for i, v in gt_info.items()}}))
