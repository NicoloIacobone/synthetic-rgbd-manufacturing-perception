"""Task B (synthrgbd.suction, PLAN §5.3) on the procedural parts: GT success check and planner."""

import numpy as np
import pytest

from synthrgbd.bop import render_object_depth
from synthrgbd.config import load_config
from synthrgbd.geometry import intrinsics_from_hfov
from synthrgbd.parts import PART_CATALOGUE, make_part
from synthrgbd.pose import axis_angle, backproject, erode_mask
from synthrgbd.suction import SuctionParams, check_success, plan_suction

CFG_B = load_config()["task_b"]
W, H = 1280, 720
K = intrinsics_from_hfov(W, H, 65.0)


def _cam(obj_id, R, t):
    mesh = make_part(PART_CATALOGUE[obj_id][1])
    return mesh, [mesh.triangles @ R.T + t]


def _grasp(point, normal):
    return {"point": np.asarray(point, float), "normal": np.asarray(normal, float) / np.linalg.norm(normal)}


# Bracket lying on its x-leg, seen from above: the camera looks along +z, and model +y (the x-leg's
# top-face normal) is rotated to camera -z, towards the camera.
R_BRACKET = axis_angle([1, 0, 0], -np.pi / 2)
T_BRACKET = np.array([0.0, 0.0, 800.0])


def test_gt_check_bracket_leg_centre_passes():
    _, tris = _cam(4, R_BRACKET, T_BRACKET)
    top = R_BRACKET @ np.array([25.0, 4.0, 0.0]) + T_BRACKET     # middle of the x-leg's top face
    n = R_BRACKET @ np.array([0, 1.0, 0])
    res = check_success(_grasp(top, n), tris, 0, CFG_B)
    assert res["success"], res
    assert res["point_to_surface_mm"] < 1e-9 and res["normal_error_deg"] < 1e-6


def test_gt_check_bracket_next_to_the_other_leg_fails():
    _, tris = _cam(4, R_BRACKET, T_BRACKET)
    near_corner = R_BRACKET @ np.array([9.0, 4.0, 0.0]) + T_BRACKET   # 5 mm from the y-leg's inner face
    res = check_success(_grasp(near_corner, R_BRACKET @ np.array([0, 1.0, 0])), tris, 0, CFG_B)
    assert not res["success"] and res["ok_point"] and res["disk_max_abs_height_mm"] == pytest.approx(10.0)


def test_gt_check_bracket_disk_over_the_edge_fails():
    _, tris = _cam(4, R_BRACKET, T_BRACKET)
    edge = R_BRACKET @ np.array([35.0, 4.0, 0.0]) + T_BRACKET          # 5 mm from the leg's free end
    res = check_success(_grasp(edge, R_BRACKET @ np.array([0, 1.0, 0])), tris, 0, CFG_B)
    assert not res["success"] and res["disk_frac_no_hit"] > 0.05      # disk partly over empty space


def test_gt_check_profile_face_fails_over_the_slot():
    R = axis_angle([0, 1, 0], np.pi / 2)
    _, tris = _cam(2, R, np.array([0, 0, 800.0]))
    face_centre = R @ np.array([0, -15.0, 0]) + np.array([0, 0, 800.0])   # centre of a side face = slot opening
    res = check_success(_grasp(face_centre, R @ np.array([0, -1.0, 0])), tris, 0, CFG_B)
    assert not res["success"] and res["disk_frac_no_hit"] == 0                # surface everywhere under the disk,
    assert res["disk_max_abs_height_mm"] == pytest.approx(8.0, abs=0.01)      # but the slot floor is 8 mm below


def test_gt_check_own_back_face_does_not_count():
    """The plate's back face lies 4 mm below the top face inside the cup cylinder; only the first surface counts."""
    _, tris = _cam(4, R_BRACKET, T_BRACKET)
    top = R_BRACKET @ np.array([25.0, 4.0, 0.0]) + T_BRACKET
    res = check_success(_grasp(top, R_BRACKET @ np.array([0, 1.0, 0])), tris, 0, CFG_B)
    assert res["success"] and res["disk_max_abs_height_mm"] < 1e-3


def test_gt_check_other_part_under_the_disk_fails_and_far_parts_are_ignored():
    _, tris = _cam(4, R_BRACKET, T_BRACKET)
    top = R_BRACKET @ np.array([25.0, 4.0, 0.0]) + T_BRACKET
    n = R_BRACKET @ np.array([0, 1.0, 0])
    g = _grasp(top, n)
    plate = lambda dz: [t + dz * n for t in _cam(4, R_BRACKET, T_BRACKET + np.array([30.0, 0, 0]))[1]]
    near = check_success(g, tris + plate(3.0), 0, CFG_B)       # neighbour 3 mm above, overlapping the disk
    far = check_success(g, tris + plate(15.0), 0, CFG_B)       # same neighbour 15 mm above: beyond the cup radius
    assert not near["success"] and near["disk_frac_other_part"] > 0
    assert far["success"]


@pytest.mark.parametrize("mode", ["raw", "plane_fit"])
def test_planner_on_ideal_bracket_view_succeeds(mode):
    R = axis_angle([1, 0, 0], -np.pi / 2) @ axis_angle([0, 1, 0], 0.3)
    t = np.array([10.0, -20.0, 800.0])
    mesh, tris = _cam(4, R, t)
    depth = render_object_depth(mesh.triangles, R, t, K, H, W)
    pts = backproject(depth, erode_mask(depth > 0, 2), K)
    g = plan_suction(pts, CFG_B["cup_radius_mm"], SuctionParams(grasp_point=mode))
    assert g is not None and g["normal"] @ g["point"] < 0          # normal points towards the camera
    res = check_success(g, tris, 0, CFG_B)
    assert res["success"], res


def test_planner_on_ideal_profile_view_cannot_succeed():
    """A-33: no flat 10 mm disk exists on a profile, so even ideal depth fails the GT check."""
    R = axis_angle([0, 1, 0], np.pi / 2) @ axis_angle([0, 0, 1], 0.35)
    t = np.array([0.0, 10.0, 800.0])
    mesh, tris = _cam(2, R, t)
    depth = render_object_depth(mesh.triangles, R, t, K, H, W)
    pts = backproject(depth, erode_mask(depth > 0, 2), K)
    g = plan_suction(pts, CFG_B["cup_radius_mm"], SuctionParams())
    assert not check_success(g, tris, 0, CFG_B)["success"]


def test_no_points_no_grasp():
    assert plan_suction(np.zeros((3, 3)), 10.0, SuctionParams()) is None
    assert check_success(None, None, 0, CFG_B) == {"success": False, "has_grasp": False}
