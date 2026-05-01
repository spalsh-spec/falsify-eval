"""examples/synthetic_demo.py — minimal end-to-end demo on a synthetic
toy benchmark (50 queries, 5 classes, no external corpus required).

Demonstrates the four-null gate correctly classifying:
  - constant_predictor  → FAIL (correctly)
  - real_engine_mock    → PASS (correctly)
  - oracle              → PASS (correctly)

Run:
    python3 examples/synthetic_demo.py
"""
from __future__ import annotations

import math
import random
import sys
from collections import Counter
from pathlib import Path

# allow `python3 examples/synthetic_demo.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from falsify_eval import four_null_gate

# ── nDCG@5 implementation (caller supplies their own metric in production) ──
def ndcg_at_k(retrieved, gold, rel, k=5):
    rels = [rel if r == gold else 0 for r in retrieved[:k]]
    ideal = sorted(rels, reverse=True)
    idcg = sum(r / math.log2(i + 2) for i, r in enumerate(ideal[:k]))
    if idcg == 0:
        return 0.0
    dcg = sum(r / math.log2(i + 2) for i, r in enumerate(rels[:k]))
    return dcg / idcg

# ── Synthetic toy bench ─────────────────────────────────────────────────────
# Use 12 labels with k=5 retrieval so Null C (random retrieval over the label
# pool) is meaningful — choosing 5 of 12 labels gives ~42% chance to include
# the gold by random alone. With LABELS=5 and k=5 that probability would be 1
# (degenerate), making Null C uninformative.
LABELS = [f"L{i:02d}" for i in range(12)]
random.seed(2026)
# Gold marginal weighted toward L00 / L01 (these get more queries) so the
# constant-predictor → Null D contrast shows clearly.
weights = [6, 4, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1]
QUERIES = [
    (f"query_{i}", random.choices(LABELS, weights=weights, k=1)[0], 3)
    for i in range(50)
]
gold_list = [g for _, g, _ in QUERIES]
rel_list  = [r for _, _, r in QUERIES]

# A "good" mock engine: returns the correct label as its top-1 with prob 0.7,
# random otherwise. Plausible retrieval system.
def mock_engine(query, gold):
    rng = random.Random(hash(query))
    if rng.random() < 0.7:
        head = [gold] + rng.sample([l for l in LABELS if l != gold], 4)
    else:
        head = rng.sample(LABELS, 5)
    return head

# A constant predictor: always returns 5x most-frequent class.
most_common_label = Counter(gold_list).most_common(1)[0][0]
def constant_predictor(query, gold):
    return [most_common_label] * 5

# An oracle: always returns gold as top-1, then 4 random.
def oracle(query, gold):
    rng = random.Random(hash(query))
    rest = [l for l in LABELS if l != gold]
    return [gold] + rng.sample(rest, 4)

# ── Run gate on each system ────────────────────────────────────────────────
def grade(retrieved_lists, system_name):
    print(f"\n=== System: {system_name} ===")
    result = four_null_gate(
        retrieved_lists, gold_list, rel_list, ndcg_at_k,
        item_pool=LABELS, k=5, n_trials=100, tau=0.05, seed=2026,
    )
    print(f"  real mean nDCG@5 = {result['real_mean']:.4f}")
    for x in "ABCD":
        m = result["null_means"][x]
        d = result["deltas"][x]
        verdict = "✓" if result["passes"][x] else "✗"
        print(f"    Null {x}:  mean={m:.4f}  Δ={d:+.4f}  {verdict}")
    print(f"  GATE: {'✓ PASS' if result['gate_passes'] else '✗ FAIL'}")
    return result


def main():
    print("falsify-eval demo on a 50-query synthetic toy benchmark")
    print(f"  {len(QUERIES)} queries, 5 labels, gold marginal weighted toward 'A'")

    for name, fn in [
        ("constant_predictor (deliberately broken)", constant_predictor),
        ("mock_engine (plausible retrieval)",        mock_engine),
        ("oracle (upper bound)",                     oracle),
    ]:
        retrieved_lists = [fn(q, g) for q, g, _ in QUERIES]
        grade(retrieved_lists, name)

    print("\nExpected: constant_predictor FAILS (esp. Null D); the other two PASS.")


if __name__ == "__main__":
    main()
