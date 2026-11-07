"""Seed policy (PLAN §5.10): every random stream derives from (master, scene seed, view, stream).

C3 and C4 draw from the same "ir_noise" stream, and all conditions from the same "init_offset"
stream, so paired comparisons differ only in the depth input (A-29).
"""

import numpy as np

STREAMS = {
    "scene": 0,        # layout, physics drop, camera placement
    "c2a_noise": 1,
    "c2b_noise": 2,
    "ir_noise": 3,     # shared by C3 and C4
    "init_offset": 4,  # shared by all conditions
    "bootstrap": 5,
    "error_structure": 6,
}


def rng(master: int, scene_seed: int, view: int, stream: str) -> np.random.Generator:
    """Independent, reproducible generator for one (scene, view, stream)."""
    ss = np.random.SeedSequence([master, scene_seed, view, STREAMS[stream]])
    return np.random.Generator(np.random.PCG64(ss))


def scene_seeds(cfg_split: dict) -> list[int]:
    """Scene seeds of a split, e.g. cfg["seeds"]["test_scenes"] -> [0, ..., 49]."""
    return list(range(cfg_split["start"], cfg_split["start"] + cfg_split["count"]))
