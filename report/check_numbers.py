"""Check that the numbers printed in report.tex are the ones in the tracked results.

Usage: .venv/bin/python report/check_numbers.py [report/report.tex]

Each claim below is computed from results/ and formatted as it appears in the text; it must occur in the source. Exit code 1 if any is
missing. A number that passes is present in the text, which does not prove it stands in the right sentence: read the report as well.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
R = REPO / "results"


def J(name):
    return json.loads((R / name).read_text())


def f3(x):
    return f"{x:.3f}"


def f1(x):
    return f"{x:.1f}"


def signed(x):
    """Percentage points as printed: +64.8, $-$27.4."""
    return ("+" if x >= 0 else "$-$") + f"{abs(x) * 100:.1f}"


def plain(x):
    return ("$-$" if x < 0 else "") + f"{abs(x) * 100:.1f}"


def sci(p):
    m, e = f"{p:.0e}".split("e")
    return rf"{m}\times10^{{{int(e)}}}"


def main():
    tex_path = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "report" / "report.tex"
    tex = tex_path.read_text()
    s, old = J("hfov71/stats.json"), J("archive_hfov65/stats.json")
    se, red, amb, rob = J("hfov71/sensor.json")["conditions"], J("hfov71/redraw.json"), J("hfov71/ambient.json"), J("hfov71/s58_robustness.json")
    dist, mech, app, robi = J("hfov71/distance.json")["conditions"], J("hfov71/mechanism_dev.json")["summary"], J("hfov71/ir_appearance.json"), J("hfov71/robi_zigzag_real.json")
    anchor, gate, intr, unlit = J("hfov71/anchor_a.json"), J("hfov71/plane_gate_no_noise.json"), J("hfov71/intrinsics_check.json"), J("hfov71/unlit_share.json")
    robi_f = 905.9  # fx of ROBI's real camera (report, What did not work)
    claims = []

    def add(label, text):
        claims.append((label, text))

    # Table of results
    names = {"C1": "C1 ideal depth", "C2a": "C2a noise 0.08\\,px", "C2b": "C2b noise 0.234\\,px", "C3": "\\textbf{C3 metal, camera model}", "C4": "C4 matte, camera model",
             "C3r02": "Metal, roughness 0.2", "C3r04": "Metal, roughness 0.4", "C3nogloss": "Metal, reflections off", "C4bright": "Matte, albedo 0.5"}
    for c, name in names.items():
        a = s["A1_recall_5mm"][c]
        rec = f3(a["all"]["recall"])
        rec = f"\\textbf{{{rec}}}" if c == "C3" else rec
        row = (f"{name} & {rec} ({f3(a['all']['ci95'][0])}--{f3(a['all']['ci95'][1])}) & {f3(a['profile']['recall'])} & {f3(a['bracket']['recall'])} & "
               f"{f3(s['A1_recall_2mm'][c]['all']['recall'])} & {f1(s['A1_secondary'][c]['median_mssd_mm'])} & {f3(s['B_success'][c]['bracket']['success'])} & "
               f"{f3(old['A1_recall_5mm'][c]['all']['recall'])} \\\\")
        add(f"table row {c}", row)
    # Fixed sequence
    for f in s["fixed_sequence"]:
        add(f"seq {f['a']}-{f['b']}", f"{signed(f['diff'])} ({plain(f['ci95'][0])} to {plain(f['ci95'][1])}), $p={sci(f['p'])}$")
        assert f["test_rejects"]
    add("MDE", ", ".join(f"{f['mde_scenes'] * 100:.1f}" for f in s["fixed_sequence"]) + " points")
    add("unit", f"{s['unit']['instance_views']} instance-views ({s['unit']['profile']} profiles, {s['unit']['bracket']} brackets)")
    assert s["unit"]["excluded_visib_lt_0.1"] == 0 and not s["dirty_tree_any"] and s["commits"] == [s["commits"][0]] and s["commits"][0].startswith("7eca5f0")
    add("factor eight", "factor of eight")
    assert round(s["A1_recall_5mm"]["C2b"]["all"]["recall"] / s["A1_recall_5mm"]["C3"]["all"]["recall"]) == 8
    add("factor two", "a factor of two at roughness 0.4 (" + f3(s["A1_recall_5mm"]["C2b"]["all"]["recall"]) + " against " + f3(s["A1_recall_5mm"]["C3"]["all"]["recall"]) + " and " + f3(s["A1_recall_5mm"]["C3r04"]["all"]["recall"]) + ")")
    assert round(s["A1_recall_5mm"]["C2b"]["all"]["recall"] / s["A1_recall_5mm"]["C3r04"]["all"]["recall"]) == 2
    # Detectable effect implied by each interval: 2.8 standard errors, with the half-width at 1.96
    implied = [2.8 * (f["ci95"][1] - f["ci95"][0]) / 2 / 1.96 * 100 for f in s["fixed_sequence"]]
    assert 7 <= min(implied) and max(implied) <= 10, implied
    add("detectable from intervals", "about 7--10 points are detectable at 80\\% power")
    add("detectable in limitations", "Detectable effects are about 7--10 points on 50 scenes")
    assert all(abs(f["diff"]) > f["mde_scenes"] for f in s["fixed_sequence"])
    # Sensor
    c3, c4, c2b = se["C3"], se["C4"], se["C2b"]
    add("C3 invalid", f"{c3['parts']['invalid_frac'] * 100:.1f}\\% of metal-part pixels are invalid")
    add("C3 > 5 mm", f"{c3['parts']['frac_gt_5mm'] * 100:.1f}\\% of the valid ones are off by more than 5\\,mm")
    add("C3 signed", f"median +{c3['parts']['median_signed_mm']:.1f}\\,mm, 5th and 95th percentiles $-${abs(c3['parts']['quantiles_mm']['5']):.1f} and +{c3['parts']['quantiles_mm']['95']:.1f}\\,mm")
    add("C2b symmetric", f"$\\pm${c2b['parts']['quantiles_mm']['95']:.1f}\\,mm")
    add("C4 edge", f"{c4['edge']['frac_gt_5mm'] * 100:.1f}\\% of edge pixels and {c4['interior']['frac_gt_5mm'] * 100:.1f}\\% of interior pixels")
    # Start at 2 mm: stored only in the jsonl, so checked in data/ when it exists
    p = REPO / "data/hfov71/test/results/A_C3_2.jsonl"
    if p.exists():
        rows = [json.loads(x) for x in p.read_text().splitlines()[1:]]
        init = [r["mssd_init_mm"] for r in rows]
        assert max(init) < 5.0
        add("start 2 mm", f"largest {max(init):.2f}\\,mm")
    add("C1 at 2 mm, C3 at 2 mm", f"C1 keeps {s['sweep_recall_5mm']['C1']['2']['recall']:.2f} and C3 ends at {f3(s['sweep_recall_5mm']['C3']['2']['recall'])}")
    # Ranking at all offsets
    for mm, row in ((m, {c: s["sweep_recall_5mm"][c][m]["recall"] for c in ("C1", "C2a", "C2b", "C3", "C4")}) for m in ("2", "5", "10", "20")):
        assert min(row["C1"], row["C2a"]) > row["C2b"] > row["C4"] > row["C3"], mm
    # Pairs
    pair = {(x["a"], x["b"]): x for x in s["A1_descriptive_pairs"]}
    x = pair[("C1", "C2a")]
    add("C1-C2a", f"{plain(x['diff'])} points ({plain(x['ci95'][0])} to {signed(x['ci95'][1])})")
    x = pair[("C3", "C3nogloss")]
    add("reflections off", f"{plain(x['diff'])} points ({plain(x['ci95'][0])} to {signed(x['ci95'][1])})")
    x = pair[("C4", "C4bright")]
    add("brighter matte", f"{signed(-x['diff'])} points ({plain(-x['ci95'][1])} to {signed(-x['ci95'][0])})")
    # Distance
    add("distance n", f"below 0.7\\,m ({dist['C1'][0]['n']} views) to 0.9\\,m and beyond ({dist['C1'][2]['n']} views)")
    add("distance C3 C4", f"C3 falls from {f3(dist['C3'][0]['recall'])} to {f3(dist['C3'][2]['recall'])} and C4 from {f3(dist['C4'][0]['recall'])} to {f3(dist['C4'][2]['recall'])}")
    add("distance C1", f"C1 rises from {f3(dist['C1'][0]['recall'])} to {f3(dist['C1'][2]['recall'])}")
    # Suction
    b = {c: s["B_success"][c] for c in ("C1", "C3")}
    add("suction C3", f"C3 plans a grasp on {b['C3']['bracket']['has_grasp'] * 100:.1f}\\% of views and {b['C3']['bracket']['success'] / b['C3']['bracket']['has_grasp'] * 100:.1f}\\% of those succeed")
    add("suction C1", f"against {b['C1']['bracket']['has_grasp'] * 100:.1f}\\% and {b['C1']['bracket']['success'] / b['C1']['bracket']['has_grasp'] * 100:.1f}\\% for C1")
    add("suction profiles", f"{b['C1']['profile']['has_grasp'] * 100:.1f}\\% of profile views in C1 and on {b['C3']['profile']['has_grasp'] * 100:.1f}\\% in C3")
    assert all(s["B_success"][c]["profile"]["success"] == 0 for c in s["B_success"])
    # Suction intervals on brackets
    bk = {c: s["B_success"][c]["bracket"] for c in ("C1", "C2a", "C2b", "C3", "C4")}
    add("suction intervals", ", ".join(f"{c} {f3(bk[c]['success'])} ({f3(bk[c]['ci95'][0])}--{f3(bk[c]['ci95'][1])})" for c in ("C1", "C2a", "C2b", "C4", "C3")))
    pb = {(x["a"], x["b"]): x for x in s["B_pairs_bracket"]}[("C1", "C3")]
    add("suction C1-C3", f"{signed(pb['diff'])} points ({plain(pb['ci95'][0])} to {plain(pb['ci95'][1])})")
    add("suction n", f"the {pb['n']} bracket views")
    # Brightness match of matte and metal
    br = J("hfov71/brightness_match.json")
    add("brightness dev", f"({br['dev']['c4_dn_mean']:.1f}\\,DN each)")
    assert f1(br["dev"]["c4_dn_mean"]) == f1(br["dev"]["c3_dn_mean"])
    add("brightness test", f"{br['test']['c4_dn_mean']:.1f}\\,DN against {br['test']['c3_dn_mean']:.1f}\\,DN on average, with a per-view ratio from {br['test']['ratio_per_view']['min']:.2f} to {br['test']['ratio_per_view']['max']:.2f}")
    # Depth overflow
    w = J("hfov71/depth_wrap.json")
    wc = w["counts"]
    assert wc["C3"]["part_wrapped"] == 0 and wc["C4"]["part_wrapped"] == 0 and wc["C3"]["part_px"] == wc["C4"]["part_px"]
    assert w["c3_views_reproducing_the_stored_depth"]["identical"] == w["c3_views_reproducing_the_stored_depth"]["views"]
    add("wrap limit", f"beyond {w['limit_m']:.2f}\\,m (disparity below {w['disparity_below_px']:.1f}\\,px)")
    add("wrap lowest", f"as low as {w['c3_stored_mm_of_wrapped_pixels_seeds_0_9']['min']:.0f}\\,mm")
    frame = (wc["C3"]["frame_wrapped"] + wc["C4"]["frame_wrapped"]) / (wc["C3"]["frame_px"] + wc["C4"]["frame_px"])
    add("wrap frame", f"{frame * 100:.2f}\\% of image pixels but none of the " + f"{wc['C3']['part_px']:,}".replace(",", "\\,") + " part pixels")
    lw = wc["C3looselr_seeds_0_9"]
    add("wrap filters off", f"{lw['part_wrapped'] / lw['part_px'] * 100:.2f}\\% of part pixels on seeds 0--9")
    # Table of what moves recall
    add("roughness", f"{f3(s['A1_recall_5mm']['C3r02']['all']['recall'])}, {f3(s['A1_recall_5mm']['C3r04']['all']['recall'])}")
    add("redraws", f"{f3(red['recall_5mm']['C3redraw1'])}, {f3(red['recall_5mm']['C3redraw2'])}")
    add("redraw spread", f"Spread {red['C3_spread_points']:.1f} points")
    assert red["recall_5mm"]["C3"] == max(red["recall_5mm"][k] for k in ("C3", "C3redraw1", "C3redraw2"))
    add("seeds 0-9", f"Baseline, seeds 0--9 & {f3(amb['recall_5mm']['C3'])} & {f3(amb['recall_5mm']['C4'])}")
    add("ambient", f"Ambient light added & {f3(amb['recall_5mm']['C3amb'])} & {f3(amb['recall_5mm']['C4amb'])}")
    add("filters off", f"All three matcher filters off & {f3(rob['recall_5mm']['C3looselr'])} & {f3(rob['recall_5mm']['C4looselr'])}")
    assert not rob["ranking_flips"]
    add("ambient DN", f"Reaches {amb['ir_appearance']['metal']['obj_dn_median']:.0f}\\,DN")
    # Mechanism
    v = lambda d: d["mean_weighted_px"]  # noqa: E731
    add("blank", f"{v(mech['blank']['part_valid']) * 100:.1f}\\% of part pixels stay valid and only {v(mech['blank']['class_frac']['correct']) * 100:.1f}\\% are correct")
    add("mirror", f"are {v(mech['class_frac_mirror_sees_scene']['correct']) * 100:.1f}\\% correct, others {v(mech['class_frac_mirror_sees_nothing']['correct']) * 100:.1f}\\%")
    assert max(abs(v(x["biased"]["median_slope"])) for k, x in mech["bgshift"].items() if k in ("3", "-3")) < 0.005
    lo, hi = sorted(v(mech["blank_bgshift"][k]["median_slope"]) for k in ("3", "-3"))
    add("blank slope", f"blanked control {lo:.2f}--{hi:.2f}")
    add("between", f"{v(mech['biased_between_surface_and_bg']) * 100:.1f}\\% lie between surface and tray")
    add("no texture", f"to {v(mech['part_frac_no_texture']) * 100:.1f}\\% here")
    add("correct 71", f"{v(mech['class_frac']['correct']) * 100:.1f})")
    p = REPO / "data/m5/mechanism/dev_final.json"
    if p.exists():
        m65 = json.loads(p.read_text())["summary"]
        add("no texture 65", f"from {v(m65['part_frac_no_texture']) * 100:.1f}\\% at 65°")
        add("correct 65", f"({v(m65['class_frac']['correct']) * 100:.1f}, ")
    # ROBI
    q = lambda d: ", ".join(f"$-${abs(d['quantiles_px'][k]):.2f}" for k in ("5", "25", "50")) + "\\,px"  # noqa: E731
    add("ROBI real", q(robi["d415"]))
    add("ROBI C3", q(se["C3"]["parts"]))
    add("ROBI r04", q(se["C3r04"]["parts"]))
    add("ROBI invalid", f"{robi['d415']['invalid_frac'] * 100:.0f}\\% real, {se['C3']['parts']['invalid_frac'] * 100:.1f}\\% in C3")
    add("ROBI SGBM invalid", f"leaves {robi['sgbm']['invalid_frac'] * 100:.0f}\\% invalid")
    add("ROBI appearance", f"{robi['ir_appearance_mean_over_views']['obj_dn_median']:.0f}\\,DN median and {robi['ir_appearance_mean_over_views']['obj_local_sd_median']:.1f}\\,DN local contrast on real parts, against {app['metal']['obj_dn_median']:.0f}\\,DN and {app['metal']['obj_local_sd_median']:.1f}\\,DN")
    add("range", f"({J('hfov71/distance.json')['part_centre_z_m'][0]:.2f}--{J('hfov71/distance.json')['part_centre_z_m'][1]:.2f}\\,m)")
    add("ROBI views", f"{robi['n_views']} ROBI Zigzag views")
    ra, am, at = robi["ir_appearance_mean_over_views"], app["metal"], app["matte"]
    add("background", f"{ra['back_dn_median']:.0f}\\,DN and {ra['back_local_sd_median']:.1f}\\,DN on ROBI, against {am['back_dn_median']:.0f}\\,DN and {am['back_local_sd_median']:.1f}\\,DN here")
    add("matte parts", f"({at['obj_dn_median']:.0f}\\,DN, {at['obj_local_sd_median']:.1f}\\,DN)")
    add("annotation", f"{robi_f * 0.055 * 0.001 / 0.365 ** 2:.2f}\\,px at this range")
    zq = robi["z_gt_mm_quantiles"]
    assert 0.31 < zq["5"] / 1000 and zq["95"] / 1000 < 0.42
    # Camera and plane
    assert abs(intr["K_set"][0][0] - 897.25) < 0.01 and intr["K_blenderproc_max_abs_diff"] < 1e-6 and intr["z_residual_mm"]["max_abs"] < 0.0021
    rows = anchor["rows"][:6] if anchor["rows"][0]["z_m"] == 0.5 else anchor["rows"]
    rows = [r for r in rows if 0.5 <= r["z_m"] <= 1.0]
    add("plane bias", f"within {max(r['bias_rel'] for r in rows) * 100:.2f}\\% of $z$")
    add("plane RMS", f"{min(r['planefit_rms_mm'] for r in rows):.2f}--{max(r['planefit_rms_mm'] for r in rows):.2f}\\,mm")
    add("plane median", f"measured: {anchor['summary']['median_subpixel_rms_px']:.4f}\\,px")
    assert all(r["valid_frac_roi"] == 1.0 for r in rows)
    add("plane band", f"within {max(abs(r['band_measured_px'] - r['band_expected_px']) for r in rows):.1f}\\,px of $B f/z$")
    add("unlit", f"{unlit['image_unlit_share_mean_over_views'] * 100:.1f}\\% of the image, {unlit['part_px_unlit_share'] * 100:.3f}\\% of part pixels")
    # ICP repeat
    rep = J("hfov71/icp_repeat.json")
    ir = rep["conditions"]
    add("ICP repeat row", f"ICP run again on identical depth & {f3(ir['C3']['recall_repeat'])} & {f3(ir['C4']['recall_repeat'])} & No view crosses 5\\,mm in {sum(v['n'] for v in ir.values())} comparisons")
    assert all(v["side_changes"] == 0 for v in ir.values()) and all(f["rejects"] for f in rep["fixed_sequence_repeat"]) and not rep["dirty_tree_any"]
    add("ICP repeat moved", f"at most {max(v['moved_gt_0.01mm'] for v in ir.values())} of {ir['C3']['n']} views")
    add("ICP repeat largest", f"the largest by {max(v['max_abs_d_mssd_mm'] for v in ir.values()):.0f}\\,mm")
    # Error structure
    es = J("hfov71/error_structure.json")
    rc, ag = es["recall_5mm"], es["against_C3"]
    assert not es["dirty_tree_any"] and es["n_instance_views"] == 98
    assert ag["C3sym"]["diff"] == 0 and rc["C3"] == rc["C3sym"]
    add("random signs row", f"random signs & {f3(rc['C3sym'])} & & {signed(ag['C3sym']['diff'])} points ({plain(ag['C3sym']['ci95'][0])} to {signed(ag['C3sym']['ci95'][1])})")
    add("permuted row", f"permuted & {f3(rc['C3shuf'])} & & {signed(ag['C3shuf']['diff'])} points ({signed(ag['C3shuf']['ci95'][0])} to {signed(ag['C3shuf']['ci95'][1])})")
    add("both row", f"Permuted, with random signs & {f3(rc['C3both'])} & & {signed(ag['C3both']['diff'])} points ({signed(ag['C3both']['ci95'][0])} to {signed(ag['C3both']['ci95'][1])})")
    b2 = es["C3both_against_C3shuf"]
    add("both vs permuted", f"{signed(b2['diff'])} points, {plain(b2['ci95'][0])} to {signed(b2['ci95'][1])}")
    add("C1 on these seeds", f"from C1 ({f3(rc['C1'])} on these seeds)")
    add("both vs C3 text", f"gives {f3(rc['C3both'])} against {f3(rc['C3'])} on the same scenes")
    add("C2b > 5 mm", f"{se['C3']['parts']['frac_gt_5mm'] * 100:.1f}\\% of valid pixels beyond 5\\,mm against {se['C2b']['parts']['frac_gt_5mm'] * 100:.1f}\\% in C2b")

    # Descriptive contrast and part-type discordance, from the per-view files
    d = REPO / "data/hfov71/test/results"
    if d.exists():
        sys.path.insert(0, str(REPO / "src"))
        import numpy as np
        from scipy.stats import binomtest
        from synthrgbd.seeds import rng
        from synthrgbd.stats import scene_bootstrap_ci

        rows_of = lambda c: [json.loads(x) for x in (d / f"A_{c}_10.jsonl").read_text().splitlines()[1:]]   # noqa: E731
        good = lambda R: np.array([r.get("mssd_mm") is not None and r["mssd_mm"] < 5 for r in R], bool)   # noqa: E731
        A, B = rows_of("C2b"), rows_of("C4")
        lo, hi = scene_bootstrap_ci(good(A).astype(float) - good(B).astype(float), np.array([r["scene"] for r in A]), 10000, rng(0, 0, 5, "bootstrap"))
        add("C2b-C4", f"{(good(A).mean() - good(B).mean()) * 100:.1f} points below C2b ({lo * 100:.1f} to {hi * 100:.1f}; descriptive)")
        A, B = rows_of("C1"), rows_of("C2a")
        for typ, text in (("profile", "profiles"), ("bracket", "brackets")):
            sel = np.array([r["type"] == typ for r in A])
            a, b = good(A)[sel], good(B)[sel]
            up, down = int((b & ~a).sum()), int((a & ~b).sum())
            add(f"C2a {typ}", f"{text} ({up} " + ("views gained" if typ == "profile" else "gained") + f", {down} " + f"lost, $p={binomtest(up, up + down, 0.5).pvalue:.3f}$)".replace("0.109", "0.11").replace("0.001", "0.001"))

    # Citations: every reference used, none out of range
    import re
    used = {int(n) for group in re.findall(r"\\cte\{([0-9,]+)\}", tex) for n in group.split(",")}
    n_refs = tex[tex.index("section*{References}"):].count("\\item ")
    if used != set(range(1, n_refs + 1)):
        print("CITATION MISMATCH", sorted(set(range(1, n_refs + 1)) - used), sorted(used - set(range(1, n_refs + 1))))
        sys.exit(1)
    print(f"{n_refs} references, all cited")
    if "@@" in tex:
        print("PLACEHOLDER LEFT")
        sys.exit(1)

    missing = [(k, t) for k, t in claims if t not in tex]
    print(f"{len(claims) - len(missing)} of {len(claims)} claims found in {tex_path.name}")
    for k, t in missing:
        print(f"MISSING {k}: {t}")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
