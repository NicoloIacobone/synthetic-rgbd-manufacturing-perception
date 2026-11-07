"""Paired statistics for the experiment (PLAN §5.5, §5.12): scene bootstrap, exact McNemar, fixed sequence, MDE."""

import numpy as np
from scipy.stats import binomtest


def scene_totals(values: np.ndarray, scenes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-scene sum of `values` and per-scene number of instance-views, in sorted scene order."""
    uniq, inv = np.unique(scenes, return_inverse=True)
    return np.bincount(inv, weights=np.asarray(values, np.float64), minlength=len(uniq)), np.bincount(inv, minlength=len(uniq)).astype(np.float64)


def _resample_means(sums: np.ndarray, counts: np.ndarray, n_resamples: int, rng: np.random.Generator) -> np.ndarray:
    k = len(sums)
    w = rng.multinomial(k, np.full(k, 1.0 / k), size=n_resamples).astype(np.float64)
    den = w @ counts
    return np.divide(w @ sums, den, out=np.full(n_resamples, np.nan), where=den > 0)


def scene_bootstrap_ci(values: np.ndarray, scenes: np.ndarray, n_resamples: int, rng: np.random.Generator,
                       ci: float = 0.95) -> tuple[float, float]:
    """Percentile CI of the mean of `values` (a success indicator or a paired difference), resampling whole scenes
    (A-17), so correlated instances in a scene stay together."""
    sums, counts = scene_totals(values, scenes)
    m = _resample_means(sums, counts, n_resamples, rng)
    a = (1.0 - ci) / 2.0
    lo, hi = np.nanquantile(m, [a, 1.0 - a])
    return float(lo), float(hi)


def mcnemar_exact(a: np.ndarray, b: np.ndarray) -> dict:
    """Two-sided exact McNemar test on paired booleans. n_a_only = a succeeds and b fails; n_b_only the reverse."""
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    n_a, n_b = int((a & ~b).sum()), int((b & ~a).sum())
    n = n_a + n_b
    p = 1.0 if n == 0 else float(binomtest(n_a, n, 0.5, alternative="two-sided").pvalue)
    return {"n_a_only": n_a, "n_b_only": n_b, "discordance": n / len(a) if len(a) else float("nan"), "p": p}


def fixed_sequence(rejected: list[bool]) -> list[str]:
    """Status of ordered comparisons (§5.12): a comparison is confirmatory only if all earlier ones rejected; the first
    non-rejection is confirmatory (and not rejected), and every later comparison is exploratory."""
    out, open_ = [], True
    for r in rejected:
        if not open_:
            out.append("exploratory")
        else:
            out.append("confirmatory: rejected" if r else "confirmatory: not rejected")
            open_ = r
    return out


def mde_mcnemar(discordance: float, n: float) -> float:
    """Minimum detectable paired difference at 80% power, two-sided alpha 0.05 (A-18): 2.8 * sqrt(pi_d / n)."""
    return float(2.8 * np.sqrt(discordance / n)) if n > 0 else float("nan")


def depth_summary(depth: np.ndarray, mm_per_unit: float = 0.1) -> dict:
    """Share of valid pixels and depth percentiles in mm of a stored depth image (0 = no depth). The quick run compares these off its reference platform (A-77)."""
    valid = depth > 0
    p5, p50, p95 = np.percentile(depth[valid], (5, 50, 95)) * mm_per_unit if valid.any() else (0.0, 0.0, 0.0)
    return {"valid_frac": float(valid.mean()), "p5_mm": float(p5), "p50_mm": float(p50), "p95_mm": float(p95)}
