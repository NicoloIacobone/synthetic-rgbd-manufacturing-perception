"""Report figure for the ROBI comparison (A-55): real D415 on metal vs the camera model.

Usage: .venv/bin/python scripts/fig_robi.py <sensor.json> <robi_json>... --out <png> [--note <text>]

Rows: for each ROBI object the D415's own depth and our SGBM on the real IR pair; then C3 at roughness 0.15, 0.2 and 0.4 and C4
on our scenes. (a), (b) signed error z - z_GT in mm and d - d_GT in px: dot = median, thick = p25-p75, thin = p5-p95.
(c) share of object pixels: correct within 5 mm, behind, in front, invalid. Working distances differ: stated in the note.
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
REAL, SIM = "#2a78d6", "#eb6834"
CLASSES = [("correct", "correct, within 5 mm", "#2a78d6"), ("behind", "behind the surface", "#eb6834"), ("in_front", "in front", "#1baf7a"), ("invalid", "invalid", "#eda100")]


def strip(ax, y, q, col):
    ax.plot([q["5"], q["95"]], [y, y], color=col, lw=1.2, solid_capstyle="round")
    ax.plot([q["25"], q["75"]], [y, y], color=col, lw=4.5, solid_capstyle="round")
    ax.plot(q["50"], y, "o", ms=6.5, color=col, mec="white", mew=1.2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sensor", type=Path)
    ap.add_argument("robi", type=Path, nargs="+")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--note")
    args = ap.parse_args()
    se = json.loads(args.sensor.read_text())["conditions"]
    rows = []
    for f in args.robi:
        r = json.loads(f.read_text())
        name = r["object"].replace("_", " ")
        for key, lab in (("d415", f"ROBI {name}: real D415"), ("sgbm", f"ROBI {name}: our SGBM, real IR")):
            rows.append((lab, r[key]["quantiles_mm"], r[key]["quantiles_px"], r[key]["classes"], REAL))
    for c, lab in (("C3", "C3 metal, roughness 0.15"), ("C3r02", "metal, roughness 0.2"), ("C3r04", "metal, roughness 0.4"), ("C4", "C4 matte, albedo 0.247")):
        p, cl = se[c]["parts"], se[c]["classes"]
        rows.append((lab, p["quantiles_mm"], p["quantiles_px"], {"correct": cl["correct"], "behind": cl["towards_bg"] + cl["beyond_bg"], "in_front": cl["in_front"], "invalid": cl["invalid"]}, SIM))
    n = len(rows)
    fig, ax = plt.subplots(1, 3, figsize=(10.8, 0.42 * n + 1.55), constrained_layout=True, sharey=True, gridspec_kw={"width_ratios": [1, 1, 1.05]})
    for i, (lab, qm, qp, cl, col) in enumerate(rows):
        strip(ax[0], i, qm, col)
        strip(ax[1], i, qp, col)
        left = 0.0
        for key, _, c in CLASSES:
            w = cl.get(key, 0.0)
            ax[2].barh(i, w, left=left, height=0.62, color=c, edgecolor="white", linewidth=1.2)
            if w >= 0.1:
                ax[2].text(left + w / 2, i, f"{100 * w:.0f}", ha="center", va="center", fontsize=8, color="white" if c in ("#2a78d6", "#eb6834") else INK)
            left += w
    ax[0].set_yticks(range(n), [r[0] for r in rows], color=INK)
    ax[0].invert_yaxis()
    ax[0].set_xlim(-15, 40)
    ax[1].set_xlim(-4, 4)
    ax[2].set_xlim(0, 1)
    ax[2].set_xticks([0, 0.25, 0.5, 0.75, 1], ["0", "25", "50", "75", "100%"])
    ax[0].set_xlabel("signed depth error (mm)", fontsize=9, color=MUTED)
    ax[1].set_xlabel("signed disparity error (px)", fontsize=9, color=MUTED)
    ax[0].set_title("(a) Error in depth", fontsize=10, loc="left", color=INK)
    ax[1].set_title("(b) Error in disparity", fontsize=10, loc="left", color=INK)
    ax[2].set_title("(c) Metal-part pixels", fontsize=10, loc="left", color=INK)
    for a in ax[:2]:
        a.axvline(0, color=MUTED, lw=0.8)
        a.xaxis.grid(True, color=GRID, lw=0.8)
    for a in ax:
        for s in ("top", "right", "left"):
            a.spines[s].set_visible(False)
        a.spines["bottom"].set_color(MUTED)
        a.tick_params(length=0, labelsize=8.5, colors=MUTED)
        a.tick_params(axis="y", labelcolor=INK)
        a.set_axisbelow(True)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in CLASSES]
    ax[2].legend(handles, [c[1] for c in CLASSES], frameon=False, fontsize=8, ncols=2, loc="upper center", bbox_to_anchor=(0.45, -0.13), handlelength=1.0, columnspacing=1.0, labelcolor=INK)
    if args.note:
        ax[0].annotate(args.note, xy=(0, -0.18), xycoords="axes fraction", fontsize=8, color=MUTED, ha="left", va="top")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=170, facecolor="white")
    print(args.out)


if __name__ == "__main__":
    main()
