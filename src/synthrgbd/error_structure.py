"""Surrogates of a stereo depth map that keep part of its error and remove the rest (A-73).

For one part's visible mask, on the pixels valid in both maps, the error e = z - z_true is either permuted among those pixels ("shuffle":
same distribution, including bias and tail; no spatial coherence) or has its sign flipped with probability 1/2 ("sign": same magnitudes;
no one-sidedness, no coherence). Invalid pixels (0) and pixels outside the mask are not touched. Depth stays in the integer units of the input.
"""

import numpy as np

MODES = ("shuffle", "sign")


def scramble_errors(z: np.ndarray, z_true: np.ndarray, mask: np.ndarray, rng: np.random.Generator, mode: str) -> np.ndarray:
    """Copy of z with the errors on the valid pixels of mask replaced as described above; results are clipped to 1..65535."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    out = z.copy()
    sel = mask & (z > 0) & (z_true > 0)
    e = z[sel].astype(np.int64) - z_true[sel].astype(np.int64)
    e = rng.permutation(e) if mode == "shuffle" else e * rng.choice(np.array([-1, 1]), size=e.size)
    out[sel] = np.clip(z_true[sel].astype(np.int64) + e, 1, 65535).astype(z.dtype)
    return out
