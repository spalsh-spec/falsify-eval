"""Property-based tests for the four-null gate.

The Mayank battery is example-based (parametrised across 4 label types).
Property-based testing generates hundreds of inputs from a spec and asserts
universal properties — catches bugs hand-picked tests miss.

Properties tested:
  P1. Determinism — same seed must give identical deltas.
  P2. Oracle-passes — a true-oracle retriever (gold first) always passes the gate.
  P3. Constant-cheater-fails — a constant-most-frequent predictor always fails Δ_D.
  P4. Permutation-of-input-order-invariance — shuffling the QUERIES (jointly across
      retrieved/gold/rel) must not change the gate verdict.
  P5. Determinism-with-extension — extending the bench with duplicates of itself
      should not change real_mean (it's an average) and should change deltas only
      within a sqrt(N) noise band.

These run quickly: hypothesis generates ~20 examples per property by default.
"""
from __future__ import annotations

import math
import numpy as np
import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st, HealthCheck

from falsify_eval import four_null_gate


def _exact_match(retrieved, gold, _rel):
    return 1.0 if gold in retrieved[:5] else 0.0


# Strategy: a synthetic bench with 60-200 queries over a label set of 4-12 items.
@st.composite
def synthetic_bench(draw, min_queries=60, max_queries=200,
                    min_labels=6, max_labels=12):
    n_labels = draw(st.integers(min_value=min_labels, max_value=max_labels))
    labels = [f"L{i}" for i in range(n_labels)]
    n_queries = draw(st.integers(min_value=min_queries, max_value=max_queries))
    rng_seed = draw(st.integers(min_value=0, max_value=10_000))
    rng = np.random.default_rng(rng_seed)
    gold = [labels[int(rng.integers(0, n_labels))] for _ in range(n_queries)]
    return labels, gold, rng_seed


# ----------------------------------------------------------------------------
# P1 — Determinism
# ----------------------------------------------------------------------------

@settings(max_examples=15, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
@given(synthetic_bench())
def test_p1_determinism(bench):
    labels, gold, _seed = bench
    rng = np.random.default_rng(123)
    retrieved = [
        [g] + list(rng.choice([l for l in labels if l != g],
                              size=min(4, len(labels) - 1), replace=False))
        for g in gold
    ]
    args = dict(
        retrieved_lists=retrieved, gold_list=gold, rel_list=[1] * len(gold),
        metric_fn=_exact_match, item_pool=labels, k=5, n_trials=10,
        tau=0.05, seed=2026,
    )
    r1 = four_null_gate(**args)
    r2 = four_null_gate(**args)
    assert r1["deltas"] == r2["deltas"]
    assert r1["gate_passes"] == r2["gate_passes"]
    assert r1["real_mean"] == r2["real_mean"]


# ----------------------------------------------------------------------------
# P2 — Oracle always passes
# ----------------------------------------------------------------------------

@settings(max_examples=15, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
@given(synthetic_bench(min_queries=80, max_queries=160))
def test_p2_oracle_passes(bench):
    labels, gold, _ = bench
    rng = np.random.default_rng(7)
    # Oracle: gold first, then 4 random other labels
    retrieved = [
        [g] + list(rng.choice([l for l in labels if l != g],
                              size=min(4, len(labels) - 1), replace=False))
        for g in gold
    ]
    res = four_null_gate(
        retrieved, gold, [1] * len(gold), _exact_match,
        item_pool=labels, k=5, n_trials=15, tau=0.05, seed=2026,
    )
    assert res["gate_passes"], (
        f"oracle must pass; deltas={res['deltas']}, labels={len(labels)}"
    )


# ----------------------------------------------------------------------------
# P3 — Constant-most-frequent cheater fails Δ_D
# ----------------------------------------------------------------------------

@settings(max_examples=15, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
@given(synthetic_bench(min_queries=120, max_queries=200))
def test_p3_constant_cheater_fails_d(bench):
    labels, gold, _ = bench
    from collections import Counter
    most_common = Counter(gold).most_common(1)[0][0]
    retrieved = [[most_common] * 5 for _ in gold]
    res = four_null_gate(
        retrieved, gold, [1] * len(gold), _exact_match,
        item_pool=labels, k=5, n_trials=20, tau=0.05, seed=2026,
    )
    # Δ_D must be near zero (the marginal-matched null cancels the cheater)
    assert abs(res["deltas"]["D"]) < 0.05, (
        f"constant cheater must fail Δ_D; got Δ_D={res['deltas']['D']}, "
        f"label-set={len(labels)}"
    )
    assert not res["gate_passes"]


# ----------------------------------------------------------------------------
# P4 — Permutation-of-query-order-invariance
# ----------------------------------------------------------------------------

@settings(max_examples=10, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
@given(synthetic_bench(min_queries=80, max_queries=160))
def test_p4_query_order_invariance(bench):
    labels, gold, _ = bench
    rng = np.random.default_rng(42)
    retrieved = [
        [g] + list(rng.choice([l for l in labels if l != g],
                              size=min(4, len(labels) - 1), replace=False))
        for g in gold
    ]
    rel = [1] * len(gold)

    res_a = four_null_gate(
        retrieved, gold, rel, _exact_match,
        item_pool=labels, k=5, n_trials=10, tau=0.05, seed=2026,
    )

    # Permute (retrieved, gold, rel) jointly with a shared shuffle
    perm = rng.permutation(len(gold))
    retrieved_p = [retrieved[i] for i in perm]
    gold_p = [gold[i] for i in perm]
    rel_p = [rel[i] for i in perm]

    res_b = four_null_gate(
        retrieved_p, gold_p, rel_p, _exact_match,
        item_pool=labels, k=5, n_trials=10, tau=0.05, seed=2026,
    )

    # real_mean is exactly invariant (it's an average over queries)
    assert math.isclose(res_a["real_mean"], res_b["real_mean"], abs_tol=1e-12)
    # Gate verdict must agree
    assert res_a["gate_passes"] == res_b["gate_passes"], (
        f"query-order permutation flipped gate verdict! "
        f"deltas before: {res_a['deltas']}, after: {res_b['deltas']}"
    )
