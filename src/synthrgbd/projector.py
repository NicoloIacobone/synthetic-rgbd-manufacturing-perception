"""Dot-pattern projector model (A-36, A-37). Pure numpy: also imported inside Blender.

The projector is a pinhole that projects a pattern image ("texture") over its field of projection
(hfov x vfov). Pattern conventions, shared with the Blender light node in synthrgbd.bproc_ir:
- Projector frame = OpenCV convention (x right, y down, z forward), same orientation as the left
  imager, centre offset along x (A-41).
- A direction (x, y, z) has tangent coords tx = x/z, ty = y/z. Pattern texel (row r, col c) has its
  centre at ((c + 0.5)/Wp - 0.5) * Fx = tx and ((r + 0.5)/Hp - 0.5) * Fy = ty, with Fx = 2 tan(hfov/2),
  Fy = 2 tan(vfov/2); row 0 is the top of the field. Continuous texel coords used below are
  x_tex = (tx/Fx + 0.5) * Wp, y_tex = (ty/Fy + 0.5) * Hp (texel c spans [c, c+1)).
- Dots: static, semi-random (Poisson-disk by dart throwing), Gaussian profile, peak 1, uniform
  envelope, no speckle (A-37). One fixed pattern per seed (a camera constant).
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PatternGeometry:
    width: int          # Wp, texels
    height: int         # Hp, texels
    hfov_deg: float
    vfov_deg: float

    @property
    def fx_span(self) -> float:   # Fx = 2 tan(hfov/2): tangent-space width of the field
        return 2.0 * np.tan(np.deg2rad(self.hfov_deg) / 2.0)

    @property
    def fy_span(self) -> float:
        return 2.0 * np.tan(np.deg2rad(self.vfov_deg) / 2.0)

    @property
    def texels_per_tan(self) -> tuple[float, float]:   # equivalent pinhole focal lengths
        return self.width / self.fx_span, self.height / self.fy_span

    def tan_to_texel(self, tx, ty):
        """Tangent coords -> continuous texel coords (x_tex, y_tex)."""
        return (np.asarray(tx) / self.fx_span + 0.5) * self.width, (np.asarray(ty) / self.fy_span + 0.5) * self.height


def pattern_geometry(f_cam_px: float, hfov_deg: float, vfov_deg: float, oversample: float) -> PatternGeometry:
    """Pattern size so that one texel ~ 1/oversample left-camera pixels (pattern focal = oversample * f)."""
    fp = oversample * f_cam_px
    w = int(round(2 * fp * np.tan(np.deg2rad(hfov_deg) / 2)))
    h = int(round(2 * fp * np.tan(np.deg2rad(vfov_deg) / 2)))
    return PatternGeometry(w, h, hfov_deg, vfov_deg)


def poisson_disk_dots(width: float, height: float, count: int, min_spacing_frac: float,
                      seed: int, max_candidates_factor: int = 50) -> np.ndarray:
    """Exactly `count` points in [0, width) x [0, height) by dart throwing with minimum distance
    r = min_spacing_frac * sqrt(width * height / count). Returns (count, 2) array of (x, y)."""
    r = min_spacing_frac * np.sqrt(width * height / count)
    cell = r / np.sqrt(2.0)
    gw, gh = int(np.ceil(width / cell)), int(np.ceil(height / cell))
    grid = -np.ones((gh, gw), dtype=np.int64)
    pts = np.empty((count, 2))
    g = np.random.Generator(np.random.PCG64(seed))
    n, tried, r2 = 0, 0, r * r
    while n < count:
        if tried > max_candidates_factor * count:
            raise RuntimeError(f"dart throwing stalled at {n}/{count} points (r = {r:.2f})")
        cand = g.uniform((0.0, 0.0), (width, height), size=(4096, 2))
        tried += len(cand)
        for x, y in cand:
            ci, cj = int(y / cell), int(x / cell)
            ok = True
            for i in range(max(ci - 2, 0), min(ci + 3, gh)):
                for j in range(max(cj - 2, 0), min(cj + 3, gw)):
                    k = grid[i, j]
                    if k >= 0 and (pts[k, 0] - x) ** 2 + (pts[k, 1] - y) ** 2 < r2:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                pts[n] = (x, y)
                grid[ci, cj] = n
                n += 1
                if n == count:
                    break
    return pts


def rasterise_dots(pts: np.ndarray, width: int, height: int, sigma_texel: float) -> np.ndarray:
    """Sum of Gaussian dots (peak 1 each) sampled at texel centres; float32 (height, width), row 0 = top."""
    img = np.zeros((height, width), dtype=np.float64)
    rad = int(np.ceil(3.0 * sigma_texel))
    offs = np.arange(-rad, rad + 1)
    cx = np.floor(pts[:, 0]).astype(int)
    cy = np.floor(pts[:, 1]).astype(int)
    for dy in offs:
        for dx in offs:
            c, r = cx + dx, cy + dy
            ok = (c >= 0) & (c < width) & (r >= 0) & (r < height)
            val = np.exp(-((c + 0.5 - pts[:, 0]) ** 2 + (r + 0.5 - pts[:, 1]) ** 2) / (2 * sigma_texel**2))
            np.add.at(img, (r[ok], c[ok]), val[ok])
    return img.astype(np.float32)


def make_pattern(cam_cfg: dict, ir_cfg: dict) -> tuple[np.ndarray, PatternGeometry, np.ndarray]:
    """Pattern image, its geometry and the dot centres (texel coords) from the two configs
    (configs/default.yaml "camera", configs/camera_d415_ir.yaml)."""
    from synthrgbd.geometry import intrinsics_from_hfov

    K = intrinsics_from_hfov(cam_cfg["width"], cam_cfg["height"], cam_cfg["hfov_deg"])
    d = ir_cfg["dots"]
    hfov, vfov = ir_cfg["projector"]["fov_deg"]
    geo = pattern_geometry(K[0, 0], hfov, vfov, d["oversample"])
    pts = poisson_disk_dots(geo.width, geo.height, d["count"], d["min_spacing_frac"], d["seed"])
    sigma_tex = d["sigma_cam_px"] * geo.texels_per_tan[0] / K[0, 0]
    return rasterise_dots(pts, geo.width, geo.height, sigma_tex), geo, pts


def sample_pattern(pattern: np.ndarray, geo: PatternGeometry, tx: np.ndarray, ty: np.ndarray) -> np.ndarray:
    """Bilinear lookup of the pattern at tangent coords (as Blender's Linear interpolation, CLIP
    extension: 0 outside the field)."""
    xt, yt = geo.tan_to_texel(tx, ty)
    x, y = xt - 0.5, yt - 0.5                  # texel-centre index space
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    out = np.zeros(np.shape(x), dtype=np.float64)
    H, W = pattern.shape
    for oy, wy in ((0, 1 - fy), (1, fy)):
        for ox, wx in ((0, 1 - fx), (1, fx)):
            xi, yi = x0 + ox, y0 + oy
            ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
            v = np.zeros(np.shape(x))
            v[ok] = pattern[yi[ok], xi[ok]]
            out += wx * wy * v
    inside = (xt >= 0) & (xt <= W) & (yt >= 0) & (yt <= H)
    return np.where(inside, out, 0.0)


def plane_pattern_in_camera(pattern: np.ndarray, geo: PatternGeometry, K: np.ndarray, width: int, height: int,
                            z: float, proj_offset_x: float) -> np.ndarray:
    """Pattern value seen at each pixel of a camera (intrinsics K) looking at the fronto-parallel
    plane z = const, with the projector at (proj_offset_x, 0, 0) in the camera frame. Ignores
    shading (cos/r^2): used only to check the projector geometry of the Blender renders."""
    u, v = np.meshgrid(np.arange(width), np.arange(height))
    X = (u - K[0, 2]) / K[0, 0] * z
    Y = (v - K[1, 2]) / K[1, 1] * z
    return sample_pattern(pattern, geo, (X - proj_offset_x) / z, Y / z)
