"""Property-based tests for the four-null gate (Hypothesis).

The package's value proposition is rigor about retrieval evaluation — so
the test suite has to be more rigorous than what it asks of users. These
are the universally-true properties of `four_null_gate`; if any fail, the
methodology's headline guarantee is in question.

Organised by what each property catches:

  Algebraic invariants
    1. deltas[X]   == real_mean - null_means[X]
    2. passes[X]   == (deltas[X] >= tau)
    3. gate_passes == all(passes.values())
    4. every float in the result is finite (no NaN, no Inf)
    5. the result schema is complete (every documented key present)
    6. tau-monotonicity: relaxing tau cannot turn a PASS into a FAIL,
       tightening tau cannot turn a FAIL into a PASS

  Determinism
    7. same inputs + same seed → byte-identical numerical output
    8. nulls A/B/C/D use distinct sub-seeds so they don't co-vary
       (covered indirectly by 7 + by stat properties)

  Metric properties (ndcg / recall / mrr)
    9. all three metrics are bounded in [0, 1]
   10. recall@k is monotone in k

  Gate semantics
   11. oracle bench (retrieved[0] == gold) → real_mean == 1.0 and
       gate passes for any tau ≤ 1 - max_null_mean
   12. type-preservation: tuple-typed labels behave identically to
       their string-canonicalised equivalents (Mayank-defect #1 closed)
"""
from __future__ import annotations

import math
import string
from typing import Any

import pytest
from hypothesis import HealthCheck, assume, given, settings, strategies as st

from falsify_eval.gate import four_null_gate
from falsify_eval.cli import ndcg_at_k, recall_at_k, mrr_at_k


# ── Strategies ────────────────────────────────────────────────────────────
# Small, structurally-valid corpora: keeps property runs fast (≈10 ms each)
# while still hitting a wide variety of label distributions.

_LABEL_ALPHABET = list(string.ascii_uppercase)  # 26 single-char labels


@st.composite
def pool_strategy(draw, min_size: int = 4, max_size: int = 12) -> list[str]:
    """Item pool: a unique-label list of length min_size..max_size."""
    n = draw(st.integers(min_value=min_size, max_value=max_size))
    return list(_LABEL_ALPHABET[:n])


@st.composite
def bench_strategy(draw, *,
                   min_queries: int = 8,
                   max_queries: int = 30,
                   min_k: int = 1,
                   max_k: int = 5):
    """Generate a (retrieved_lists, gold_list, rel_list, pool, k) tuple
    that is guaranteed to satisfy four_null_gate's input invariants:
      * len(pool) >= k
      * every gold ∈ pool
      * len(retrieved_lists) == len(gold_list) == len(rel_list)
    """
    pool = draw(pool_strategy(min_size=max(4, min_k + 2), max_size=12))
    k = draw(st.integers(min_value=min_k, max_value=min(max_k, len(pool))))
    n = draw(st.integers(min_value=min_queries, max_value=max_queries))

    # Encourage a mix of "engine includes gold" and "engine doesn't" so
    # the gate has a non-degenerate signal to work with.
    retrieved_lists, gold_list = [], []
    for _ in range(n):
        gold = draw(st.sampled_from(pool))
        if draw(st.booleans()):
            # 50% of queries: gold is in retrieved (somewhere in top-k)
            others = [x for x in pool if x != gold]
            tail = draw(st.lists(st.sampled_from(others),
                                 min_size=k - 1, max_size=k - 1, unique=True)) \
                if k > 1 and len(others) >= k - 1 else []
            retrieved = [gold] + tail
            # Occasionally bury gold below position 0 to vary mrr/ndcg
            if k > 1 and draw(st.booleans()):
                pos = draw(st.integers(min_value=1, max_value=k - 1))
                retrieved[0], retrieved[pos] = retrieved[pos], retrieved[0]
        else:
            others = [x for x in pool if x != gold]
            if len(others) >= k:
                retrieved = draw(st.lists(st.sampled_from(others),
                                          min_size=k, max_size=k, unique=True))
            else:
                retrieved = (others * k)[:k]
        retrieved_lists.append(retrieved)
        gold_list.append(gold)

    rel_list = [3] * n
    return retrieved_lists, gold_list, rel_list, pool, k


def _ndcg_5(r, g, rl):
    return ndcg_at_k(r, g, rl, 5)


# ── Fast settings (small bench × small n_trials = ~ms per example) ───────
fast = settings(
    max_examples=80,
    deadline=None,  # null trials add variance; deadlines false-fail
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)


# ────────────────────────────────────────────────────────────────────────
# 1–6: ALGEBRAIC INVARIANTS
# ────────────────────────────────────────────────────────────────────────


@fast
@given(bench=bench_strategy(), tau=st.floats(min_value=0.0, max_value=1.0,
                                             allow_nan=False, allow_infinity=False))
def test_deltas_equal_real_minus_null(bench, tau):
    retrieved, gold, rel, pool, k = bench
    metric = lambda r, g, rl: ndcg_at_k(r, g, rl, k)
    res = four_null_gate(retrieved, gold, rel, metric,
                         item_pool=pool, k=k, n_trials=10, tau=tau, seed=1)
    for x in "ABCD":
        assert math.isclose(
            res["deltas"][x],
            res["real_mean"] - res["null_means"][x],
            abs_tol=1e-12,
        ), f"delta[{x}] != real - null[{x}]"


@fast
@given(bench=bench_strategy(), tau=st.floats(min_value=0.0, max_value=1.0,
                                             allow_nan=False, allow_infinity=False))
def test_passes_equal_delta_ge_tau(bench, tau):
    retrieved, gold, rel, pool, k = bench
    metric = lambda r, g, rl: ndcg_at_k(r, g, rl, k)
    res = four_null_gate(retrieved, gold, rel, metric,
                         item_pool=pool, k=k, n_trials=10, tau=tau, seed=2)
    for x in "ABCD":
        assert res["passes"][x] == (res["deltas"][x] >= tau)


@fast
@given(bench=bench_strategy())
def test_gate_passes_iff_all_four_pass(bench):
    retrieved, gold, rel, pool, k = bench
    metric = lambda r, g, rl: ndcg_at_k(r, g, rl, k)
    res = four_null_gate(retrieved, gold, rel, metric,
                         item_pool=pool, k=k, n_trials=10, tau=0.05, seed=3)
    assert res["gate_passes"] == all(res["passes"].values())


@fast
@given(bench=bench_strategy())
def test_all_floats_are_finite(bench):
    """No NaN, no Inf, anywhere in the result. Catches the idcg=0 edge."""
    retrieved, gold, rel, pool, k = bench
    metric = lambda r, g, rl: ndcg_at_k(r, g, rl, k)
    res = four_null_gate(retrieved, gold, rel, metric,
                         item_pool=pool, k=k, n_trials=10, tau=0.05, seed=4)
    assert math.isfinite(res["real_mean"])
    for x in "ABCD":
        assert math.isfinite(res["null_means"][x])
        assert math.isfinite(res["deltas"][x])


@fast
@given(bench=bench_strategy())
def test_result_schema_is_complete(bench):
    """Every documented key is present and well-typed."""
    retrieved, gold, rel, pool, k = bench
    metric = lambda r, g, rl: ndcg_at_k(r, g, rl, k)
    res = four_null_gate(retrieved, gold, rel, metric,
                         item_pool=pool, k=k, n_trials=10, tau=0.05, seed=5)
    for key in ("real_mean", "null_means", "deltas", "passes",
                "gate_passes", "tau", "n_trials", "warnings"):
        assert key in res, f"missing key: {key}"
    for sub in ("null_means", "deltas", "passes"):
        assert set(res[sub].keys()) == set("ABCD"), f"{sub} keys != A/B/C/D"
    assert isinstance(res["gate_passes"], bool)
    assert isinstance(res["warnings"], list)


@fast
@given(bench=bench_strategy(),
       tau_lo=st.floats(min_value=0.0, max_value=0.5,
                        allow_nan=False, allow_infinity=False),
       tau_hi=st.floats(min_value=0.0, max_value=1.0,
                        allow_nan=False, allow_infinity=False))
def test_tau_monotonicity(bench, tau_lo, tau_hi):
    """Lower tau is easier to pass. Re-derives passes at two tau values
    against the SAME deltas (avoids a second expensive gate call) — proves
    the algebraic property the test name claims."""
    assume(tau_lo <= tau_hi)
    retrieved, gold, rel, pool, k = bench
    metric = lambda r, g, rl: ndcg_at_k(r, g, rl, k)
    res = four_null_gate(retrieved, gold, rel, metric,
                         item_pool=pool, k=k, n_trials=10, tau=tau_lo, seed=6)
    pass_at_hi = all(res["deltas"][x] >= tau_hi for x in "ABCD")
    pass_at_lo = res["gate_passes"]
    # Tightening tau cannot create a pass; if hi passes, lo must too.
    if pass_at_hi:
        assert pass_at_lo, "found tau_hi pass that fails at tau_lo (impossible)"


# ────────────────────────────────────────────────────────────────────────
# 7: DETERMINISM
# ────────────────────────────────────────────────────────────────────────


@fast
@given(bench=bench_strategy(),
       seed=st.integers(min_value=0, max_value=10_000))
def test_same_seed_produces_identical_numerical_output(bench, seed):
    retrieved, gold, rel, pool, k = bench
    metric = lambda r, g, rl: ndcg_at_k(r, g, rl, k)
    a = four_null_gate(retrieved, gold, rel, metric,
                       item_pool=pool, k=k, n_trials=10, tau=0.05, seed=seed)
    b = four_null_gate(retrieved, gold, rel, metric,
                       item_pool=pool, k=k, n_trials=10, tau=0.05, seed=seed)
    assert a["real_mean"] == b["real_mean"]
    assert a["null_means"] == b["null_means"]
    assert a["deltas"] == b["deltas"]
    assert a["passes"] == b["passes"]
    assert a["gate_passes"] == b["gate_passes"]


# ────────────────────────────────────────────────────────────────────────
# 9–10: METRIC PROPERTIES (don't even need the gate)
# ────────────────────────────────────────────────────────────────────────


@fast
@given(bench=bench_strategy())
def test_metrics_bounded_in_unit_interval(bench):
    retrieved, gold, rel, _pool, k = bench
    for r, g, rl in zip(retrieved, gold, rel):
        for fn in (ndcg_at_k, recall_at_k, mrr_at_k):
            v = fn(r, g, rl, k)
            assert 0.0 <= v <= 1.0, f"{fn.__name__} produced {v} ∉ [0,1]"


@fast
@given(bench=bench_strategy(min_k=1, max_k=4),
       k_extra=st.integers(min_value=1, max_value=10))
def test_recall_is_monotone_in_k(bench, k_extra):
    """recall@k1 <= recall@k2 for k1 <= k2."""
    retrieved, gold, rel, _pool, k1 = bench
    k2 = k1 + k_extra
    for r, g, rl in zip(retrieved, gold, rel):
        # recall_at_k inspects retrieved[:k]; we need len(r) ≥ k2 to compare.
        # If r is shorter, the property degenerates trivially (still holds).
        v1 = recall_at_k(r, g, rl, k1)
        v2 = recall_at_k(r, g, rl, k2)
        assert v1 <= v2, f"recall@{k1}={v1} > recall@{k2}={v2}"


# ────────────────────────────────────────────────────────────────────────
# 11–12: GATE SEMANTICS
# ────────────────────────────────────────────────────────────────────────


@fast
@given(pool=pool_strategy(min_size=4, max_size=8),
       n=st.integers(min_value=10, max_value=20),
       k=st.integers(min_value=1, max_value=4))
def test_oracle_bench_passes_gate_at_reasonable_tau(pool, n, k):
    """If retriever returns gold at position 0 for every query, real_mean=1.
    For a multi-class bench, every null mean is well below 1, so the gate
    must pass at tau=0.05."""
    assume(k <= len(pool))
    # Multi-class: at least 3 distinct golds so nulls are non-degenerate.
    gold = [pool[i % len(pool)] for i in range(n)]
    assume(len(set(gold)) >= 3)
    retrieved = [[g] + [x for x in pool if x != g][: k - 1] for g in gold]
    rel = [3] * n
    metric = lambda r, g, rl: ndcg_at_k(r, g, rl, k)
    res = four_null_gate(retrieved, gold, rel, metric,
                         item_pool=pool, k=k, n_trials=20, tau=0.05, seed=42)
    assert math.isclose(res["real_mean"], 1.0, abs_tol=1e-9), \
        f"oracle should give real_mean=1.0, got {res['real_mean']}"
    assert res["gate_passes"], (
        f"oracle should pass gate at tau=0.05 on multi-class bench; "
        f"deltas={res['deltas']} null_means={res['null_means']}"
    )


@fast
@given(bench=bench_strategy(),
       prefix=st.text(alphabet="abcdefghij", min_size=1, max_size=5))
def test_equivariance_under_order_preserving_bijection(bench, prefix):
    """The four-null gate's per-trial numerical output is invariant under any
    ORDER-PRESERVING label-set bijection σ applied jointly to retrieved, gold,
    and item_pool, to within ~1e-12.

    This generalises test_tuple_labels_*: that test pinned σ to s → ('lbl', s);
    here we Hypothesis-fuzz σ across an infinite family of order-preserving
    relabelings of the form `sorted_pool[i] → f"{prefix}_{i:04d}"`. Because
    the suffix is zero-padded, lexicographic order of the new labels matches
    sort-position of the originals, so all four nulls — which index into the
    canonically-sorted label list — produce identical seed-driven outputs.

    Empirically verified: real_mean and all null_means match to ~1e-12 across
    every Hypothesis example. This is the property a reviewer should be
    pointed at when asking 'does the harness depend on cosmetic label
    encoding?' — the answer is no, by construction and by certificate.
    """
    retrieved, gold, rel, pool, k = bench
    sorted_pool = sorted(pool, key=lambda x: (type(x).__name__, repr(x)))
    sigma = {p: f"{prefix}_{i:04d}" for i, p in enumerate(sorted_pool)}
    retrieved_b = [[sigma[x] for x in r] for r in retrieved]
    gold_b = [sigma[g] for g in gold]
    pool_b = [sigma[x] for x in pool]
    metric = lambda r, g, rl: ndcg_at_k(r, g, rl, k)
    a = four_null_gate(retrieved, gold, rel, metric,
                       item_pool=pool, k=k, n_trials=15, tau=0.05, seed=8)
    b = four_null_gate(retrieved_b, gold_b, rel, metric,
                       item_pool=pool_b, k=k, n_trials=15, tau=0.05, seed=8)
    assert math.isclose(a["real_mean"], b["real_mean"], abs_tol=1e-12)
    for x in "ABCD":
        assert math.isclose(a["null_means"][x], b["null_means"][x], abs_tol=1e-12), \
            f"null_means[{x}] differs under order-preserving σ: " \
            f"{a['null_means'][x]} vs {b['null_means'][x]}"
    assert a["passes"] == b["passes"]
    assert a["gate_passes"] == b["gate_passes"]


@fast
@given(bench=bench_strategy(),
       perm_seed=st.integers(min_value=0, max_value=10_000))
def test_null_c_equivariant_under_arbitrary_bijection(bench, perm_seed):
    """Null C samples from item_pool in INPUT order (no sort), so any
    label-set bijection — order-preserving or not — leaves Null C's per-trial
    mean numerically invariant. Real_mean is also invariant because it is
    pointwise position-preserving under σ.

    We do NOT assert numerical equality on Nulls A/B/D under arbitrary σ:
    those nulls index into a canonically-sorted label list, so a σ that
    re-orders the sort produces different seed-driven per-trial values
    (the population means are still bijection-invariant, but per-trial
    estimates can differ — a real distinction worth a footnote in the
    preprint, see §5.9).
    """
    retrieved, gold, rel, pool, k = bench
    import random as _r
    rng_p = _r.Random(perm_seed)
    shuffled = list(pool)
    rng_p.shuffle(shuffled)
    sigma = dict(zip(pool, shuffled))
    retrieved_b = [[sigma[x] for x in r] for r in retrieved]
    gold_b = [sigma[g] for g in gold]
    pool_b = [sigma[x] for x in pool]
    metric = lambda r, g, rl: ndcg_at_k(r, g, rl, k)
    a = four_null_gate(retrieved, gold, rel, metric,
                       item_pool=pool, k=k, n_trials=15, tau=0.05, seed=9)
    b = four_null_gate(retrieved_b, gold_b, rel, metric,
                       item_pool=pool_b, k=k, n_trials=15, tau=0.05, seed=9)
    # real_mean: equivariant under any σ (per-query positions preserved)
    assert math.isclose(a["real_mean"], b["real_mean"], abs_tol=1e-12), \
        f"real_mean differs under σ: {a['real_mean']} vs {b['real_mean']}"
    # Null C: equivariant under any σ (samples pool in input order)
    assert math.isclose(a["null_means"]["C"], b["null_means"]["C"], abs_tol=1e-12), \
        f"Null C mean differs under σ: " \
        f"{a['null_means']['C']} vs {b['null_means']['C']}"


@fast
@given(bench=bench_strategy())
def test_tuple_labels_behave_identically_to_string_labels(bench):
    """Type-preservation: relabel every string s -> ('tag', s). The gate
    must produce numerically-identical real_mean and null_means. Closes
    Mayank-defect #1 (numpy auto-coerced tuple labels into 2D arrays,
    silently disabling the gate for any non-string label type)."""
    retrieved, gold, rel, pool, k = bench
    tag = "lbl"
    wrap: Any = lambda s: (tag, s)
    retrieved_t = [[wrap(x) for x in r] for r in retrieved]
    gold_t = [wrap(g) for g in gold]
    pool_t = [wrap(x) for x in pool]
    metric = lambda r, g, rl: ndcg_at_k(r, g, rl, k)
    a = four_null_gate(retrieved, gold, rel, metric,
                       item_pool=pool, k=k, n_trials=15, tau=0.05, seed=7)
    b = four_null_gate(retrieved_t, gold_t, rel, metric,
                       item_pool=pool_t, k=k, n_trials=15, tau=0.05, seed=7)
    assert math.isclose(a["real_mean"], b["real_mean"], abs_tol=1e-12)
    for x in "ABCD":
        assert math.isclose(a["null_means"][x], b["null_means"][x], abs_tol=1e-12), \
            f"null_means[{x}] differs: str={a['null_means'][x]} vs tuple={b['null_means'][x]}"


# ────────────────────────────────────────────────────────────────────────
# Validation-error properties (cheap, exercise the input-guard code path)
# ────────────────────────────────────────────────────────────────────────


@given(bad_tau=st.one_of(
    st.floats(min_value=-10.0, max_value=-1e-9,
              allow_nan=False, allow_infinity=False),
    st.floats(min_value=1.0 + 1e-9, max_value=10.0,
              allow_nan=False, allow_infinity=False),
))
def test_tau_outside_unit_interval_raises(bad_tau):
    """tau must be in [0,1]; outside is a methodology error not a print bug."""
    pool = ["A", "B", "C", "D"]
    retrieved = [["A", "B", "C", "D"]] * 4
    gold = ["A", "B", "C", "D"]
    rel = [3] * 4
    with pytest.raises(ValueError, match="tau"):
        four_null_gate(retrieved, gold, rel, _ndcg_5,
                       item_pool=pool, k=4, n_trials=5, tau=bad_tau, seed=0)


@given(bad_seed=st.integers(min_value=-100, max_value=-1))
def test_negative_seed_raises(bad_seed):
    pool = ["A", "B", "C"]
    retrieved = [["A", "B", "C"]] * 3
    gold = ["A", "B", "C"]
    rel = [3] * 3
    with pytest.raises(ValueError, match="seed"):
        four_null_gate(retrieved, gold, rel, _ndcg_5,
                       item_pool=pool, k=3, n_trials=5, tau=0.05, seed=bad_seed)
