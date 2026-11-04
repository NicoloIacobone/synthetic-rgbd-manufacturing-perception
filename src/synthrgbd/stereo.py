"""Own stereo matching for the active-stereo camera model (D13), run in .venv with OpenCV.

Pipeline: linear IR radiance (float, unclipped, A-32) -> exposure + 8-bit quantisation (OpenCV SGBM
accepts only 8-bit, A-40) -> StereoSGBM on left/right images that both extend `pad` px to the left
of the D415 image (cx + pad, same f) -> crop -> invalidate (no match, d > 126 px, x - d < 0) ->
z = f B / d. Invalid pixels are 0 in disparity and depth (RealSense convention, S-03).

Left-band fix (A-40): plain SGBM invalidates the first num_disparities columns whatever the depth.
With the extended images every left pixel x of the D415 image has the full search range; a
pixel is then invalid only if its match x - d would fall outside the real right sensor (x - d < 0),
so the invalid left band has width B f / Z as on the D415 (S-01 §4.5).
"""

import cv2
import numpy as np

from synthrgbd.geometry import disparity_to_depth, sgbm_raw_to_disparity

_MODES = {"SGBM": cv2.STEREO_SGBM_MODE_SGBM, "HH": cv2.STEREO_SGBM_MODE_HH,
          "SGBM_3WAY": cv2.STEREO_SGBM_MODE_SGBM_3WAY}


def expose_to_uint8(radiance: np.ndarray, gain: float) -> np.ndarray:
    """Fixed linear exposure: DN = clip(round(gain * L), 0, 255). Saturation happens only here."""
    return np.clip(np.rint(np.asarray(radiance, np.float64) * gain), 0, 255).astype(np.uint8)


def exposure_roi_x0(fx: float, baseline_m: float, z_min_m: float) -> int:
    """First column of the auto-exposure ROI (A-42): right of the widest invalid left band, f·B/Z at Min-Z."""
    return int(np.ceil(fx * baseline_m / z_min_m))


def auto_exposure_gain(left_radiance: np.ndarray, x0: int, setpoint_dn: float) -> float:
    """Per-frame auto exposure (A-42): gain such that the mean DN over columns >= x0 of the D415 left image
    (radiance, unpadded, before noise) equals setpoint_dn. Computed on the C3 (metal) left image and shared
    with C4 and the right image."""
    m = float(np.mean(np.asarray(left_radiance, np.float64)[:, x0:]))
    if m <= 0:
        raise ValueError("left image has no signal in the auto-exposure ROI")
    return setpoint_dn / m


def add_sensor_noise(dn: np.ndarray, z: np.ndarray, e_per_dn: float, read_noise_dn: float) -> np.ndarray:
    """Shot + read noise on an exposed image in DN (float, before clipping and quantisation, A-12):
    DN + sqrt(max(DN, 0) / e_per_dn + read_noise_dn^2) · z, with z ~ N(0, 1) drawn once per frame and
    image and **shared by C3 and C4** (A-29). e_per_dn = electrons per DN (conversion gain)."""
    dn = np.asarray(dn, np.float64)
    return dn + np.sqrt(np.maximum(dn, 0.0) / e_per_dn + read_noise_dn ** 2) * z


def quantise_uint8(dn: np.ndarray) -> np.ndarray:
    """Clip to [0, 255] and round to 8 bits (SGBM input, A-40). Saturation happens only here."""
    return np.clip(np.rint(dn), 0, 255).astype(np.uint8)


def exposed_pair_uint8(L: np.ndarray, R: np.ndarray, gain: float, noise_cfg: dict | None,
                       z_left: np.ndarray | None, z_right: np.ndarray | None) -> tuple[np.ndarray, np.ndarray]:
    """Linear radiance pair -> exposed DN -> (shot + read noise with the given standard-normal draws) -> 8 bit."""
    out = []
    for img, z in ((L, z_left), (R, z_right)):
        dn = np.asarray(img, np.float64) * gain
        if noise_cfg is not None and noise_cfg.get("e_per_dn") is not None:
            dn = add_sensor_noise(dn, z, noise_cfg["e_per_dn"], noise_cfg["read_noise_dn"])
        out.append(quantise_uint8(dn))
    return out[0], out[1]


def make_sgbm(cfg: dict) -> cv2.StereoSGBM:
    """StereoSGBM from the `sgbm` section of configs/camera_d415_ir.yaml."""
    b = cfg["block_size"]
    return cv2.StereoSGBM_create(
        minDisparity=cfg["min_disparity"], numDisparities=cfg["num_disparities"], blockSize=b,
        P1=cfg["p1_per_px"] * b * b, P2=cfg["p2_per_px"] * b * b, disp12MaxDiff=cfg["disp12_max_diff"],
        preFilterCap=cfg["pre_filter_cap"], uniquenessRatio=cfg["uniqueness_ratio"],
        speckleWindowSize=cfg["speckle_window_size"], speckleRange=cfg["speckle_range"],
        mode=_MODES[cfg["mode"]])


def pad_left(img: np.ndarray, pad: int) -> np.ndarray:
    """Zero-pad `pad` columns on the left (for a left image rendered at the D415 width only)."""
    return np.pad(img, ((0, 0), (pad, 0)))


def match_extended(left_ext: np.ndarray, right_ext: np.ndarray, pad: int, matcher: cv2.StereoSGBM,
                   max_disparity_px: float) -> np.ndarray:
    """Disparity (px, float64) of the D415 left image from 8-bit images extended by `pad` columns on
    the left. Returns an array of width W = left_ext.shape[1] - pad; invalid = 0.

    Invalid: SGBM gave no disparity (raw < min_disparity*16), d > max_disparity_px (126, A-25),
    or x - d < 0 (match outside the real right sensor, A-40)."""
    if left_ext.dtype != np.uint8 or right_ext.dtype != np.uint8:
        raise TypeError("SGBM input must be 8-bit (expose_to_uint8 first)")
    if left_ext.shape != right_ext.shape:
        raise ValueError(f"left {left_ext.shape} and right {right_ext.shape} must have the same shape")
    if pad < matcher.getNumDisparities() + matcher.getMinDisparity():
        raise ValueError("pad must be >= min_disparity + num_disparities, or the left band stays 128 px")
    raw = matcher.compute(left_ext, right_ext)[:, pad:]
    d = sgbm_raw_to_disparity(raw)
    valid = raw >= matcher.getMinDisparity() * 16
    valid &= d <= max_disparity_px
    x = np.arange(d.shape[1])[None, :]
    valid &= (x - d) >= 0
    d[~valid] = 0.0
    return d


def depth_from_ir(left_rad: np.ndarray, right_rad: np.ndarray, gain: float, pad: int, matcher: cv2.StereoSGBM,
                  fx: float, baseline_m: float, max_disparity_px: float) -> tuple[np.ndarray, np.ndarray]:
    """Linear IR pair (both extended by `pad`) -> (depth m, disparity px) of the D415 left image."""
    d = match_extended(expose_to_uint8(left_rad, gain), expose_to_uint8(right_rad, gain), pad, matcher,
                       max_disparity_px)
    return disparity_to_depth(d, fx, baseline_m, max_disparity_px), d


def first_valid_column(valid: np.ndarray) -> np.ndarray:
    """Per row, index of the first valid column (W if the row has none)."""
    has = valid.any(axis=1)
    return np.where(has, valid.argmax(axis=1), valid.shape[1])
