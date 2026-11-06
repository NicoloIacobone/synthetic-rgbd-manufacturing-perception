"""Report figure for the experiment results (static, for the PDF).

Usage: .venv/bin/python scripts/fig_results.py <stats.json> <sensor.json> <distance.json> --out <png>

(a) A1 recall@5 mm with the 95% scene-bootstrap CI: protocol conditions, then the descriptive passes in grey.
(b) Recall@5 mm against the initial offset for the protocol conditions (offset = n mm and n degrees, A-30).
(c) What the depth does on part pixels: correct (within 5 mm), behind the surface up to the tray, in front, invalid.
(d) Recall@5 mm by part distance at 10 mm / 10 deg (open item 34, scripts/distance_table.py).
Colours: the categorical order of the dataviz reference palette, in a fixed order; text stays in neutral ink. Noise levels and
albedo come from the configs, so the labels cannot go stale.
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
SLOTS = {"C1": "#2a78d6", "C2a": "#eb6834", "C2b": "#1baf7a", "C3": "#eda100", "C4": "#e87ba4"}
DESCRIPTIVE = "#8a8983"
ORDER = ["C1", "C2a", "C2b", "C3", "C4", "C4bright", "C3r04", "C3r02", "C3nogloss"]
CLASS_ORDER = [("correct", "correct, within 5 mm", "#2a78d6"), ("towards_bg", "behind the surface, up to the tray", "#eb6834"),
               ("in_front", "in front of the surface", "#1baf7a"), ("invalid", "invalid", "#eda100")]


def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=MUTED, length=0, labelsize=8.5)
    ax.set_axisbelow(True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stats", type=Path)
    ap.add_argument("sensor", type=Path)
    ap.add_argument("distance", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    st = json.loads(args.stats.read_text())
    se = json.loads(args.sensor.read_text())["conditions"]
    dist = json.loads(args.distance.read_text())
    noise = load_config()["noise"]
    ir = load_config(REPO / "configs" / "camera_d415_ir.yaml")
    rough, albedo = ir["materials_metal"]["roughness"], ir["materials_matte"]["part_albedo"]
    labels = {"C1": "C1 ideal depth", "C2a": f"C2a noise, {noise['c2a_eps_d_px']:g} px", "C2b": f"C2b noise, {noise['c2b_eps_d_px']:g} px", "C3": "C3 metal (camera model)",
              "C4": "C4 matte, matched", "C4bright": "matte, albedo 0.5", "C3r04": "metal, roughness 0.4", "C3r02": "metal, roughness 0.2", "C3nogloss": "metal, reflections off"}
    short = {"C3": f"C3 metal, roughness {rough:g}", "C4": f"C4 matte, albedo {albedo:g}", "C4bright": "matte, albedo 0.5", "C3r04": "metal, roughness 0.4", "C3r02": "metal, roughness 0.2",
             "C3nogloss": "metal, reflections off"}
    fig, ax = plt.subplots(2, 2, figsize=(11.2, 7.0), constrained_layout=True, gridspec_kw={"width_ratios": [1.15, 1.0]})
    protocol = ("C1", "C2a", "C2b", "C3", "C4")

    a = ax[0, 0]
    conds = [c for c in ORDER if c in st["A1_recall_5mm"]]
    for i, c in enumerate(conds):
        r = st["A1_recall_5mm"][c]["all"]
        col = SLOTS.get(c, DESCRIPTIVE)
        a.plot(r["ci95"], [i, i], color=col, lw=2, solid_capstyle="round")
        a.plot(r["recall"], i, "o", ms=7, color=col, mec="white", mew=1.2)
        a.text(r["ci95"][1] + 0.025, i, f"{r['recall']:.3f}", va="center", fontsize=8.5, color=INK)
    a.set_yticks(range(len(conds)), [labels[c] for c in conds], color=INK)
    a.invert_yaxis()
    a.set_xlim(0, 1.04)
    a.xaxis.grid(True, color=GRID, lw=0.8)
    a.set_xlabel("recall at MSSD < 5 mm (10 mm / 10°)", fontsize=9, color=MUTED)
    a.set_title("(a) Primary endpoint, 95% CI over scenes", fontsize=10, color=INK, loc="left")
    style(a)
    a.tick_params(axis="y", labelcolor=INK)

    b = ax[0, 1]
    offs = ["2", "5", "10", "20"]
    for c in protocol:
        if c not in st["sweep_recall_5mm"]:
            continue
        ys = [st["sweep_recall_5mm"][c][o]["recall"] for o in offs if o in st["sweep_recall_5mm"][c]]
        b.plot([int(o) for o in offs][:len(ys)], ys, "-o", color=SLOTS[c], lw=2, ms=4.5, mec="white", mew=0.8, label=c)
    b.set_xticks([2, 5, 10, 20])
    b.set_ylim(0, 1.02)
    b.yaxis.grid(True, color=GRID, lw=0.8)
    b.set_xlabel("initial offset (mm and °)", fontsize=9, color=MUTED)
    b.set_ylabel("recall at MSSD < 5 mm", fontsize=9, color=MUTED)
    b.set_title("(b) Offset sweep", fontsize=10, color=INK, loc="left")
    b.legend(frameon=False, fontsize=8.5, ncols=5, loc="upper center", bbox_to_anchor=(0.5, -0.17), labelcolor=INK, handlelength=1.4, columnspacing=1.0)
    style(b)

    d = ax[1, 0]
    rows = [c for c in ("C4bright", "C4", "C3r04", "C3r02", "C3", "C3nogloss") if c in se]
    for i, c in enumerate(rows):
        left = 0.0
        cl = se[c]["classes"]
        for key, _, col in CLASS_ORDER:
            w = cl.get(key, 0.0) + (cl.get("beyond_bg", 0.0) if key == "towards_bg" else 0.0)
            d.barh(i, w, left=left, height=0.62, color=col, edgecolor="white", linewidth=1.2)
            if w >= 0.09:
                d.text(left + w / 2, i, f"{100 * w:.0f}", ha="center", va="center", fontsize=8, color="white" if col in ("#2a78d6", "#eb6834") else INK)
            left += w
    d.set_yticks(range(len(rows)), [short[c] for c in rows], color=INK)
    d.invert_yaxis()
    d.set_xlim(0, 1)
    d.set_xticks([0, 0.25, 0.5, 0.75, 1], ["0", "25", "50", "75", "100%"])
    d.set_title("(c) Depth on part pixels", fontsize=10, color=INK, loc="left")
    handles = [plt.Rectangle((0, 0), 1, 1, color=col) for _, _, col in CLASS_ORDER]
    d.legend(handles, [lab for _, lab, _ in CLASS_ORDER], frameon=False, fontsize=8, ncols=2, loc="upper center", bbox_to_anchor=(0.32, -0.08), labelcolor=INK, handlelength=1.0, columnspacing=1.0)
    style(d)
    d.tick_params(axis="y", labelcolor=INK)

    e = ax[1, 1]
    bands = dist["bands"]
    for c in protocol:
        v = dist["conditions"][c]
        e.plot(range(len(bands)), [b_["recall"] for b_ in v], "-o", color=SLOTS[c], lw=2, ms=4.5, mec="white", mew=0.8, label=c)
    ns = [b_["n"] for b_ in dist["conditions"]["C1"]]
    e.set_xticks(range(len(bands)), [f"{b_.replace('>=', '≥')}\nn = {n}" for b_, n in zip(bands, ns)])
    e.set_xlim(-0.2, len(bands) - 0.8)
    e.set_ylim(0, 1.02)
    e.yaxis.grid(True, color=GRID, lw=0.8)
    e.set_xlabel("distance of the part from the camera", fontsize=9, color=MUTED)
    e.set_ylabel("recall at MSSD < 5 mm", fontsize=9, color=MUTED)
    e.set_title("(d) By part distance, 10 mm / 10°", fontsize=10, color=INK, loc="left")
    e.legend(frameon=False, fontsize=8.5, ncols=5, loc="upper center", bbox_to_anchor=(0.5, -0.22), labelcolor=INK, handlelength=1.4, columnspacing=1.0)
    style(e)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=170, facecolor="white")
    print(args.out)


if __name__ == "__main__":
    main()
