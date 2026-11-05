"""Task A harness (synthrgbd.pose, A-46) on ideal ray-cast views of the procedural parts."""

import numpy as np
import pytest

from synthrgbd.bop import render_object_depth
from synthrgbd.geometry import intrinsics_from_hfov
from synthrgbd.mssd import equal_leg_bracket_symmetries, mssd, profile_symmetries
from synthrgbd.parts import PART_CATALOGUE, make_part
from synthrgbd.pose import (IcpParams, apply_offset, axis_angle, backproject, draw_offset_directions,
                            erode_mask, icp_refine, rotation_error_deg, sample_with_normals,
                            unique_vertices)

W, H = 1280, 720
K = intrinsics_from_hfov(W, H, 65.0)


def _pose(R, t):
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = R, t
    return T


def _view(obj_id, T):
    mesh = make_part(PART_CATALOGUE[obj_id][1])
    depth = render_object_depth(mesh.triangles, T[:3, :3], T[:3, 3], K, H, W)
    return mesh, depth


def _setup(obj_id, T, erosion=2):
    mesh, depth = _view(obj_id, T)
    pts = backproject(depth, erode_mask(depth > 0, erosion), K)
    mp, mn = sample_with_normals(mesh, 50000, np.random.default_rng(0))
    syms = profile_symmetries() if obj_id < 4 else equal_leg_bracket_symmetries()
    return mesh, pts, mp, mn, syms


# A bracket seen obliquely (both legs and the end face visible) at 0.8 m.
T_BRACKET = _pose(axis_angle([1, 0.3, 0], np.deg2rad(140)) @ axis_angle([0, 0, 1], 0.4), [20, -10, 800])
# A 100 mm profile lying across the view, seen from the side only (no end face visible).
T_PROFILE_SIDE = _pose(axis_angle([0, 1, 0], np.pi / 2) @ axis_angle([0, 0, 1], np.deg2rad(20)), [0, 0, 800])


def test_backproject_plane_and_erosion():
    z = np.full((H, W), 750.0)
    mask = np.zeros((H, W), bool)
    mask[300:320, 600:640] = True
    pts = backproject(z, mask, K)
    assert pts.shape == (20 * 40, 3) and np.allclose(pts[:, 2], 750.0)
    v, u = 300, 600
    assert np.allclose(pts[0], [(u - K[0, 2]) * 750 / K[0, 0], (v - K[1, 2]) * 750 / K[1, 1], 750])
    assert erode_mask(mask, 2).sum() == 16 * 36
    z2 = z.copy()
    z2[300, 600] = 0                       # invalid depth pixels are skipped
    assert len(backproject(z2, mask, K)) == 20 * 40 - 1


@pytest.mark.parametrize("mm,deg", [(2, 2), (10, 10), (20, 20)])
def test_offset_has_exact_magnitude(mm, deg):
    rng = np.random.default_rng(5)
    d = draw_offset_directions(rng, 4)
    centre = np.array([20.0, 20.0, 0.0])            # bracket bounding-box centre
    for k in range(4):
        To = apply_offset(T_BRACKET, d[k, 0], d[k, 1], mm, deg, centre)
        c_gt = T_BRACKET[:3, :3] @ centre + T_BRACKET[:3, 3]
        c_off = To[:3, :3] @ centre + To[:3, 3]
        assert np.linalg.norm(c_off - c_gt) == pytest.approx(mm, abs=1e-9)
        assert rotation_error_deg(To[:3, :3], T_BRACKET[:3, :3]) == pytest.approx(deg, abs=1e-6)


def test_offset_directions_reproducible_and_shared_across_levels():
    a = draw_offset_directions(np.random.default_rng(7), 3)
    b = draw_offset_directions(np.random.default_rng(7), 3)
    assert np.array_equal(a, b) and np.allclose(np.linalg.norm(a, axis=2), 1.0)


def test_sampled_normals_are_cad_normals():
    mesh = make_part(PART_CATALOGUE[4][1])
    p, n = sample_with_normals(mesh, 500, np.random.default_rng(1))
    assert np.allclose(np.linalg.norm(n, axis=1), 1.0)
    assert set(np.round(np.abs(n), 6).max(1)) == {1.0}     # bracket faces are axis-aligned


@pytest.mark.parametrize("obj_id,T", [(4, T_BRACKET), (2, T_PROFILE_SIDE)])
def test_zero_offset_is_a_fixed_point(obj_id, T):
    """§5.11 sanity on ideal data: ICP started at the GT pose must stay there (MSSD << 0.5 mm)."""
    mesh, pts, mp, mn, syms = _setup(obj_id, T)
    T_est, info = icp_refine(pts, mp, mn, T, IcpParams())
    assert info["status"] == "ok"
    assert mssd(T_est, T, unique_vertices(mesh), syms) < 0.05


def test_bracket_converges_from_5mm_5deg():
    mesh, pts, mp, mn, syms = _setup(4, T_BRACKET)
    d = draw_offset_directions(np.random.default_rng(3), 5)
    for k in range(5):
        T0 = apply_offset(T_BRACKET, d[k, 0], d[k, 1], 5, 5, np.array([20.0, 20.0, 0.0]))
        T_est, _ = icp_refine(pts, mp, mn, T0, IcpParams())
        assert mssd(T_est, T_BRACKET, unique_vertices(mesh), syms) < 0.5


def test_profile_slides_along_its_axis_when_end_faces_are_unseen():
    """Known geometric failure (PLAN §5.9): with no end face visible, an axial offset is not
    corrected, while the across-axis error is."""
    mesh, pts, mp, mn, syms = _setup(2, T_PROFILE_SIDE)
    axis_cam = T_PROFILE_SIDE[:3, :3] @ np.array([0, 0, 1.0])
    T0 = apply_offset(T_PROFILE_SIDE, axis_cam, [0, 0, 1.0], 8, 0, np.zeros(3))
    T_est, _ = icp_refine(pts, mp, mn, T0, IcpParams())
    dt = T_est[:3, 3] - T_PROFILE_SIDE[:3, 3]
    assert abs(dt @ axis_cam) > 7.0                                     # still slid
    assert np.linalg.norm(dt - (dt @ axis_cam) * axis_cam) < 0.2        # across-axis recovered


def test_too_few_points_gives_no_estimate():
    mesh = make_part(PART_CATALOGUE[4][1])
    mp, mn = sample_with_normals(mesh, 100, np.random.default_rng(0))
    T_est, info = icp_refine(np.zeros((5, 3)), mp, mn, T_BRACKET, IcpParams())
    assert T_est is None and info["status"] == "too_few_points"


VARIANTS = {
    "H0": IcpParams(),
    "H1": IcpParams(stages=((20.0, 20.0), (10.0, 10.0), (5.0, 5.0))),
    "H2": IcpParams(stages=((20.0, 20.0), (10.0, 10.0), (5.0, 5.0)), visibility="raycast"),
    "H3": IcpParams(stages=((20.0, 20.0), (10.0, 10.0), (5.0, 5.0)), visibility="raycast", o3d_step_clamp=True),
}


@pytest.mark.parametrize("name", sorted(VARIANTS))
@pytest.mark.parametrize("obj_id,T", [(4, T_BRACKET), (2, T_PROFILE_SIDE)])
def test_harness_candidates_keep_the_zero_offset_fixed_point(name, obj_id, T):
    mesh, pts, mp, mn, syms = _setup(obj_id, T)
    T_est, info = icp_refine(pts, mp, mn, T, VARIANTS[name], mesh.triangles)
    assert info["status"] == "ok" and mssd(T_est, T, unique_vertices(mesh), syms) < 0.05


def test_raycast_visibility_removes_self_occluded_faces():
    """Inside of the L: with the camera looking into the corner both inner faces are visible; from behind
    the y-leg, the x-leg's inner face is hidden by the y-leg although it faces the camera."""
    from synthrgbd.pose import visible_model_points
    mesh = make_part(PART_CATALOGUE[4][1])
    mp, mn = sample_with_normals(mesh, 20000, np.random.default_rng(0))
    cam = np.array([-300.0, 20.0, 0.0])                    # behind the y-leg (x < 0), level with the x-leg
    back = visible_model_points(mp, mn, cam, None)
    ray = visible_model_points(mp, mn, cam, mesh.triangles)
    inner_x_leg_top = (np.abs(mp[:, 1] - 4.0) < 1e-6) & (mp[:, 0] > 4.0)
    assert ray.sum() < back.sum()
    assert not ray[inner_x_leg_top & back].any()


# Regression tests for the cache bug found at the §5.11 gate (A-62). `Mesh.triangles` returns a new array per call and
# all profile lengths have the same triangle count, so a cache keyed on id() could hand back another profile's scene.

def test_raycast_visibility_uses_the_mesh_it_is_given():
    """A longer profile encloses the end faces of a shorter one, so its scene would cull them."""
    from synthrgbd.pose import visible_model_points
    short, long_ = make_part(PART_CATALOGUE[1][1]), make_part(PART_CATALOGUE[3][1])
    mp, mn = sample_with_normals(short, 20000, np.random.default_rng(0))
    cam = np.array([150.0, 100.0, 400.0])                  # sees the +z end face of the 60 mm profile
    end_face = np.abs(mp[:, 2] - 30.0) < 1e-9
    assert end_face.sum() > 100
    for _ in range(10):
        hidden = visible_model_points(mp, mn, cam, long_.triangles)
        assert hidden[end_face].mean() < 0.05              # the long mesh hides them, bar the 0.5 mm tolerance at its side
        assert visible_model_points(mp, mn, cam, short.triangles)[end_face].all()


def test_load_part_models_gives_each_part_its_own_long_lived_triangles():
    from synthrgbd.pose import _model_scene, load_part_models
    models = load_part_models(100, 0)
    assert {o: float(np.ptp(m["tri"][:, :, 2])) for o, m in models.items()} == {1: 60.0, 2: 100.0, 3: 150.0, 4: 30.0}
    assert models[1]["tri"] is models[1]["tri"]            # not rebuilt per access, unlike Mesh.triangles
    assert _model_scene(models[1]["tri"]) is _model_scene(models[1]["tri"])
    assert _model_scene(models[1]["tri"]) is not _model_scene(models[3]["tri"])
