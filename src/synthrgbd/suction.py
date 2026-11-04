"""Task B (PLAN §5.3): suction grasp on the masked depth points, checked against the GT mesh.

Planner (measured data only; cup radius and thresholds from configs/default.yaml task_b, A-19):
- candidate centres = the instance's scene points on a `candidate_voxel_mm` grid (first point per voxel);
- for each candidate, the measured points within the cup radius r (3D ball) are fitted with a plane (PCA);
  the normal is oriented towards the camera. The candidate "fits the cup" if the measured surface supports
  the whole disk: each of `rim_samples` points on the rim (radius r, in the fitted plane) has a measured
  point (from the ball of radius r + `rim_gap_mm`, projected onto the plane) within `rim_gap_mm`. With the
  mask erosion keeping measured points ≥ ~1.6 mm inside a true edge at 0.8 m, this keeps the disk on the part;
- the flattest fitting candidate (lowest RMS plane residual) is chosen. Its grasp point is either the raw
  measured point ("raw") or that point projected onto the fitted plane ("plane_fit"); A-44 chooses on dev.

Success (GT; all must hold), with the part's GT mesh in the camera frame:
1. the grasp point lies within `max_point_to_surface_mm` of the part's surface;
2. the angle between the grasp normal and the GT outward normal of the closest face is below
   `max_normal_error_deg`;
3. planarity (D11, A-19, A-50), on the GT tangent plane at the closest surface point: rays are cast along the
   cup axis (−n) from `cup_radius_mm` above the plane to `cup_radius_mm` below it, from a polar grid over the
   cup disk, against the GT meshes of all parts in the view. For every ray the **first surface hit** must
   exist (else the disk hangs over empty space or the tray), belong to the same part, and lie within
   ±`planarity_tolerance_mm` of the plane (two-sided: a surface rising into the cup fails, and so does a slot
   floor 8 mm below). Surfaces hidden behind the first one (e.g. the plate's own back face) do not count,
   nor do surfaces more than one cup radius above the plane (approach collisions are not checked).
"""

from dataclasses import dataclass

import numpy as np
import open3d as o3d
from scipy.spatial import cKDTree

from synthrgbd.meshdist import closest_on_triangles


@dataclass(frozen=True)
class SuctionParams:
    """Planner settings: PROVISIONAL until fixed by the A-45 rule (configs/harness.yaml suction)."""

    mask_erosion_px: int = 2
    candidate_voxel_mm: float = 2.0
    rim_samples: int = 32
    rim_gap_mm: float = 1.5
    min_neighbours: int = 20
    grasp_point: str = "plane_fit"       # "raw" | "plane_fit" (A-44)

    @classmethod
    def from_cfg(cls, cfg: dict) -> "SuctionParams":
        return cls(**{k: cfg[k] for k in cls.__dataclass_fields__ if k in cfg})


def _plane_basis(n: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(n, a)
    u /= np.linalg.norm(u)
    return u, np.cross(n, u)


def plan_suction(pts: np.ndarray, cup_radius_mm: float, p: SuctionParams) -> dict | None:
    """Choose a grasp on camera-frame points (mm). Returns dict(point, normal, rms_mm, n_candidates)."""
    if len(pts) < p.min_neighbours:
        return None
    vox = np.floor(pts / p.candidate_voxel_mm).astype(np.int64)
    _, first = np.unique(vox, axis=0, return_index=True)
    cand = np.sort(first)
    tree = cKDTree(pts)
    best = None
    a = np.linspace(0, 2 * np.pi, p.rim_samples, endpoint=False)
    rim_xy = cup_radius_mm * np.stack([np.cos(a), np.sin(a)], 1)
    for i in cand:
        nb = tree.query_ball_point(pts[i], cup_radius_mm)
        if len(nb) < p.min_neighbours:
            continue
        q = pts[nb]
        c = q.mean(0)
        _, s, vt = np.linalg.svd(q - c, full_matrices=False)
        n = vt[2]
        if n @ c > 0:                     # orient towards the camera (camera at the origin)
            n = -n
        u, v = _plane_basis(n)
        d = pts[tree.query_ball_point(pts[i], cup_radius_mm + p.rim_gap_mm)] - pts[i]
        gap, _ = cKDTree(np.stack([d @ u, d @ v], 1)).query(rim_xy)
        if gap.max() > p.rim_gap_mm:
            continue
        rms = float(s[2] / np.sqrt(len(q)))
        if best is None or rms < best[0]:
            best = (rms, i, n, c)
    if best is None:
        return None
    rms, i, n, c = best
    point = pts[i] if p.grasp_point == "raw" else pts[i] - ((pts[i] - c) @ n) * n
    return {"point": point, "normal": n, "rms_mm": rms, "n_candidates": int(len(cand))}


def closest_surface_point(tri: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, int, float]:
    """Closest point on the triangles (F, 3, 3) to x (3,), its face index and the distance."""
    cp = closest_on_triangles(x[None, :], tri[:, 0], tri[:, 1], tri[:, 2])[0]
    d = np.linalg.norm(cp - x, axis=1)
    f = int(np.argmin(d))
    return cp[f], f, float(d[f])


def face_normals(tri: np.ndarray) -> np.ndarray:
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def disk_samples(centre: np.ndarray, n: np.ndarray, r: float, ring_step_mm: float = 0.5,
                 n_angles: int = 72) -> np.ndarray:
    u, v = _plane_basis(n)
    rings = np.arange(0.0, r + 1e-9, ring_step_mm)
    a = np.linspace(0, 2 * np.pi, n_angles, endpoint=False)
    rr, aa = np.meshgrid(rings, a)
    return centre + (rr * np.cos(aa)).reshape(-1, 1) * u + (rr * np.sin(aa)).reshape(-1, 1) * v


def first_surface_heights(view_tris: list, origins: np.ndarray, direction: np.ndarray,
                          max_t: float) -> tuple[np.ndarray, np.ndarray]:
    """Cast rays origins + t·direction (t in [0, max_t]) against the triangle sets (camera frame, mm).
    Returns (t_hit, part index); t_hit = inf and index = -1 where nothing is hit within max_t, and t_hit = 0
    where the ray starts inside a part (its first hit is a back face)."""
    scene = o3d.t.geometry.RaycastingScene()
    for tri in view_tris:
        v = tri.reshape(-1, 3).astype(np.float32)
        scene.add_triangles(o3d.core.Tensor(v), o3d.core.Tensor(np.arange(len(v), dtype=np.uint32).reshape(-1, 3)))
    rays = np.hstack([origins, np.broadcast_to(direction, origins.shape)]).astype(np.float32)
    ans = scene.cast_rays(o3d.core.Tensor(rays))
    t = ans["t_hit"].numpy().astype(np.float64)
    gid = ans["geometry_ids"].numpy().astype(np.int64)
    miss = ~np.isfinite(t) | (t > max_t)
    t[miss], gid[miss] = np.inf, -1
    # A first hit on a triangle facing away from the ray means the ray started inside material: the solid
    # fills the cup volume up to the ray origin, so report t = 0 (surface at the top of the checked range).
    inside = ~miss & ((ans["primitive_normals"].numpy() @ np.asarray(direction, np.float32)) > 0)
    t[inside] = 0.0
    return t, gid


def check_success(grasp: dict | None, view_tris: list, part_index: int, cfg_b: dict) -> dict:
    """Evaluate a grasp on part `part_index` against the GT meshes of all parts in the view
    (`view_tris`: list of (F, 3, 3) triangle arrays, camera frame, mm)."""
    out = {"success": False, "has_grasp": grasp is not None}
    if grasp is None:
        return out
    r, tol = cfg_b["cup_radius_mm"], cfg_b["planarity_tolerance_mm"]
    part_tri = view_tris[part_index]
    cp, f, dist = closest_surface_point(part_tri, grasp["point"])
    n_gt = face_normals(part_tri[f:f + 1])[0]
    ang = float(np.degrees(np.arccos(np.clip(grasp["normal"] @ n_gt, -1, 1))))
    ds = disk_samples(cp, n_gt, r)
    t, gid = first_surface_heights(view_tris, ds + r * n_gt, -n_gt, 2 * r)
    h = r - t                                           # height of the first surface above the plane
    hit_same = gid == part_index
    out.update(point_to_surface_mm=dist, normal_error_deg=ang,
               disk_frac_no_hit=float((gid < 0).mean()), disk_frac_other_part=float(((gid >= 0) & ~hit_same).mean()),
               disk_max_abs_height_mm=float(np.abs(h[hit_same]).max()) if hit_same.any() else float("inf"),
               ok_point=dist <= cfg_b["max_point_to_surface_mm"],
               ok_normal=ang < cfg_b["max_normal_error_deg"])
    out["ok_planar"] = bool(hit_same.all() and np.abs(h).max() <= tol)
    out["success"] = bool(out["ok_point"] and out["ok_normal"] and out["ok_planar"])
    return out
