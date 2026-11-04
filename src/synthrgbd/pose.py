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
from dataclasses import replace as _replace

import cv2
import numpy as np
import open3d as o3d
from scipy.spatial import cKDTree

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
    """Provisional until fixed by the A-45 pooled worst-case rule (configs/harness.yaml).

    solver "o3d": Open3D point-to-plane (M4 step 1; diverges on near-planar views, A-46).
    solver "lm": own damped point-to-plane (Levenberg-Marquardt) with a coarse-to-fine schedule `stages`
    of (max correspondence distance, Tukey scale) in mm; back-face culling refreshed every iteration."""

    mask_erosion_px: int = 2
    max_corr_mm: float = 15.0
    tukey_k_mm: float = 5.0          # 0 = no robust kernel (plain least squares)
    outer_iters: int = 5             # back-face culling refreshes ("o3d")
    inner_iters: int = 30            # iterations per outer loop ("o3d") or per stage ("lm")
    min_points: int = 30             # fewer valid scene points -> no estimate (counted as failure)
    solver: str = "o3d"
    stages: tuple | None = None      # ((max_corr_mm, tukey_k_mm), ...) coarse-to-fine; None = ((max_corr_mm, tukey_k_mm),)
    visibility: str = "backface"     # "backface" | "raycast" (first hit from the camera on the CAD mesh: self-occlusion)
    damping: float = 1e-3            # "lm": Tikhonov lambda = damping * sum(w), on (L·ω, v)
    damping_len_mm: float = 30.0     # "lm": length scale L that makes rotation and translation comparable
    max_step_mm: float = 5.0         # "lm": per-iteration clamp
    max_step_deg: float = 5.0
    knn: int = 8                     # "lm": nearest model points searched for a camera-facing one
    o3d_step_clamp: bool = False     # "o3d": run single iterations and clamp each to max_step_mm / max_step_deg

    @classmethod
    def from_cfg(cls, cfg: dict) -> "IcpParams":
        kw = {k: cfg[k] for k in cls.__dataclass_fields__ if k in cfg}
        if kw.get("stages") is not None:
            kw["stages"] = tuple(tuple(map(float, st)) for st in kw["stages"])
        return cls(**kw)


def _model_scene(tri: np.ndarray, cache: dict = {}):                  # noqa: B006 (deliberate cache)
    key = (id(tri), tri.shape)
    if key not in cache:
        sc = o3d.t.geometry.RaycastingScene()
        v = tri.reshape(-1, 3).astype(np.float32)
        sc.add_triangles(o3d.core.Tensor(v), o3d.core.Tensor(np.arange(len(v), dtype=np.uint32).reshape(-1, 3)))
        cache[key] = sc
    return cache[key]


def visible_model_points(model_pts: np.ndarray, model_nrm: np.ndarray, cam_in_model: np.ndarray,
                         tri: np.ndarray | None, tol_mm: float = 0.5) -> np.ndarray:
    """Mask of model points that face the camera and, if `tri` is given, are the first hit of the ray from the
    camera centre (self-occlusion removed)."""
    facing = np.einsum("ij,ij->i", model_nrm, model_pts - cam_in_model) < 0
    if tri is None:
        return facing
    d = model_pts[facing] - cam_in_model
    dist = np.linalg.norm(d, axis=1)
    rays = np.hstack([np.broadcast_to(cam_in_model, d.shape), d / dist[:, None]]).astype(np.float32)
    t = _model_scene(tri).cast_rays(o3d.core.Tensor(rays))["t_hit"].numpy()
    vis = facing.copy()
    vis[facing] = t >= dist - tol_mm
    return vis


def _model_tree(model_pts: np.ndarray, cache: dict = {}) -> cKDTree:   # noqa: B006 (deliberate cache)
    key = (id(model_pts), model_pts.shape)
    if key not in cache:
        cache[key] = cKDTree(model_pts)
    return cache[key]


def icp_lm(scene_pts: np.ndarray, model_pts: np.ndarray, model_nrm: np.ndarray, T_init: np.ndarray,
           p: IcpParams) -> tuple[np.ndarray | None, dict]:
    """Damped point-to-plane ICP. Estimates A (camera -> model) applied to the scene points; the pose is A^-1.
    Residual r_i = n_i·(A p_i - q_i) to the nearest camera-facing model point q_i (CAD normal n_i);
    Jacobian [x_i × n_i, n_i] for a left update A <- exp(ω, v) A; Tukey weights; Levenberg damping keeps
    degenerate directions (sliding along a prism, in-plane on a single face) from exploding."""
    info = {"n_scene": int(len(scene_pts))}
    if len(scene_pts) < p.min_points:
        info["status"] = "too_few_points"
        return None, info
    tree = _model_tree(model_pts)
    A = np.linalg.inv(np.asarray(T_init, np.float64))
    k = min(p.knn, len(model_pts))
    n_inl = 0
    for max_corr, tukey in p.stages:
        for _ in range(p.inner_iters):
            x = scene_pts @ A[:3, :3].T + A[:3, 3]
            cam = A[:3, 3]                                             # camera centre in the model frame
            dist, idx = tree.query(x, k=k, distance_upper_bound=max_corr)
            idx = np.atleast_2d(idx.T).T if k == 1 else idx
            valid = idx < len(model_pts)
            safe = np.where(valid, idx, 0)
            facing = valid & (np.einsum("ijk,ijk->ij", model_nrm[safe], model_pts[safe] - cam) < 0)
            first = np.argmax(facing, axis=1)
            ok = facing[np.arange(len(x)), first]
            if ok.sum() < 6:
                info.update(status="no_correspondences", fitness=0.0)
                return None, info
            j = safe[np.arange(len(x)), first][ok]
            q, n, xs = model_pts[j], model_nrm[j], x[ok]
            r = np.einsum("ij,ij->i", n, xs - q)
            w = (1 - (r / tukey) ** 2) ** 2 * (np.abs(r) < tukey) if tukey > 0 else np.ones_like(r)
            J = np.hstack([np.cross(xs, n), n])
            H = J.T @ (J * w[:, None])
            g = J.T @ (w * r)
            H += p.damping * w.sum() * np.diag([p.damping_len_mm ** 2] * 3 + [1.0] * 3)
            delta = -np.linalg.solve(H, g)
            om, v = delta[:3], delta[3:]
            ang = np.linalg.norm(om)
            s = min(1.0, np.deg2rad(p.max_step_deg) / ang if ang > 0 else 1.0,
                    p.max_step_mm / np.linalg.norm(v) if np.linalg.norm(v) > 0 else 1.0)
            om, v = om * s, v * s
            dA = np.eye(4)
            dA[:3, :3] = axis_angle(om, np.linalg.norm(om)) if np.linalg.norm(om) > 0 else np.eye(3)
            dA[:3, 3] = v
            A = dA @ A
            n_inl = int((w > 0).sum())
            if np.linalg.norm(v) < 1e-5 and np.linalg.norm(om) < 1e-7:
                break
    info.update(status="ok", fitness=n_inl / len(scene_pts))
    return np.linalg.inv(A), info


def icp_refine(scene_pts: np.ndarray, model_pts: np.ndarray, model_nrm: np.ndarray,
               T_init: np.ndarray, p: IcpParams, model_tri: np.ndarray | None = None) -> tuple[np.ndarray | None, dict]:
    """Refine a model-to-camera pose. Returns (T_est or None, info). `model_tri` (CAD triangles, model frame)
    is needed for visibility="raycast"."""
    stages = p.stages if p.stages is not None else ((p.max_corr_mm, p.tukey_k_mm),)
    if p.solver == "lm":
        return icp_lm(scene_pts, model_pts, model_nrm, T_init, p if p.stages else _replace(p, stages=stages))
    T, info = np.asarray(T_init, np.float64), {}
    for max_corr, tukey in stages:
        T_new, info = _icp_o3d(scene_pts, model_pts, model_nrm, T, _replace(p, max_corr_mm=max_corr, tukey_k_mm=tukey),
                               model_tri if p.visibility == "raycast" else None)
        if T_new is None:
            return None, info
        T = T_new
    info["stages"] = len(stages)
    return T, info


def _clamp_increment(T_old: np.ndarray, T_new: np.ndarray, max_mm: float, max_deg: float) -> np.ndarray:
    """Limit the pose change T_new·T_old^-1 to max_deg (rotation about the object centre in the camera frame is
    approximated by the rotation part) and max_mm (translation of the model origin)."""
    D = T_new @ np.linalg.inv(T_old)
    c = np.clip((np.trace(D[:3, :3]) - 1) / 2, -1, 1)
    ang = np.degrees(np.arccos(c))
    dt = T_new[:3, 3] - T_old[:3, 3]
    s = min(1.0, max_deg / ang if ang > 0 else 1.0, max_mm / np.linalg.norm(dt) if np.linalg.norm(dt) > 0 else 1.0)
    if s >= 1.0:
        return T_new
    rv, _ = cv2.Rodrigues(D[:3, :3])
    R = cv2.Rodrigues(rv * s)[0]
    out = np.eye(4)
    out[:3, :3] = R @ T_old[:3, :3]
    out[:3, 3] = T_old[:3, 3] + s * dt
    return out


def _icp_o3d(scene_pts, model_pts, model_nrm, T_init, p, tri):
    """One Open3D point-to-plane stage with visibility refreshes (M4 step 1 harness)."""
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
    crit1 = o3d.pipelines.registration.ICPConvergenceCriteria(relative_fitness=0, relative_rmse=0, max_iteration=1)
    T = np.asarray(T_init, np.float64).copy()
    for _ in range(p.outer_iters):
        R, t = T[:3, :3], T[:3, 3]
        cam_in_model = -R.T @ t
        facing = visible_model_points(model_pts, model_nrm, cam_in_model, tri)
        tgt = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(model_pts[facing]))
        tgt.normals = o3d.utility.Vector3dVector(model_nrm[facing])
        if p.o3d_step_clamp:          # one iteration per call; clamp each increment (near-planar views diverge)
            T_new = T
            for _ in range(p.inner_iters):
                reg = o3d.pipelines.registration.registration_icp(src, tgt, p.max_corr_mm, np.linalg.inv(T_new), est, crit1)
                T_next = np.linalg.inv(np.asarray(reg.transformation))
                T_next = _clamp_increment(T_new, T_next, p.max_step_mm, p.max_step_deg)
                done = np.linalg.norm(T_next[:3, 3] - T_new[:3, 3]) < 1e-5
                T_new = T_next
                if done:
                    break
            reg = o3d.pipelines.registration.evaluate_registration(src, tgt, p.max_corr_mm, np.linalg.inv(T_new))
        else:
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
