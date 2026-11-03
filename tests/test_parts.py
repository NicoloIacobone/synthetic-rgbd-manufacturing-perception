"""Generated part meshes: model frames and symmetries (A-20), closedness, BOP-friendly output."""

import numpy as np
import open3d as o3d
import pytest

from synthrgbd.meshdist import surface_distance
from synthrgbd.mssd import _rot, equal_leg_bracket_symmetries, mssd, profile_symmetries
from synthrgbd.parts import (
    PART_CATALOGUE, BracketSpec, ProfileSpec, bracket_cross_section, cross_section_area, diameter,
    make_bracket, make_part, make_profile, profile_cross_section, sample_surface, signed_volume,
    triangulate_polygon, write_ply,
)

PROFILES = [s for _, s in PART_CATALOGUE.values() if isinstance(s, ProfileSpec)]
BRACKETS = [s for _, s in PART_CATALOGUE.values() if isinstance(s, BracketSpec)]


def _apply(T, pts):
    return pts @ T[:3, :3].T + T[:3, 3]


def _surface_distance(mesh, pts):
    return surface_distance(mesh.triangles, pts)


def test_exact_surface_distance_helper():
    """The helper itself: known distances to a unit right triangle in z = 0."""
    from synthrgbd.parts import Mesh
    tri = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0]])
    mesh = Mesh(vertices=tri, faces=np.array([[0, 1, 2]]), normals=np.tile([0.0, 0, 1], (3, 1)))
    pts = np.array([[0.2, 0.2, 3.0], [-1, -1, 0], [2, 0, 0], [1, 1, 0], [0.5, -2, 0]])
    expected = [3.0, np.sqrt(2), 1.0, np.sqrt(0.5), 2.0]
    np.testing.assert_allclose(_surface_distance(mesh, pts), expected, atol=1e-12)


def _vertex_set(pts):
    return {tuple(p) for p in np.round(pts, 6) + 0.0}  # + 0.0 folds -0.0 into 0.0


def _assert_symmetry(mesh, T, tol=1e-3):
    # (i) the vertex set maps onto itself; (ii) the surface maps onto itself.
    assert _vertex_set(_apply(T, mesh.vertices)) == _vertex_set(mesh.vertices)
    pts = sample_surface(mesh, 20000, np.random.default_rng(0))
    assert _surface_distance(mesh, _apply(T, pts)).max() < tol


def _pose(R):
    T = np.eye(4)
    T[:3, :3] = R
    return T


# --- Symmetries -----------------------------------------------------------------------------------

@pytest.mark.parametrize("spec", PROFILES, ids=lambda s: f"L{s.length:g}")
def test_profile_mesh_has_all_8_symmetries(spec):
    mesh = make_profile(spec)
    syms = profile_symmetries()
    assert len(syms) == 8
    for T in syms:
        _assert_symmetry(mesh, T)


@pytest.mark.parametrize("spec", BRACKETS, ids=lambda s: f"leg{s.leg:g}")
def test_bracket_mesh_has_both_symmetries(spec):
    mesh = make_bracket(spec)
    syms = equal_leg_bracket_symmetries()
    assert len(syms) == 2
    for T in syms:
        _assert_symmetry(mesh, T)


@pytest.mark.parametrize("make, T", [
    (lambda: make_profile(ProfileSpec()), _pose(_rot([1, 0, 0], np.pi / 2))),   # profile: 90° about x
    (lambda: make_profile(ProfileSpec()), _pose(_rot([0, 0, 1], np.pi / 4))),   # 45° about the axis
    (lambda: make_bracket(BracketSpec()), _pose(_rot([0, 0, 1], np.pi / 2))),   # bracket: 90° about z
    (lambda: make_bracket(BracketSpec()), _pose(_rot([1, -1, 0], np.pi))),      # wrong bisector
])
def test_non_symmetries_are_detected(make, T):
    """Guards against a vacuous symmetry test: a wrong transform must move the surface."""
    mesh = make()
    pts = sample_surface(mesh, 20000, np.random.default_rng(0))
    assert _surface_distance(mesh, _apply(T, pts)).max() > 1.0


def test_mssd_is_zero_for_symmetric_poses_on_generated_meshes():
    """MSSD (S-07) on the generated meshes: a pose that differs by a symmetry costs nothing."""
    for _, spec in PART_CATALOGUE.values():
        mesh = make_part(spec)
        syms = profile_symmetries() if isinstance(spec, ProfileSpec) else equal_leg_bracket_symmetries()
        pts = np.unique(np.round(mesh.vertices, 9), axis=0)
        T_gt = np.eye(4)
        T_gt[:3, 3] = [10, -20, 800]
        for S in syms:
            assert mssd(T_gt @ S, T_gt, pts, syms) < 1e-9


# --- Model frames (A-20) --------------------------------------------------------------------------

@pytest.mark.parametrize("spec", PROFILES, ids=lambda s: f"L{s.length:g}")
def test_profile_model_frame(spec):
    v = make_profile(spec).vertices
    h = spec.side / 2
    np.testing.assert_allclose(v.min(0), [-h, -h, -spec.length / 2])
    np.testing.assert_allclose(v.max(0), [h, h, spec.length / 2])


@pytest.mark.parametrize("spec", BRACKETS, ids=lambda s: f"leg{s.leg:g}")
def test_bracket_model_frame(spec):
    v = make_bracket(spec).vertices
    np.testing.assert_allclose(v.min(0), [0, 0, -spec.width / 2])
    np.testing.assert_allclose(v.max(0), [spec.leg, spec.leg, spec.width / 2])
    # The outer corner edge lies on the z-axis; the legs run along +x and +y.
    assert np.any(np.all(np.isclose(v[:, :2], 0), axis=1))
    assert np.any(np.all(np.isclose(v[:, :2], [spec.leg, 0]), axis=1))
    assert np.any(np.all(np.isclose(v[:, :2], [0, spec.leg]), axis=1))


# --- Mesh validity --------------------------------------------------------------------------------

@pytest.mark.parametrize("spec", [s for _, s in PART_CATALOGUE.values()], ids=lambda s: repr(s)[:24])
def test_mesh_is_closed_with_outward_winding(spec):
    mesh = make_part(spec)
    if isinstance(spec, ProfileSpec):
        area, extent = cross_section_area(profile_cross_section(spec)), spec.length
    else:
        area, extent = cross_section_area(bracket_cross_section(spec)), spec.width
    # Volume from the divergence theorem matches the analytic prism volume, so the caps are
    # complete, nothing overlaps, and all faces point outwards.
    assert signed_volume(mesh) == pytest.approx(area * extent, rel=1e-9)
    # Every edge is shared by exactly two triangles, in opposite directions (2-manifold, closed).
    tri = np.round(mesh.triangles, 6)
    directed = {}
    for t in tri:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e = (tuple(t[a]), tuple(t[b]))
            directed[e] = directed.get(e, 0) + 1
    # Ear clipping splits cap edges at T-junction-free vertices only, so a directed-edge match holds.
    assert all(c == 1 for c in directed.values())
    assert all((b, a) in directed for a, b in directed)


def test_profile_cross_section_area_matches_hand_calculation():
    s = ProfileSpec()
    slot = s.slot_opening * s.lip + s.cavity_width * (s.slot_depth - s.lip)
    assert cross_section_area(profile_cross_section(s)) == pytest.approx(s.side**2 - 4 * slot)


def test_inconsistent_profile_is_rejected():
    with pytest.raises(ValueError):
        profile_cross_section(ProfileSpec(slot_depth=12.0, cavity_width=14.0))  # cavities overlap


def test_triangulation_rejects_clockwise():
    with pytest.raises(ValueError):
        triangulate_polygon(bracket_cross_section(BracketSpec())[::-1])


def test_diameter_and_ply_roundtrip(tmp_path):
    spec = ProfileSpec(length=100.0)
    mesh = make_profile(spec)
    assert diameter(mesh) == pytest.approx(np.sqrt(2 * spec.side**2 + spec.length**2))
    path = tmp_path / "p.ply"
    write_ply(mesh, path)
    m = o3d.io.read_triangle_mesh(str(path))
    np.testing.assert_allclose(np.asarray(m.vertices), mesh.vertices, atol=1e-6)
    assert len(m.triangles) == len(mesh.faces)
