"""falsify-eval — calibrated falsification harness for retrieval evaluation.

A Python library implementing the four-null Δ-metric gate, SHA-256 +
git-commit integrity locking, side-effect suppression, and statistical-
reporting pattern described in:

  Sharma, S. (2026). "Calibrated Falsification Harnesses for Retrieval
  Evaluation: A Methodology-First Case Study." (Preprint.)

Apache 2.0. Bring your own retrieval system, your own corpus, your own
metric. The library is corpus-agnostic and metric-agnostic; the public
interface accepts any callable that returns top-K rankings.
"""
from .gate import (
    null_a_permuted,
    null_b_uniform,
    null_c_random_retrieval,
    null_d_marginal_matched,
    four_null_gate,
)
from .lock import lock_state, verify_state
from .stats import (
    bootstrap_ci,
    bootstrap_diff_ci,
    paired_permutation_p,
    cohens_d_paired,
    power_n_required,
)

__version__ = "0.1.5.1"
__all__ = [
    "null_a_permuted", "null_b_uniform", "null_c_random_retrieval",
    "null_d_marginal_matched", "four_null_gate",
    "lock_state", "verify_state",
    "bootstrap_ci", "bootstrap_diff_ci",
    "paired_permutation_p", "cohens_d_paired", "power_n_required",
]
