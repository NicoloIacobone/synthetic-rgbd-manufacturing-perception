import blenderproc as bproc  # noqa: I001  (BlenderProc requires this to be the first import)

"""A-28 check, Blender side: render the depth of a tilted plane at a known pose with our K.

Run:  scripts/bproc.sh scripts/bproc_check_intrinsics.py <out_dir>
Then: .venv/bin/python scripts/check_intrinsics.py <out_dir>

Writes depth.npy (BlenderProc depth output, metres), plane.json (plane in the OpenCV camera frame)
and K_blenderproc.json (K as BlenderProc reports it back after setting ours).
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from synthrgbd.geometry import intrinsics_from_hfov  # noqa: E402

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
W, H, HFOV = 1280, 720, 65.0           # configs/default.yaml camera (not read here: no yaml in Blender)

bproc.init()
K = intrinsics_from_hfov(W, H, HFOV)
bproc.camera.set_intrinsics_from_K_matrix(K, W, H)
bproc.camera.add_camera_pose(np.eye(4))  # Blender camera at the origin, looking along -z (world)

# Plane in the OpenCV camera frame (x right, y down, z forward): tilted about x and y so that
# errors in fx, cx and cy all show up. OpenCV -> Blender camera frame: diag(1, -1, -1).
def rot(axis, a):
    a_ = np.asarray(axis, float) / np.linalg.norm(axis)
    k = np.array([[0, -a_[2], a_[1]], [a_[2], 0, -a_[0]], [-a_[1], a_[0], 0]])
    return np.eye(3) + np.sin(a) * k + (1 - np.cos(a)) * k @ k

n_cv = rot([1, 0, 0], np.deg2rad(30)) @ rot([0, 1, 0], np.deg2rad(15)) @ np.array([0.0, 0.0, -1.0])
p_cv = np.array([0.01, -0.02, 0.80])
F = np.diag([1.0, -1.0, -1.0])
n_w, p_w = F @ n_cv, F @ p_cv

plane = bproc.object.create_primitive("PLANE", size=4.0)   # local normal +z
z = np.array([0.0, 0.0, 1.0])
axis = np.cross(z, n_w)
angle = np.arccos(np.clip(z @ n_w, -1, 1))
T = np.eye(4)
T[:3, :3] = rot(axis, angle) if np.linalg.norm(axis) > 1e-12 else np.eye(3)
T[:3, 3] = p_w
plane.set_local2world_mat(T)

bproc.renderer.enable_depth_output(activate_antialiasing=False)
bproc.renderer.set_max_amount_of_samples(1)
data = bproc.renderer.render()

np.save(out / "depth.npy", np.asarray(data["depth"][0], dtype=np.float64))
json.dump({"normal_cv": n_cv.tolist(), "point_cv": p_cv.tolist()}, open(out / "plane.json", "w"))
json.dump({"K_set": K.tolist(),
           "K_blenderproc": np.asarray(bproc.camera.get_intrinsics_as_K_matrix()).tolist(),
           "width": W, "height": H}, open(out / "K_blenderproc.json", "w"), indent=1)
print("wrote", out)
