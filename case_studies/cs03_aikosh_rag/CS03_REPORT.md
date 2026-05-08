# CS03 — falsify-eval against an internal AI Kosh RAG retriever

> **Status: AWAITING RESULTS.** This is a scaffolded case-study slot. CS01
> (NFCorpus) and CS02 (SciFact) covered public BEIR benchmarks; CS03 is the
> first run against a real production retriever inside an organisation. Until
> the run lands, nothing in this report is empirical — the structure below is
> the template we'll fill from `results/cs03_results.json`.

> **External tester:** Jasmeet Singh (AI Kosh, India). Reported the original
> Windows / cp1252 console-encoding defect on 2026-05-08 (closed in v0.1.6.4),
> verified the upgrade path 0.1.6.2 → 0.1.6.7 on Windows 10 + Python 3.14 +
> PowerShell, and volunteered to wire the gate into AI Kosh's internal RAG
> retriever as a follow-up. This case study captures that integration.

## What this case study is for

CS01 and CS02 demonstrated the four-null gate against synthetic predictors
(Mira-constant, popularity-top-K) and two legitimate retrievers (BM25, dense
MiniLM) on **public** benchmarks where the gold-relevance distribution is
well-understood. CS03 is the first time the gate is run on:

- a **real production retriever** (architecture: TBD — see §1)
- an **organisation's internal benchmark** (corpus + queries: TBD — see §2)
- by an **independent external tester** (not the package author)

The combination is the difference between "the methodology works in the
author's hands on public data" and "the methodology survives contact with
someone else's stack."

## 1. The retriever (TO BE FILLED)

> *Jasmeet to fill. Two sentences max. Architecture, components, anything
> custom on top of an off-the-shelf encoder. Example: "BGE-large embeddings
> over the AI Kosh internal documentation corpus, with a colBERT-style late-
> interaction reranker on the top-50 candidates."*

## 2. The bench (TO BE FILLED)

> *Jasmeet to fill. Number of queries, number of documents in the pool,
> distribution of golds (single-gold vs. multi-label), how queries were
> elicited, whether queries are held out from any training split.*

| | Value |
|---|---|
| Queries (N) | TBD |
| Pool (\|item_pool\|) | TBD |
| Avg. relevant docs per query | TBD |
| Single-gold or multi-label | TBD |
| Held-out from training? | TBD |

## 3. Protocol

Same as CS01 / CS02, with the additions documented in `PREPRINT.md` §5.5
(broken-predictor positive controls) and §5.9 (equivariance certificate):

- `n_trials = 200` (publishable-grade null-distribution CI)
- `tau = 0.05`
- `seed = 2026`
- Run **both** a graded metric (nDCG@10) and a strict single-gold metric
  (recall@5_top1). Per CS01's finding: graded metrics on dense-relevance
  benches can mask null separation a strict metric restores. Treat any
  disagreement between the two as a flag for the graded metric, not the
  strict one.
- Capture the full result dict (`falsify-eval grade ... --json > results/cs03_results.json`).

## 4. Results (TO BE FILLED)

> *Drop the `cs03_results.json` here. Format mirrors CS01 / CS02. Single
> table; readers should be able to scan it in 15 seconds.*

| System | nDCG@10 | recall@5_top1 | gate (nDCG) | gate (recall) |
|---|---:|---:|:---:|:---:|
| Mira (constant — sanity control) | TBD | TBD | TBD | TBD |
| AI Kosh production retriever | TBD | TBD | TBD | TBD |

## 5. What we expect (pre-registered, before running)

So we can falsify ourselves with the actual results when they land:

1. **Mira-constant control fails** the gate at Δ_D ≈ 0 under both metrics.
   This is a sanity check: if Mira *passes* on AI Kosh's bench, something
   is wrong with the bench's gold distribution (probably a single dominant
   class), not with the retriever.
2. **AI Kosh's production retriever passes** under at least one metric.
   The expected outcome on a working production system. A passing result
   here is unsurprising and not the interesting case.
3. **Most interesting outcome (~10% prior):** the production retriever
   *fails* one of the four nulls — most likely Null D, indicating the
   retriever is matched to the gold marginal but doesn't actually use the
   query. If this happens, that's the case-study writeup; if it doesn't,
   the boring-and-good outcome is also a worthwhile entry.

## 6. Reproduction

When `data/` and `results/` are populated, the run is:

```
cd case_studies/cs03_aikosh_rag
python run_case_study.py --metric ndcg@10 --metric recall@5_top1 \
                         --n-trials 200 --tau 0.05 --seed 2026
```

The run script will refuse to overwrite an existing `results/cs03_results.json`
without `--force`, so committed numbers cannot be silently regenerated.

---

*Apache 2.0. Bench data and any company-specific identifiers redacted at
AI Kosh's discretion.*
