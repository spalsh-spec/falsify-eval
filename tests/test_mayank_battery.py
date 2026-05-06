"""Mayank Singh adversarial battery (v0.1.5).

47-test stress run by Mayank Singh / "Indian AI Lab" against falsify-eval
v0.1.4. Surfaced 14 real defects. This module is the public regression
suite for those defects: every test below is a pinned counter-example to
something v0.1.4 got wrong.

Credit: Mayank Singh — adversarial review that produced v0.1.5.
"""
from __future__ import annotations

import math
import numpy as np
import pytest

from falsify_eval import (
    four_null_gate,
    null_a_permuted, null_b_uniform,
    null_c_random_retrieval, null_d_marginal_matched,
    lock_state, verify_state,
)
from falsify_eval.lock import DEFAULT_TRACKED


# --------------------------------------------------------------------------- #
# Defect #1 — str() cast catastrophe (the headline bug).                      #
# v0.1.4 wrapped each random gold draw in str(). For any non-string label    #
# type, the comparator inside the metric never matched, the null mean       #
# collapsed to ~0, Δ → real, and a constant predictor passed the gate.      #
# v0.1.5 must use type-preserving index-based sampling.                      #
# --------------------------------------------------------------------------- #

def _exact_match(retrieved, gold, rel):
    return 1.0 if gold in retrieved[:5] else 0.0


def _build_constant_cheater(gold_list, labels, k=5):
    """Engine that always returns the most-frequent class K times."""
    from collections import Counter
    most_common = Counter(gold_list).most_common(1)[0][0]
    return [[most_common] * k for _ in gold_list]


@pytest.mark.parametrize("label_type", ["str", "int", "np_int64", "float"])
def test_d1_str_cast_constant_cheater_fails_d_for_all_label_types(label_type):
    """Constant-most-frequent predictor must FAIL Null D for every label type.

    v0.1.4: passed silently for int/float/np.int64 because str(label) erased the type.
    v0.1.5: index-based sampling; cheater fails on every type.
    """
    n = 120
    if label_type == "str":
        labels = [f"L{i}" for i in range(8)]
    elif label_type == "int":
        labels = list(range(8))
    elif label_type == "np_int64":
        labels = [np.int64(i) for i in range(8)]
    elif label_type == "float":
        labels = [float(i) for i in range(8)]

    gold = [labels[i % 8] for i in range(n)]
    rels = [3] * n
    retrieved = _build_constant_cheater(gold, labels, k=5)

    res = four_null_gate(retrieved, gold, rels, _exact_match,
                         item_pool=labels, k=5, n_trials=40, tau=0.05, seed=2026)
    assert not res["gate_passes"], (
        f"[{label_type}] constant cheater MUST fail; deltas={res['deltas']}"
    )
    assert abs(res["deltas"]["D"]) < 0.05, (
        f"[{label_type}] Null D should cancel the marginal-matched cheater, "
        f"got Δ_D={res['deltas']['D']}"
    )


# --------------------------------------------------------------------------- #
# Defect #2 — Null C silently used gold-label set as the pool.                #
# That makes the random-retrieval baseline ~|gold-set|/|real-pool| times     #
# stronger than honest. v0.1.5 requires item_pool explicitly.                #
# --------------------------------------------------------------------------- #

def test_d2_null_c_requires_item_pool():
    with pytest.raises(ValueError, match="item_pool"):
        null_c_random_retrieval(["A"] * 10, [3] * 10, _exact_match,
                                k=3, item_pool=None, n_trials=5, seed=1)


def test_d2_null_c_k_must_fit_pool():
    with pytest.raises(ValueError, match="k=10 > len.item_pool.=3"):
        null_c_random_retrieval(["A"] * 10, [3] * 10, _exact_match,
                                k=10, item_pool=["A", "B", "C"], n_trials=5, seed=1)


# --------------------------------------------------------------------------- #
# Defect #4 — README/docstring oversold "cryptographic". The lock is a       #
# SHA-256 + git-commit integrity check, not a tamper-proof cryptographic     #
# seal. v0.1.5 corrects the framing and documents the threat model.          #
# --------------------------------------------------------------------------- #

def test_d4_lock_docstring_threat_model_present():
    from falsify_eval import lock as lock_module
    doc = (lock_module.__doc__ or "")
    assert "Threat model" in doc, "lock.py must document its threat model"
    assert "NOT a tamper-proof" in doc, (
        "lock.py docstring must explicitly say it is not tamper-proof"
    )


# --------------------------------------------------------------------------- #
# Defect #5 — DEFAULT_TRACKED extension list excluded source files (.py,    #
# .md, .csv, .yaml). Reasonable default — but undocumented in v0.1.4. The   #
# v0.1.5 docstring spells out (a) what's tracked, (b) why source files are  #
# not, (c) how to add them.                                                  #
# --------------------------------------------------------------------------- #

def test_d5_default_tracked_documented_and_extensible(tmp_path):
    """Default tracks binary artifacts; source files are intentionally skipped.
    Caller can opt in by passing tracked_extensions explicitly."""
    (tmp_path / "data.json").write_text('{"ok": true}')
    (tmp_path / "README.md").write_text("# hi")
    (tmp_path / "script.py").write_text("print('x')")

    # Default: only .json tracked.
    lock = lock_state(tmp_path)
    assert "data.json" in lock["artifacts"]
    assert "README.md" not in lock["artifacts"]
    assert "script.py" not in lock["artifacts"]

    # Opt-in: caller can extend.
    lock2 = lock_state(tmp_path,
                       tracked_extensions=DEFAULT_TRACKED | {".md", ".py"})
    assert "README.md" in lock2["artifacts"]
    assert "script.py" in lock2["artifacts"]


# --------------------------------------------------------------------------- #
# Defect #6 — empty inputs produced RuntimeWarning + NaN in v0.1.2; v0.1.3 #
# added a clean ValueError. Lock that contract here.                         #
# --------------------------------------------------------------------------- #

def test_d6_empty_gold_list_raises_clean_value_error():
    with pytest.raises(ValueError, match="empty"):
        four_null_gate([], [], [], _exact_match,
                       item_pool=["A"], k=1, n_trials=5, tau=0.05, seed=1)


# --------------------------------------------------------------------------- #
# Defect #7 — version drift between __init__.py and pyproject.toml.          #
# --------------------------------------------------------------------------- #

def test_d7_version_sync():
    import falsify_eval
    import re
    pyproject = open(
        __file__.replace("tests/test_mayank_battery.py", "pyproject.toml")
    ).read()
    m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    assert m, "could not find version in pyproject.toml"
    assert m.group(1) == falsify_eval.__version__, (
        f"version drift: pyproject={m.group(1)} __init__={falsify_eval.__version__}"
    )


# --------------------------------------------------------------------------- #
# Defect #8 — Null A and Null D collapse to identical distributions for     #
# single-class benches. v0.1.4 silently double-counted; v0.1.5 emits a      #
# warning so the user knows ΔA and ΔD are one test, not two.                #
# --------------------------------------------------------------------------- #

def test_d8_single_class_bench_emits_warning():
    res = four_null_gate(
        [["A", "B", "C"]] * 100, ["A"] * 100, [3] * 100, _exact_match,
        item_pool=["A", "B", "C", "D"], k=3, n_trials=10, tau=0.05, seed=1,
    )
    assert any("single-class" in w for w in res["warnings"])
    assert res["deltas"]["A"] == res["deltas"]["D"]


# --------------------------------------------------------------------------- #
# Defect #9 — when N << |item_pool|, Null D's marginal estimator is         #
# essentially Null B because every label appears at most once. v0.1.5       #
# warns the caller.                                                          #
# --------------------------------------------------------------------------- #

def test_d9_sparse_marginal_warning():
    LABELS = [f"L{i:04d}" for i in range(500)]
    res = four_null_gate(
        [["L0000", "L0001", "L0002"]] * 30,
        [LABELS[i] for i in range(30)],
        [3] * 30, _exact_match,
        item_pool=LABELS, k=3, n_trials=10, tau=0.05, seed=1,
    )
    assert any("sparse marginal" in w for w in res["warnings"])


# --------------------------------------------------------------------------- #
# Defect #10 — type confusion across nulls. The label set used internally  #
# in null_b/null_d MUST be order-stable across runs and across types. The   #
# v0.1.5 sort key (type-name, repr) gives total order even with mixed types. #
# --------------------------------------------------------------------------- #

def test_d10_label_set_order_stable_across_runs():
    gold = [1, "a", 2, "b", 1, "a"]
    res1 = null_b_uniform(
        [["x"]] * 6, gold, [1] * 6, _exact_match, n_trials=3, seed=42
    )
    res2 = null_b_uniform(
        [["x"]] * 6, gold, [1] * 6, _exact_match, n_trials=3, seed=42
    )
    assert np.array_equal(res1, res2), "same seed must give identical output"


# --------------------------------------------------------------------------- #
# Defect #11 — k must be a positive integer; v0.1.4 accepted floats and    #
# zero, then crashed deep inside numpy. v0.1.5 rejects up front.            #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("bad_k", [0, -1, 0.5, "5", None])
def test_d11_k_must_be_positive_int(bad_k):
    with pytest.raises(ValueError, match="k must be"):
        four_null_gate([["A"]] * 5, ["A"] * 5, [3] * 5, _exact_match,
                       item_pool=["A", "B"], k=bad_k, n_trials=5, tau=0.05, seed=1)


# --------------------------------------------------------------------------- #
# Defect #12 — tau outside [0, 1] silently produced wrong gate verdicts.   #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("bad_tau", [-0.1, 1.5, 2.0])
def test_d12_tau_must_be_in_unit_interval(bad_tau):
    with pytest.raises(ValueError, match="tau must be in"):
        four_null_gate([["A"]] * 5, ["A"] * 5, [3] * 5, _exact_match,
                       item_pool=["A", "B"], k=1, n_trials=5, tau=bad_tau, seed=1)


# --------------------------------------------------------------------------- #
# Defect #13 — gold label not in item_pool used to silently produce all-   #
# zero output (because Null C could never sample the gold). v0.1.5 raises. #
# --------------------------------------------------------------------------- #

def test_d13_gold_not_in_pool_raises():
    with pytest.raises(ValueError, match="gold label.s. not present"):
        four_null_gate(
            [["A", "B"]] * 10, ["Z"] * 10, [3] * 10, _exact_match,
            item_pool=["A", "B", "C"], k=2, n_trials=5, tau=0.05, seed=1,
        )


# --------------------------------------------------------------------------- #
# Defect #14 — input length mismatch silently truncated to the shortest    #
# of the three lists. v0.1.5 raises with the exact lengths.                  #
# --------------------------------------------------------------------------- #

def test_d14_length_mismatch_raises_with_lengths():
    with pytest.raises(ValueError, match="length mismatch.*retrieved_lists=5"):
        four_null_gate(
            [["A"]] * 5, ["A"] * 10, [3] * 10, _exact_match,
            item_pool=["A", "B"], k=1, n_trials=5, tau=0.05, seed=1,
        )


# --------------------------------------------------------------------------- #
# Determinism check — the whole gate result must be byte-identical for the #
# same seed. This locks down everything Mayank's battery touched at once.   #
# --------------------------------------------------------------------------- #

def test_d1b_tuple_labels_no_crash_oracle_passes_cheater_fails():
    """v0.1.5 left null_a passing labels to rng.permutation, which converts
    list-of-tuples to a 2D numpy array and breaks the comparator inside the
    user metric. v0.1.5.1 closes the third null with the same index-based
    pattern as null_b/null_d."""
    import numpy as np
    labels = [(i, i + 1) for i in range(8)]
    gold = [labels[i % 8] for i in range(80)]

    oracle = [[g] + [labels[(i + 1) % 8]] * 4 for i, g in enumerate(gold)]
    cheater = [[labels[0]] * 5 for _ in gold]

    r_oracle = four_null_gate(oracle, gold, [3] * 80, _exact_match,
                              item_pool=labels, k=5, n_trials=15, tau=0.05, seed=1)
    r_cheat = four_null_gate(cheater, gold, [3] * 80, _exact_match,
                             item_pool=labels, k=5, n_trials=15, tau=0.05, seed=1)
    assert r_oracle["gate_passes"], f"tuple oracle must pass, deltas={r_oracle['deltas']}"
    assert not r_cheat["gate_passes"], "tuple constant cheater must FAIL the gate"


def test_d1c_dataclass_labels_no_crash_oracle_passes_cheater_fails():
    """Frozen dataclasses without order=True don't support `<`. v0.1.4 and v0.1.5
    crashed inside null_a's naked sorted(). v0.1.5.1 uses (type, repr) sort key."""
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class Lbl:
        name: str

    labels = [Lbl(f"x{i}") for i in range(8)]
    gold = [labels[i % 8] for i in range(80)]
    oracle = [[g] + [labels[(i + 1) % 8]] * 4 for i, g in enumerate(gold)]
    cheater = [[labels[0]] * 5 for _ in gold]

    r_oracle = four_null_gate(oracle, gold, [3] * 80, _exact_match,
                              item_pool=labels, k=5, n_trials=15, tau=0.05, seed=1)
    r_cheat = four_null_gate(cheater, gold, [3] * 80, _exact_match,
                             item_pool=labels, k=5, n_trials=15, tau=0.05, seed=1)
    assert r_oracle["gate_passes"], f"dataclass oracle must pass, deltas={r_oracle['deltas']}"
    assert not r_cheat["gate_passes"], "dataclass constant cheater must FAIL the gate"


def test_full_gate_determinism():
    LABELS = [f"L{i}" for i in range(10)]
    GOLD = [LABELS[i % 10] for i in range(60)]
    rng = np.random.default_rng(42)
    retrieved = []
    for g in GOLD:
        rest = [l for l in LABELS if l != g]
        retrieved.append([g] + list(rng.choice(rest, size=4, replace=False)))

    r1 = four_null_gate(retrieved, GOLD, [3] * 60, _exact_match,
                        item_pool=LABELS, k=5, n_trials=15, tau=0.05, seed=2026)
    r2 = four_null_gate(retrieved, GOLD, [3] * 60, _exact_match,
                        item_pool=LABELS, k=5, n_trials=15, tau=0.05, seed=2026)
    assert r1["deltas"] == r2["deltas"], "same seed must give identical deltas"
    assert r1["gate_passes"] == r2["gate_passes"]
