"""Report figure for the ROBI comparison, framed as A-65 fixes it: disparity in pixels, invalid pixels and IR appearance.

Usage: .venv/bin/python scripts/fig_robi.py <sensor.json> <ir_appearance.json> <robi_json> --out <png> [--note <text>]

Rows: the real D415 on ROBI Zigzag and our SGBM on its real IR pair; then C3 at roughness 0.15, 0.2 and 0.4 and C4 on our scenes.
(a) signed disparity error d - d_GT in px: dot = median, thick = p25-p75, thin = p5-p95. (b) invalid share of part pixels.
(c) median DN and median 7 x 7 local SD on part pixels of the left image. "Correct within 5 mm" is left out on purpose: 5 mm is about
2.15 px at ROBI's 0.34 m and 0.30 px at 0.9 m here, so it compares different tolerances. Working distances differ: state it in the note.
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.config import load_config  # noqa: E402

INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
REAL, SIM = "#2a78d6", "#eb6834"
DN_COL, SD_COL = "#2a78d6", "#eb6834"


def strip(ax, y, q, col):
    ax.plot([q["5"], q["95"]], [y, y], color=col, lw=1.2, solid_capstyle="round")
    ax.plot([q["25"], q["75"]], [y, y], color=col, lw=4.5, solid_capstyle="round")
    ax.plot(q["50"], y, "o", ms=6.5, color=col, mec="white", mew=1.2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sensor", type=Path)
    ap.add_argument("appearance", type=Path)
    ap.add_argument("robi", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--note")
    args = ap.parse_args()
    se = json.loads(args.sensor.read_text())["conditions"]
    ap_sim = json.loads(args.appearance.read_text())
    r = json.loads(args.robi.read_text())
    ir = load_config(REPO / "configs" / "camera_d415_ir.yaml")
    rough, albedo = ir["materials_metal"]["roughness"], ir["materials_matte"]["part_albedo"]
    name = r["object"].replace("_", " ")
    real_ap = r["ir_appearance_mean_over_views"]
    rows = [(f"ROBI {name}: real D415", r["d415"]["quantiles_px"], r["d415"]["invalid_frac"], real_ap, REAL),
            (f"ROBI {name}: our SGBM, real IR", r["sgbm"]["quantiles_px"], r["sgbm"]["invalid_frac"], real_ap, REAL)]
    for c, p, lab in (("C3", "metal", f"C3 metal, roughness {rough:g}"), ("C3r02", "r02", "metal, roughness 0.2"), ("C3r04", "r04", "metal, roughness 0.4"), ("C4", "matte", f"C4 matte, albedo {albedo:g}")):
        rows.append((lab, se[c]["parts"]["quantiles_px"], se[c]["parts"]["invalid_frac"], ap_sim[p], SIM))
    n = len(rows)
    fig, ax = plt.subplots(1, 3, figsize=(10.8, 0.42 * n + 1.75), constrained_layout=True, sharey=True, gridspec_kw={"width_ratios": [1.1, 0.8, 1.0]})
    for i, (lab, qp, inv, app, col) in enumerate(rows):
        strip(ax[0], i, qp, col)
        ax[1].barh(i, 100 * inv, height=0.5, color=col)
        ax[1].text(100 * inv + 0.8, i, f"{100 * inv:.0f}%" if inv >= 0.095 else f"{100 * inv:.1f}%", va="center", fontsize=8.5, color=INK)
        ax[2].plot(app["obj_dn_median"], i, "o", ms=6.5, color=DN_COL, mec="white", mew=1.2)
        ax[2].plot(app["obj_local_sd_median"], i, "s", ms=6, color=SD_COL, mec="white", mew=1.2)
    ax[0].set_yticks(range(n), [row[0] for row in rows], color=INK)
    ax[0].invert_yaxis()
    ax[0].set_xlim(-4, 4)
    ax[1].set_xlim(0, 32)
    ax[0].set_xlabel("signed disparity error (px)", fontsize=9, color=MUTED)
    ax[1].set_xlabel("invalid part pixels (%)", fontsize=9, color=MUTED)
    ax[2].set_xlabel("left image, part pixels (DN)", fontsize=9, color=MUTED)
    ax[0].set_title("(a) Error in disparity", fontsize=10, loc="left", color=INK)
    ax[1].set_title("(b) Invalid pixels", fontsize=10, loc="left", color=INK)
    ax[2].set_title("(c) IR appearance", fontsize=10, loc="left", color=INK)
    ax[0].axvline(0, color=MUTED, lw=0.8)
    for a in (ax[0], ax[1], ax[2]):
        a.xaxis.grid(True, color=GRID, lw=0.8)
        for s in ("top", "right", "left"):
            a.spines[s].set_visible(False)
        a.spines["bottom"].set_color(MUTED)
        a.tick_params(length=0, labelsize=8.5, colors=MUTED)
        a.tick_params(axis="y", labelcolor=INK)
        a.set_axisbelow(True)
    ax[2].legend(handles=[plt.Line2D([], [], marker="o", ls="", color=DN_COL, label="median DN"), plt.Line2D([], [], marker="s", ls="", color=SD_COL, label="median 7 × 7 local SD")],
                 frameon=False, fontsize=8, ncols=2, loc="upper center", bbox_to_anchor=(0.45, -0.16), handletextpad=0.2, columnspacing=1.0, labelcolor=INK)
    if args.note:
        fig.text(0.01, 0.005, args.note, fontsize=8, color=MUTED, ha="left", va="bottom")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=170, facecolor="white")
    print(args.out)


if __name__ == "__main__":
    main()
