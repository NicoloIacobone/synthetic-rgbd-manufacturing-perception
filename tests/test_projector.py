"""Dot pattern (A-37) and projector geometry (A-36)."""

import numpy as np
import pytest
from scipy.spatial import cKDTree

from synthrgbd.config import REPO_ROOT, load_config
from synthrgbd.geometry import intrinsics_from_hfov
from synthrgbd.projector import (make_pattern, pattern_geometry, plane_pattern_in_camera, poisson_disk_dots,
                                 rasterise_dots, sample_pattern)

CAM = load_config()["camera"]
IR = load_config(REPO_ROOT / "configs" / "camera_d415_ir.yaml")
K = intrinsics_from_hfov(CAM["width"], CAM["height"], CAM["hfov_deg"])


def test_poisson_disk_count_spacing_determinism():
    pts = poisson_disk_dots(400, 300, 3000, 0.6, seed=1)
    assert pts.shape == (3000, 2)
    assert (pts >= 0).all() and (pts[:, 0] < 400).all() and (pts[:, 1] < 300).all()
    r = 0.6 * np.sqrt(400 * 300 / 3000)
    dmin = cKDTree(pts).query(pts, k=2)[0][:, 1].min()
    assert dmin >= r
    assert np.array_equal(pts, poisson_disk_dots(400, 300, 3000, 0.6, seed=1))
    assert not np.array_equal(pts, poisson_disk_dots(400, 300, 3000, 0.6, seed=2))


def test_rasterise_single_dot_peak_and_mass():
    img = rasterise_dots(np.array([[20.5, 10.5]]), 41, 21, sigma_texel=1.4)
    assert img.max() == pytest.approx(1.0, abs=1e-6)
    assert img[10, 20] == img.max()
    assert img.sum() == pytest.approx(2 * np.pi * 1.4**2, rel=0.01)


def test_pattern_geometry_d415():
    hfov, vfov = IR["projector"]["fov_deg"]
    geo = pattern_geometry(K[0, 0], hfov, vfov, IR["dots"]["oversample"])
    fpx, fpy = geo.texels_per_tan
    assert fpx == pytest.approx(2 * K[0, 0], rel=1e-3) and fpy == pytest.approx(2 * K[0, 0], rel=2e-3)
    # field corners map to the texel-grid corners
    x, y = geo.tan_to_texel(np.tan(np.deg2rad(hfov / 2)), -np.tan(np.deg2rad(vfov / 2)))
    assert x == pytest.approx(geo.width) and y == pytest.approx(0.0, abs=1e-9)


def test_dots_in_left_image_match_a37():
    """A-37: 30 000 dots over 67 x 41 deg -> ~27 700 within the 1280x720 left image (far plane)."""
    _, geo, pts = make_pattern(CAM, IR)
    fpx, fpy = geo.texels_per_tan
    tx = pts[:, 0] / fpx - geo.fx_span / 2
    ty = pts[:, 1] / fpy - geo.fy_span / 2
    u = K[0, 0] * tx + K[0, 2]
    v = K[1, 1] * ty + K[1, 2]
    n = ((u > -0.5) & (u < CAM["width"] - 0.5) & (v > -0.5) & (v < CAM["height"] - 0.5)).sum()
    assert n == pytest.approx(27700, rel=0.01)


def test_sample_pattern_texel_centres_and_clip():
    pat = np.arange(12, dtype=np.float32).reshape(3, 4)
    geo = pattern_geometry(1.0, 90.0, 90.0, 1.0)            # Fx = Fy = 2
    geo = type(geo)(4, 3, 90.0, 90.0)
    c, r = 2, 1
    tx = ((c + 0.5) / 4 - 0.5) * 2
    ty = ((r + 0.5) / 3 - 0.5) * 2
    assert sample_pattern(pat, geo, np.array([tx]), np.array([ty]))[0] == pytest.approx(pat[r, c])
    assert sample_pattern(pat, geo, np.array([5.0]), np.array([0.0]))[0] == 0.0


def test_plane_pattern_parallax():
    """A projector offset of b shifts the pattern on a plane at depth z by f b / z camera pixels."""
    _, geo, pts = make_pattern(CAM, IR)
    pat = rasterise_dots(pts, geo.width, geo.height, 1.4)
    z, b = 0.6, IR["projector"]["position_x_m"]
    a = plane_pattern_in_camera(pat, geo, K, CAM["width"], CAM["height"], z, 0.0)
    s = plane_pattern_in_camera(pat, geo, K, CAM["width"], CAM["height"], z, b)
    shift = int(round(K[0, 0] * b / z))                      # 46 px
    assert np.corrcoef(a[100:600, 200:1000].ravel(), s[100:600, 200 + shift:1000 + shift].ravel())[0, 1] > 0.99
