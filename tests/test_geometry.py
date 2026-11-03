"""Silent-bug guards (R5): disparity scaling, disparity <-> depth, z-depth vs ray distance."""

import cv2
import numpy as np
import pytest

from synthrgbd.config import load_config
from synthrgbd.geometry import (
    depth_to_disparity,
    disparity_to_depth,
    intrinsics_from_hfov,
    ray_distance_to_z,
    sgbm_raw_to_disparity,
    z_to_ray_distance,
)

CFG = load_config()["camera"]
K = intrinsics_from_hfov(CFG["width"], CFG["height"], CFG["hfov_deg"])
FX, B = K[0, 0], CFG["baseline_m"]


def test_d415_focal_length_and_min_z():
    # A-28: fx ~ 1004.6 px; A-16: f*B/126 ~ 0.44 m, consistent with datasheet Min-Z 0.45 m
    assert FX == pytest.approx(1004.6, abs=0.1)
    min_z = FX * B / CFG["disparity_search_px"]
    assert min_z == pytest.approx(0.4385, abs=1e-3)
    assert min_z < CFG["min_z_m"]


def test_sgbm_output_is_scaled_by_16():
    rng = np.random.default_rng(0)
    left = (rng.random((120, 240)) * 255).astype(np.uint8)
    shift = 10
    right = np.roll(left, -shift, axis=1)
    sgbm = cv2.StereoSGBM_create(minDisparity=0, numDisparities=64, blockSize=7)
    raw = sgbm.compute(left, right)
    assert raw.dtype == np.int16
    d = sgbm_raw_to_disparity(raw)[:, 100:200]
    assert np.median(d) == pytest.approx(shift, abs=0.1)


def test_disparity_depth_roundtrip_and_invalids():
    z = np.array([0.5, 0.8, 1.0, 2.0])
    d = depth_to_disparity(z, FX, B)
    assert np.allclose(disparity_to_depth(d, FX, B), z)
    # invalid: zero/negative disparity, and disparity beyond the 126 px search range (A-25)
    out = disparity_to_depth(np.array([0.0, -1.0, 126.0, 127.0]), FX, B, max_disparity_px=126)
    assert out[0] == 0 and out[1] == 0 and out[2] > 0 and out[3] == 0
    assert depth_to_disparity(np.array([0.0]), FX, B)[0] == 0


def test_ray_distance_vs_z_on_fronto_parallel_plane():
    h, w = CFG["height"], CFG["width"]
    z_true = np.full((h, w), 0.8)
    t = z_to_ray_distance(z_true, K)
    # ray distance equals z only at the principal point and is larger elsewhere
    assert t[0, 0] > 0.8 * 1.15
    assert np.allclose(ray_distance_to_z(t, K), z_true)


def test_ray_distance_invalids_map_to_zero():
    t = np.full((4, 5), np.inf)
    t[0, 0] = 0.0
    t[1, 1] = 1.0
    z = ray_distance_to_z(t, intrinsics_from_hfov(5, 4, 65.0))
    assert z[0, 0] == 0 and z[2, 2] == 0 and 0 < z[1, 1] <= 1.0


def test_plane_depth_backprojects_onto_the_plane():
    from synthrgbd.geometry import plane_depth
    K = intrinsics_from_hfov(64, 36, 65.0)
    n = np.array([0.3, -0.5, -1.0])
    n /= np.linalg.norm(n)
    p = np.array([0.02, -0.01, 0.8])
    z = plane_depth(K, n, p, 36, 64)
    assert (z > 0).all()
    u, v = np.meshgrid(np.arange(64), np.arange(36))
    X = np.stack([(u - K[0, 2]) / K[0, 0] * z, (v - K[1, 2]) / K[1, 1] * z, z], -1)
    np.testing.assert_allclose((X - p) @ n, 0.0, atol=1e-12)
    # At the principal point the ray is the optical axis.
    assert np.isclose(plane_depth(np.eye(3), [0, 0, -1], [0, 0, 0.8], 1, 1)[0, 0], 0.8)
