"""MSSD (S-07) and part symmetries (A-20) on ideal symmetric point sets."""

import numpy as np
import pytest
from scipy.spatial import cKDTree

from synthrgbd.mssd import equal_leg_bracket_symmetries, mssd, profile_symmetries


def _grid(xs, ys, zs):
    return np.stack(np.meshgrid(xs, ys, zs, indexing="ij"), -1).reshape(-1, 3)


def square_profile_pts(a=20.0, length=200.0):
    s = np.linspace(-a, a, 9)
    return _grid(s, s, np.linspace(-length / 2, length / 2, 21))


def equal_leg_bracket_pts(leg=40.0, thick=4.0, width=20.0):
    step = 2.0
    zs = np.linspace(-width / 2, width / 2, 11)
    leg_x = _grid(np.arange(0, leg + step / 2, step), np.arange(0, thick + step / 2, step), zs)
    leg_y = leg_x[:, [1, 0, 2]]
    return np.unique(np.round(np.vstack([leg_x, leg_y]), 9), axis=0)


def _random_pose(seed):
    rng = np.random.default_rng(seed)
    q = rng.normal(size=4)
    q /= np.linalg.norm(q)
    w, x, y, z = q
    R = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = rng.uniform(-100, 100, 3) + [0, 0, 800]
    return T


CASES = [(square_profile_pts, profile_symmetries, 8), (equal_leg_bracket_pts, equal_leg_bracket_symmetries, 2)]


@pytest.mark.parametrize("pts_fn,sym_fn,n", CASES)
def test_symmetries_map_the_shape_onto_itself(pts_fn, sym_fn, n):
    pts = pts_fn()
    syms = sym_fn()
    assert len(syms) == n
    tree = cKDTree(pts)
    for S in syms:
        assert np.allclose(S[:3, :3] @ S[:3, :3].T, np.eye(3)) and np.isclose(np.linalg.det(S[:3, :3]), 1)
        mapped = pts @ S[:3, :3].T + S[:3, 3]
        assert tree.query(mapped)[0].max() < 1e-6


@pytest.mark.parametrize("pts_fn,sym_fn,n", CASES)
def test_symmetric_estimate_has_zero_mssd(pts_fn, sym_fn, n):
    pts = pts_fn()
    T_gt = _random_pose(1)
    for S in sym_fn():
        assert mssd(T_gt @ S, T_gt, pts, sym_fn()) == pytest.approx(0, abs=1e-9)
    # without symmetries, a symmetric-but-different estimate is penalised
    assert mssd(T_gt @ sym_fn()[1], T_gt, pts) > 1.0


def test_translation_offset_gives_its_magnitude():
    pts = square_profile_pts()
    T_gt = _random_pose(2)
    T_est = T_gt.copy()
    T_est[:3, 3] += [3.0, 4.0, 0.0]  # 5 mm
    assert mssd(T_est, T_gt, pts, profile_symmetries()) == pytest.approx(5.0, abs=1e-9)
