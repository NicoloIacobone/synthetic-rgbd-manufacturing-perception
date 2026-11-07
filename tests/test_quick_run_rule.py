"""The two pass rules of the quick run (A-71, A-72, A-77)."""

import importlib.util
from pathlib import Path

import numpy as np

from synthrgbd.stats import depth_summary

spec = importlib.util.spec_from_file_location("quick_run", Path(__file__).resolve().parents[1] / "scripts" / "quick_run.py")
quick_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quick_run)

GOOD = {"complete": True, "depth_same": True, "depth_close": True, "side_changes": 0, "median_mm": 0.0, "suction_differences": 0, "recall_diff": 0, "suction_diff": 0}


def test_exact_rule_demands_identical_pixels_and_suction():
    assert quick_run.passes("exact", GOOD)
    assert not quick_run.passes("exact", {**GOOD, "depth_same": False})
    assert not quick_run.passes("exact", {**GOOD, "suction_differences": 1})
    assert quick_run.passes("exact", {**GOOD, "side_changes": 1})
    assert not quick_run.passes("exact", {**GOOD, "side_changes": 2})


def test_tolerance_rule_allows_different_pixels_and_one_view_only():
    assert quick_run.passes("tolerance", {**GOOD, "depth_same": False, "suction_differences": 3, "median_mm": 0.5, "recall_diff": -1, "suction_diff": 1})
    assert not quick_run.passes("tolerance", {**GOOD, "depth_close": False})
    assert not quick_run.passes("tolerance", {**GOOD, "recall_diff": 2})
    assert not quick_run.passes("tolerance", {**GOOD, "suction_diff": -2})
    assert not quick_run.passes("tolerance", {**GOOD, "median_mm": 0.51})
    assert not quick_run.passes("tolerance", {**GOOD, "complete": False})


def test_depth_close_uses_the_stated_limits():
    want = {"valid_frac": 0.9, "p5_mm": 500.0, "p50_mm": 600.0, "p95_mm": 700.0}
    assert quick_run.depth_close({"valid_frac": 0.904, "p5_mm": 500.9, "p50_mm": 599.1, "p95_mm": 700.0}, want)
    assert not quick_run.depth_close({**want, "valid_frac": 0.906}, want)
    assert not quick_run.depth_close({**want, "p50_mm": 601.1}, want)


def test_depth_summary_ignores_invalid_pixels():
    d = np.array([[0, 0, 5000, 5000], [5000, 5000, 5000, 5000]], np.uint16)
    s = depth_summary(d)
    assert s["valid_frac"] == 0.75
    assert s["p50_mm"] == 500.0
    assert depth_summary(np.zeros((2, 2), np.uint16)) == {"valid_frac": 0.0, "p5_mm": 0.0, "p50_mm": 0.0, "p95_mm": 0.0}
