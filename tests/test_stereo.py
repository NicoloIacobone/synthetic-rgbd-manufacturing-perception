"""Own SGBM wrapper (D13) and the left-band fix (A-40) on synthetic textures with known shifts."""

import cv2
import numpy as np
import pytest

from synthrgbd.config import REPO_ROOT, load_config
from synthrgbd.stereo import (SGBM_VARIANTS, depth_from_ir, expose_to_uint8, first_valid_column, make_sgbm,
                              match_extended, pad_left)

IR_CFG = load_config(REPO_ROOT / "configs" / "camera_d415_ir.yaml")
W, H, PAD = 640, 120, 128
FX, B = 897.25, 0.055                                 # any f works here; the D415 value is pinned in test_geometry.py


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


def two_depth_pair():
    """Left/right with a disparity step (20 px, then 60 px), so part of the left image has no match in the right one."""
    n = W + PAD
    T = texture(n + 60, H)
    left = np.ascontiguousarray(T[:, :n])
    right = np.empty_like(left)
    step = n // 2
    right[:, :step] = T[:, 20:20 + step]
    right[:, step:] = T[:, step + 60:n + 60]
    return left, right


def test_left_right_check_is_off_only_with_a_large_value():
    """A-63: in OpenCV 5.0.0 disp12MaxDiff <= 0 behaves as 1, against its documentation. Off means at least the search range."""
    left, right = two_depth_pair()

    def run(v):
        return make_sgbm({**IR_CFG["sgbm"], "disp12_max_diff": v}).compute(left, right)

    on = run(1)
    assert np.array_equal(run(-1), on) and np.array_equal(run(0), on)
    off = run(1000)
    assert (off != on).sum() > 0
    assert np.array_equal(off, run(IR_CFG["sgbm"]["num_disparities"]))


def test_sgbm_variants_switch_off_what_the_ledger_says():
    """The §5.8 definition: uniqueness, left-right check and speckle filter all off (A-63)."""
    strict = make_sgbm(IR_CFG["sgbm"])
    assert strict.getUniquenessRatio() > 0 and strict.getSpeckleWindowSize() > 0
    assert 0 < strict.getDisp12MaxDiff() < IR_CFG["sgbm"]["num_disparities"]      # strict: the check is on
    for name in ("looselr", "nolr1000"):
        m = make_sgbm({**IR_CFG["sgbm"], **SGBM_VARIANTS[name]})
        assert m.getDisp12MaxDiff() >= IR_CFG["sgbm"]["num_disparities"]
    m = make_sgbm({**IR_CFG["sgbm"], **SGBM_VARIANTS["looselr"]})
    assert m.getUniquenessRatio() == 0 and m.getSpeckleWindowSize() == 0


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


# --- Step 2 (A-42 auto exposure, A-12 sensor noise) -------------------------------------------------

def test_auto_exposure_hits_setpoint_and_ignores_left_band():
    from synthrgbd.stereo import auto_exposure_gain, exposure_roi_x0
    x0 = exposure_roi_x0(FX, B, 0.45)
    assert x0 == 110                                  # ceil(f·B / Min-Z); 123 at fx 1004.6 px (A-42, A-66)
    L = np.full((10, 300), 0.02)
    L[:, :x0] = 5.0                                   # bright junk inside the band must not matter
    g = auto_exposure_gain(L, x0, 60.0)
    assert np.mean(L[:, x0:] * g) == pytest.approx(60.0)


def test_sensor_noise_shared_draws_and_variance():
    from synthrgbd.stereo import add_sensor_noise
    rng = np.random.default_rng(0)
    z = rng.normal(size=200_000)
    a = add_sensor_noise(np.full(z.shape, 100.0), z, e_per_dn=4.0, read_noise_dn=1.0)
    assert np.var(a) == pytest.approx(100 / 4 + 1, rel=0.02)          # shot (DN / e_per_dn) + read^2
    b = add_sensor_noise(np.full(z.shape, 100.0), z, e_per_dn=4.0, read_noise_dn=1.0)
    assert np.array_equal(a, b)                                       # same draws -> identical (pairing A-29)
    dark = add_sensor_noise(np.zeros(5), np.ones(5), e_per_dn=4.0, read_noise_dn=2.0)
    assert np.allclose(dark, 2.0)                                     # only read noise in the dark
