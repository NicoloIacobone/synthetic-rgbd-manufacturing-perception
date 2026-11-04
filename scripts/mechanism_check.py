"""Mechanism behind the C3 depth bias (A-54): reflected dots (i) vs SGBM fill from the background (ii).

Usage: .venv/bin/python scripts/mechanism_check.py <dataset_root> <scene_seed>... --out <json>

Diagnostic only: nothing here changes the matcher, the material or any frozen setting, and no result is written
back into the dataset. Per view, on metal-part pixels (GT visible masks eroded 2 px, as in the harness):

Observation
- classes: invalid / correct (|err| <= 5 mm) / towards background (z > z_gt + 5 and z <= z_bg + 5) / in front / beyond.
- (i) mirror prediction: for a planar mirror, stereo triangulates a reflected dot at its virtual image, on the camera
  ray at the camera-to-surface distance plus the reflected path length. z_virt comes from ray-casting the GT scene.
- (ii) texture: noise-free 7 x 7 local DN contrast over the sensor noise at that level (SNR); P(biased | no texture).
Interventions on the 8-bit SGBM input (same noise draws, same matcher):
- blank: part pixels set to 0 DN in both images. If the disparity on metal does not depend on the metal's own image
  content (reflected dots included), it survives blanking.
- bgshift k: background pixels of the right image shifted by k px, so the background disparity becomes d + k; part
  pixels are untouched. A pixel filled from the background follows (slope 1); a pixel matched on its own content
  stays (slope 0). Large k can push the fill onto textured tray, so "blank + bgshift" is the positive control.
- bgcut: background pixels of the right image permuted, which removes the left-right correspondence of the background
  while keeping its brightness and the dark part silhouette. A fill loses its source; own-content matches do not.
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import open3d as o3d

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.config import load_config  # noqa: E402
from synthrgbd.geometry import disparity_to_depth  # noqa: E402
from synthrgbd.parts import PART_CATALOGUE, make_part  # noqa: E402
from synthrgbd.pose import erode_mask  # noqa: E402
from synthrgbd.seeds import rng  # noqa: E402
from synthrgbd.stereo import auto_exposure_gain, exposed_pair_uint8, exposure_roi_x0, make_sgbm, match_extended  # noqa: E402

# M2 scene model (scripts/bproc_render_scene.py, A-34), metres, world frame (tray floor top at z = 0).
IX, IY, WALL_H, WALL_T, FLOOR_T = 0.50, 0.35, 0.04, 0.01, 0.02
BOXES = [((2.0, 2.0, 0.02), (0, 0, -FLOOR_T - 0.01)),
         ((IX + 2 * WALL_T, IY + 2 * WALL_T, FLOOR_T), (0, 0, -FLOOR_T / 2)),
         ((WALL_T, IY + 2 * WALL_T, WALL_H), (IX / 2 + WALL_T / 2, 0, WALL_H / 2)),
         ((WALL_T, IY + 2 * WALL_T, WALL_H), (-IX / 2 - WALL_T / 2, 0, WALL_H / 2)),
         ((IX, WALL_T, WALL_H), (0, IY / 2 + WALL_T / 2, WALL_H / 2)),
         ((IX, WALL_T, WALL_H), (0, -IY / 2 - WALL_T / 2, WALL_H / 2))]
SHIFTS = (-8, -3, 3, 8)
SNR_BINS = [(0, 0.5), (0.5, 1), (1, 2), (2, 5), (5, np.inf)]
DIST_BINS = [(0, 3), (3, 5), (5, 10), (10, 20), (20, 1e9)]        # px from the edge of the uneroded GT mask
TOL_MM = 5.0


def add_tris(scene, verts, faces):
    scene.add_triangles(o3d.core.Tensor(verts.astype(np.float32)), o3d.core.Tensor(faces.astype(np.uint32)))


def build_scenes(gt, Rw, tw):
    """(full scene, tray/table only), camera frame, mm. Geometry ids 0 .. len(gt)-1 of the full scene are the parts."""
    full, bg = o3d.t.geometry.RaycastingScene(), o3d.t.geometry.RaycastingScene()
    for g in gt:
        tri = make_part(PART_CATALOGUE[g["obj_id"]][1]).triangles
        R, t = np.array(g["cam_R_m2c"]).reshape(3, 3), np.array(g["cam_t_m2c"], float)
        v = tri.reshape(-1, 3) @ R.T + t
        add_tris(full, v, np.arange(len(v)).reshape(-1, 3))
    for size, loc in BOXES:
        b = o3d.geometry.TriangleMesh.create_box(*size)
        b.translate(np.array(loc) - np.array(size) / 2)
        v = (np.asarray(b.vertices) * 1e3) @ Rw.T + tw
        add_tris(full, v, np.asarray(b.triangles))
        add_tris(bg, v, np.asarray(b.triangles))
    return full, bg


def pixel_rays(K, W, H, u0=0):
    u, v = np.meshgrid(np.arange(W) - u0, np.arange(H))
    d = np.stack([(u - K[0, 2]) / K[0, 0], (v - K[1, 2]) / K[1, 1], np.ones(u.shape)], -1).reshape(-1, 3)
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def cast(scene, origin, d):
    o = np.broadcast_to(origin, d.shape)
    return scene.cast_rays(o3d.core.Tensor(np.hstack([o, d]).astype(np.float32)))


def part_mask_ext(full, n_parts, K, W_ext, H, pad, origin_mm):
    """Mask of part pixels in an image extended by `pad` columns, seen from `origin_mm` (A-40 geometry)."""
    gid = cast(full, origin_mm, pixel_rays(K, W_ext, H, pad))["geometry_ids"].numpy().astype(np.int64)
    return (gid < n_parts).reshape(H, W_ext)


def texture_snr(dn_clean, e_per_dn, read_dn, w=7):
    """Noise-free local contrast in the SGBM window / sensor noise at the local mean level."""
    d = dn_clean.astype(np.float32)
    m = cv2.boxFilter(d, -1, (w, w), borderType=cv2.BORDER_REFLECT)
    m2 = cv2.boxFilter(d * d, -1, (w, w), borderType=cv2.BORDER_REFLECT)
    return np.sqrt(np.maximum(m2 - m * m, 0)) / np.sqrt(np.maximum(m, 0) / e_per_dn + read_dn ** 2)


def classes(z, z_gt, z_bg, mask):
    """Boolean maps (mm inputs) of the pixel classes inside mask; they partition the mask."""
    valid = mask & (z > 0)
    err = z - z_gt
    correct = valid & (np.abs(err) <= TOL_MM)
    towards = valid & (err > TOL_MM) & (z <= z_bg + TOL_MM)
    beyond = valid & (err > TOL_MM) & (z > z_bg + TOL_MM)
    front = valid & (err < -TOL_MM)
    return {"invalid": mask & ~valid, "correct": correct, "towards_bg": towards, "beyond_bg": beyond, "in_front": front}


def frac(a, b):
    return float(a.sum() / b.sum()) if b.sum() else None


def shift_background(r8, mR, k):
    """R'(x) = R(x + k) on background pixels, so the background disparity d becomes d + k. Part pixels stay; background
    pixels whose source is a part pixel stay too (part content is not smeared outwards)."""
    src = np.clip(np.arange(r8.shape[1]) + k, 0, r8.shape[1] - 1)
    out = r8.copy()
    put = ~mR & ~mR[:, src]
    out[put] = r8[:, src][put]
    return out


def tracking(d_new, d_ref, k, sel):
    """How a disparity map d_new follows a background shift k relative to d_ref on the pixels `sel`."""
    ok = sel & (d_new > 0)
    delta = d_new - d_ref
    return {"still_valid": frac(ok, sel), "followed_shift_half_px": frac(ok & (np.abs(delta - k) <= 0.5), sel),
            "stayed_half_px": frac(ok & (np.abs(delta) <= 0.5), sel),
            "median_slope": float(np.median(delta[ok]) / k) if ok.any() else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("scenes", type=int, nargs="+")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cfg, ir = load_config(), load_config(REPO / "configs" / "camera_d415_ir.yaml")
    cam, sn, B = cfg["camera"], ir["sensor_noise"], cfg["camera"]["baseline_m"]
    W, H, pad, maxd = cam["width"], cam["height"], ir["ir_render"]["pad_px"], cam["disparity_search_px"]
    sgbm = make_sgbm(ir["sgbm"])
    per_view = []
    for seed in args.scenes:
        sc = args.root / "synthrgbd" / "train_pbr" / f"{seed:06d}"
        gt_all = json.loads((sc / "scene_gt.json").read_text())
        cams = json.loads((sc / "scene_camera.json").read_text())
        for im in sorted(gt_all, key=int):
            gt = gt_all[im]
            cc = cams[im]
            K = np.array(cc["cam_K"]).reshape(3, 3)
            Rw, tw = np.array(cc["cam_R_w2c"]).reshape(3, 3), np.array(cc["cam_t_w2c"], float)
            fx = K[0, 0]
            full, bg = build_scenes(gt, Rw, tw)
            d = pixel_rays(K, W, H)
            ans = cast(full, np.zeros(3), d)
            t_hit = ans["t_hit"].numpy().astype(np.float64)
            nrm = ans["primitive_normals"].numpy().astype(np.float64)
            nrm[(nrm * d).sum(1) > 0] *= -1
            p = d * t_hit[:, None]
            mirror = d - 2 * (d * nrm).sum(1, keepdims=True) * nrm
            m_ans = full.cast_rays(o3d.core.Tensor(np.hstack([p + 0.05 * nrm, mirror]).astype(np.float32)))
            L = m_ans["t_hit"].numpy().astype(np.float64)
            z_virt = (d * (t_hit + L)[:, None])[:, 2].reshape(H, W)              # inf when the reflection sees nothing
            z_bg = (d * cast(bg, np.zeros(3), d)["t_hit"].numpy()[:, None])[:, 2].reshape(H, W)
            z_gt = cv2.imread(str(sc / "depth" / f"{int(im):06d}.png"), cv2.IMREAD_UNCHANGED).astype(np.float64) * 0.1
            parts = np.zeros((H, W), bool)
            for k in range(len(gt)):
                parts |= erode_mask(cv2.imread(str(sc / "mask_visib" / f"{int(im):06d}_{k:06d}.png"), 0) > 0, 2)

            r = rng(cfg["seeds"]["master"], seed, int(im), "ir_noise")
            ir_m = np.load(sc / "ir" / f"{int(im):06d}_metal.npz")
            Lm, Rm = ir_m["left"].astype(np.float32), ir_m["right"].astype(np.float32)
            zl, zr = r.standard_normal(Lm.shape), r.standard_normal(Lm.shape)
            gain = auto_exposure_gain(Lm[:, pad:], exposure_roi_x0(fx, B, cam["min_z_m"]), float(ir["exposure"]["setpoint_dn"]))
            l8, r8 = exposed_pair_uint8(Lm, Rm, gain, sn, zl, zr)
            d_c3 = match_extended(l8, r8, pad, sgbm, maxd)
            z_c3 = disparity_to_depth(d_c3, fx, B, maxd) * 1e3
            stored = cv2.imread(str(sc / "depth_stereo_metal" / f"{int(im):06d}.png"), cv2.IMREAD_UNCHANGED) * 0.1
            reproduced = float(np.abs(stored - np.round(z_c3 * 10) * 0.1).max())

            # right image background shift and blanking use each camera's own part mask
            Hext, Wext = l8.shape
            mL = part_mask_ext(full, len(gt), K, Wext, Hext, pad, np.zeros(3))
            mR = part_mask_ext(full, len(gt), K, Wext, Hext, pad, np.array([B * 1e3, 0.0, 0.0]))

            cls = classes(z_c3, z_gt, z_bg, parts)
            biased = cls["towards_bg"] | cls["beyond_bg"] | cls["in_front"]
            valid = parts & (z_c3 > 0)
            snr = texture_snr(Lm[:, pad:] * gain, sn["e_per_dn"], sn["read_noise_dn"])
            textured = snr >= 1.0
            rad = Lm[:, pad:]
            tray = (~parts) & (z_gt > 0)
            has_mirror = np.isfinite(z_virt)
            row = {
                "scene": seed, "im_id": int(im), "gain": gain, "reproduced_max_diff_mm": reproduced,
                "n_part_px": int(parts.sum()),
                "class_frac": {k: frac(v, parts) for k, v in cls.items()},
                "dn_clean_part_median": float(np.median((rad * gain)[parts])),
                "dn_clean_tray_median": float(np.median((rad * gain)[tray])),
                "dn_clean_part_p99": float(np.percentile((rad * gain)[parts], 99)),
                "dn_clean_tray_p99": float(np.percentile((rad * gain)[tray], 99)),
                "part_frac_no_texture": frac(parts & ~textured, parts),
                "tray_frac_no_texture": frac(tray & ~textured, tray),
                "P_biased_given_no_texture": frac(biased & ~textured, valid & ~textured),
                "P_biased_given_texture": frac(biased & textured, valid & textured),
                "biased_share_no_texture": frac(biased & ~textured, biased),
                # (i) mirror image
                "part_frac_mirror_sees_scene": frac(parts & has_mirror, parts),
                "biased_within_5mm_of_virtual": frac(biased & has_mirror & (np.abs(z_c3 - z_virt) <= TOL_MM), biased),
                "biased_mirror_sees_scene": frac(biased & has_mirror, biased),
                # (ii) fill from the background
                "biased_within_5mm_of_bg": frac(biased & (np.abs(z_c3 - z_bg) <= TOL_MM), biased),
                "biased_between_surface_and_bg": frac(cls["towards_bg"], biased),
            }
            # Chance level for the virtual-image match: the same biased pixels against z_virt of a shifted pixel
            shuffled = np.roll(z_virt, 97, axis=1)
            row["biased_within_5mm_of_virtual_null"] = frac(biased & np.isfinite(shuffled) & (np.abs(z_c3 - shuffled) <= TOL_MM), biased)

            # Control: C4 under the same gain and noise draws. Matte parts cannot mirror anything, so bias here is fill.
            z_c4 = cv2.imread(str(sc / "depth_stereo_matte" / f"{int(im):06d}.png"), cv2.IMREAD_UNCHANGED).astype(np.float64) * 0.1
            rad_m = np.load(sc / "ir" / f"{int(im):06d}_matte.npz")["left"][:, pad:].astype(np.float32)
            snr_m = texture_snr(rad_m * gain, sn["e_per_dn"], sn["read_noise_dn"])
            row["c4_class_frac"] = {k: frac(v, parts) for k, v in classes(z_c4, z_gt, z_bg, parts).items()}
            row["c4_part_frac_no_texture"] = frac(parts & (snr_m < 1.0), parts)

            # Strata and profiles: where the mirror ray sees the scene or nothing; texture; distance from the mask edge
            row["class_frac_mirror_sees_scene"] = {k: frac(v & has_mirror, parts & has_mirror) for k, v in cls.items()}
            row["class_frac_mirror_sees_nothing"] = {k: frac(v & ~has_mirror, parts & ~has_mirror) for k, v in cls.items()}
            row["P_correct_by_snr"] = {f"{a}-{b}": frac(cls["correct"] & (snr >= a) & (snr < b), valid & (snr >= a) & (snr < b)) for a, b in SNR_BINS}
            row["share_px_by_snr"] = {f"{a}-{b}": frac(parts & (snr >= a) & (snr < b), parts) for a, b in SNR_BINS}
            dist = np.zeros((H, W), np.float32)
            for k in range(len(gt)):
                mk = cv2.imread(str(sc / "mask_visib" / f"{int(im):06d}_{k:06d}.png"), 0) > 0
                dist = np.maximum(dist, cv2.distanceTransform(mk.astype(np.uint8), cv2.DIST_L2, 5))
            row["P_correct_by_edge_dist"] = {f"{a}-{b}": frac(cls["correct"] & (dist >= a) & (dist < b), parts & (dist >= a) & (dist < b)) for a, b in DIST_BINS}
            row["share_px_by_edge_dist"] = {f"{a}-{b}": frac(parts & (dist >= a) & (dist < b), parts) for a, b in DIST_BINS}
            d_gt = fx * B * 1e3 / np.maximum(z_gt, 1e-6)
            d_bg = fx * B * 1e3 / np.maximum(z_bg, 1e-6)
            rho = (d_gt - d_c3) / np.maximum(d_gt - d_bg, 1e-6)                 # 0 = surface, 1 = tray behind it
            bt = cls["towards_bg"]
            row["towards_bg_rho"] = {"p10": float(np.percentile(rho[bt], 10)), "p50": float(np.percentile(rho[bt], 50)),
                                     "p90": float(np.percentile(rho[bt], 90)), "n": int(bt.sum())} if bt.any() else None
            row["gap_surface_to_bg_px"] = float(np.median((d_gt - d_bg)[parts]))
            row["biased_median_abs_disp_err_px"] = float(np.median(np.abs(d_c3 - d_gt)[biased])) if biased.any() else None
            row["tol_5mm_in_px"] = float(np.median((d_gt - fx * B * 1e3 / (z_gt + TOL_MM))[parts]))

            # Intervention: blank the parts in both images
            l_b, r_b = l8.copy(), r8.copy()
            l_b[mL], r_b[mR] = 0, 0
            d_blank = match_extended(l_b, r_b, pad, sgbm, maxd)
            both = biased & (d_blank > 0)
            row["blank"] = {"part_valid": frac(parts & (d_blank > 0), parts),
                            "biased_still_valid": frac(both, biased),
                            "biased_same_disparity_1px": frac(both & (np.abs(d_blank - d_c3) <= 1), biased),
                            "correct_same_disparity_1px": frac(cls["correct"] & (d_blank > 0) & (np.abs(d_blank - d_c3) <= 1), cls["correct"])}
            cb = classes(disparity_to_depth(d_blank, fx, B, maxd) * 1e3, z_gt, z_bg, parts)
            row["blank"]["class_frac"] = {k: frac(v, parts) for k, v in cb.items()}

            # Intervention: remove the left-right correspondence of the background (right image only)
            perm = np.random.default_rng([seed, int(im), 77]).permutation(int((~mR).sum()))
            r_c = r8.copy()
            r_c[~mR] = r8[~mR][perm]
            d_cut = match_extended(l8, r_c, pad, sgbm, maxd)
            cc_ = classes(disparity_to_depth(d_cut, fx, B, maxd) * 1e3, z_gt, z_bg, parts)
            row["bgcut"] = {"class_frac": {k: frac(v, parts) for k, v in cc_.items()},
                            "biased_same_disparity_1px": frac(biased & (d_cut > 0) & (np.abs(d_cut - d_c3) <= 1), biased),
                            "correct_same_disparity_1px": frac(cls["correct"] & (d_cut > 0) & (np.abs(d_cut - d_c3) <= 1), cls["correct"]),
                            "class_frac_mirror_sees_scene": {k: frac(v & has_mirror, parts & has_mirror) for k, v in cc_.items()},
                            "class_frac_mirror_sees_nothing": {k: frac(v & ~has_mirror, parts & ~has_mirror) for k, v in cc_.items()}}

            # Intervention: shift the background of the right image only; positive control on blanked metal
            row["bgshift"], row["blank_bgshift"] = {}, {}
            for k in SHIFTS:
                d_s = match_extended(l8, shift_background(r8, mR, k), pad, sgbm, maxd)
                row["bgshift"][str(k)] = {"biased": tracking(d_s, d_c3, k, biased), "correct": tracking(d_s, d_c3, k, cls["correct"]),
                                          "biased_mirror_scene": tracking(d_s, d_c3, k, biased & has_mirror),
                                          "biased_mirror_nothing": tracking(d_s, d_c3, k, biased & ~has_mirror),
                                          "tray": tracking(d_s, d_c3, k, tray & (z_c3 > 0) & (np.abs(z_c3 - z_gt) <= TOL_MM))}
                d_bs = match_extended(l_b, shift_background(r_b, mR, k), pad, sgbm, maxd)
                row["blank_bgshift"][str(k)] = {"parts": tracking(d_bs, d_blank, k, parts & (d_blank > 0))}
            per_view.append(row)
            print(json.dumps({k: row[k] for k in ("scene", "im_id", "reproduced_max_diff_mm", "class_frac")}), flush=True)

    def pool(path):
        vals = []
        for row in per_view:
            x = row
            for key in path:
                x = x[key]
            if x is not None:
                vals.append((x, row["n_part_px"]))
        if not vals:                 # e.g. the first edge-distance bin: the 2 px erosion leaves no pixel there
            return {"mean_weighted_px": None, "min": None, "max": None}
        v, w = np.array([a for a, _ in vals], float), np.array([b for _, b in vals], float)
        return {"mean_weighted_px": float(np.sum(v * w) / np.sum(w)), "min": float(v.min()), "max": float(v.max())}

    def pool_dict(key):
        return {k: pool([key, k]) for k in per_view[0][key]}

    summary = {"n_views": len(per_view)}
    for key in ("class_frac", "c4_class_frac", "class_frac_mirror_sees_scene", "class_frac_mirror_sees_nothing", "P_correct_by_snr",
                "share_px_by_snr", "P_correct_by_edge_dist", "share_px_by_edge_dist"):
        summary[key] = pool_dict(key)
    for key in ("c4_part_frac_no_texture", "part_frac_no_texture", "tray_frac_no_texture", "P_biased_given_no_texture", "P_biased_given_texture",
                "biased_share_no_texture", "part_frac_mirror_sees_scene", "biased_mirror_sees_scene",
                "biased_within_5mm_of_virtual", "biased_within_5mm_of_virtual_null", "biased_within_5mm_of_bg",
                "biased_between_surface_and_bg", "dn_clean_part_median", "dn_clean_tray_median", "dn_clean_part_p99",
                "dn_clean_tray_p99", "gap_surface_to_bg_px", "biased_median_abs_disp_err_px", "tol_5mm_in_px"):
        summary[key] = pool([key])
    summary["towards_bg_rho_p50_median_over_views"] = float(np.median([r["towards_bg_rho"]["p50"] for r in per_view if r["towards_bg_rho"]]))
    summary["blank"] = {k: pool(["blank", k]) for k in ("part_valid", "biased_still_valid", "biased_same_disparity_1px", "correct_same_disparity_1px")}
    summary["blank"]["class_frac"] = {k: pool(["blank", "class_frac", k]) for k in per_view[0]["blank"]["class_frac"]}
    summary["bgcut"] = {"class_frac": {k: pool(["bgcut", "class_frac", k]) for k in per_view[0]["bgcut"]["class_frac"]},
                        "biased_same_disparity_1px": pool(["bgcut", "biased_same_disparity_1px"]),
                        "correct_same_disparity_1px": pool(["bgcut", "correct_same_disparity_1px"]),
                        "class_frac_mirror_sees_scene": {k: pool(["bgcut", "class_frac_mirror_sees_scene", k]) for k in per_view[0]["bgcut"]["class_frac"]},
                        "class_frac_mirror_sees_nothing": {k: pool(["bgcut", "class_frac_mirror_sees_nothing", k]) for k in per_view[0]["bgcut"]["class_frac"]}}
    metrics = ("still_valid", "followed_shift_half_px", "stayed_half_px", "median_slope")
    summary["bgshift"] = {str(k): {n: {m: pool(["bgshift", str(k), n, m]) for m in metrics} for n in ("biased", "biased_mirror_scene", "biased_mirror_nothing", "correct", "tray")} for k in SHIFTS}
    summary["blank_bgshift"] = {str(k): {m: pool(["blank_bgshift", str(k), "parts", m]) for m in metrics} for k in SHIFTS}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"summary": summary, "per_view": per_view}, indent=1))
    print("SUMMARY", json.dumps(summary))


if __name__ == "__main__":
    main()
