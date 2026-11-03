"""Maximum Symmetry-Aware Surface Distance (BOP 2020, S-07 eq. 2) and part symmetries.

e_MSSD = min over symmetries S of max over model points x of || P_est x - P_gt S x ||_2

Model-frame conventions (A-20), which the procedural mesh generator must follow:
- Profile: extrusion axis = z, centred at the origin, square cross-section centred on the axis.
- Equal-leg L-bracket: corner at the origin, legs along +x and +y, centred in z.
"""

import numpy as np


def _rot(axis, angle_rad: float) -> np.ndarray:
    a = np.asarray(axis, dtype=np.float64)
    a = a / np.linalg.norm(a)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(angle_rad) * k + (1 - np.cos(angle_rad)) * k @ k


def _pose(R: np.ndarray, t=(0.0, 0.0, 0.0)) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


def profile_symmetries() -> list[np.ndarray]:
    """Square profile: 4-fold about z x 2-fold end flip (180 deg about x) = 8 transforms."""
    flips = [np.eye(3), _rot([1, 0, 0], np.pi)]
    return [_pose(F @ _rot([0, 0, 1], k * np.pi / 2)) for F in flips for k in range(4)]


def equal_leg_bracket_symmetries() -> list[np.ndarray]:
    """Equal-leg L-bracket: identity and 180 deg about the leg bisector (1, 1, 0)."""
    return [np.eye(4), _pose(_rot([1, 1, 0], np.pi))]


def _apply(T: np.ndarray, pts: np.ndarray) -> np.ndarray:
    return pts @ T[:3, :3].T + T[:3, 3]


def mssd(T_est: np.ndarray, T_gt: np.ndarray, model_pts: np.ndarray, symmetries=None) -> float:
    """MSSD in the units of model_pts. T_* are 4x4 model-to-camera poses."""
    syms = symmetries if symmetries is not None else [np.eye(4)]
    p_est = _apply(T_est, model_pts)
    errs = [np.linalg.norm(p_est - _apply(T_gt @ S, model_pts), axis=1).max() for S in syms]
    return float(min(errs))
