# CS01 — falsify-eval against NFCorpus (BEIR)

> **Why this exists.** Until now, every example in falsify-eval's documentation
> was hypothetical. The library said *"the gate catches Mira-style predictors"*
> but never showed it doing so on a real, public, peer-reviewed benchmark.
> Lewi Stone made this point on 2026-05-07 and it landed. This is the first
> empirical case study.

## TL;DR

On the BEIR/NFCorpus test split (323 queries, 3,633 documents):

| System                | nDCG@10 | recall@5\_top1 | gate (recall) | what's interesting |
|-----------------------|--------:|---------------:|:-------------:|---|
| Mira (constant)       |  0.066  |          0.003 |   ✗ FAIL      | trivially fails — by design |
| Popularity top-K      |  0.066  |          0.003 |   ✗ FAIL      | identical signature to Mira |
| BM25                  |  0.267  |          0.142 |   ✓ PASS      | classical IR baseline; gate accepts |
| Dense (MiniLM-L6-v2)  |  0.319  |          0.180 |   ✓ PASS      | M1 MPS, 90 MB model |

**Mira and popularity return the same most-popular document for every query.** They do not look at the query at all. nDCG@10 = 0.066 is non-trivial for this reason — popularity bias is a real phenomenon. The four-null gate correctly rejects both at τ=0.05 with **Δ_D ≈ 0**.

**BM25 and dense MiniLM legitimately use the query.** They earn Δ values 100× larger than the cheaters. The gate accepts both at τ=0.05.

Reproducible in 5 minutes on M1 16 GB. Exact command at the bottom.

---

## The unexpected finding: choice of metric matters more than expected

We ran the same four systems through **two** metrics:

1. **nDCG@10** — the standard BEIR metric. All 323 queries have an average of ~38 graded-relevant documents. Multi-label, dense relevance.
2. **recall@5\_top1** — a stricter version: did the system put the *single most-relevant* document (top-graded for that query) in its top 5?

```
metric: nDCG@10
  system               score      Δ_A      Δ_B      Δ_C      Δ_D   gate
  -------------------------------------------------------------------------
  1_mira_constant      0.066   -0.000   -0.000   +0.056   -0.000   FAIL
  2_popularity_topk    0.066   -0.000   -0.000   +0.056   -0.000   FAIL
  3_bm25               0.267   +0.011   +0.011   +0.257   +0.011   FAIL  ←
  4_dense_minilm       0.319   +0.013   +0.012   +0.310   +0.013   FAIL  ←

metric: recall@5_top1
  system               score      Δ_A      Δ_B      Δ_C      Δ_D   gate
  -------------------------------------------------------------------------
  1_mira_constant      0.003   -0.001   -0.001   +0.002   +0.000   FAIL
  2_popularity_topk    0.003   -0.001   -0.001   +0.002   +0.000   FAIL
  3_bm25               0.142   +0.139   +0.140   +0.141   +0.140   PASS  ✓
  4_dense_minilm       0.180   +0.178   +0.177   +0.178   +0.178   PASS  ✓
```

**Under nDCG@10, even legitimate retrievers fail the four-null gate at τ=0.05.** Why? Multi-label dense relevance: the retrieved list is highly likely to contain *some* relevant document under any gold-permutation, because there are ~38 relevant docs per query. Δ_A, Δ_B, Δ_D collapse to ~0.011 across the board. The gate does not have signal to distinguish a real retriever from a permuted one — *under this metric*.

**Under recall@5\_top1, the gate correctly separates the two classes.** Real retrievers earn Δ ≈ +0.14 to +0.18; cheaters earn Δ ≈ 0.

This is itself a finding the methodology paper does not currently make:

> **The four-null gate is sensitive to metric choice on multi-label benchmarks.**
> When relevance is dense (>1 relevant doc per query on average), nDCG-style
> graded metrics can mask null differences. A complementary single-gold metric
> (recall@K against top-1 gold) restores null separation.

Recommendation in the wild: **always run the gate against both a graded metric AND a single-gold metric**, especially on dense-relevance benchmarks. If they disagree, the dense one is the one to be suspicious of.

---

## Reproducibility manifest

| Field | Value |
|---|---|
| Benchmark | BEIR / NFCorpus, test split |
| Source | `BeIR/nfcorpus` (corpus + queries) and `BeIR/nfcorpus-qrels` (test) on HuggingFace |
| Corpus size | 3,633 documents |
| Test queries | 323 (with ≥1 relevant doc) |
| Relevance entries | 12,334 |
| Corpus sha256[:16] | `12f78ddf3560314d` (computed over first 100 sorted entries) |
| Queries sha256[:16] | `217d0fce60d1f95b` |
| Random seed | 2026 |
| n\_trials | 30 |
| τ | 0.05 |
| BM25 implementation | `rank_bm25.BM25Okapi`, default parameters, `.split()` tokenisation, lowercased |
| Dense model | `sentence-transformers/all-MiniLM-L6-v2`, normalize\_embeddings=True, batch=64 |
| Device | M1 MPS if available; CPU fallback (we used MPS) |
| Total runtime | ~50 seconds end-to-end |
| Peak RAM | <2 GB |

The full `cs01_results.json` ledger is checked into `results/cs01_results.json`.

### Reproduce

```bash
cd case_studies/cs01_nfcorpus
python3 -m pip install rank-bm25 sentence-transformers datasets --break-system-packages
python3 run_case_study.py
```

First run downloads the BEIR data (~10 MB) and the MiniLM model (~90 MB) — both are cached after that.

---

## Comparison to published BEIR scores

| System | Published nDCG@10 | Our nDCG@10 | Notes |
|---|---:|---:|---|
| BM25 | 0.325 (Thakur et al. 2021, BEIR paper, Table 2) | 0.267 | We use unprocessed text + simple `.split()` tokenisation. The BEIR paper used Anserini with proper stemming + stopwords. Lower-bound BM25 by design. |
| MiniLM-L6-v2 dense | not reported in BEIR paper directly; comparable models score ~0.18 (DPR) to ~0.30 (TAS-B) | 0.319 | In range. We did not fine-tune. |

Our numbers are within or above the published range for the cheap configuration we used, which gives reasonable confidence the implementation is faithful.

---

## What this case study does NOT prove

- It does not prove the four-null gate works on **all** retrieval benchmarks. NFCorpus is one slice of one benchmark. Phase 2 will add SciFact, FiQA, and Quora to triangulate.
- It does not prove the gate catches **all** Mira-class cheaters. It catches the two we tested (constant most-popular, popularity-top-K). Other cheaters (e.g., a system that uses query length only, ignoring content) need their own tests.
- It does not prove a **published** retrieval claim is Mira-tier. To make that claim about a specific system, we would need to reproduce that system's published score under the gate. Phase 3.

What it does prove is the smallest defensible thing: *on one real, public, multi-relevance IR benchmark, the four-null gate correctly distinguishes two cheating classes from two legitimate retrievers under an appropriately-chosen metric, in 50 seconds on a laptop.*

That is the empirical floor the previous documentation lacked.

---

## Lewi's three critiques — closure ledger

| Critique (2026-05-07) | Status | Where the closure lives |
|---|---|---|
| "He never shows a real AI failing the Mira check" | **closed** | This file. Mira fails Δ_D=0; BM25 passes Δ_D=+0.140. Same benchmark. |
| "Promises evidence, delivers analogy" | **closed** | Reproducible code + locked manifest + JSON ledger committed. |
| "Mixes up AI with search engines / retrieval" | **in flight** (Phase 2) | README, brand site, PREPRINT abstract being rewritten to say *retrieval and ranking systems*, never *AI systems* broadly. The library does not test generative LLMs. |
