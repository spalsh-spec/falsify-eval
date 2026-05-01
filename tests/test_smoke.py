"""Minimal smoke test — verifies the public surface and runs the demo."""
import math
import numpy as np
from falsify_eval import (
    four_null_gate,
    null_a_permuted, null_b_uniform, null_c_random_retrieval, null_d_marginal_matched,
    bootstrap_ci, paired_permutation_p, cohens_d_paired,
    lock_state, verify_state,
)


def ndcg5(retrieved, gold, rel):
    rels = [rel if r == gold else 0 for r in retrieved[:5]]
    ideal = sorted(rels, reverse=True)
    idcg = sum(r / math.log2(i + 2) for i, r in enumerate(ideal[:5]))
    return 0.0 if idcg == 0 else sum(r / math.log2(i + 2) for i, r in enumerate(rels[:5])) / idcg


# Tiny fixed bench — pool size 10 so random retrieval (k=5) makes sense
LABELS = [f"L{i}" for i in range(10)]
GOLD   = [LABELS[i % 10] for i in range(60)]   # 60 queries, even per label
RELS   = [3] * len(GOLD)


def test_oracle_passes():
    # gold first then 4 random other labels
    rng = np.random.default_rng(42)
    retrieved = []
    for g in GOLD:
        rest = [l for l in LABELS if l != g]
        retrieved.append([g] + list(rng.choice(rest, size=4, replace=False)))
    res = four_null_gate(retrieved, GOLD, RELS, ndcg5,
                         item_pool=LABELS, k=5, n_trials=20, tau=0.05, seed=2026)
    assert res["gate_passes"], f"oracle should pass, deltas: {res['deltas']}"


def test_constant_predictor_fails_null_d():
    # always returns 5 copies of the most-frequent class
    most_common = "L0"
    retrieved = [[most_common] * 5 for _ in GOLD]
    res = four_null_gate(retrieved, GOLD, RELS, ndcg5,
                         item_pool=LABELS, k=5, n_trials=30, tau=0.05, seed=2026)
    # Null D should give Δ near zero (matched marginal cancels constant predictor exactly)
    assert abs(res["deltas"]["D"]) < 0.05, (
        f"constant predictor should not exceed τ on Null D, got {res['deltas']['D']}"
    )
    assert not res["gate_passes"], "constant predictor must FAIL the gate"


def test_anti_oracle_fails_all_nulls():
    # always returns 5 labels EXCLUDING the gold
    rng = np.random.default_rng(7)
    retrieved = []
    for g in GOLD:
        wrong = [l for l in LABELS if l != g]
        retrieved.append(list(rng.choice(wrong, size=5, replace=False)))
    res = four_null_gate(retrieved, GOLD, RELS, ndcg5,
                         item_pool=LABELS, k=5, n_trials=20, tau=0.05, seed=2026)
    assert not res["gate_passes"]
    # All four Δ should be ≤ 0 (real==0 always; nulls can only be ≥ 0)
    for x in "ABCD":
        assert res["deltas"][x] <= 0.05, (
            f"anti_oracle should fail null {x}, got {res['deltas'][x]}"
        )


def test_bootstrap_ci_basic():
    x = np.array([0.5, 0.7, 0.8, 0.6, 0.9, 0.4, 0.65, 0.75, 0.55, 0.85])
    mean, lo, hi, sd = bootstrap_ci(x, n_resamples=2000, seed=2026)
    assert lo < mean < hi
    assert sd > 0


def test_paired_perm_p_zero_diff():
    a = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    b = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    obs, p = paired_permutation_p(a, b, n_resamples=1000, seed=2026)
    assert obs == 0.0
    assert p == 1.0


def test_cohens_d_paired_constant_diff():
    # Constant per-element difference: sd of diff is zero by definition,
    # so Cohen's d is undefined; library returns 0.0 by convention.
    # In practice, floating-point may produce tiny nonzero sd → check |d| is huge OR returns 0.
    a = np.array([1.0, 1.1, 1.2, 1.3])
    b = np.array([0.9, 1.0, 1.1, 1.2])
    d = cohens_d_paired(a, b)
    # If sd is exactly zero, d=0; if it's float-noise-tiny, d will be huge — both are
    # acceptable for the "no variance" edge case the function documents.
    assert d == 0.0 or abs(d) > 100, f"expected 0 or |d|>100 for zero-variance diff, got {d}"


def test_cohens_d_paired_meaningful():
    # Real diff with real variance
    a = np.array([0.6, 0.7, 0.8, 0.5, 0.75])
    b = np.array([0.5, 0.55, 0.6, 0.45, 0.65])
    d = cohens_d_paired(a, b)
    assert d > 1.0   # large effect


def test_lock_roundtrip(tmp_path):
    art = tmp_path / "data.json"
    art.write_text('{"hello": "world"}')
    lock = lock_state(tmp_path)
    assert "data.json" in lock["artifacts"]
    diff = verify_state(lock, tmp_path)
    assert diff["matches"]
    art.write_text('{"hello": "mutated"}')
    diff2 = verify_state(lock, tmp_path)
    assert not diff2["matches"]
    assert any(c["path"] == "data.json" for c in diff2["changed"])


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
