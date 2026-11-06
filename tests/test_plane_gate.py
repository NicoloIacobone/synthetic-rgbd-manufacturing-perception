"""Plane gate at 71 degrees (A-67) and stop rules of the final run (ledger "Final-run stop rules")."""

import numpy as np
import pytest

from synthrgbd.config import REPO_ROOT, load_config
from synthrgbd.geometry import intrinsics_from_hfov
from synthrgbd.plane_gate import gate_roi, gate_verdict, lit_left_column, roi_rows
from synthrgbd.stop_rules import check_ambient, check_primary, check_redraw, check_s58

CAM = load_config()["camera"]
IR = load_config(REPO_ROOT / "configs" / "camera_d415_ir.yaml")
GC = IR["plane_gate"]
K = intrinsics_from_hfov(CAM["width"], CAM["height"], CAM["hfov_deg"])
FX, CX, B = K[0, 0], K[0, 2], CAM["baseline_m"]


def lit(z):
    return lit_left_column(FX, CX, IR["projector"]["position_x_m"], IR["projector"]["fov_deg"][0], z)


def good_rows():
    rows = []
    for z in sorted(set(GC["gate_z_m"]) | set(GC["minz_z_m"])):
        d = FX * B / z
        rows.append({"z_m": z, "valid_frac_roi": 1.0 if d <= 126 else 0.03, "band_measured_px": max(d, lit(z)), "bias_rel": 0.002})
    return rows


def set_row(rows, z, **kw):
    next(r for r in rows if r["z_m"] == z).update(kw)
    return rows


def test_lit_edge_and_band_as_predeclared():
    assert [round(lit(z), 1) for z in GC["lit_z_m"]] == [86.7, 80.9, 76.5, 73.0, 70.3]
    assert FX * B / 0.70 == pytest.approx(70.5, abs=0.05)
    for z in GC["band_z_m"]:
        assert FX * B / z > lit(z)      # the old band test is only meaningful where the band exceeds the lit edge
    for z in GC["lit_z_m"]:
        assert lit(z) > FX * B / z
    # From 0.7 m up the lit edge is more than 10% past the band. That was the reason for (iv'). Measured on the planes, the matcher fills
    # the unlit strip, so the first valid column stays at the band and A-38 (iv) as written would in fact have passed (A-67).
    assert all(abs(lit(z) - FX * B / z) > 0.1 * FX * B / z for z in (0.7, 0.8, 0.9, 1.0))


def test_gate_roi_is_lit_on_every_plane():
    roi = gate_roi(1280, 720, 0.0, 3, GC["roi_frac"])
    cols, rows = np.nonzero(roi.any(0))[0], np.nonzero(roi.any(1))[0]
    assert (cols[0], cols[-1], rows[0], rows[-1]) == (128, 1151, 72, 647)
    assert roi_rows(720, GC["roi_frac"]) == (72, 648)
    assert max(lit(z) for z in GC["gate_z_m"] + GC["minz_z_m"]) < cols[0]    # left lit edge at most 112 px
    near = gate_roi(1280, 720, FX * B / 0.37, 3, GC["roi_frac"])             # the band still cuts the ROI on the nearest plane
    assert np.nonzero(near.any(0))[0][0] == int(np.ceil(FX * B / 0.37)) + 3


def test_verdict_pass_marginal_and_stop():
    v = gate_verdict(good_rows(), GC, FX, B, lit)
    assert not v["stop"] and not v["marginal_iii"] and v["iii_invalid_side_strict"]
    v = gate_verdict(set_row(good_rows(), 0.38, valid_frac_roi=0.06), GC, FX, B, lit)    # the known marginal failure
    assert v["marginal_iii"] and not v["iii_invalid_side_strict"] and not v["stop"]
    assert gate_verdict(set_row(good_rows(), 0.37, valid_frac_roi=0.11), GC, FX, B, lit)["stop"]
    assert gate_verdict(set_row(good_rows(), 0.40, valid_frac_roi=0.90), GC, FX, B, lit)["stop"]
    assert gate_verdict(set_row(good_rows(), 0.70, valid_frac_roi=0.94), GC, FX, B, lit)["stop"]
    assert gate_verdict(set_row(good_rows(), 0.60, bias_rel=0.011), GC, FX, B, lit)["stop"]
    assert gate_verdict(set_row(good_rows(), 0.45, band_measured_px=100.0 * 1.3), GC, FX, B, lit)["stop"]    # band off by > 10%
    assert gate_verdict(set_row(good_rows(), 1.00, band_measured_px=40.0), GC, FX, B, lit)["stop"]           # before the band
    assert gate_verdict(set_row(good_rows(), 1.00, band_measured_px=90.0), GC, FX, B, lit)["stop"]           # past the lit edge


def stats(c1=0.7, c2a=0.7, c2b=0.5, c3=0.1, c4=0.3, rejects=(True, True, True)):
    seq = [{"a": a, "b": b, "diff": 0.1, "ci95": [0.05, 0.2], "p": 1e-3, "test_rejects": r} for (a, b), r in zip((("C1", "C3"), ("C2b", "C3"), ("C3", "C4")), rejects)]
    return {"fixed_sequence": seq, "A1_recall_5mm": {k: {"all": {"recall": v}} for k, v in dict(C1=c1, C2a=c2a, C2b=c2b, C3=c3, C4=c4).items()}}


def test_primary_stop_rule():
    assert check_primary(stats()) == []
    assert len(check_primary(stats(rejects=(True, False, True)))) == 1
    assert check_primary(stats(c3=0.31))                # C3 passes C4
    assert check_primary(stats(c4=0.55))                # C4 passes C2b
    assert check_primary(stats(c2a=0.45))               # C2b passes C2a
    assert check_primary(stats(c1=0.8, c2a=0.75)) == []  # C1 and C2a count as tied, in either order
    assert check_primary(stats(c1=0.75, c2a=0.8)) == []


def test_other_stop_rules():
    assert check_s58({"pairs": [{"a": "C1", "b": "C3", "strict": 0.5, "loose": 0.5, "flip": False}]}) == []
    assert check_s58({"pairs": [{"a": "C3", "b": "C4", "strict": -0.2, "loose": 0.1, "flip": True}]})
    assert check_redraw({"recall_5mm": {"C3": 0.1, "C3redraw1": 0.12, "C3redraw2": 0.09, "C4": 0.3}}) == []
    assert check_redraw({"recall_5mm": {"C3": 0.1, "C3redraw1": 0.3, "C3redraw2": 0.09, "C4": 0.3}})
    base = {"C2b": 0.5, "C3": 0.1, "C4": 0.3}
    assert check_ambient({"recall_5mm": {**base, "C3amb": 0.2, "C4amb": 0.4}}) == []
    assert check_ambient({"recall_5mm": {**base, "C3amb": 0.4, "C4amb": 0.4}})
    assert check_ambient({"recall_5mm": {**base, "C3amb": 0.5, "C4amb": 0.6}})
