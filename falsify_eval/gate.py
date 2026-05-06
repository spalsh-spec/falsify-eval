"""Four-null Δ-metric gate. Corpus-agnostic and metric-agnostic.

Definition 1 of the methodology paper. Implements four orthogonal nulls:

  G_A — gold-label permutation (bijection π over the set of class labels)
  G_B — gold-label random (iid uniform draw per query)
  G_C — random retrieval (replace engine output with K random items)
  G_D — gold marginal-matched random (iid draw from empirical class frequency)

Null D is the new contribution; it correctly rejects predictors matched
to the empirical class marginal that A and B can false-positive.
"""
from __future__ import annotations

from collections import Counter
from typing import Callable, Sequence, Any

import numpy as np


def _grade(retrieved_lists, gold_list, rel_list, metric_fn):
    """Apply metric_fn(retrieved_ids, gold, rel) per-query, return mean."""
    return float(np.mean([
        metric_fn(r, g, rel) for r, g, rel in zip(retrieved_lists, gold_list, rel_list)
    ]))


def _validate_inputs(retrieved_lists, gold_list, rel_list, *,
                     item_pool, k: int, n_trials: int, tau: float) -> None:
    """Raise ValueError early on common input mistakes.

    Catches the failure modes that previously produced silent all-zero output
    or raw numpy ValueError from inside the null hypotheses.
    """
    n_r, n_g, n_rel = len(retrieved_lists), len(gold_list), len(rel_list)
    if not (n_r == n_g == n_rel):
        raise ValueError(
            f"length mismatch: retrieved_lists={n_r}, gold_list={n_g}, "
            f"rel_list={n_rel}; all three must have one entry per query"
        )
    if n_g == 0:
        raise ValueError("gold_list is empty — need at least one query")
    if not isinstance(k, int) or k < 1:
        raise ValueError(f"k must be a positive integer, got {k!r}")
    if not isinstance(n_trials, int) or n_trials < 1:
        raise ValueError(f"n_trials must be a positive integer, got {n_trials!r}")
    if not (0.0 <= tau <= 1.0):
        raise ValueError(f"tau must be in [0, 1], got {tau}")

    if item_pool is not None:
        pool = list(item_pool)
        if len(pool) == 0:
            raise ValueError("item_pool is empty")
        if k > len(pool):
            raise ValueError(
                f"k={k} > len(item_pool)={len(pool)}; Null C samples k items "
                f"without replacement from item_pool, so k must be ≤ pool size"
            )
        # Catch the silent gold-not-in-pool failure
        pool_set = set(pool)
        missing_gold = sorted({g for g in gold_list if g not in pool_set})
        if missing_gold:
            preview = missing_gold[:5]
            more = "" if len(missing_gold) <= 5 else f" (+{len(missing_gold)-5} more)"
            raise ValueError(
                f"{len(missing_gold)} gold label(s) not present in item_pool: "
                f"{preview}{more}; check label-set alignment between bench and pool"
            )

    distinct_gold = len(set(gold_list))
    if distinct_gold == 1:
        # Mathematically valid but worth a quiet flag in the result later;
        # we don't raise here because single-class benches are legitimate.
        pass


def null_a_permuted(retrieved_lists, gold_list, rel_list, metric_fn,
                    *, n_trials: int = 50, seed: int = 2026) -> np.ndarray:
    """G_A: permute gold labels via a bijection π over distinct labels.

    Type-preserving: permutes INDICES into the sorted label list rather than
    passing the labels to ``rng.permutation`` directly. Critical for tuple,
    dataclass, and any container-like label types — numpy auto-converts
    list-of-tuples into a 2D array, which silently changes the comparator
    semantics inside the user-supplied metric (same defect class as Mayank #1
    in null_b/null_d; closed for null_a in v0.1.5.1).

    Sort key is ``(type(x).__name__, repr(x))`` so mixed-type and unorderable
    label sets (frozen dataclasses without ``order=True``) are handled.

    Returns the array of N_trials null mean values.
    """
    rng = np.random.default_rng(seed)
    labels = sorted(set(gold_list), key=lambda x: (type(x).__name__, repr(x)))
    n = len(labels)
    means = np.empty(n_trials)
    for i in range(n_trials):
        perm_idx = rng.permutation(n)
        mapping = {labels[j]: labels[int(perm_idx[j])] for j in range(n)}
        new_gold = [mapping[g] for g in gold_list]
        means[i] = _grade(retrieved_lists, new_gold, rel_list, metric_fn)
    return means


def null_b_uniform(retrieved_lists, gold_list, rel_list, metric_fn,
                   *, n_trials: int = 50, seed: int = 2026) -> np.ndarray:
    """G_B: per-query iid uniform draw of gold from the label set.

    Type-preserving: draws indices into the label list rather than letting
    numpy coerce the labels themselves. This is the fix for Mayank's
    catastrophic-defect #1 (v0.1.4 wrapped each draw in str(), which
    silently disabled the gate for any non-string label type).
    """
    rng = np.random.default_rng(seed)
    labels = sorted(set(gold_list), key=lambda x: (type(x).__name__, repr(x)))
    n = len(labels)
    means = np.empty(n_trials)
    for i in range(n_trials):
        idx = rng.integers(0, n, size=len(gold_list))
        new_gold = [labels[j] for j in idx]
        means[i] = _grade(retrieved_lists, new_gold, rel_list, metric_fn)
    return means


def null_c_random_retrieval(gold_list, rel_list, metric_fn,
                            *, k: int = 5, item_pool: Sequence | None = None,
                            n_trials: int = 50, seed: int = 2026) -> np.ndarray:
    """G_C: replace engine output with K random items from item_pool.

    item_pool is REQUIRED for an honest Null C. Per Mayank-defect #2:
    defaulting to the gold-label set makes Null C ~1000× weaker than honest
    on a real corpus. The caller must pass the actual chunk-id / item pool;
    otherwise we raise rather than silently produce a misleading number.

    Type-preserving via index-based sampling.
    """
    if item_pool is None:
        raise ValueError(
            "null_c_random_retrieval requires item_pool. Defaulting to the "
            "gold-label set (as v0.1.4 did) makes Null C ~1000x weaker than "
            "an honest random-retrieval baseline. Pass item_pool=<your chunk "
            "pool> explicitly."
        )
    rng = np.random.default_rng(seed)
    pool = list(item_pool)
    n_pool = len(pool)
    if k > n_pool:
        raise ValueError(
            f"k={k} > len(item_pool)={n_pool}; Null C samples k items "
            f"without replacement from item_pool."
        )
    means = np.empty(n_trials)
    for i in range(n_trials):
        rand_lists = []
        for _ in gold_list:
            idx = rng.choice(n_pool, size=k, replace=False)
            rand_lists.append([pool[j] for j in idx])
        means[i] = _grade(rand_lists, gold_list, rel_list, metric_fn)
    return means


def null_d_marginal_matched(retrieved_lists, gold_list, rel_list, metric_fn,
                            *, n_trials: int = 50, seed: int = 2026) -> np.ndarray:
    """G_D — NEW IN THIS WORK: per-query iid draw of gold from the EMPIRICAL
    gold-frequency distribution. Catches predictors matched to the gold
    marginal (e.g., constant predictor of the most-frequent class) which
    A and B can false-positive.

    Type-preserving: draws indices into the label list rather than letting
    numpy coerce the labels themselves. This is the central fix for
    Mayank's catastrophic-defect #1 — without it, the headline guarantee
    of the gate is silently void for any non-string label type.
    """
    rng = np.random.default_rng(seed)
    counts = Counter(gold_list)
    labels = sorted(counts.keys(), key=lambda x: (type(x).__name__, repr(x)))
    n = len(labels)
    total = sum(counts.values())
    p = np.array([counts[t] / total for t in labels])
    means = np.empty(n_trials)
    for i in range(n_trials):
        idx = rng.choice(n, size=len(gold_list), p=p)
        new_gold = [labels[j] for j in idx]
        means[i] = _grade(retrieved_lists, new_gold, rel_list, metric_fn)
    return means


def four_null_gate(retrieved_lists,
                   gold_list,
                   rel_list,
                   metric_fn: Callable[[list, Any, Any], float],
                   *,
                   item_pool: Sequence | None = None,
                   k: int = 5,
                   n_trials: int = 50,
                   tau: float = 0.05,
                   seed: int = 2026,
                   progress: bool = False) -> dict:
    """Run all four nulls; return structured verdict.

    Args:
        progress: if True, prints per-stage timing to stderr so a user can
            tell whether a long-running gate is genuinely making progress or
            stuck. Critical for benches where ``metric_fn`` is expensive
            (e.g., calls an LLM-judge at ~200 ms / call).

    A note on runtime cost (added in v0.1.5.2 after Akosh-AI 5-hour incident):
    the gate calls ``metric_fn`` exactly ``N * (1 + 4 * n_trials)`` times.
    For an LLM-judge metric at 200 ms / call, that is ~6 hours on N=500
    with default n_trials=50. The library cannot speed up a slow metric, but
    ``progress=True`` will tell you per-stage where the time is going so you
    can decide to lower n_trials, cache calls, or parallelise outside the
    library.

    Returns:
        {
          "real_mean":         float,
          "null_means":        {"A": float, "B": float, "C": float, "D": float},
          "deltas":            {"A": float, "B": float, "C": float, "D": float},
          "passes":            {"A": bool,  "B": bool,  "C": bool,  "D": bool},
          "gate_passes":       bool,        # all 4 must pass
          "tau":               float,
          "n_trials":          int,
          "warnings":          list[str],
          "stage_seconds":     dict | None,   # only if progress=True
        }
    """
    _validate_inputs(retrieved_lists, gold_list, rel_list,
                     item_pool=item_pool, k=k, n_trials=n_trials, tau=tau)

    warnings: list[str] = []
    distinct_gold = len(set(gold_list))
    if distinct_gold == 1:
        warnings.append(
            "single-class benchmark: Null A and Null D collapse to the same "
            "distribution; treat ΔA and ΔD as one test, not two"
        )
    if item_pool is not None and len(gold_list) < 2 * len(set(item_pool)):
        warnings.append(
            f"sparse marginal: N={len(gold_list)} queries over "
            f"{len(set(item_pool))} pool items; Null D's marginal estimator "
            f"is noisy when N < 2·|pool| — Δ_D may behave like Δ_B"
        )

    import sys
    import time as _time
    stage_seconds: dict[str, float] = {}

    def _stage(label: str, fn):
        if not progress:
            return fn()
        t0 = _time.time()
        N = len(gold_list)
        n_calls = N if label == "real" else N * n_trials
        print(f"[falsify-eval] {label}: starting "
              f"({n_calls:,} metric_fn calls expected)",
              file=sys.stderr, flush=True)
        result = fn()
        elapsed = _time.time() - t0
        stage_seconds[label] = elapsed
        rate = n_calls / elapsed if elapsed > 0 else float("inf")
        print(f"[falsify-eval] {label}: done in {elapsed:7.2f}s "
              f"({rate:,.0f} calls/s)",
              file=sys.stderr, flush=True)
        return result

    real = _stage("real",   lambda: _grade(retrieved_lists, gold_list, rel_list, metric_fn))
    a    = _stage("null_a", lambda: null_a_permuted(retrieved_lists, gold_list, rel_list, metric_fn,
                                                    n_trials=n_trials, seed=seed).mean())
    b    = _stage("null_b", lambda: null_b_uniform(retrieved_lists, gold_list, rel_list, metric_fn,
                                                   n_trials=n_trials, seed=seed + 1).mean())
    c    = _stage("null_c", lambda: null_c_random_retrieval(gold_list, rel_list, metric_fn,
                                                            k=k, item_pool=item_pool,
                                                            n_trials=n_trials, seed=seed + 2).mean())
    d    = _stage("null_d", lambda: null_d_marginal_matched(retrieved_lists, gold_list, rel_list, metric_fn,
                                                            n_trials=n_trials, seed=seed + 3).mean())
    deltas = {"A": real - a, "B": real - b, "C": real - c, "D": real - d}
    passes = {x: deltas[x] >= tau for x in "ABCD"}
    result = {
        "real_mean":   real,
        "null_means":  {"A": a, "B": b, "C": c, "D": d},
        "deltas":      deltas,
        "passes":      passes,
        "gate_passes": all(passes.values()),
        "tau":         tau,
        "n_trials":    n_trials,
        "warnings":    warnings,
    }
    if progress:
        result["stage_seconds"] = stage_seconds
    return result
