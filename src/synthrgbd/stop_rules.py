"""Stop rules of the final run (ledger "Final-run stop rules", A-66, A-70). Each function returns the reasons to stop; empty = go on."""

SEQUENCE = (("C1", "C3"), ("C2b", "C3"), ("C3", "C4"))


def check_primary(stats: dict) -> list[str]:
    """Fixed sequence and the order of the point estimates at the primary offset. C1 and C2a count as tied."""
    why = [f"{r['a']} vs {r['b']} does not reject (diff {r['diff']:+.3f}, CI {r['ci95']}, p {r['p']:.3g})"
           for r in stats["fixed_sequence"] if not r["test_rejects"]]
    rec = {c: v["all"]["recall"] for c, v in stats["A1_recall_5mm"].items()}
    if not min(rec["C1"], rec["C2a"]) > rec["C2b"]:
        why.append(f"ranking: C2b {rec['C2b']:.3f} reaches C1 {rec['C1']:.3f} or C2a {rec['C2a']:.3f}")
    if not rec["C2b"] > rec["C4"]:
        why.append(f"ranking: C4 {rec['C4']:.3f} reaches C2b {rec['C2b']:.3f}")
    if not rec["C4"] > rec["C3"]:
        why.append(f"ranking: C3 {rec['C3']:.3f} reaches C4 {rec['C4']:.3f}")
    return why


def check_s58(robustness: dict) -> list[str]:
    return [f"§5.8 flip: {p['a']}-{p['b']} strict {p['strict']:+.3f}, loose {p['loose']:+.3f}" for p in robustness["pairs"] if p["flip"]]


def check_redraw(summary: dict) -> list[str]:
    c4 = summary["recall_5mm"]["C4"]
    return [f"noise redraw: {c} {r:.3f} reaches C4 {c4:.3f}" for c, r in summary["recall_5mm"].items() if c.startswith("C3") and r >= c4]


def check_ambient(summary: dict) -> list[str]:
    rec = summary["recall_5mm"]
    why = []
    if rec["C3amb"] >= rec["C4amb"]:
        why.append(f"ambient: C3amb {rec['C3amb']:.3f} reaches C4amb {rec['C4amb']:.3f}")
    if rec["C3amb"] >= rec["C2b"]:
        why.append(f"ambient: C3amb {rec['C3amb']:.3f} reaches C2b {rec['C2b']:.3f} on the same seeds")
    return why
