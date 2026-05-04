"""Validation tests — confirm v0.1.3 input-validation guards raise clear
errors rather than crashing or silently producing garbage."""
import pytest
from falsify_eval import four_null_gate


def _metric(retrieved, gold, rel):
    return 1.0 if gold in retrieved[:5] else 0.0


def test_k_greater_than_pool_raises_clear_error():
    """v0.1.2 crashed with raw numpy ValueError; v0.1.3 must raise our own."""
    with pytest.raises(ValueError, match="k=5 > len.item_pool.=3"):
        four_null_gate([["A","B","C"]] * 10, ["A"]*10, [3]*10, _metric,
                       item_pool=["A","B","C"], k=5, n_trials=10, tau=0.05, seed=1)


def test_gold_not_in_pool_raises_clear_error():
    """v0.1.2 silently returned all-zero output; v0.1.3 must raise."""
    with pytest.raises(ValueError, match="gold label.s. not present in item_pool"):
        four_null_gate([["A","B","C"]] * 10, ["Z"]*10, [3]*10, _metric,
                       item_pool=["A","B","C"], k=3, n_trials=10, tau=0.05, seed=1)


def test_length_mismatch_raises():
    with pytest.raises(ValueError, match="length mismatch"):
        four_null_gate([["A","B"]] * 5, ["A"]*10, [3]*10, _metric,
                       item_pool=["A","B"], k=2, n_trials=10, tau=0.05, seed=1)


def test_empty_gold_raises():
    with pytest.raises(ValueError, match="empty"):
        four_null_gate([], [], [], _metric,
                       item_pool=["A","B"], k=2, n_trials=10, tau=0.05, seed=1)


def test_invalid_k_raises():
    with pytest.raises(ValueError, match="k must be a positive integer"):
        four_null_gate([["A"]]*5, ["A"]*5, [3]*5, _metric,
                       item_pool=["A","B"], k=0, n_trials=10, tau=0.05, seed=1)


def test_invalid_tau_raises():
    with pytest.raises(ValueError, match="tau must be in"):
        four_null_gate([["A"]]*5, ["A"]*5, [3]*5, _metric,
                       item_pool=["A","B"], k=1, n_trials=10, tau=1.5, seed=1)


def test_single_class_warning():
    """Single-class bench is legitimate but should be flagged in result.warnings."""
    res = four_null_gate([["A","B","C"]]*200, ["A"]*200, [3]*200, _metric,
                         item_pool=["A","B","C","D","E"], k=3, n_trials=20, tau=0.05, seed=1)
    assert any("single-class" in w for w in res["warnings"])
    # ΔA and ΔD must be exactly equal in this case (both nulls collapse).
    assert res["deltas"]["A"] == res["deltas"]["D"]


def test_sparse_marginal_warning():
    """N << |pool| → Null D becomes Null B; flag it."""
    LABELS = [f"L{i:04d}" for i in range(1000)]
    res = four_null_gate([["L0000","L0001","L0002","L0003","L0004"]]*50,
                         [LABELS[i] for i in range(50)], [3]*50, _metric,
                         item_pool=LABELS, k=5, n_trials=20, tau=0.05, seed=1)
    assert any("sparse marginal" in w for w in res["warnings"])


def test_empty_retrieval_handled():
    """Empty retrieved lists should not crash; metric returns 0 for them."""
    res = four_null_gate([[]] * 50 + [["A","B","C"]] * 50,
                         ["A"]*100, [3]*100, _metric,
                         item_pool=list("ABCDEF"), k=3, n_trials=20, tau=0.05, seed=1)
    assert 0.0 <= res["real_mean"] <= 1.0
