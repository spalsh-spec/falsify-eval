# falsify-eval

### The missing test in AI evaluation.

A small, free library that catches a class of false positives that the standard
retrieval-evaluation pipeline silently accepts. Bring your own retrieval system,
your own corpus, your own metric — verify your numbers in thirty seconds.

```bash
pip install falsify-eval
python -m falsify_eval.examples.synthetic_demo
```

[![CI](https://github.com/spalsh-spec/falsify-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/spalsh-spec/falsify-eval/actions/workflows/ci.yml)
[![Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python ≥ 3.10](https://img.shields.io/badge/python-≥3.10-blue.svg)](https://www.python.org/)
[![Release](https://img.shields.io/github/v/release/spalsh-spec/falsify-eval?color=blue)](https://github.com/spalsh-spec/falsify-eval/releases/latest)
[![Docs](https://img.shields.io/badge/docs-README%20%2B%20preprint-blue)](#preprint)

> *A house of standards.* Released by **Bhardwaj & Sons** under Apache 2.0.
> The methodology is free, public, and citable so it can become a standard
> rather than a product. [bhardwajandsons.com](https://bhardwajandsons.com) →

---

## Why this exists

Most retrieval-system papers report a single aggregate metric (nDCG@k, MRR) and
call it a contribution. Three failure modes make this practice unsafe at any
benchmark size and dangerous on small ones:

1. **Null-distribution silence.** A learned ranker can absorb gold-label
   distribution shape without learning underlying query–document relevance.
   A constant predictor matched to the empirical class marginal can score
   non-trivially without using the query at all.
2. **Corpus drift between commits.** ALTER TABLE migrations and feedback-loop
   side effects mutate runtime artifacts without changing source code. A
   "score-neutral" annotation can be true about the source diff while false
   about the runnable system.
3. **Small-sample claims masquerading as significance.** A +0.02 metric gain
   on N < 50 queries usually sits inside the bench's noise floor.

This library implements a four-part falsification harness that addresses all
three, in <1000 lines of Python with only `numpy` as a runtime dependency:

| Component | What it does |
|---|---|
| **`four_null_gate`** | Tests engine output against four null distributions: gold-permuted (A), gold-uniform-random (B), random-retrieval (C), **gold-marginal-matched (D, novel)**. The gate PASSes when Δ ≥ τ on all four. Null D is original to this work; it correctly rejects predictors matched to the empirical gold marginal that A and B can false-positive. |
| **`lock_state` / `verify_state`** | Walk a directory, hash every binary artifact via SHA-256, bind to the current git commit. CI-enforceable verification exits non-zero on any drift. |
| **`bootstrap_ci`, `paired_permutation_p`, `cohens_d_paired`** | Statistical reporting requirements: bootstrap confidence intervals on means and paired differences, paired permutation tests, effect-size reporting. |
| **`power_n_required`** | Compute N required to detect an observed Δ at α=0.05, power=0.80. Quantifies why your UNDER-NS verdict is UNDER-NS. |

The methodology is corpus-agnostic, metric-agnostic, and engine-agnostic. The
public interface accepts any callable that returns top-K rankings.

## Quick demo

```bash
git clone https://github.com/<your-handle>/falsify-eval.git
cd falsify-eval
pip install -e .
python3 examples/synthetic_demo.py
```

The demo runs the four-null gate on three systems against a 50-query synthetic
benchmark with 5 labels: a constant predictor (deliberately broken), a mock
plausible engine (70% top-1 hit rate), and an oracle (perfect top-1).

Expected output:

```
=== System: constant_predictor (deliberately broken) ===
  real mean nDCG@5 = 0.X
    Null A:  Δ ≈ +0   ✓ but small
    Null B:  Δ ≈ +0   ✓ but small
    Null D:  Δ = exactly 0.0000   ✗ FAIL  ← marginal-matched null catches it
  GATE: ✗ FAIL (correctly rejected)

=== System: mock_engine (plausible retrieval) ===
  real mean nDCG@5 = 0.6X
    Δ ≥ +0.4 across all 4 nulls   ✓ PASS
  GATE: ✓ PASS (correctly accepted)

=== System: oracle (upper bound) ===
  real mean nDCG@5 = 1.0
  GATE: ✓ PASS by maximum margin
```

## Library API (one example each)

```python
import numpy as np
from falsify_eval import four_null_gate, lock_state, verify_state
from falsify_eval import bootstrap_ci, paired_permutation_p, cohens_d_paired


# 1. The four-null gate
def my_metric(retrieved_ids, gold, rel):
    """Your scoring function. Return float in [0, 1]."""
    return 1.0 if gold in retrieved_ids[:5] else 0.0

result = four_null_gate(
    retrieved_lists=engine_top_k_per_query,    # list of lists of item-ids
    gold_list=gold_label_per_query,             # list of class labels
    rel_list=relevance_per_query,               # list of relevance grades
    metric_fn=my_metric,
    item_pool=all_item_ids_in_corpus,           # for null C
    k=5, n_trials=50, tau=0.05, seed=2026,
)
assert result["gate_passes"], f"Engine failed gate: {result['deltas']}"


# 2. Cryptographic state lock
import json
lock = lock_state("./corpus", git_repo=".", bench_score=result["real_mean"])
with open("corpus.lock.json", "w") as f:
    json.dump(lock, f, indent=2, sort_keys=True)

# Later (in CI or before reporting a score):
diff = verify_state("corpus.lock.json", "./corpus")
assert diff["matches"], f"Corpus drift: {diff}"


# 3. Statistical reporting
mean, ci_lo, ci_hi, sd = bootstrap_ci(per_query_scores)
delta_mean, p = paired_permutation_p(scores_with_feature, scores_without)
d = cohens_d_paired(scores_with_feature, scores_without)

verdict = (
    "HIT"      if delta_mean > 0 and p < 0.05 else
    "UNDER-NS" if delta_mean > 0 else
    "MISS"
)
```

## What the harness *does* prove (Proposition 1)

If the four-null gate PASSes (Δ ≥ τ on all four nulls) at N_trials = 50,
τ = 0.05, then with Bonferroni-corrected confidence ≥ 0.95:

- The engine is **not** equivalent to a label-permutation-invariant ranker (rejected by G_A).
- The engine is **not** achieving its score solely via the uniform-class-prior assumption (rejected by G_B).
- The engine is **not** equivalent to a uniform-random retriever (rejected by G_C).
- The engine is **not** equivalent to a gold-marginal-matched predictor (rejected by G_D — *new in this work*).

## What the harness does **not** prove

A passing gate is a *necessary* condition for credible reporting, not sufficient.
It does not prove (a) the engine learned the actual relevance signal, only that
it learned *something* beyond the four enumerated trivial classes; (b) the
engine generalises beyond the evaluation set; (c) per-feature contribution
claims are significant (handled separately by the statistical reporting
helpers); (d) the engine is free of bench-developer overfitting in query
phrasing.

## Preprint

The companion methodology paper is included in this repository:

- [`PREPRINT.md`](PREPRINT.md) — *Calibrated Falsification Harnesses for Retrieval Evaluation* (v7, with N=10,000 validation, broken-predictor suite, sensitivity grid, and the soundness proposition for the four-null gate).
- [`SUPPLEMENTARY.md`](SUPPLEMENTARY.md) — extended tables, ablations, and the bench-size calibration curve.

Submission to arXiv is pending. The DOI will be added to `CITATION.cff` on acceptance. In the interim, the markdown is the canonical source; both files are immutable for v0.1.0 (verifiable via `lock_state` against the v0.1.0 tag).

## How this complements existing tools

| Capability | DVC | MLflow | W&B Artifacts | Ragas | TruLens | falsify-eval |
|---|---|---|---|---|---|---|
| Vendor-free | ✓ | ✓ (server) | ✗ | ✓ | partial | ✓ |
| Pure-text human-readable lock | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Couples artifact hash + verified score | ✗ | ✗ | partial | ✗ | partial | ✓ |
| Falsification gate (CI-enforced) | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Marginal-matched null | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Positive-control self-validation | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |

## Citation

If this library helps your work, please cite the methodology paper:

```bibtex
@article{sharma2026calibrated,
  title  = {Calibrated Falsification Harnesses for Retrieval Evaluation},
  author = {Sharma, Sparsh},
  year   = {2026},
  eprint = {<arxiv-id-when-published>},
  archivePrefix = {arXiv},
  primaryClass  = {cs.IR}
}
```

## Contributing

Issues and PRs welcome. The reference implementation is intentionally minimal;
the goal is for the protocol to be small enough that adopters audit the entire
library before depending on it.

## Status

v0.1.0 — initial public release. The interfaces are documented in the
methodology paper and intended to be stable; minor implementation refinements
expected through v0.x; v1.0 ships when the broken-predictor suite is extended
to cover at least 10 distinct broken systems.

---

*Independent work. No institutional affiliation. Apache 2.0.*
