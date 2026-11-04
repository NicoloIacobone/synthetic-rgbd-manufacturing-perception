"""Own SGBM wrapper (D13) and the left-band fix (A-40) on synthetic textures with known shifts."""

import cv2
import numpy as np
import pytest

from synthrgbd.config import REPO_ROOT, load_config
from synthrgbd.stereo import (depth_from_ir, expose_to_uint8, first_valid_column, make_sgbm, match_extended,
                              pad_left)

IR_CFG = load_config(REPO_ROOT / "configs" / "camera_d415_ir.yaml")
W, H, PAD = 640, 120, 128
FX, B = 1004.6, 0.055


def texture(width, height, seed=0):
    """Random dot-like texture, 8-bit, no periodicity."""
    g = np.random.default_rng(seed)
    t = cv2.GaussianBlur(g.uniform(0, 1, (height, width)), (0, 0), 0.8)
    return expose_to_uint8((t - t.min()) / np.ptp(t), 255.0)


def shifted_pair(d):
    """Left/right images extended by PAD on the left, with constant integer disparity d:
    left(x) = T[x], right(x') = T[x' + d], so right(x - d) = left(x)."""
    n = W + PAD
    T = texture(n + d, H)
    return np.ascontiguousarray(T[:, :n]), np.ascontiguousarray(T[:, d:d + n])


@pytest.fixture(scope="module")
def sgbm():
    return make_sgbm(IR_CFG["sgbm"])


@pytest.mark.parametrize("d", [55, 92, 110])
def test_band_width_equals_disparity(sgbm, d):
    left, right = shifted_pair(d)
    disp = match_extended(left, right, PAD, sgbm, 126)
    assert disp.shape == (H, W)
    valid = disp > 0
    first = first_valid_column(valid)
    assert np.median(first) == d                                    # band = f B / Z (A-40), not 128
    assert np.median(disp[valid]) == pytest.approx(d, abs=1 / 16)
    rows = slice(4, H - 4)                                          # away from the window border
    assert valid[rows, d:].mean() > 0.99
    assert not valid[:, :d].any()                                   # x - d < 0 is never valid


def test_plain_sgbm_band_is_num_disparities(sgbm):
    """Documents the OpenCV pitfall of A-40: without the extension the first 128 columns are invalid."""
    left, right = shifted_pair(55)
    raw = sgbm.compute(np.ascontiguousarray(left[:, PAD:]), np.ascontiguousarray(right[:, PAD:]))
    assert np.median(first_valid_column(raw >= 0)) >= 128


def test_zero_padded_left_matches_extended(sgbm):
    """Left image rendered at the D415 width only, zero-padded: same band and disparities."""
    left, right = shifted_pair(55)
    disp = match_extended(pad_left(np.ascontiguousarray(left[:, PAD:]), PAD), right, PAD, sgbm, 126)
    assert np.median(first_valid_column(disp > 0)) == 55
    assert np.median(disp[disp > 0]) == pytest.approx(55, abs=1 / 16)


def test_disparity_above_search_range_is_invalid(sgbm):
    """d > 126 px is masked (A-25): a shift of 127 px gives (almost) no valid pixels."""
    left, right = shifted_pair(127)
    disp = match_extended(left, right, PAD, sgbm, 126)
    assert (disp > 0).mean() < 0.02
    left, right = shifted_pair(126)
    disp = match_extended(left, right, PAD, sgbm, 126)
    assert (disp[4:-4, 126:] > 0).mean() > 0.99


def test_pad_too_small_raises(sgbm):
    left, right = shifted_pair(55)
    with pytest.raises(ValueError):
        match_extended(left[:, 64:], right[:, 64:], 64, sgbm, 126)


def test_requires_uint8(sgbm):
    left, right = shifted_pair(55)
    with pytest.raises(TypeError):
        match_extended(left.astype(np.uint16), right.astype(np.uint16), PAD, sgbm, 126)


def test_depth_from_linear_ir(sgbm):
    """Float radiance in, metric z-depth out: z = f B / d (x16 scaling handled), invalid = 0."""
    left, right = shifted_pair(55)
    gain = 1000.0
    z, disp = depth_from_ir(left / gain, right / gain, gain, PAD, sgbm, FX, B, 126)
    v = z > 0
    assert np.array_equal(v, disp > 0)
    assert np.median(z[v]) == pytest.approx(FX * B / 55, rel=1e-3)
    assert not v[:, :55].any()


def test_expose_to_uint8_clips_and_rounds():
    out = expose_to_uint8(np.array([-1.0, 0.0, 0.0024, 0.0026, 1.0, 10.0]), 200.0)
    assert out.dtype == np.uint8
    assert out.tolist() == [0, 0, 0, 1, 200, 255]
