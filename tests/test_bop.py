"""Amodal-mask ray casting and BOP gt_info (A-35)."""

import numpy as np

from synthrgbd.bop import bbox_xywh, gt_info_entry, render_object_depth
from synthrgbd.geometry import intrinsics_from_hfov
from synthrgbd.parts import BracketSpec, ProfileSpec, make_bracket, make_profile


def test_profile_end_on_projects_to_expected_square():
    """A 30 mm profile seen end-on at 800 mm: near face at 750 mm, side f*30/750 px, z exact."""
    W, H = 1280, 720
    K = intrinsics_from_hfov(W, H, 65.0)
    spec = ProfileSpec(length=100.0)
    z = render_object_depth(make_profile(spec).triangles, np.eye(3), [0.0, 0.0, 800.0], K, H, W)
    m = z > 0
    side_px = K[0, 0] * spec.side / (800.0 - spec.length / 2)
    x, y, w, h = bbox_xywh(m)
    assert abs(w - side_px) <= 1.5 and abs(h - side_px) <= 1.5
    np.testing.assert_allclose(z[m].min(), 750.0, atol=1e-3)
    # The slots are visible as notches: fewer pixels than the full square.
    assert m.sum() < side_px**2


def test_gt_info_entry_counts_and_bbox():
    K = intrinsics_from_hfov(320, 180, 65.0)
    z = render_object_depth(make_bracket(BracketSpec()).triangles, np.eye(3), [0.0, 0.0, 600.0], K, 180, 320)
    m_all = z > 0
    m_vis = m_all.copy()
    m_vis[:, : m_vis.shape[1] // 2 + 3] = False          # pretend the left part is occluded
    info = gt_info_entry(m_all, m_vis, np.where(m_all, 1.0, 0.0))
    assert info["px_count_all"] == info["px_count_valid"] == m_all.sum()
    assert 0 < info["visib_fract"] < 1
    assert info["bbox_visib"][0] > info["bbox_obj"][0]
    assert bbox_xywh(np.zeros((4, 4), bool)) == [-1, -1, -1, -1]
