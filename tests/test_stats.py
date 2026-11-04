import numpy as np
import pytest

from synthrgbd.stats import fixed_sequence, mcnemar_exact, mde_mcnemar, scene_bootstrap_ci, scene_totals


def test_scene_totals():
    s, n = scene_totals(np.array([1, 0, 1, 1]), np.array([5, 5, 2, 9]))
    assert s.tolist() == [1, 1, 1]          # scenes 2, 5, 9
    assert n.tolist() == [1, 2, 1]


def test_bootstrap_identical_differences_collapse():
    scenes = np.repeat(np.arange(10), 3)
    lo, hi = scene_bootstrap_ci(np.full(30, 0.25), scenes, 500, np.random.default_rng(0))
    assert lo == pytest.approx(0.25) and hi == pytest.approx(0.25)


def test_bootstrap_resamples_scenes_not_instances():
    """Scene-level effects: half the scenes all succeed, half all fail. Treating instances as independent would give a CI
    of about +-0.05 on 400 instances; resampling scenes gives about +-0.3 on 10 scenes."""
    scenes = np.repeat(np.arange(10), 40)
    x = (scenes < 5).astype(float)
    lo, hi = scene_bootstrap_ci(x, scenes, 4000, np.random.default_rng(1))
    assert hi - lo > 0.4


def test_bootstrap_reproducible():
    scenes = np.repeat(np.arange(8), 2)
    x = np.arange(16) % 3 == 0
    assert scene_bootstrap_ci(x, scenes, 300, np.random.default_rng(3)) == scene_bootstrap_ci(x, scenes, 300, np.random.default_rng(3))


def test_mcnemar_exact_known_value():
    a = np.array([1] * 9 + [0] * 1 + [1] * 5 + [0] * 5, bool)
    b = np.array([0] * 9 + [1] * 1 + [1] * 5 + [0] * 5, bool)
    r = mcnemar_exact(a, b)
    assert (r["n_a_only"], r["n_b_only"]) == (9, 1)
    assert r["p"] == pytest.approx(2 * (1 + 10) / 1024)
    assert r["discordance"] == pytest.approx(0.5)


def test_mcnemar_no_discordance():
    a = np.array([1, 0, 1], bool)
    assert mcnemar_exact(a, a)["p"] == 1.0


def test_fixed_sequence():
    assert fixed_sequence([True, True, True]) == ["confirmatory: rejected"] * 3
    assert fixed_sequence([True, False, True]) == ["confirmatory: rejected", "confirmatory: not rejected", "exploratory"]
    assert fixed_sequence([False, True, True]) == ["confirmatory: not rejected", "exploratory", "exploratory"]


def test_mde_matches_a18():
    assert mde_mcnemar(0.1, 112) == pytest.approx(0.0837, abs=1e-3)   # A-18: 8 points at pi_d = 0.1, n = 112
    assert mde_mcnemar(0.3, 56) == pytest.approx(0.2049, abs=1e-3)    # A-18: 21 points at pi_d = 0.3, n = 56
