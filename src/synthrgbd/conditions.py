"""Depth conditions: name -> depth folder inside a BOP scene (uint16, BOP depth scale 0.1 mm, invalid = 0).

C1-C4 are the protocol conditions (PLAN §5.1). The others are descriptive and never enter the fixed sequence:
metal roughness passes (A-51), bright matte (A-52), reflections off (A-57), the loose matcher (§5.8, A-63), noise redraws (A-59),
the lower sensor noise (A-64), the ambient-IR test (A-70), the error structure check (A-73) and the dot-density test (A-74).
"""

DEPTH_SCALE_MM = 0.1

PROTOCOL_CONDITIONS = ("C1", "C2a", "C2b", "C3", "C4")

DEPTH_DIRS = {
    "C1": "depth",
    "C2a": "depth_c2a",
    "C2b": "depth_c2b",
    "C3": "depth_stereo_metal",
    "C4": "depth_stereo_matte",
    "C3r02": "depth_stereo_r02",
    "C3r04": "depth_stereo_r04",
    "C3nogloss": "depth_stereo_nogloss",
    "C4bright": "depth_stereo_bright",
    "C3loose": "depth_stereo_metal_loose",          # first §5.8 run: the left-right check stayed on (A-63)
    "C4loose": "depth_stereo_matte_loose",
    "C3looselr": "depth_stereo_metal_looselr",      # §5.8 as defined: all three filters off (A-63)
    "C4looselr": "depth_stereo_matte_looselr",
    "C3nouniq": "depth_stereo_metal_nouniq",        # one filter off at a time, sensor classes only (§5.8)
    "C3nolr": "depth_stereo_metal_nolr",            # identical to C3: -1 leaves the check on (A-63)
    "C3nolr1000": "depth_stereo_metal_nolr1000",
    "C3nospeckle": "depth_stereo_metal_nospeckle",
    "C3redraw1": "depth_stereo_metal_redraw1",      # same IR and matcher, independent sensor noise (A-59)
    "C3redraw2": "depth_stereo_metal_redraw2",
    "C3e1": "depth_stereo_metal_e1",                # e_per_dn 1 instead of 0.087: lower sensor noise (A-64)
    "C4e1": "depth_stereo_matte_e1",
    "C3amb": "depth_stereo_metal_amb",              # projector + ambient light, one level (A-70)
    "C4amb": "depth_stereo_matte_amb",
    "C3shuf": "depth_stereo_metal_shuf",            # C3 with each part's errors permuted among its pixels (A-73)
    "C3sym": "depth_stereo_metal_sym",              # C3 with each error's sign random (A-73)
    "C3both": "depth_stereo_metal_both",            # both: independent zero-mean noise of the part's own error sizes (A-73)
    "C3dots10k": "depth_stereo_metal_dots10000",    # 10 000 dots instead of 30 000, new render (A-74)
    "C4dots10k": "depth_stereo_matte_dots10000",
}
