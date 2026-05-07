"""Statistical reporting requirements (R in Definition 1).

Bootstrap CIs on means and paired differences. Paired permutation tests.
Cohen's d. All pure-numpy.
"""
from __future__ import annotations

import math
import numpy as np


def bootstrap_ci(x: np.ndarray, *, n_resamples: int = 10000,
                 alpha: float = 0.05, seed: int = 2026
                 ) -> tuple[float, float, float, float]:
    """Bootstrap (mean, ci_lo, ci_hi, sd) on the per-sample vector x."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    means = np.empty(n_resamples)
    for i in range(n_resamples):
        means[i] = rng.choice(x, size=n, replace=True).mean()
    lo, hi = np.quantile(means, [alpha/2, 1 - alpha/2])
    return float(x.mean()), float(lo), float(hi), float(means.std())


def bootstrap_diff_ci(a: np.ndarray, b: np.ndarray,
                      *, n_resamples: int = 10000, alpha: float = 0.05,
                      seed: int = 2026) -> tuple[float, float, float]:
    """Paired bootstrap CI on (a - b)."""
    rng = np.random.default_rng(seed)
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    n = len(a)
    diffs = np.empty(n_resamples)
    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        diffs[i] = a[idx].mean() - b[idx].mean()
    lo, hi = np.quantile(diffs, [alpha/2, 1 - alpha/2])
    return float((a - b).mean()), float(lo), float(hi)


def paired_permutation_p(a: np.ndarray, b: np.ndarray,
                         *, n_resamples: int = 10000, seed: int = 2026
                         ) -> tuple[float, float]:
    """Two-sided paired permutation test on (a - b). Returns (mean_diff, p)."""
    rng = np.random.default_rng(seed)
    diff = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    obs = float(diff.mean())
    swaps = rng.integers(0, 2, size=(n_resamples, len(diff))) * 2 - 1
    sims = (swaps * diff).mean(axis=1)
    p = float((np.abs(sims) >= abs(obs)).mean())
    return obs, p


def cohens_d_paired(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's d for paired data: mean(diff) / sd(diff). Returns 0 if sd==0."""
    diff = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    sd = float(diff.std(ddof=1))
    return float(diff.mean() / sd) if sd > 0 else 0.0


def power_n_required(observed_diff: float, observed_sd: float,
                     *, target_delta: float | None = None,
                     alpha: float = 0.05, power: float = 0.80) -> float:
    """N required to detect target_delta (default: observed_diff) at the
    given α and power, assuming paired-test approximation
    N ≈ ((z_{α/2} + z_β) σ / δ)²."""
    delta = target_delta if target_delta is not None else observed_diff
    if delta == 0 or observed_sd == 0:
        return float("inf")
    z_a = 1.96 if alpha == 0.05 else float(np.abs(np.percentile(
        np.random.default_rng(0).standard_normal(100000), 100*(1-alpha/2))))
    z_b = 0.84 if power == 0.80 else float(np.abs(np.percentile(
        np.random.default_rng(0).standard_normal(100000), 100*power)))
    return ((z_a + z_b) * observed_sd / abs(delta)) ** 2


def bonferroni(p_values: list[float] | np.ndarray, *,
               alpha: float = 0.05) -> dict:
    """Bonferroni multiplicity correction.

    Honours the PREPRINT abstract promise of *Bonferroni-corrected paired
    tests*. When a hypothesis is tested at multiple α-levels (e.g., the four
    Δ-comparisons of the gate, or per-feature significance across many
    features), the family-wise error rate inflates linearly. Bonferroni
    divides α by the number of comparisons, giving a conservative bound.

    Args:
        p_values: list / array of raw p-values to correct.
        alpha: family-wise α budget (default 0.05).

    Returns:
        dict with:
          'm':              number of tests
          'alpha_per_test': alpha / m
          'p_adjusted':     [min(1, p * m) for p in p_values]
          'reject':         [bool: is p_adjusted_i < alpha]
          'family_alpha':   alpha (unchanged)

    Example:
        >>> bonferroni([0.01, 0.02, 0.03, 0.04])
        # m=4, alpha_per_test=0.0125, only the first two reject
    """
    p = np.asarray(p_values, dtype=np.float64)
    if p.ndim != 1 or p.size == 0:
        raise ValueError("p_values must be a non-empty 1-d sequence")
    if not np.all((p >= 0) & (p <= 1)):
        raise ValueError("p_values must lie in [0, 1]")
    if not (0.0 < alpha <= 1.0):
        raise ValueError("alpha must lie in (0, 1]")
    m = int(p.size)
    p_adj = np.minimum(1.0, p * m)
    return {
        "m":               m,
        "alpha_per_test":  float(alpha / m),
        "p_adjusted":      [float(x) for x in p_adj],
        "reject":          [bool(x < alpha) for x in p_adj],
        "family_alpha":    float(alpha),
    }
