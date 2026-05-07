"""Cross-check our stats module against scipy on the same fixed-seed inputs.

Mayank attack-surface #4: 'I have NOT cross-checked them against scipy.'
This test suite closes that gap before he reaches it.

We do not import scipy as a runtime dependency (the library remains numpy-only);
scipy is only required to run THIS test file. Skipped cleanly if not installed.
"""
from __future__ import annotations

import math
import numpy as np
import pytest

scipy = pytest.importorskip("scipy")
from scipy import stats as ss

from falsify_eval import (
    bootstrap_ci,
    bootstrap_diff_ci,
    paired_permutation_p,
    cohens_d_paired,
    bonferroni,
)


# ----------------------------------------------------------------------------
# Bootstrap mean CI vs scipy.stats.bootstrap (single-sample percentile)
# ----------------------------------------------------------------------------

def test_bootstrap_ci_matches_scipy_percentile():
    """Same data, same seed-equivalent setup, our CI should land within
    the scipy-reported CI to about ±0.02 (bootstrap noise; both honest)."""
    rng_seed = 42
    np.random.seed(rng_seed)
    x = np.random.beta(2, 5, size=300)

    ours_mean, ours_lo, ours_hi, _ours_sd = bootstrap_ci(
        x, n_resamples=10000, alpha=0.05, seed=rng_seed
    )

    res = ss.bootstrap(
        (x,), np.mean,
        confidence_level=0.95, n_resamples=10000,
        method="percentile",
        random_state=rng_seed,
    )
    scipy_lo = float(res.confidence_interval.low)
    scipy_hi = float(res.confidence_interval.high)
    scipy_mean = float(np.mean(x))

    assert abs(ours_mean - scipy_mean) < 1e-9, "mean must be exact"
    # CI bounds will differ slightly because of bootstrap RNG path divergence.
    # Both are valid percentile bootstraps; within 0.02 is expected on N=300.
    assert abs(ours_lo - scipy_lo) < 0.02, (
        f"bootstrap_ci lo drift: ours={ours_lo} scipy={scipy_lo}"
    )
    assert abs(ours_hi - scipy_hi) < 0.02, (
        f"bootstrap_ci hi drift: ours={ours_hi} scipy={scipy_hi}"
    )


# ----------------------------------------------------------------------------
# Paired permutation p-value vs scipy.stats.permutation_test (paired)
# ----------------------------------------------------------------------------

def test_paired_permutation_p_matches_scipy():
    rng_seed = 7
    np.random.seed(rng_seed)
    a = np.random.normal(0.6, 0.1, size=80)
    b = np.random.normal(0.5, 0.1, size=80)

    ours_diff, ours_p = paired_permutation_p(
        a, b, n_resamples=10000, seed=rng_seed
    )

    def stat(x, y):
        return float(np.mean(x - y))

    res = ss.permutation_test(
        (a, b), stat,
        permutation_type="samples",
        n_resamples=10000, alternative="two-sided",
        random_state=rng_seed,
    )
    scipy_p = float(res.pvalue)
    scipy_stat = float(res.statistic)

    assert abs(ours_diff - scipy_stat) < 1e-9, "observed stat must be exact"
    # Permutation p has discrete jitter; expect agreement within ~0.02.
    assert abs(ours_p - scipy_p) < 0.02, (
        f"paired-perm-p drift: ours={ours_p} scipy={scipy_p}"
    )


# ----------------------------------------------------------------------------
# Cohen's d vs hand-calculated value (no direct scipy equivalent for paired d)
# ----------------------------------------------------------------------------

def test_cohens_d_paired_matches_hand_calc():
    a = np.array([0.6, 0.7, 0.8, 0.5, 0.75])
    b = np.array([0.5, 0.55, 0.6, 0.45, 0.65])
    diff = a - b
    expected = float(diff.mean() / diff.std(ddof=1))
    assert abs(cohens_d_paired(a, b) - expected) < 1e-12


# ----------------------------------------------------------------------------
# Bonferroni — golden-case behaviour and edge cases
# ----------------------------------------------------------------------------

def test_bonferroni_classic_case():
    """4 tests, α=0.05 family-wise → α-per-test=0.0125. Only p<0.0125 rejects."""
    res = bonferroni([0.001, 0.01, 0.02, 0.04], alpha=0.05)
    assert res["m"] == 4
    assert math.isclose(res["alpha_per_test"], 0.0125)
    # p_adjusted = p * 4, capped at 1
    assert math.isclose(res["p_adjusted"][0], 0.004)
    assert math.isclose(res["p_adjusted"][1], 0.04)
    assert math.isclose(res["p_adjusted"][2], 0.08)
    assert math.isclose(res["p_adjusted"][3], 0.16)
    # Only first two reject (adjusted < 0.05)
    assert res["reject"] == [True, True, False, False]


def test_bonferroni_caps_at_one():
    """Adjusted p must be ≤ 1 even when p × m > 1."""
    res = bonferroni([0.5, 0.6, 0.7, 0.8, 0.9], alpha=0.05)
    assert all(p == 1.0 for p in res["p_adjusted"])
    assert all(r is False for r in res["reject"])


@pytest.mark.parametrize("bad", [
    [],                          # empty
    [-0.1, 0.5],                 # negative p
    [0.5, 1.5],                  # p > 1
])
def test_bonferroni_validates_inputs(bad):
    with pytest.raises(ValueError):
        bonferroni(bad, alpha=0.05)


def test_bonferroni_validates_alpha():
    with pytest.raises(ValueError):
        bonferroni([0.01, 0.02], alpha=0)
    with pytest.raises(ValueError):
        bonferroni([0.01, 0.02], alpha=1.5)


# ----------------------------------------------------------------------------
# bootstrap_diff_ci sanity: 0 expected when a == b, sign correct otherwise
# ----------------------------------------------------------------------------

def test_bootstrap_diff_ci_sign():
    rng = np.random.default_rng(99)
    a = rng.normal(0.7, 0.05, size=100)
    b = rng.normal(0.6, 0.05, size=100)
    diff_mean, lo, hi = bootstrap_diff_ci(a, b, n_resamples=2000, seed=1)
    assert diff_mean > 0
    assert lo > 0  # 95% CI on positive diff should not include 0


def test_bootstrap_diff_ci_zero_when_equal():
    a = np.full(100, 0.5)
    diff_mean, lo, hi = bootstrap_diff_ci(a, a, n_resamples=500, seed=1)
    assert diff_mean == 0.0
    assert lo == 0.0
    assert hi == 0.0
