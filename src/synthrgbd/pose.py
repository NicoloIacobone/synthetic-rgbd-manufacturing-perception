"""Task A harness (PLAN §5.2, A-46): masked depth -> point-to-plane ICP against the CAD model.

- Scene points: depth pixels inside the (eroded) ground-truth visible mask (A-07), back-projected
  through K (z-depth, A-28), in mm.
- Model points: area-uniform samples on the CAD mesh **with the CAD face normals** (A-46), so sensor
  noise never enters the normals.
- ICP: Open3D point-to-plane from scene (source) to model (target, model frame). An outer loop
  culls model points whose normal faces away from the camera at the current pose estimate, so a
  4 mm bracket plate cannot lock onto its far face. Robust kernel and maximum correspondence
  distance come from configs/harness.yaml (provisional until tuned by the A-45 rule).
- Initial offsets (A-30): a translation of exactly `mm` in a uniformly random direction, composed
  with a rotation of exactly `deg` about a uniformly random axis through the model's bounding-box
  centre. Directions and axes are drawn once per instance from the `init_offset` stream (§5.10),
  so every condition and every sweep level shares them; the level only scales the magnitude.
"""

from dataclasses import dataclass

import cv2
import numpy as np
import open3d as o3d

from synthrgbd.mssd import equal_leg_bracket_symmetries, profile_symmetries
from synthrgbd.parts import PART_CATALOGUE, Mesh, ProfileSpec, make_part


def load_part_models(n_pts: int, seed: int) -> dict:
    """Per obj_id: mesh, CAD samples + normals (seed: harness constant), unique vertices (MSSD),
    bounding-box centre (offset pivot) and symmetries (A-20)."""
    models = {}
    for obj_id, (name, spec) in PART_CATALOGUE.items():
        mesh = make_part(spec)
        pts, nrm = sample_with_normals(mesh, n_pts, np.random.default_rng([seed, obj_id]))
        verts = unique_vertices(mesh)
        is_profile = isinstance(spec, ProfileSpec)
        models[obj_id] = {
            "name": name, "mesh": mesh, "pts": pts, "nrm": nrm, "verts": verts,
            "centre": (verts.min(0) + verts.max(0)) / 2,
            "syms": profile_symmetries() if is_profile else equal_leg_bracket_symmetries(),
            "type": "profile" if is_profile else "bracket"}
    return models


def erode_mask(mask: np.ndarray, px: int) -> np.ndarray:
    """Erode a boolean mask by `px` pixels (square structuring element of side 2 px + 1)."""
    if px <= 0:
        return mask.astype(bool)
    k = np.ones((2 * px + 1, 2 * px + 1), np.uint8)
    return cv2.erode(mask.astype(np.uint8), k, borderValue=0) > 0


def backproject(depth_mm: np.ndarray, mask: np.ndarray, K: np.ndarray) -> np.ndarray:
    """(N, 3) camera-frame points (mm) of the valid (> 0) depth pixels inside `mask`."""
    v, u = np.nonzero(mask & (depth_mm > 0))
    z = depth_mm[v, u].astype(np.float64)
    x = (u - K[0, 2]) * z / K[0, 0]
    y = (v - K[1, 2]) * z / K[1, 1]
    return np.stack([x, y, z], 1)


def sample_with_normals(mesh: Mesh, n: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Area-uniform surface samples (n, 3) mm and their face normals (n, 3)."""
    t = mesh.triangles
    cr = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    area = 0.5 * np.linalg.norm(cr, axis=1)
    f = rng.choice(len(t), size=n, p=area / area.sum())
    s, r2 = np.sqrt(rng.random(n)), rng.random(n)
    w0, w1, w2 = 1 - s, s * (1 - r2), s * r2
    pts = w0[:, None] * t[f, 0] + w1[:, None] * t[f, 1] + w2[:, None] * t[f, 2]
    return pts, cr[f] / np.linalg.norm(cr[f], axis=1, keepdims=True)


def unique_vertices(mesh: Mesh) -> np.ndarray:
    """Distinct mesh vertices (mm). MSSD over a polyhedron's surface is attained at a vertex."""
    return np.unique(np.round(mesh.vertices, 9), axis=0)


def axis_angle(axis: np.ndarray, angle_rad: float) -> np.ndarray:
    a = np.asarray(axis, np.float64) / np.linalg.norm(axis)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(angle_rad) * k + (1 - np.cos(angle_rad)) * k @ k


def draw_offset_directions(rng: np.random.Generator, n_instances: int) -> np.ndarray:
    """(n, 2, 3): per instance a unit translation direction and a unit rotation axis (uniform on S²).
    Drawn in instance (gt_id) order from the `init_offset` stream so conditions share them."""
    d = rng.normal(size=(n_instances, 2, 3))
    return d / np.linalg.norm(d, axis=2, keepdims=True)


def apply_offset(T_gt: np.ndarray, direction: np.ndarray, axis: np.ndarray, mm: float, deg: float,
                 centre_model: np.ndarray) -> np.ndarray:
    """Model-to-camera pose offset from T_gt by exactly `mm` (centre displacement) and `deg`
    (rotation about `axis`, camera frame, through the model point `centre_model`)."""
    R_off = axis_angle(axis, np.deg2rad(deg))
    R_gt, t_gt = T_gt[:3, :3], T_gt[:3, 3]
    c_cam = R_gt @ centre_model + t_gt
    T = np.eye(4)
    T[:3, :3] = R_off @ R_gt
    T[:3, 3] = R_off @ (t_gt - c_cam) + c_cam + mm * np.asarray(direction) / np.linalg.norm(direction)
    return T


def rotation_error_deg(R_a: np.ndarray, R_b: np.ndarray) -> float:
    c = (np.trace(R_a.T @ R_b) - 1) / 2
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


@dataclass(frozen=True)
class IcpParams:
    """Provisional until fixed by the A-45 pooled worst-case rule (configs/harness.yaml)."""

    mask_erosion_px: int = 2
    max_corr_mm: float = 15.0
    tukey_k_mm: float = 5.0          # 0 = no robust kernel (plain least squares)
    outer_iters: int = 5             # back-face culling refreshes
    inner_iters: int = 30            # Open3D ICP iterations per outer loop
    min_points: int = 30             # fewer valid scene points -> no estimate (counted as failure)

    @classmethod
    def from_cfg(cls, cfg: dict) -> "IcpParams":
        return cls(**{k: cfg[k] for k in cls.__dataclass_fields__ if k in cfg})


def icp_refine(scene_pts: np.ndarray, model_pts: np.ndarray, model_nrm: np.ndarray,
               T_init: np.ndarray, p: IcpParams) -> tuple[np.ndarray | None, dict]:
    """Refine a model-to-camera pose. Returns (T_est or None, info)."""
    info = {"n_scene": int(len(scene_pts))}
    if len(scene_pts) < p.min_points:
        info["status"] = "too_few_points"
        return None, info
    src = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(scene_pts))
    est = (o3d.pipelines.registration.TransformationEstimationPointToPlane(
        o3d.pipelines.registration.TukeyLoss(k=p.tukey_k_mm)) if p.tukey_k_mm > 0
        else o3d.pipelines.registration.TransformationEstimationPointToPlane())
    crit = o3d.pipelines.registration.ICPConvergenceCriteria(
        relative_fitness=1e-7, relative_rmse=1e-7, max_iteration=p.inner_iters)
    T = np.asarray(T_init, np.float64).copy()
    for _ in range(p.outer_iters):
        R, t = T[:3, :3], T[:3, 3]
        cam_in_model = -R.T @ t
        facing = np.einsum("ij,ij->i", model_nrm, model_pts - cam_in_model) < 0
        tgt = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(model_pts[facing]))
        tgt.normals = o3d.utility.Vector3dVector(model_nrm[facing])
        reg = o3d.pipelines.registration.registration_icp(
            src, tgt, p.max_corr_mm, np.linalg.inv(T), est, crit)
        T_new = np.linalg.inv(np.asarray(reg.transformation))
        moved = np.linalg.norm(T_new[:3, 3] - T[:3, 3]) + np.abs(T_new[:3, :3] - R).max()
        T = T_new
        info.update(fitness=float(reg.fitness), inlier_rmse=float(reg.inlier_rmse))
        if moved < 1e-6:
            break
    info["status"] = "ok" if info["fitness"] > 0 else "no_correspondences"
    return (T if info["fitness"] > 0 else None), info
