"""§5.11 diagnosis (A-62): why ICP leaves the ground-truth pose on ideal depth. C1, zero offset, test scenes only.
No recall at a real offset is computed and no ICP variant outside the ledger is evaluated.

Usage (run in this order):
  OMP_NUM_THREADS=2 .venv/bin/python scripts/sanity_diagnosis.py replay <root> <diag_dir> <first> <last>
  .venv/bin/python scripts/sanity_diagnosis.py static <root> <diag_dir> <first> <last>
  .venv/bin/python scripts/sanity_diagnosis.py report <root> <diag_dir>
  .venv/bin/python scripts/sanity_diagnosis.py trace <root> <diag_dir>
  OMP_NUM_THREADS=1 .venv/bin/python scripts/sanity_diagnosis.py replay <root> <diag_dir> <first> <last> _omp1

replay: H2 exactly as run by pose_eval.py, in one process and the same instance order, logging which mesh the
        ray-cast cache (`synthrgbd.pose._model_scene`) really used for each instance-view.
static: no ICP. At the ground-truth pose, per instance-view, compares three target surfaces: back-face culling only,
        ray cast against the part's own mesh, ray cast against the mesh the replay used. For each: which measured
        points lost their surface, fitness, conditioning of the point-to-plane normal matrix, and the first
        Gauss-Newton step that ICP would take from the ground-truth pose.
report: pass/fail table (ledger rule), determinism and thread checks, and the group tables.
trace:  the 7 axial slides, stage by stage, with H1 settings (no ray cast, so no cache): where the axial pull comes from.
"""

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

L_MM = 30.0                  # length scale that makes rotation and translation comparable (as IcpParams.damping_len_mm)
SLIDE_MAX_R_DEG = 0.1        # boundary of the two drift groups, as in the 2026-11-04 recount
BASELINE = "results/sanity_C1_zero.jsonl"


def load_rows(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines()[1:]]


def mssd_of(r: dict) -> float:
    return r["mssd_mm"] if r["mssd_mm"] is not None else np.inf


def key(r: dict) -> tuple:
    return r["scene"], r["im_id"], r["gt_id"]


def group(r: dict) -> str:
    m = mssd_of(r)
    if m < 0.5:
        return "pass"
    if m >= 5.0:
        return "jump"
    return "slide" if r["R_err_deg"] < SLIDE_MAX_R_DEG else "rotation"


def replay(root: Path, out: Path, first: int, last: int, tag: str = "") -> None:
    import pose_eval

    import synthrgbd.pose as P

    orig, cache = P._model_scene, P._model_scene.__defaults__[0]
    built, used, calls = {}, [], []

    def scene(tri):
        k = (id(tri), tri.shape)
        if k not in cache:
            built[k] = (int(tri.shape[0]), round(float(tri[:, :, 2].max() - tri[:, :, 2].min()), 3))
        used.append(built[k])
        return orig(tri)

    def refine(*a, **kw):
        used.clear()
        res = P.icp_refine(*a, **kw)
        calls.append(sorted(set(used)))
        return res

    P._model_scene, pose_eval.icp_refine = scene, refine
    sys.argv = ["pose_eval.py", str(root), *map(str, range(first, last + 1)), "--condition", "C1", "--offset", "0", "0",
                f"--out={out / f'H2_replay{tag}.jsonl'}"]
    pose_eval.main()
    (out / f"H2_replay{tag}_meshes.json").write_text(json.dumps(calls))
    print("scenes built by the cache:", len(cache), sorted(set(built.values())))


def analyse_target(x, x_c, mp, mn, keep, true_n, idx_all, half_len):
    """Scene points x (model frame, at the GT pose) against the surviving target `keep`."""
    from scipy.spatial import cKDTree

    tree = cKDTree(mp[keep])
    d, j = tree.query(x)
    q, n = mp[keep][j], mn[keep][j]
    out = {"removed": float((~keep[idx_all]).mean()),      # measured points whose own surface patch was removed
           "fit_5mm": float((d < 5).mean()), "fit_1mm": float((d < 1).mean()),
           "wrong_face_5mm": float(((np.einsum("ij,ij->i", n, true_n) < 0.87) & (d < 5)).mean())}
    # End faces, by geometry: measured points on z = ±half_len, and whether the surviving target still has that face.
    on_end = np.abs(np.abs(x[:, 2]) - half_len) < 0.1
    end_pts = mp[keep][np.abs(mn[keep][:, 2]) > 0.9]
    out["n_end_pts"] = int(on_end.sum())
    out["end_target_share"] = float(len(end_pts) / max(1, keep.sum()))
    if on_end.any():
        dd = cKDTree(end_pts).query(x[on_end])[0] if len(end_pts) else np.full(int(on_end.sum()), np.inf)
        out["end_pts_lost"] = float((dd > 1.0).mean())
    else:
        out["end_pts_lost"] = None
    out["side_matched_to_end"] = int(((np.abs(n[:, 2]) > 0.9) & ~on_end & (d < 5)).sum())
    # Normal matrix at the GT pose, centred on the scene points, rotation scaled by L_MM (last stage: 5 mm).
    ok = d < 5
    if ok.sum() < 6:
        return {**out, "kappa": None, "lam_min": None, "end_frac": None, "null_axial_t": None}
    J = np.hstack([np.cross(x_c[ok], n[ok]) / L_MM, n[ok]])
    H = J.T @ J / ok.sum()
    w, v = np.linalg.eigh(H)
    out.update(kappa=float(w[-1] / max(w[0], 1e-30)), lam_min=float(w[0]), end_frac=float((np.abs(n[ok][:, 2]) > 0.9).mean()),
               null_axial_t=float(abs(v[5, 0])), null_rot=float(np.linalg.norm(v[:3, 0])))
    # First Gauss-Newton step from the GT pose, first stage of H2 (max correspondence 20 mm, Tukey 20 mm).
    ok = d < 20
    r = np.einsum("ij,ij->i", n[ok], x[ok] - q[ok])
    wt = (1 - (r / 20.0) ** 2) ** 2
    J = np.hstack([np.cross(x_c[ok], n[ok]), n[ok]])
    Js = np.hstack([J[:, :3] / L_MM, J[:, 3:]])
    H = Js.T @ (Js * wt[:, None])
    g = Js.T @ (wt * r)
    delta = -np.linalg.lstsq(H, g, rcond=1e-12)[0]
    out.update(step_rot_deg=float(np.degrees(np.linalg.norm(delta[:3] / L_MM))), step_axial_mm=float(abs(delta[5])),
               step_across_mm=float(np.linalg.norm(delta[3:5])), resid_mean_mm=float(np.abs(r).mean()),
               resid_nonzero=float((np.abs(r) > 1e-6).mean()))
    return out


def static(root: Path, out: Path, first: int, last: int) -> None:
    import cv2

    from synthrgbd.conditions import DEPTH_DIRS, DEPTH_SCALE_MM
    from synthrgbd.config import load_config
    from synthrgbd.pose import _model_tree, backproject, erode_mask, load_part_models, visible_model_points

    hcfg = load_config(REPO / "configs" / "harness.yaml")
    models = load_part_models(hcfg["model_sampling"]["points_per_model"], hcfg["model_sampling"]["seed"])
    tri_own = {o: m["mesh"].triangles for o, m in models.items()}       # persistent arrays: stable cache keys
    by_extent = {round(float(t[:, :, 2].max() - t[:, :, 2].min()), 3): t for t in tri_own.values()}
    rows = load_rows(out / "H2_replay.jsonl")
    meshes = json.loads((out / "H2_replay_meshes.json").read_text())
    res = []
    for r, used in zip(rows, meshes):
        sc = root / "synthrgbd" / "train_pbr" / f"{r['scene']:06d}"
        g = json.loads((sc / "scene_gt.json").read_text())[str(r["im_id"])][r["gt_id"]]
        K = np.array(json.loads((sc / "scene_camera.json").read_text())[str(r["im_id"])]["cam_K"]).reshape(3, 3)
        depth = cv2.imread(str(sc / DEPTH_DIRS["C1"] / f"{r['im_id']:06d}.png"), cv2.IMREAD_UNCHANGED).astype(np.float64) * DEPTH_SCALE_MM
        mask = cv2.imread(str(sc / "mask_visib" / f"{r['im_id']:06d}_{r['gt_id']:06d}.png"), cv2.IMREAD_GRAYSCALE) > 0
        pts = backproject(depth, erode_mask(mask, hcfg["icp"]["mask_erosion_px"]), K)
        R, t = np.array(g["cam_R_m2c"]).reshape(3, 3), np.array(g["cam_t_m2c"], np.float64)
        m = models[r["obj_id"]]
        x = (pts - t) @ R                                               # model frame
        cam = -R.T @ t
        tree = _model_tree(m["pts"])
        d_all, idx_all = tree.query(x)
        true_n = m["nrm"][idx_all]
        x_c = x - x.mean(0)
        used_extent = used[0][1] if len(used) == 1 else None            # None would mean several meshes in one call
        filters = {"backface": visible_model_points(m["pts"], m["nrm"], cam, None),
                   "raycast_own": visible_model_points(m["pts"], m["nrm"], cam, tri_own[r["obj_id"]]),
                   "raycast_used": visible_model_points(m["pts"], m["nrm"], cam, by_extent[used_extent])}
        row = {"scene": r["scene"], "im_id": r["im_id"], "gt_id": r["gt_id"], "obj_id": r["obj_id"], "group": group(r),
               "n_meshes_in_call": len(used), "used_extent": used_extent, "gt_on_surface_p99_mm": float(np.percentile(d_all, 99)),
               "n_pts": len(x), "fitness_run": r.get("fitness"), "mssd_mm": r["mssd_mm"], "R_err_deg": r.get("R_err_deg"),
               "centre_err_axial_mm": r.get("centre_err_axial_mm"), "centre_err_across_mm": r.get("centre_err_across_mm")}
        for name, keep in filters.items():
            row[name] = analyse_target(x, x_c, m["pts"], m["nrm"], keep, true_n, idx_all, float(np.abs(m["verts"][:, 2]).max()))
        res.append(row)
    (out / "static_gt.json").write_text(json.dumps(res))
    print("static rows", len(res))


def report(root: Path, out: Path) -> None:
    base = load_rows(root / BASELINE)
    fails = {key(r) for r in base if mssd_of(r) >= 0.5}
    runs = json.loads((out / "runs.json").read_text())
    names = {1: "60", 2: "100", 3: "150", 4: "bracket"}
    table = {}
    print("== candidates, C1 zero offset, test scenes; pass = at least 99% at MSSD < 0.5 mm ==")
    for name in ["H0", "H1", "H3", "lm", "H2_repeat_omp2", "H2_omp1", "H2_ompdefault", "H2_replay"]:
        p = out / f"{name}.jsonl"
        if not p.exists():
            continue
        rows = load_rows(p)
        assert [key(r) for r in rows] == [key(r) for r in base], name
        ms = np.array([mssd_of(r) for r in rows])
        f = {key(r) for r, m in zip(rows, ms) if m >= 0.5}
        by = {names[o]: sum(1 for r, m in zip(rows, ms) if m >= 0.5 and r["obj_id"] == o) for o in names}
        table[name] = {"n": len(rows), "ok": int((ms < 0.5).sum()), "frac": float((ms < 0.5).mean()),
                       "pass": bool((ms < 0.5).mean() >= 0.99), "fail_ge5": int((ms >= 5).sum()),
                       "fail_05_5": int(((ms >= 0.5) & (ms < 5)).sum()), "by_part": by, "fails_shared_with_43": len(f & fails),
                       "new_fails": len(f - fails), "median_mm": float(np.median(ms)), "max_mm": float(ms.max()),
                       "no_estimate": int(np.isinf(ms).sum()), "wall_s": runs.get(name, {}).get("wall_s"),
                       "meta_dirty": json.loads(p.read_text().splitlines()[0])["meta"]["dirty_tree"]}
        print(name, json.dumps(table[name]))

    print("\n== determinism against the failed run (same instance order) ==")
    det = {}
    for name in ["H2_repeat_omp2", "H2_omp2_b", "H2_omp2_c", "H2_ompdefault", "H2_omp1", "H2_omp1_b", "H2_omp1_c",
                 "H2_replay", "H2_replay_omp1"]:
        p = out / f"{name}.jsonl"
        if not p.exists():
            continue
        rows = load_rows(p)
        a, b = np.array([mssd_of(r) for r in base]), np.array([mssd_of(r) for r in rows])
        f = {key(r) for r in rows if mssd_of(r) >= 0.5}
        det[name] = {"same_fail_set": f == fails, "n_fail": len(f), "only_in_base": len(fails - f), "only_here": len(f - fails),
                     "n_differ_gt_1e-9mm": int((np.abs(a - b) > 1e-9).sum()), "max_abs_diff_mm": float(np.abs(a - b).max())}
        print(name, json.dumps(det[name]))

    s = json.loads((out / "static_gt.json").read_text())
    own = {1: 60.0, 2: 100.0, 3: 150.0, 4: 30.0}
    prof = [r for r in s if r["obj_id"] != 4]

    print("\n== mesh used by the ray-cast cache vs the part's own mesh (H2 replay) ==")
    print("meshes per ICP call:", sorted({r["n_meshes_in_call"] for r in s}))
    pairs = {}
    for r in s:
        k = f"{own[r['obj_id']]:.0f}<-{r['used_extent']:.0f}"
        d = pairs.setdefault(k, {"n": 0, "fail": 0, "jump": 0, "slide": 0, "rotation": 0})
        d["n"] += 1
        if r["group"] != "pass":
            d["fail"] += 1
            d[r["group"]] += 1
    for k in sorted(pairs):
        print(k, json.dumps(pairs[k]))
    same = [r for r in prof if r["used_extent"] == own[r["obj_id"]]]
    diff = [r for r in prof if r["used_extent"] != own[r["obj_id"]]]
    print("profiles right mesh:", len(same), "fail", sum(r["group"] != "pass" for r in same),
          "| wrong mesh:", len(diff), "fail", sum(r["group"] != "pass" for r in diff))

    def med(rows, *path):
        v = []
        for r in rows:
            x = r
            for p in path:
                x = x[p]
            if x is not None:
                v.append(x)
        return round(float(np.median(v)), 4) if v else None

    print("\n== groups: run outcome and static measures at the GT pose (medians) ==")
    for g in ["pass", "slide", "rotation", "jump"]:
        for label, sub in [("right mesh", [r for r in same if r["group"] == g]), ("wrong mesh", [r for r in diff if r["group"] == g])]:
            if not sub:
                continue
            print(f"{g:9s} {label}: n={len(sub)}", "parts", {names[o]: sum(r['obj_id'] == o for r in sub) for o in names if o != 4},
                  "| run: fit", med(sub, "fitness_run"), "R", med(sub, "R_err_deg"), "axial", med(sub, "centre_err_axial_mm"),
                  "across", med(sub, "centre_err_across_mm"))
            for f in ["backface", "raycast_own", "raycast_used"]:
                print(f"    {f:12s} removed {med(sub, f, 'removed'):.4f} fit5 {med(sub, f, 'fit_5mm'):.4f} wrong_face {med(sub, f, 'wrong_face_5mm'):.4f}"
                      f" kappa {med(sub, f, 'kappa'):.3g} lam_min {med(sub, f, 'lam_min'):.3g} end_frac {med(sub, f, 'end_frac'):.4f}"
                      f" null_axial {med(sub, f, 'null_axial_t'):.3f} | step: R {med(sub, f, 'step_rot_deg'):.4f} deg axial {med(sub, f, 'step_axial_mm'):.4f} across {med(sub, f, 'step_across_mm'):.4f}")

    print("\n== low fitness in the run vs fitness at the GT pose ==")
    for lo, hi in [(0, 0.9), (0.9, 0.99), (0.99, 1.01)]:
        sub = [r for r in prof if r["fitness_run"] is not None and lo <= r["fitness_run"] < hi]
        print(f"run fitness [{lo},{hi}): n={len(sub)} fail={sum(r['group'] != 'pass' for r in sub)} wrong mesh={sum(r['used_extent'] != own[r['obj_id']] for r in sub)}"
              f" | GT fit5 used {med(sub, 'raycast_used', 'fit_5mm')} own {med(sub, 'raycast_own', 'fit_5mm')} backface {med(sub, 'backface', 'fit_5mm')}"
              f" | removed used {med(sub, 'raycast_used', 'removed')} own {med(sub, 'raycast_own', 'removed')} backface {med(sub, 'backface', 'removed')}")

    print("\n== do the filters remove surface the camera sees? all instance-views, measured points whose own patch is culled ==")
    for f in ["backface", "raycast_own", "raycast_used"]:
        for lab, sub in [("brackets", [r for r in s if r["obj_id"] == 4]), ("profiles right mesh", same), ("profiles wrong mesh", diff)]:
            v = np.array([r[f]["removed"] for r in sub]) if sub else np.array([0.0])
            print(f"{f:12s} {lab:20s} n={len(sub)} median {np.median(v):.5f} p99 {np.percentile(v, 99):.5f} max {v.max():.5f} share of views > 1%: {(v > 0.01).mean():.3f}")

    print("\n== failure rate by conditioning at the GT pose, target as used in the run ==")
    k = np.array([r["raycast_used"]["kappa"] or np.inf for r in prof])
    fail = np.array([r["group"] != "pass" for r in prof])
    edges = np.percentile(k, [0, 25, 50, 75, 100])
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (k >= lo) & (k <= hi)
        print(f"kappa [{lo:.3g},{hi:.3g}]: n={m.sum()} fail={fail[m].sum()}")
    print("by end-face share of correspondences, target as used in the run:")
    e = np.array([r["raycast_used"]["end_frac"] or 0.0 for r in prof])
    for lo, hi in [(0, 1e-9), (1e-9, 0.01), (0.01, 0.05), (0.05, 0.2), (0.2, 1.01)]:
        m = (e >= lo) & (e < hi)
        by = {g: int(sum(r["group"] == g for r, mm in zip(prof, m) if mm)) for g in ["slide", "rotation", "jump"]}
        print(f"end_frac [{lo},{hi}): n={m.sum()} fail={fail[m].sum()} {by}")
    print("same, with the part's own mesh as the target (right-mesh and wrong-mesh views together):")
    e = np.array([r["raycast_own"]["end_frac"] or 0.0 for r in prof])
    for lo, hi in [(0, 1e-9), (1e-9, 0.01), (0.01, 0.05), (0.05, 0.2), (0.2, 1.01)]:
        m = (e >= lo) & (e < hi)
        by = {g: int(sum(r["group"] == g for r, mm in zip(prof, m) if mm)) for g in ["slide", "rotation", "jump"]}
        print(f"end_frac [{lo},{hi}): n={m.sum()} fail={fail[m].sum()} {by}")

    print("\n== end faces at the GT pose: measured points on an end face with no end-face target within 1 mm ==")
    for lab, sub in [("profiles right mesh", same),
                     ("wrong mesh, used longer than part", [r for r in diff if r["used_extent"] > own[r["obj_id"]]]),
                     ("wrong mesh, used shorter than part", [r for r in diff if r["used_extent"] < own[r["obj_id"]]])]:
        for f in ["raycast_own", "raycast_used"]:
            v = [r[f]["end_pts_lost"] for r in sub if r[f]["end_pts_lost"] is not None]
            print(f"{lab:36s} {f:12s} views with end-face points {len(v)}/{len(sub)}, median lost {np.median(v):.3f}, end-face share of target {med(sub, f, 'end_target_share'):.4f},"
                  f" fail {sum(r['group'] != 'pass' for r in sub)}, of which not slide {sum(r['group'] in ('rotation', 'jump') for r in sub)}")

    print("\n== rotation and jump groups vs the direction of the mesh mismatch ==")
    for g in ["rotation", "jump", "slide"]:
        sub = [r for r in diff if r["group"] == g]
        print(g, "used longer", sum(r["used_extent"] > own[r["obj_id"]] for r in sub), "used shorter", sum(r["used_extent"] < own[r["obj_id"]] for r in sub))

    print("\n== the failures of H0, H1, solver lm against the groups of the failed H2 run ==")
    gb = {(r["scene"], r["im_id"], r["gt_id"]): r for r in s}
    for name in ["H0", "H1", "lm"]:
        rows = load_rows(out / f"{name}.jsonl")
        c = {}
        for r in rows:
            if mssd_of(r) >= 0.5:
                g = gb[key(r)]["group"]
                c[g] = c.get(g, 0) + 1
        ms = sorted(mssd_of(r) for r in rows)[-12:]
        print(name, "fails by H2 group", c, "| largest MSSD", [round(float(m), 3) for m in ms])

    print("\n== the axial slides, per instance-view ==")
    runs_ = {n: {key(r): r for r in load_rows(out / f"{n}.jsonl")} for n in ["H0", "H1", "lm"]}
    for r in [r for r in s if r["group"] == "slide"]:
        k = (r["scene"], r["im_id"], r["gt_id"])
        print(k, f"part {own[r['obj_id']]:.0f} used {r['used_extent']:.0f} | H2 MSSD {r['mssd_mm']:.3f} axial {r['centre_err_axial_mm']:.3f} across {r['centre_err_across_mm']:.3f} R {r['R_err_deg']:.3f}"
              f" fit {r['fitness_run']:.3f} | H0 {runs_['H0'][k]['mssd_mm']:.3f} H1 {runs_['H1'][k]['mssd_mm']:.3f} lm {runs_['lm'][k]['mssd_mm']:.3f}"
              f" | true end-face pts {r['backface']['n_end_pts']} side-to-end matches {r['backface']['side_matched_to_end']} of {r['n_pts']}")

    p1 = out / "H2_replay_omp1_meshes.json"
    if p1.exists():
        print("\n== threads, instrumented replay: which mesh the cache used at 1 thread vs the failed run (2 threads) ==")
        m2 = [c[0][1] for c in json.loads((out / "H2_replay_meshes.json").read_text())]
        m1 = [c[0][1] for c in json.loads(p1.read_text())]
        r1 = load_rows(out / "H2_replay_omp1.jsonl")
        o = [own[r["obj_id"]] for r in r1]
        isp = [r["obj_id"] != 4 for r in r1]
        print("profiles with a different mesh between 1 and 2 threads:", sum(a != b for a, b, c in zip(m1, m2, isp) if c), "of", sum(isp))
        wrong = [a != b for a, b in zip(m1, o)]
        fail1 = [mssd_of(r) >= 0.5 for r in r1]
        print("1 thread: wrong mesh", sum(wrong), "fail on wrong mesh", sum(w and f for w, f in zip(wrong, fail1)),
              "| right mesh", sum(not w and c for w, c in zip(wrong, isp)), "fail on right mesh", sum(not w and f and c for w, f, c in zip(wrong, fail1, isp)))
        h2 = np.array([mssd_of(r) for r in base])
        same_mesh = np.array([a == b for a, b in zip(m1, m2)])
        d = np.abs(np.array([mssd_of(r) for r in r1]) - h2)
        print(f"MSSD differs by > 1e-9 mm: on same mesh {int((d[same_mesh] > 1e-9).sum())}/{int(same_mesh.sum())} (max {d[same_mesh].max():.3g} mm),"
              f" on different mesh {int((d[~same_mesh] > 1e-9).sum())}/{int((~same_mesh).sum())}")
    for nm in ["H1_omp1", "H1_ompdefault"]:
        if (out / f"{nm}.jsonl").exists():
            a = np.array([mssd_of(r) for r in load_rows(out / "H1.jsonl")])
            b = np.array([mssd_of(r) for r in load_rows(out / f"{nm}.jsonl")])
            print(f"{nm} vs H1 at 2 threads (no ray cast, no cache): differ by > 1e-9 mm {int((np.abs(a - b) > 1e-9).sum())}/{len(a)}, max {np.abs(a - b).max():.3g} mm, fails {int((b >= 0.5).sum())}")

    print("\n== what remains without the ray cast: H1 failures, per instance-view ==")
    h1 = load_rows(out / "H1.jsonl")
    h1k = {key(r): r for r in h1}
    lmk = {key(r): r for r in load_rows(out / "lm.jsonl")}
    for r in h1:
        if mssd_of(r) >= 0.5:
            x = gb[key(r)]
            print(key(r), f"part {own[r['obj_id']]:.0f} H1 MSSD {r['mssd_mm']:.3f} axial {r['centre_err_axial_mm']:.3f} across {r['centre_err_across_mm']:.3f} R {r['R_err_deg']:.3f}"
                  f" fit {r['fitness']:.3f} | H2 group {x['group']}, MSSD {x['mssd_mm']:.3f} | lm {lmk[key(r)]['mssd_mm']:.3f}"
                  f" | end-face pts {x['backface']['n_end_pts']}, side-to-end matches {x['backface']['side_matched_to_end']} of {r['n_pts']}")
    print("H2 groups that H1 cures (H1 MSSD < 0.5 mm):", {g: sum(1 for r in s if r["group"] == g and h1k[(r["scene"], r["im_id"], r["gt_id"])]["mssd_mm"] < 0.5) for g in ["slide", "rotation", "jump"]})

    print("\n== H1 MSSD by part vs mean CAD sample spacing sqrt(area/N) ==")
    from synthrgbd.parts import PART_CATALOGUE, make_part
    for o, (nm, spec) in PART_CATALOGUE.items():
        t = make_part(spec).triangles
        spacing = np.sqrt(0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1).sum() / 50000)
        v = np.array([r["mssd_mm"] for r in h1 if r["obj_id"] == o])
        print(f"{nm:12s} spacing {spacing:.3f} mm | n {len(v)} median {np.median(v):.3f} p99 {np.percentile(v, 99):.3f} max {v.max():.3f} (max/spacing {v.max() / spacing:.2f}) | at or above 0.5 mm: {int((v >= 0.5).sum())}")

    print("\n== axial error under H1 vs side-face points matched to end-face samples; profiles with no measured end-face point ==")
    for lo, hi in [(0, 1), (1, 5)]:
        sub = [h1k[(r["scene"], r["im_id"], r["gt_id"])] for r in prof if r["backface"]["n_end_pts"] == 0 and lo <= r["backface"]["side_matched_to_end"] < hi]
        a = np.array([x["centre_err_axial_mm"] for x in sub])
        print(f"matches [{lo},{hi}): n {len(sub)} axial median {np.median(a):.3f} max {a.max():.3f} mm, MSSD at or above 0.5 mm: {sum(x['mssd_mm'] >= 0.5 for x in sub)}")

    print("\n== fitness on the part's own mesh at the GT pose, all instance-views ==")
    for f in ["backface", "raycast_own"]:
        print(f, "min fit5", round(min(r[f]["fit_5mm"] for r in s), 4), "min fit1", round(min(r[f]["fit_1mm"] for r in s), 4))
    print("worst removed fraction, ray cast on the used mesh:", round(max(r["raycast_used"]["removed"] for r in s), 3))

    print("\n== used mesh longer than the part: failures by whether an end face is measured ==")
    longer = [r for r in diff if r["used_extent"] > own[r["obj_id"]]]
    for lab, sub in [("end-face points measured", [r for r in longer if r["backface"]["n_end_pts"] > 0]), ("none", [r for r in longer if r["backface"]["n_end_pts"] == 0])]:
        print(lab, "n", len(sub), "fail", sum(r["group"] != "pass" for r in sub), "rotation or jump", sum(r["group"] in ("rotation", "jump") for r in sub))

    (out / "diagnosis.json").write_text(json.dumps({"candidates": table, "determinism": det, "mesh_pairs": pairs}, indent=1))


def trace(root: Path, out: Path) -> None:
    """H1 settings, stage by stage and outer loop by outer loop, on the 7 axial slides. Uses the same code path as
    icp_refine (one Open3D stage per call), so the final pose must match H1.jsonl."""
    from dataclasses import replace

    import cv2

    from synthrgbd.conditions import DEPTH_DIRS, DEPTH_SCALE_MM
    from synthrgbd.config import load_config
    from synthrgbd.pose import IcpParams, _icp_o3d, backproject, erode_mask, load_part_models

    hcfg = load_config(REPO / "configs" / "harness.yaml")
    hcfg["icp"].update({"visibility": "backface", "o3d_step_clamp": False})
    p = IcpParams.from_cfg(hcfg["icp"])
    models = load_part_models(hcfg["model_sampling"]["points_per_model"], hcfg["model_sampling"]["seed"])
    for o, m in models.items():
        t = m["mesh"].triangles
        area = 0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1).sum()
        print(f"obj {o} {m['name']}: area {area:.0f} mm2, mean sample spacing sqrt(area/N) = {np.sqrt(area / len(m['pts'])):.3f} mm")
    h1 = {key(r): r for r in load_rows(out / "H1.jsonl")}
    slides = [r for r in json.loads((out / "static_gt.json").read_text()) if r["group"] == "slide"]
    res = []
    for r in slides:
        k = (r["scene"], r["im_id"], r["gt_id"])
        sc = root / "synthrgbd" / "train_pbr" / f"{r['scene']:06d}"
        g = json.loads((sc / "scene_gt.json").read_text())[str(r["im_id"])][r["gt_id"]]
        K = np.array(json.loads((sc / "scene_camera.json").read_text())[str(r["im_id"])]["cam_K"]).reshape(3, 3)
        depth = cv2.imread(str(sc / DEPTH_DIRS["C1"] / f"{r['im_id']:06d}.png"), cv2.IMREAD_UNCHANGED).astype(np.float64) * DEPTH_SCALE_MM
        mask = cv2.imread(str(sc / "mask_visib" / f"{r['im_id']:06d}_{r['gt_id']:06d}.png"), cv2.IMREAD_GRAYSCALE) > 0
        pts = backproject(depth, erode_mask(mask, p.mask_erosion_px), K)
        T_gt = np.eye(4)
        T_gt[:3, :3], T_gt[:3, 3] = np.array(g["cam_R_m2c"]).reshape(3, 3), g["cam_t_m2c"]
        m = models[r["obj_id"]]
        half = float(np.abs(m["verts"][:, 2]).max())
        T, line = T_gt.copy(), []
        for max_corr, tukey in p.stages:
            T, _ = _icp_o3d(pts, m["pts"], m["nrm"], T, replace(p, max_corr_mm=max_corr, tukey_k_mm=tukey), None)
            line.append(round(float((T[:3, 3] - T_gt[:3, 3]) @ T_gt[:3, 2]), 3))
        x_gt = (pts - T_gt[:3, 3]) @ T_gt[:3, :3]
        z = x_gt[:, 2]
        near = np.abs(np.abs(z) - half)
        res.append({"key": k, "axial_by_stage_mm": line, "H1_axial_mm": h1[k]["centre_err_axial_mm"], "n_pts": len(pts),
                    "pts_within_1mm_of_end": int((near < 1).sum()), "pts_on_end_face": int((near < 0.1).sum()),
                    "z_range_mm": [round(float(z.min()), 2), round(float(z.max()), 2)], "half_len": half})
        print(json.dumps(res[-1]))
    (out / "trace_slides.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    cmd, root_, out_ = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    if cmd == "replay":
        replay(root_, out_, int(sys.argv[4]), int(sys.argv[5]), sys.argv[6] if len(sys.argv) > 6 else "")
    elif cmd == "static":
        static(root_, out_, int(sys.argv[4]), int(sys.argv[5]))
    elif cmd == "trace":
        trace(root_, out_)
    else:
        report(root_, out_)
