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


def null_a_permuted(retrieved_lists, gold_list, rel_list, metric_fn,
                    *, n_trials: int = 50, seed: int = 2026) -> np.ndarray:
    """G_A: permute gold labels via a bijection π over distinct labels.

    Returns the array of N_trials null mean values.
    """
    rng = np.random.default_rng(seed)
    labels = sorted(set(gold_list))
    means = np.empty(n_trials)
    for i in range(n_trials):
        perm = rng.permutation(labels)
        mapping = dict(zip(labels, perm))
        new_gold = [mapping[g] for g in gold_list]
        means[i] = _grade(retrieved_lists, new_gold, rel_list, metric_fn)
    return means


def null_b_uniform(retrieved_lists, gold_list, rel_list, metric_fn,
                   *, n_trials: int = 50, seed: int = 2026) -> np.ndarray:
    """G_B: per-query iid uniform draw of gold from the label set."""
    rng = np.random.default_rng(seed)
    labels = sorted(set(gold_list))
    means = np.empty(n_trials)
    for i in range(n_trials):
        new_gold = [str(rng.choice(labels)) for _ in gold_list]
        means[i] = _grade(retrieved_lists, new_gold, rel_list, metric_fn)
    return means


def null_c_random_retrieval(gold_list, rel_list, metric_fn,
                            *, k: int = 5, item_pool: Sequence | None = None,
                            n_trials: int = 50, seed: int = 2026) -> np.ndarray:
    """G_C: replace engine output with K random items from item_pool.

    If item_pool is None, defaults to the set of distinct labels (which
    measures "random retrieval over the label space" rather than the chunk
    pool — caller should pass the actual chunk-id pool for the strict version).
    """
    rng = np.random.default_rng(seed)
    pool = list(item_pool) if item_pool is not None else sorted(set(gold_list))
    means = np.empty(n_trials)
    for i in range(n_trials):
        rand_lists = [list(rng.choice(pool, size=k, replace=False)) for _ in gold_list]
        means[i] = _grade(rand_lists, gold_list, rel_list, metric_fn)
    return means


def null_d_marginal_matched(retrieved_lists, gold_list, rel_list, metric_fn,
                            *, n_trials: int = 50, seed: int = 2026) -> np.ndarray:
    """G_D — NEW IN THIS WORK: per-query iid draw of gold from the EMPIRICAL
    gold-frequency distribution. Catches predictors matched to the gold
    marginal (e.g., constant predictor of the most-frequent class) which
    A and B can false-positive.
    """
    rng = np.random.default_rng(seed)
    counts = Counter(gold_list)
    labels = sorted(counts.keys())
    p = np.array([counts[t] / sum(counts.values()) for t in labels])
    means = np.empty(n_trials)
    for i in range(n_trials):
        new_gold = [str(rng.choice(labels, p=p)) for _ in gold_list]
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
                   seed: int = 2026) -> dict:
    """Run all four nulls; return structured verdict.

    Returns:
        {
          "real_mean":         float,
          "null_means":        {"A": float, "B": float, "C": float, "D": float},
          "deltas":            {"A": float, "B": float, "C": float, "D": float},
          "passes":            {"A": bool,  "B": bool,  "C": bool,  "D": bool},
          "gate_passes":       bool,        # all 4 must pass
          "tau":               float,
          "n_trials":          int,
        }
    """
    real = _grade(retrieved_lists, gold_list, rel_list, metric_fn)
    a = null_a_permuted(retrieved_lists, gold_list, rel_list, metric_fn,
                        n_trials=n_trials, seed=seed).mean()
    b = null_b_uniform(retrieved_lists, gold_list, rel_list, metric_fn,
                       n_trials=n_trials, seed=seed + 1).mean()
    c = null_c_random_retrieval(gold_list, rel_list, metric_fn,
                                k=k, item_pool=item_pool,
                                n_trials=n_trials, seed=seed + 2).mean()
    d = null_d_marginal_matched(retrieved_lists, gold_list, rel_list, metric_fn,
                                n_trials=n_trials, seed=seed + 3).mean()
    deltas = {"A": real - a, "B": real - b, "C": real - c, "D": real - d}
    passes = {x: deltas[x] >= tau for x in "ABCD"}
    return {
        "real_mean":   real,
        "null_means":  {"A": a, "B": b, "C": c, "D": d},
        "deltas":      deltas,
        "passes":      passes,
        "gate_passes": all(passes.values()),
        "tau":         tau,
        "n_trials":    n_trials,
    }
