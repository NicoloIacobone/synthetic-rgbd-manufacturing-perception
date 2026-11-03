"""Procedural part meshes: T-slot-like aluminium profiles and equal-leg L-brackets (D2, A-05).

Meshes are in millimetres (BOP model convention) and follow the model frames of A-20, which
`synthrgbd.mssd` relies on:
- Profile: extrusion axis = z, centred at the origin, square cross-section centred on the axis.
- Equal-leg L-bracket: corner at the origin, legs along +x and +y, centred in z.

Both parts are prisms: a simple 2D polygon in the xy-plane extruded along z. Triangles have
unshared vertices (flat shading) and outward, counter-clockwise winding.

This module needs only numpy, so it runs both in the analysis env (.venv) and in Blender's
bundled Python (BlenderProc scripts).

Dimensions are simplifications chosen for this project (A-33), not copied from a vendor
datasheet: the profile cross-section resembles a 30-series T-slot profile without the central
bore, and the bracket has no holes or gusset.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ProfileSpec:
    """Square T-slot-like profile; one identical slot centred on each of the 4 faces (mm)."""

    length: float = 100.0
    side: float = 30.0            # outer square side
    slot_opening: float = 8.0     # width of the slot opening at the face
    lip: float = 2.2              # thickness of the lips that form the opening
    cavity_width: float = 11.0    # width of the T-cavity behind the lips
    slot_depth: float = 8.0       # depth from the face to the bottom of the cavity


@dataclass(frozen=True)
class BracketSpec:
    """Equal-leg L-bracket (mm)."""

    leg: float = 40.0             # outer leg length along +x and +y
    thickness: float = 4.0
    width: float = 30.0           # extent along z


@dataclass
class Mesh:
    vertices: np.ndarray          # (3F, 3) float64, mm; unshared, 3 per triangle
    faces: np.ndarray             # (F, 3) int64
    normals: np.ndarray           # (3F, 3) per-vertex = face normal

    @property
    def triangles(self) -> np.ndarray:
        return self.vertices[self.faces]


# Parts used in the scenes (D2): 3 profile lengths and 1 equal-leg bracket. Keys are BOP obj_ids.
PART_CATALOGUE = {
    1: ("profile_60", ProfileSpec(length=60.0)),
    2: ("profile_100", ProfileSpec(length=100.0)),
    3: ("profile_150", ProfileSpec(length=150.0)),
    4: ("bracket_40", BracketSpec()),
}


# --- 2D cross-sections (counter-clockwise, simple polygons) -------------------------------------

def profile_cross_section(spec: ProfileSpec) -> np.ndarray:
    """CCW outline of the square profile with a T-slot on each face, 4-fold symmetric about z."""
    h = spec.side / 2
    o = spec.slot_opening / 2
    c = spec.cavity_width / 2
    lip_in = h - spec.lip            # inner face of the lips
    bottom = h - spec.slot_depth     # bottom of the cavity
    if not (0 < o < c < h and 0 < bottom < lip_in):
        raise ValueError(f"inconsistent profile dimensions: {spec}")
    if bottom <= c:
        # Adjacent cavities would meet at the corners: the core would detach from the shell.
        raise ValueError("cavities of adjacent slots overlap; increase side or reduce slot size")
    # Right face (x = +h), walked bottom to top, starting just after the lower-right corner.
    right = np.array([
        [h, -o], [lip_in, -o], [lip_in, -c], [bottom, -c],
        [bottom, c], [lip_in, c], [lip_in, o], [h, o],
        [h, h],                       # upper-right corner
    ])
    rot90 = np.array([[0.0, -1.0], [1.0, 0.0]])
    sides = [right @ np.linalg.matrix_power(rot90, k).T for k in range(4)]
    return np.vstack(sides)


def bracket_cross_section(spec: BracketSpec) -> np.ndarray:
    """CCW L-shape with the outer corner at the origin and legs along +x and +y."""
    L, t = spec.leg, spec.thickness
    if not 0 < t < L:
        raise ValueError(f"inconsistent bracket dimensions: {spec}")
    return np.array([[0, 0], [L, 0], [L, t], [t, t], [t, L], [0, L]], dtype=np.float64)


# --- Triangulation and extrusion ------------------------------------------------------------------

def _signed_area(poly: np.ndarray) -> float:
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _cross(o, a, b) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _in_triangle(p, a, b, c) -> bool:
    """Closed test (points on the boundary count as inside), for CCW a, b, c."""
    return _cross(a, b, p) >= 0 and _cross(b, c, p) >= 0 and _cross(c, a, p) >= 0


def triangulate_polygon(poly: np.ndarray) -> np.ndarray:
    """Ear-clipping triangulation of a simple CCW polygon -> (n-2, 3) vertex indices (CCW)."""
    if _signed_area(poly) <= 0:
        raise ValueError("polygon must be counter-clockwise")
    idx = list(range(len(poly)))
    tris = []
    guard = 0
    while len(idx) > 3:
        guard += 1
        if guard > 10 * len(poly) ** 2:
            raise RuntimeError("ear clipping did not converge (polygon not simple?)")
        n = len(idx)
        for k in range(n):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % n]
            a, b, c = poly[i0], poly[i1], poly[i2]
            if _cross(a, b, c) <= 1e-12:      # reflex or degenerate vertex: not an ear
                continue
            others = (poly[j] for j in idx if j not in (i0, i1, i2))
            if any(_in_triangle(p, a, b, c) for p in others):
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
    tris.append(tuple(idx))
    return np.array(tris, dtype=np.int64)


def extrude(poly: np.ndarray, z0: float, z1: float) -> Mesh:
    """Closed prism: CCW polygon extruded from z0 to z1 (z1 > z0), outward-facing triangles."""
    cap = triangulate_polygon(poly)
    tris = []
    for a, b, c in cap:                                   # top cap (+z): CCW seen from +z
        tris.append([[*poly[a], z1], [*poly[b], z1], [*poly[c], z1]])
    for a, b, c in cap:                                   # bottom cap (-z): reversed
        tris.append([[*poly[a], z0], [*poly[c], z0], [*poly[b], z0]])
    n = len(poly)
    for i in range(n):                                    # side walls; CCW outline -> outward
        p, q = poly[i], poly[(i + 1) % n]
        tris.append([[*p, z0], [*q, z0], [*q, z1]])
        tris.append([[*p, z0], [*q, z1], [*p, z1]])
    tri = np.asarray(tris, dtype=np.float64)              # (F, 3, 3)
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    fn /= np.linalg.norm(fn, axis=1, keepdims=True)
    F = len(tri)
    return Mesh(
        vertices=tri.reshape(-1, 3),
        faces=np.arange(3 * F, dtype=np.int64).reshape(F, 3),
        normals=np.repeat(fn, 3, axis=0),
    )


def make_profile(spec: ProfileSpec = ProfileSpec()) -> Mesh:
    return extrude(profile_cross_section(spec), -spec.length / 2, spec.length / 2)


def make_bracket(spec: BracketSpec = BracketSpec()) -> Mesh:
    return extrude(bracket_cross_section(spec), -spec.width / 2, spec.width / 2)


def make_part(spec) -> Mesh:
    if isinstance(spec, ProfileSpec):
        return make_profile(spec)
    if isinstance(spec, BracketSpec):
        return make_bracket(spec)
    raise TypeError(spec)


# --- Mesh properties ------------------------------------------------------------------------------

def signed_volume(mesh: Mesh) -> float:
    """Divergence theorem; positive for a closed mesh with outward winding (mm^3)."""
    t = mesh.triangles
    return float(np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6.0)


def cross_section_area(poly: np.ndarray) -> float:
    return abs(_signed_area(poly))


def diameter(mesh: Mesh) -> float:
    """Largest distance between two vertices (BOP models_info 'diameter'), mm."""
    v = np.unique(np.round(mesh.vertices, 9), axis=0)
    d2 = ((v[:, None, :] - v[None, :, :]) ** 2).sum(-1)
    return float(np.sqrt(d2.max()))


def sample_surface(mesh: Mesh, n: int, rng: np.random.Generator) -> np.ndarray:
    """Area-weighted uniform samples on the mesh surface, (n, 3) mm."""
    t = mesh.triangles
    area = 0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
    f = rng.choice(len(t), size=n, p=area / area.sum())
    r1, r2 = rng.random(n), rng.random(n)
    s = np.sqrt(r1)
    w0, w1, w2 = 1 - s, s * (1 - r2), s * r2
    return w0[:, None] * t[f, 0] + w1[:, None] * t[f, 1] + w2[:, None] * t[f, 2]


# --- I/O ------------------------------------------------------------------------------------------

def write_ply(mesh: Mesh, path, color=(180, 180, 185)) -> None:
    """ASCII PLY with per-vertex normals and colours, as BOP models expect (mm)."""
    v, n, f = mesh.vertices, mesh.normals, mesh.faces
    with open(path, "w") as fh:
        fh.write("ply\nformat ascii 1.0\n")
        fh.write(f"element vertex {len(v)}\n")
        fh.write("property float x\nproperty float y\nproperty float z\n")
        fh.write("property float nx\nproperty float ny\nproperty float nz\n")
        fh.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        fh.write(f"element face {len(f)}\nproperty list uchar int vertex_indices\nend_header\n")
        for p, q in zip(v, n):
            fh.write(f"{p[0]:.6f} {p[1]:.6f} {p[2]:.6f} {q[0]:.6f} {q[1]:.6f} {q[2]:.6f} "
                     f"{color[0]} {color[1]} {color[2]}\n")
        for a, b, c in f:
            fh.write(f"3 {a} {b} {c}\n")
