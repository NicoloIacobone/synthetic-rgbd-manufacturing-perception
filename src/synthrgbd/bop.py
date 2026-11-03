"""BOP ground-truth helpers computed outside Blender (A-35).

Amodal masks (BOP mask/) are obtained by ray-casting one CAD model alone through pixel-centre rays
of K, the sampling that Blender uses (A-28 check: residual 0.0016 mm, principal-point shift 0 px).
"""

import numpy as np
import open3d as o3d


def pixel_rays(K: np.ndarray, height: int, width: int) -> np.ndarray:
    """(H, W, 6) Open3D rays from the camera centre; direction has z = 1, so t_hit is z-depth."""
    u, v = np.meshgrid(np.arange(width), np.arange(height))
    d = np.stack([(u - K[0, 2]) / K[0, 0], (v - K[1, 2]) / K[1, 1], np.ones(u.shape)], -1)
    return np.concatenate([np.zeros_like(d), d], -1).astype(np.float32)


def render_object_depth(triangles_model: np.ndarray, R: np.ndarray, t: np.ndarray,
                        K: np.ndarray, height: int, width: int) -> np.ndarray:
    """z-depth (same units as t) of one object alone; 0 where the object is not hit."""
    tri_cam = triangles_model.reshape(-1, 3) @ np.asarray(R).T + np.asarray(t)
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(o3d.core.Tensor(tri_cam.astype(np.float32)),
                        o3d.core.Tensor(np.arange(len(tri_cam), dtype=np.uint32).reshape(-1, 3)))
    hit = scene.cast_rays(o3d.core.Tensor(pixel_rays(K, height, width)))["t_hit"].numpy()
    return np.where(np.isfinite(hit), hit, 0.0).astype(np.float64)


def bbox_xywh(mask: np.ndarray) -> list[int]:
    """BOP bounding box [x, y, w, h] of a mask; [-1, -1, -1, -1] if empty (BOP convention)."""
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return [-1, -1, -1, -1]
    return [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)]


def gt_info_entry(mask_all: np.ndarray, mask_visib: np.ndarray, depth: np.ndarray) -> dict:
    """One scene_gt_info.json entry (BOP format) from amodal/visible masks and the depth image."""
    n_all = int(mask_all.sum())
    n_visib = int(mask_visib.sum())
    return {
        "bbox_obj": bbox_xywh(mask_all),
        "bbox_visib": bbox_xywh(mask_visib),
        "px_count_all": n_all,
        "px_count_valid": int((mask_all & (depth > 0)).sum()),
        "px_count_visib": n_visib,
        "visib_fract": float(n_visib / n_all) if n_all else 0.0,
    }
