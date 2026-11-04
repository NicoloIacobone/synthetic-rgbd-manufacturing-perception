"""Depth conditions: name -> depth folder inside a BOP scene (uint16, BOP depth scale 0.1 mm, invalid = 0).

C1-C4 are the protocol conditions (PLAN §5.1). The others are descriptive and never enter the fixed sequence:
metal roughness passes (A-51), bright matte (A-52), reflections off (A-57), the loose matcher (§5.8) and noise redraws (A-59).
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
    "C3loose": "depth_stereo_metal_loose",
    "C4loose": "depth_stereo_matte_loose",
    "C3nouniq": "depth_stereo_metal_nouniq",        # one filter off at a time, sensor classes only (§5.8)
    "C3nolr": "depth_stereo_metal_nolr",
    "C3nospeckle": "depth_stereo_metal_nospeckle",
    "C3redraw1": "depth_stereo_metal_redraw1",      # same IR and matcher, independent sensor noise (A-59)
    "C3redraw2": "depth_stereo_metal_redraw2",
}
