"""Write BOP models: <out>/synthrgbd/models/obj_XXXXXX.ply (mm) and models_info.json.

Usage: .venv/bin/python scripts/export_models.py <out_root>     (e.g. data/m2)

models_info.json follows the BOP format: diameter, bounding box (min_*, size_*) and
symmetries_discrete (flattened 4x4, translation in mm, identity excluded) from A-20.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from synthrgbd.mssd import equal_leg_bracket_symmetries, profile_symmetries
from synthrgbd.parts import PART_CATALOGUE, ProfileSpec, diameter, make_part, write_ply

out = Path(sys.argv[1]) / "synthrgbd" / "models"
out.mkdir(parents=True, exist_ok=True)
info = {}
for obj_id, (name, spec) in PART_CATALOGUE.items():
    mesh = make_part(spec)
    write_ply(mesh, out / f"obj_{obj_id:06d}.ply")
    syms = profile_symmetries() if isinstance(spec, ProfileSpec) else equal_leg_bracket_symmetries()
    lo, hi = mesh.vertices.min(0), mesh.vertices.max(0)
    info[str(obj_id)] = {
        "name": name,
        "diameter": diameter(mesh),
        "min_x": lo[0], "min_y": lo[1], "min_z": lo[2],
        "size_x": hi[0] - lo[0], "size_y": hi[1] - lo[1], "size_z": hi[2] - lo[2],
        "symmetries_discrete": [np.round(S, 12).flatten().tolist() for S in syms
                                if not np.allclose(S, np.eye(4))],
    }
    info[str(obj_id)] = {k: (float(v) if isinstance(v, (np.floating, float)) else v)
                         for k, v in info[str(obj_id)].items()}
(out / "models_info.json").write_text(json.dumps(info, indent=1))
print(f"wrote {len(info)} models to {out}")
