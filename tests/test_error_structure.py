"""A-73: the surrogates keep what they claim to keep and touch nothing else."""

import numpy as np
import pytest

from synthrgbd.error_structure import scramble_errors


def _maps():
    g = np.random.default_rng(1)
    z_true = np.full((40, 50), 8000, dtype=np.uint16)
    z = (z_true.astype(np.int64) + g.integers(-30, 200, z_true.shape)).astype(np.uint16)
    z[5:8, 5:8] = 0
    mask = np.zeros(z.shape, bool)
    mask[2:30, 2:40] = True
    return z, z_true, mask


def test_shuffle_keeps_the_error_distribution_of_the_part():
    z, z_true, mask = _maps()
    out = scramble_errors(z, z_true, mask, np.random.default_rng(0), "shuffle")
    sel = mask & (z > 0)
    assert np.array_equal(np.sort(out[sel]), np.sort(z[sel]))
    assert not np.array_equal(out[sel], z[sel])


def test_sign_keeps_magnitudes_and_removes_one_sidedness():
    z, z_true, mask = _maps()
    out = scramble_errors(z, z_true, mask, np.random.default_rng(0), "sign")
    sel = mask & (z > 0)
    a, b = z[sel].astype(int) - 8000, out[sel].astype(int) - 8000
    assert np.array_equal(np.abs(a), np.abs(b))
    # Random signs on these 1055 pixels: standard error of the mean = rms / sqrt(n) = 108 / 32.5 = 3.3, so 15 is about 4.5 standard errors.
    assert a.mean() > 40 and abs(b.mean()) < 15


def test_both_keeps_magnitudes_as_a_set_and_removes_their_layout():
    z, z_true, mask = _maps()
    out = scramble_errors(z, z_true, mask, np.random.default_rng(0), "both")
    sel = mask & (z > 0)
    a, b = z[sel].astype(int) - 8000, out[sel].astype(int) - 8000
    assert np.array_equal(np.sort(np.abs(a)), np.sort(np.abs(b)))
    assert not np.array_equal(np.abs(a), np.abs(b))
    assert abs(b.mean()) < 15   # same bound as the sign test


@pytest.mark.parametrize("mode", ["shuffle", "sign", "both"])
def test_invalid_pixels_and_pixels_outside_the_mask_are_untouched(mode):
    z, z_true, mask = _maps()
    out = scramble_errors(z, z_true, mask, np.random.default_rng(0), mode)
    assert (out[z == 0] == 0).all()
    assert np.array_equal(out[~mask], z[~mask])


def test_unknown_mode_is_refused():
    z, z_true, mask = _maps()
    with pytest.raises(ValueError):
        scramble_errors(z, z_true, mask, np.random.default_rng(0), "other")
