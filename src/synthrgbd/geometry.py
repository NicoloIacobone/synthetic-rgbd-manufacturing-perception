"""Camera geometry and depth conventions.

Conventions (A-28):
- Depth images are z-depth in metres; invalid pixels are 0 (as in RealSense output, S-03).
- Pixel (u, v) has its centre at integer coordinates (OpenCV convention); K is passed in
  explicitly so the principal point always matches the renderer's.
- OpenCV StereoSGBM returns int16 disparity scaled by 16.
"""

import numpy as np

SGBM_DISPARITY_SCALE = 16.0


def intrinsics_from_hfov(width: int, height: int, hfov_deg: float) -> np.ndarray:
    """K for square pixels, fx = fy from the horizontal FOV, principal point at the image centre."""
    fx = (width / 2.0) / np.tan(np.deg2rad(hfov_deg) / 2.0)
    cx = (width - 1) / 2.0
    cy = (height - 1) / 2.0
    return np.array([[fx, 0.0, cx], [0.0, fx, cy], [0.0, 0.0, 1.0]])


def sgbm_raw_to_disparity(raw: np.ndarray) -> np.ndarray:
    """OpenCV SGBM int16 output (disparity x 16) -> float disparity in pixels."""
    return raw.astype(np.float64) / SGBM_DISPARITY_SCALE


def disparity_to_depth(
    disparity_px: np.ndarray, fx: float, baseline_m: float, max_disparity_px: float | None = None
) -> np.ndarray:
    """z = f * B / d (S-02 Eq. 1). Non-positive disparities, and those above the matcher's
    search range (D415: 126 px, A-25), are invalid and map to depth 0."""
    d = np.asarray(disparity_px, dtype=np.float64)
    valid = d > 0
    if max_disparity_px is not None:
        valid &= d <= max_disparity_px
    depth = np.zeros_like(d)
    depth[valid] = fx * baseline_m / d[valid]
    return depth


def depth_to_disparity(depth_m: np.ndarray, fx: float, baseline_m: float) -> np.ndarray:
    """Inverse of disparity_to_depth; depth 0 (invalid) maps to disparity 0."""
    z = np.asarray(depth_m, dtype=np.float64)
    d = np.zeros_like(z)
    valid = z > 0
    d[valid] = fx * baseline_m / z[valid]
    return d


def _ray_norm(K: np.ndarray, height: int, width: int) -> np.ndarray:
    """Per-pixel norm of the unnormalised ray direction [(u-cx)/fx, (v-cy)/fy, 1]."""
    u, v = np.meshgrid(np.arange(width), np.arange(height))
    x = (u - K[0, 2]) / K[0, 0]
    y = (v - K[1, 2]) / K[1, 1]
    return np.sqrt(x**2 + y**2 + 1.0)


def ray_distance_to_z(t: np.ndarray, K: np.ndarray) -> np.ndarray:
    """Distance along the camera ray (e.g. Open3D t_hit, S-12) -> z-depth. 0/inf stay invalid (0)."""
    t = np.asarray(t, dtype=np.float64)
    z = t / _ray_norm(K, *t.shape)
    z[~np.isfinite(z) | (t <= 0)] = 0.0
    return z


def z_to_ray_distance(z: np.ndarray, K: np.ndarray) -> np.ndarray:
    """z-depth -> distance along the camera ray."""
    z = np.asarray(z, dtype=np.float64)
    return z * _ray_norm(K, *z.shape)
