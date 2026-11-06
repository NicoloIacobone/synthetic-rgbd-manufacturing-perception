"""Plane gate at the imager focal length (A-67): ROI, lit edge and verdict, shared by scripts/plane_gate.py and scripts/anchor_a.py.

At 71 degrees the imager is wider than the 67 x 41 degree projector, so the image has unlit margins (A-36). A-38 (ii) and (iv)
as written would measure those margins rather than the matcher, and A-38 (iii) would fail by construction. Criteria: A-67.
"""

import numpy as np


def lit_left_column(fx: float, cx: float, proj_offset_x: float, proj_hfov_deg: float, z_m: float) -> float:
    """First lit column of the left image on a fronto-parallel plane at z (projector at the baseline midpoint, A-41)."""
    return cx + fx * (proj_offset_x / z_m - np.tan(np.deg2rad(proj_hfov_deg) / 2))


def roi_rows(height: int, frac: float) -> tuple[int, int]:
    y0 = int(round((1 - frac) / 2 * height))
    return y0, height - y0


def gate_roi(width: int, height: int, band_px: float, half_window: int, frac: float) -> np.ndarray:
    """Central `frac` of width and height, minus the band f B / z and a border of half the matching window."""
    x0 = int(round((1 - frac) / 2 * width))
    y0, y1 = roi_rows(height, frac)
    roi = np.zeros((height, width), bool)
    roi[max(y0, half_window):min(y1, height - half_window), max(x0, int(np.ceil(band_px)) + half_window):min(width - x0, width - half_window)] = True
    return roi


def gate_verdict(rows: list[dict], gc: dict, fx: float, baseline_m: float, lit_edge) -> dict:
    """A-67 criteria from per-plane rows (z_m, valid_frac_roi, band_measured_px and, on the gate planes, bias_rel).
    lit_edge(z) gives the predicted first lit column. `stop` is True when the run must stop and ask the user."""
    by_z = {round(r["z_m"], 2): r for r in rows}
    band = lambda z: fx * baseline_m / z   # noqa: E731
    tol = gc["band_tol"]
    i_bias = all(by_z[z]["bias_rel"] < gc["bias_max"] for z in gc["gate_z_m"])
    ii_valid = all(by_z[z]["valid_frac_roi"] >= gc["valid_min"] for z in gc["gate_z_m"])
    iv_band = all(abs(by_z[z]["band_measured_px"] - band(z)) <= tol * band(z) for z in gc["band_z_m"])
    iv_lit = all((1 - tol) * band(z) <= by_z[z]["band_measured_px"] <= (1 + tol) * max(band(z), lit_edge(z)) for z in gc["lit_z_m"])
    iii_valid = all(by_z[z]["valid_frac_roi"] >= gc["minz_valid_min"] for z in gc["minz_valid_z_m"])
    low = [by_z[z]["valid_frac_roi"] for z in gc["minz_invalid_z_m"]]
    iii_strict = max(low) <= gc["minz_invalid_max"]
    iii_within_stop = max(low) <= gc["minz_invalid_stop"]
    return {"i_bias": bool(i_bias), "ii_valid": bool(ii_valid), "iv_band": bool(iv_band), "iv_lit": bool(iv_lit), "iii_valid_side": bool(iii_valid),
            "iii_invalid_side_strict": bool(iii_strict), "iii_invalid_side_within_stop_limit": bool(iii_within_stop),
            "marginal_iii": bool(iii_valid and iii_within_stop and not iii_strict),
            "stop": not (i_bias and ii_valid and iv_band and iv_lit and iii_valid and iii_within_stop)}
