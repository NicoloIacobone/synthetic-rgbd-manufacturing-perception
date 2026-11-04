"""Task B (PLAN §5.3): suction grasp on the masked depth points, checked against the GT mesh.

Planner (measured data only; cup radius and thresholds from configs/default.yaml task_b, A-19):
- candidate centres = the instance's scene points on a `candidate_voxel_mm` grid (first point per voxel);
- for each candidate, the measured points within the cup radius r (3D ball) are fitted with a plane (PCA);
  the normal is oriented towards the camera. The candidate "fits the cup" if the plane-projected
  neighbours cover the disk: at least one point in each of `coverage_sectors` angular sectors of the
  outer annulus [coverage_inner_frac·r, r];
- the flattest fitting candidate (lowest RMS plane residual) is chosen. Its grasp point is either the raw
  measured point ("raw") or that point projected onto the fitted plane ("plane_fit"); A-44 chooses on dev.

Success (GT; all must hold), with the part's GT mesh in the camera frame:
1. the grasp point lies within `max_point_to_surface_mm` of the part's surface;
2. the angle between the grasp normal and the GT outward normal of the closest face is below
   `max_normal_error_deg`;
3. planarity (D11, A-19) on the GT tangent plane at the closest surface point:
   (a) the whole disk lies on the part: every disk sample is within `planarity_tolerance_mm` of the
       part's surface (this fails over slot openings, edges and corners);
   (b) no GT surface of any part in the view rises more than `planarity_tolerance_mm` above the plane
       (cup side) inside the disk's cylinder (this fails next to a bracket's other leg or a neighbour).
"""

from dataclasses import dataclass

import numpy as np
from scipy.spatial import cKDTree

from synthrgbd.meshdist import closest_on_triangles


@dataclass(frozen=True)
class SuctionParams:
    """Planner settings: PROVISIONAL until fixed by the A-45 rule (configs/harness.yaml suction)."""

    mask_erosion_px: int = 2
    candidate_voxel_mm: float = 2.0
    coverage_sectors: int = 8
    coverage_inner_frac: float = 0.7
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
    sector_w = 2 * np.pi / p.coverage_sectors
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
        d = q - pts[i]
        x, y = d @ u, d @ v
        rad = np.hypot(x, y)
        ring = rad >= p.coverage_inner_frac * cup_radius_mm
        sectors = np.unique(np.floor((np.arctan2(y[ring], x[ring]) + np.pi) / sector_w).astype(int)
                            % p.coverage_sectors)
        if len(sectors) < p.coverage_sectors:
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


def check_success(grasp: dict | None, part_tri: np.ndarray, view_surface_pts: np.ndarray, cfg_b: dict) -> dict:
    """Evaluate a grasp against the GT mesh of its part (camera frame, mm). `view_surface_pts` are dense
    GT surface samples of every part in the view (camera frame), used for check 3(b)."""
    out = {"success": False, "has_grasp": grasp is not None}
    if grasp is None:
        return out
    r, tol = cfg_b["cup_radius_mm"], cfg_b["planarity_tolerance_mm"]
    cp, f, dist = closest_surface_point(part_tri, grasp["point"])
    n_gt = face_normals(part_tri[f:f + 1])[0]
    ang = float(np.degrees(np.arccos(np.clip(grasp["normal"] @ n_gt, -1, 1))))
    ds = disk_samples(cp, n_gt, r)
    cps = closest_on_triangles(ds, part_tri[:, 0], part_tri[:, 1], part_tri[:, 2])
    disk_dev = float(np.linalg.norm(cps - ds[:, None, :], axis=2).min(1).max())
    rel = view_surface_pts - cp
    h = rel @ n_gt
    radial = np.linalg.norm(rel - h[:, None] * n_gt, axis=1)
    above = float(h[radial < r].max()) if (radial < r).any() else 0.0
    out.update(point_to_surface_mm=dist, normal_error_deg=ang, disk_max_dev_mm=disk_dev,
               max_height_above_mm=above,
               ok_point=dist <= cfg_b["max_point_to_surface_mm"],
               ok_normal=ang < cfg_b["max_normal_error_deg"],
               ok_planar=disk_dev <= tol and above <= tol)
    out["success"] = bool(out["ok_point"] and out["ok_normal"] and out["ok_planar"])
    return out
