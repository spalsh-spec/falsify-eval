# CS02 — falsify-eval against SciFact (BEIR)

> **Why this exists.** CS01 (NFCorpus) showed the gate working but surfaced an
> unexpected effect: under nDCG@10, even legitimate retrievers were failing
> because NFCorpus's dense relevance (~38 relevant docs / query) collapsed
> the null distributions. CS02 triangulates that finding by running the same
> protocol on SciFact, which has *sparse* relevance (~1.1 relevant docs / query).
> Different benchmark, same systems, same protocol — does the gate still work?

## TL;DR

On the BEIR/SciFact test split (300 queries, 5,183 documents, ~1.1 relevant docs/query):

| System                | nDCG@10 | recall@5\_top1 | gate (nDCG) | gate (recall) |
|-----------------------|--------:|---------------:|:-----------:|:-------------:|
| Mira (constant)       |  0.049  |          0.053 |   ✗ FAIL    |   ✗ FAIL      |
| Popularity top-K      |  0.049  |          0.053 |   ✗ FAIL    |   ✗ FAIL      |
| BM25                  |  0.567  |          0.630 |   ✓ PASS    |   ✓ PASS      |
| Dense (MiniLM-L6-v2)  |  0.648  |          0.737 |   ✓ PASS    |   ✓ PASS      |

**This is cleaner than CS01.** On SciFact, *both* metrics correctly distinguish cheaters from legitimate retrievers. The CS01 metric-sensitivity finding was not a gate flaw — it was an artefact of NFCorpus's dense relevance. The gate works correctly when the metric is appropriate to the benchmark structure.

Reproducible in 70 seconds on M1 16 GB.

---

## What CS02 confirms vs CS01

| Question | CS01 (NFCorpus, dense relevance) | CS02 (SciFact, sparse relevance) |
|---|---|---|
| Does the gate reject Mira/popularity? | yes (Δ_D ≈ 0 on both metrics) | yes (Δ_D ≈ 0 on both metrics) |
| Does the gate accept BM25? | only under recall@5 (Δ_D = +0.140); fails under nDCG@10 | yes on both (Δ_D = +0.211 nDCG, +0.627 recall) |
| Does the gate accept dense MiniLM? | only under recall@5 (Δ_D = +0.178); fails under nDCG@10 | yes on both (Δ_D = +0.241 nDCG, +0.734 recall) |
| Does metric choice matter? | yes — graded metric on dense relevance hides null separation | no — sparse relevance gives both metrics clean separation |

**Joint finding from CS01 + CS02:** the gate is sound. The metric-sensitivity caveat applies *specifically* to graded metrics on multi-label benchmarks where average relevant-docs-per-query is high. As a rule-of-thumb threshold from these two data points: when the average exceeds ~5 relevant docs/query, prefer a single-gold strict metric (recall@K against top-1 gold). When it's near 1, either metric works.

---

## Reproducibility manifest

| Field | Value |
|---|---|
| Benchmark | BEIR / SciFact, test split |
| Source | `BeIR/scifact` (corpus + queries) and `BeIR/scifact-qrels` (test) on HuggingFace |
| Corpus size | 5,183 documents |
| Test queries | 300 (with ≥1 relevant doc) |
| Relevance entries | 339 (~1.1 relevant docs/query) |
| Corpus sha256[:16] | `8746799146f0abe5` |
| Queries sha256[:16] | `0ee762ffc05a9182` |
| Random seed | 2026 |
| n\_trials | 30 |
| τ | 0.05 |
| Total runtime | ~66 seconds end-to-end |
| Peak RAM | <2 GB |

### Reproduce

```bash
cd case_studies/cs02_scifact
python3 run_case_study.py
```

### Implementation note

SciFact uses **integer** `query-id` and `corpus-id` in the qrels, while the corpus and queries datasets use **string** `_id`. CS02's loader normalises everything to string before joining. CS01's loader did not need this; this is a per-benchmark idiosyncrasy of the BEIR HuggingFace mirror, not a gate issue. *(Caught by running the case study; documented here as guidance for future CS03+.)*

---

## Comparison to published BEIR scores

| System | Published nDCG@10 (BEIR Table 2) | Our nDCG@10 |
|---|---:|---:|
| BM25 | 0.665 (Anserini, proper tokenisation) | 0.567 (rank\_bm25, simple `.split()` tokenisation) |
| MiniLM-L6-v2 dense | not reported directly; SBERT models on SciFact range 0.55–0.69 | 0.648 |

Our BM25 number is below published because we use a deliberately-cheap configuration (`.split()` lowercase tokenisation, default BM25 params) — the goal is reproducibility on a laptop in <2 minutes, not to match the SOTA tokeniser stack. Dense is in range.

---

## Joint CS01 + CS02 picture

Two real benchmarks, two relevance regimes (dense vs sparse), four broken predictors tested across both, four legitimate retrievers tested across both. Across all eight ⟨benchmark, system⟩ pairs:

- **All four cheaters fail the gate** under their appropriate metric. Δ_D ≈ 0 in every case.
- **All four legitimate retrievers pass the gate** under recall@5\_top1. Δ_D ranges from +0.14 to +0.73.
- **Under nDCG@10, dense-relevance benchmarks (NFCorpus) flatten the gate.** Sparse-relevance benchmarks (SciFact) do not.

That's the empirical foundation that the documentation lacked before today.

CS03 (FiQA, financial domain, denser than SciFact but sparser than NFCorpus) and CS04 (Quora, paraphrase retrieval) will further triangulate the metric-sensitivity finding. Both planned for this week.
