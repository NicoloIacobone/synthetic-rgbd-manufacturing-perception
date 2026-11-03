"""Seed policy (PLAN §5.10) and protocol config consistency with PLAN §5."""

import numpy as np

from synthrgbd.config import load_config
from synthrgbd.seeds import STREAMS, rng, scene_seeds

CFG = load_config()


def test_streams_are_reproducible_and_independent():
    a = rng(0, 3, 1, "ir_noise").random(5)
    assert np.array_equal(a, rng(0, 3, 1, "ir_noise").random(5))
    for other in [rng(0, 3, 1, "init_offset"), rng(0, 3, 0, "ir_noise"), rng(0, 4, 1, "ir_noise"), rng(1, 3, 1, "ir_noise")]:
        assert not np.array_equal(a, other.random(5))
    assert len(set(STREAMS.values())) == len(STREAMS)


def test_dev_and_test_scenes_are_disjoint():
    test = scene_seeds(CFG["seeds"]["test_scenes"])
    dev = scene_seeds(CFG["seeds"]["dev_scenes"])
    assert len(test) == 50 and len(dev) == 5
    assert not set(test) & set(dev)


def test_protocol_values_match_plan():
    a, b, s = CFG["task_a"], CFG["task_b"], CFG["sanity"]
    assert a["init_offset"] == {"mm": 10, "deg": 10} and a["recall_threshold_mm"] == 5.0
    assert b["cup_radius_mm"] == 10.0 and b["planarity_tolerance_mm"] == 1.0
    assert b["max_normal_error_deg"] == 15.0 and b["max_point_to_surface_mm"] == 2.0
    assert s["c1_zero_offset_max_mssd_mm"] == 0.5 and s["c1_zero_offset_min_fraction"] == 0.99
    assert CFG["camera"]["sgbm_num_disparities"] % 16 == 0
