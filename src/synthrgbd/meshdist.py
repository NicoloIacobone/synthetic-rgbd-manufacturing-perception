"""Exact float64 point-to-mesh distance (closest point on triangles, Ericson 2005, §5.1.5).

Used to verify part symmetries and, later, ground-truth surface queries. Open3D's float32
RaycastingScene.compute_distance was off by up to 0.02 mm on our meshes, too coarse for that.
"""

import numpy as np


def closest_on_triangles(p, a, b, c):
    """Exact float64 closest point on triangles (Ericson, Real-Time Collision Detection §5.1.5).
    p: (N, 3); a, b, c: (F, 3) -> (N, F, 3)."""
    p = p[:, None, :]
    ab, ac = b - a, c - a
    ap, bp, cp = p - a, p - b, p - c
    d1, d2 = (ab * ap).sum(-1), (ac * ap).sum(-1)
    d3, d4 = (ab * bp).sum(-1), (ac * bp).sum(-1)
    d5, d6 = (ab * cp).sum(-1), (ac * cp).sum(-1)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    with np.errstate(divide="ignore", invalid="ignore"):
        denom = va + vb + vc
        v, w = vb / denom, vc / denom
        out = a + v[..., None] * ab + w[..., None] * ac                      # interior
        t_ab, t_ac = d1 / (d1 - d3), d2 / (d2 - d6)
        t_bc = (d4 - d3) / ((d4 - d3) + (d5 - d6))
    regions = [                                                              # later wins
        (vc <= 0) & (d1 >= 0) & (d3 <= 0), a + t_ab[..., None] * ab,         # edge ab
        (vb <= 0) & (d2 >= 0) & (d6 <= 0), a + t_ac[..., None] * ac,         # edge ac
        (va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0), b + t_bc[..., None] * (c - b),  # edge bc
        (d1 <= 0) & (d2 <= 0), np.broadcast_to(a, out.shape),                # vertex a
        (d3 >= 0) & (d4 <= d3), np.broadcast_to(b, out.shape),               # vertex b
        (d6 >= 0) & (d5 <= d6), np.broadcast_to(c, out.shape),               # vertex c
    ]
    for mask, q in zip(regions[::2], regions[1::2]):
        out = np.where(mask[..., None], q, out)
    return out


def surface_distance(triangles: np.ndarray, pts: np.ndarray, chunk: int = 500) -> np.ndarray:
    """Unsigned distance from each point (N, 3) to the closest of the triangles (F, 3, 3)."""
    t = np.asarray(triangles, dtype=np.float64)
    pts = np.asarray(pts, dtype=np.float64)
    d = []
    for i in range(0, len(pts), chunk):
        q = closest_on_triangles(pts[i:i + chunk], t[:, 0], t[:, 1], t[:, 2])
        d.append(np.linalg.norm(q - pts[i:i + chunk, None, :], axis=-1).min(1))
    return np.concatenate(d)
