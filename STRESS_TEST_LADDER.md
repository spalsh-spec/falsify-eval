# Stress-test ladder — finding falsify-eval's breaking point

Five tiers, increasing difficulty, designed to push the four-null gate from
its happy path to its mathematical limits. Each tier is a self-contained
Python script you can paste into a fresh `.venv` and run.

The point is to find the **wall**, not to validate the floor. We already
know the floor works (8/8 unit tests pass on a fresh clone). What we don't
know is exactly where the methodology stops being trustworthy.

| Tier | Time | Goal | What "breaking" looks like |
|---|---|---|---|
| 1 | 30 sec | Smoke — repro the published demo | Demo crashes or gives wrong verdicts |
| 2 | 2 min | Realistic academic scale (N=500, pool=50) | Compute too slow OR gate misclassifies |
| 3 | 5–15 min | Industrial scale (N=10,000) | OOM, crash, or gate flips its verdict |
| 4 | 5 min | Adversarial predictors designed to fool the gate | Sneaky predictor passes when it shouldn't |
| 5 | varies | Boundary / mathematical limits | The methodology returns nonsense |

---

## Tier 1 — Smoke (the published demo)

```bash
cd falsify-eval
source .venv/bin/activate
python3 examples/synthetic_demo.py
```

**Pass criteria:** three systems graded, `constant_predictor → FAIL`,
`mock_engine → PASS`, `oracle → PASS`. Runs in under 30 seconds.

**If this fails:** stop. Open an issue with the full traceback.

---

## Tier 2 — Realistic academic scale

A 500-query benchmark with 50 labels, top-10 retrieval, on a "noisy oracle"
that gets the right answer 60% of the time. This is what an actual small
information-retrieval paper looks like.

```python
# tier2_realistic.py
import math, random
from falsify_eval import four_null_gate

random.seed(2026)
N, POOL_SIZE, K = 500, 50, 10
LABELS = [f"L{i:03d}" for i in range(POOL_SIZE)]

# Zipfian gold marginal — like a real corpus, a few labels dominate
weights = [1.0 / (i + 1) for i in range(POOL_SIZE)]
gold = [random.choices(LABELS, weights=weights, k=1)[0] for _ in range(N)]
rels = [3] * N

def ndcg_at_k(retrieved, g, r, k=K):
    rels_ = [r if x == g else 0 for x in retrieved[:k]]
    ideal = sorted(rels_, reverse=True)
    idcg = sum(rr/math.log2(i+2) for i, rr in enumerate(ideal[:k]))
    if idcg == 0: return 0.0
    return sum(rr/math.log2(i+2) for i, rr in enumerate(rels_[:k])) / idcg

# 60%-correct retriever
def noisy_oracle(g):
    rng = random.Random(hash(g))
    if rng.random() < 0.6:
        return [g] + rng.sample([l for l in LABELS if l != g], K - 1)
    return rng.sample(LABELS, K)

retrieved = [noisy_oracle(g) for g in gold]
res = four_null_gate(retrieved, gold, rels, ndcg_at_k,
                     item_pool=LABELS, k=K, n_trials=50, tau=0.05, seed=2026)
print(f"real mean = {res['real_mean']:.4f}")
for x in "ABCD":
    print(f"  Null {x}: Δ={res['deltas'][x]:+.4f}  {'✓' if res['passes'][x] else '✗'}")
print("GATE:", "PASS ✓" if res["gate_passes"] else "FAIL ✗")
```

**Expected:** GATE passes with all four Δ ≥ +0.30. Runtime ~30 seconds on M1.

**Breaking point to watch for:** if any single Δ is below +0.05 it suggests
the noisy oracle isn't separating cleanly from a null — that's a signal that
the test setup is degenerate, not that the methodology is wrong.

---

## Tier 3 — Industrial scale (N=10,000)

This is the same scale we validated internally. Re-running it on Akosh's
hardware is the strongest possible third-party check.

```python
# tier3_industrial.py
import math, random, time
from falsify_eval import four_null_gate

random.seed(2026)
N, POOL_SIZE, K = 10_000, 200, 20
LABELS = [f"L{i:04d}" for i in range(POOL_SIZE)]
weights = [1.0 / (i + 1) for i in range(POOL_SIZE)]
gold = [random.choices(LABELS, weights=weights, k=1)[0] for _ in range(N)]
rels = [3] * N

def ndcg(retrieved, g, r, k=K):
    rels_ = [r if x == g else 0 for x in retrieved[:k]]
    ideal = sorted(rels_, reverse=True)
    idcg = sum(rr/math.log2(i+2) for i, rr in enumerate(ideal[:k]))
    if idcg == 0: return 0.0
    return sum(rr/math.log2(i+2) for i, rr in enumerate(rels_[:k])) / idcg

def good_engine(g):
    rng = random.Random(hash(g) ^ 17)
    if rng.random() < 0.55:
        return [g] + rng.sample([l for l in LABELS if l != g], K - 1)
    return rng.sample(LABELS, K)

t0 = time.time()
retrieved = [good_engine(g) for g in gold]
print(f"  built {N} retrievals in {time.time()-t0:.1f}s")
t0 = time.time()
res = four_null_gate(retrieved, gold, rels, ndcg,
                     item_pool=LABELS, k=K, n_trials=100, tau=0.05, seed=2026)
print(f"  ran four-null gate in {time.time()-t0:.1f}s")
print(f"real mean = {res['real_mean']:.4f}")
for x in "ABCD":
    print(f"  Null {x}: Δ={res['deltas'][x]:+.4f}")
print("GATE:", "PASS" if res["gate_passes"] else "FAIL")
```

**Expected:** GATE passes. Build time ~10 sec, gate runtime 2–10 minutes
depending on hardware (M1: ~2 min; older Intel: ~10 min). Memory peak under
2 GB.

**Breaking point to watch for:**
- Out of memory → the harness should be O(N·K) in memory; if you OOM under
  16 GB the bench is the problem, not the harness
- Runtime > 30 min on M1 → there's a perf regression worth filing
- Gate FAILs → either the engine you wrote is genuinely bad or there's a
  numerical instability worth investigating

---

## Tier 4 — Adversarial predictors (designed to fool the gate)

Five predictors, four of which the gate **must** classify correctly. The
fifth is the one I'm honestly less sure about — that's where the
methodology gets tested.

```python
# tier4_adversarial.py
import math, random
from collections import Counter
from falsify_eval import four_null_gate

random.seed(2026)
N, POOL_SIZE, K = 1000, 30, 10
LABELS = [f"L{i:02d}" for i in range(POOL_SIZE)]
weights = [3, 3, 2, 2, 2, 1, 1, 1, 1, 1] + [0.5] * 20
gold = [random.choices(LABELS, weights=weights, k=1)[0] for _ in range(N)]
rels = [3] * N
marginal = Counter(gold)
ranked_labels = [l for l, _ in marginal.most_common()]

def ndcg(retrieved, g, r, k=K):
    rels_ = [r if x == g else 0 for x in retrieved[:k]]
    ideal = sorted(rels_, reverse=True)
    idcg = sum(rr/math.log2(i+2) for i, rr in enumerate(ideal[:k]))
    if idcg == 0: return 0.0
    return sum(rr/math.log2(i+2) for i, rr in enumerate(rels_[:k])) / idcg

predictors = {
    # 1. Constant predictor — always returns most-frequent label k times.
    #    Should FAIL on Null D specifically.
    "constant": lambda g: [ranked_labels[0]] * K,

    # 2. Marginal-rank predictor — returns the K most frequent labels in
    #    descending order, regardless of query. Better than constant at
    #    matching the marginal. SHOULD STILL FAIL Null D.
    "marginal_rank": lambda g: ranked_labels[:K],

    # 3. THE SNEAKY ONE: marginal-rank + tiny query-conditional perturbation.
    #    Looks like it uses the query (because the order changes per query)
    #    but the perturbation is INDEPENDENT of the gold. This is the
    #    pathology Null D was specifically designed to catch.
    "sneaky_marginal": lambda g: (lambda r: r.sample(ranked_labels, K))(random.Random(hash(g))),

    # 4. Plausible engine — 55% top-1 hit rate. SHOULD PASS.
    "plausible": lambda g: ([g] + random.Random(hash(g)).sample(
        [l for l in LABELS if l != g], K-1)
        if random.Random(hash(g)).random() < 0.55
        else random.Random(hash(g)).sample(LABELS, K)),

    # 5. Oracle — perfect top-1. SHOULD PASS by maximum margin.
    "oracle": lambda g: [g] + random.Random(hash(g)).sample(
        [l for l in LABELS if l != g], K-1),
}

EXPECTED = {"constant": "FAIL", "marginal_rank": "FAIL", "sneaky_marginal": "FAIL",
            "plausible": "PASS", "oracle": "PASS"}

print(f"{'predictor':<18} {'real':>7} {'ΔA':>7} {'ΔB':>7} {'ΔC':>7} {'ΔD':>7} {'verdict':>8} {'expected':>9} {'agree':>6}")
for name, fn in predictors.items():
    retrieved = [fn(g) for g in gold]
    res = four_null_gate(retrieved, gold, rels, ndcg,
                         item_pool=LABELS, k=K, n_trials=80, tau=0.05, seed=2026)
    verdict = "PASS" if res["gate_passes"] else "FAIL"
    agree = "✓" if verdict == EXPECTED[name] else "✗ MISMATCH"
    print(f"{name:<18} {res['real_mean']:7.4f} "
          f"{res['deltas']['A']:+7.4f} {res['deltas']['B']:+7.4f} "
          f"{res['deltas']['C']:+7.4f} {res['deltas']['D']:+7.4f} "
          f"{verdict:>8} {EXPECTED[name]:>9} {agree:>6}")
```

**Expected:** all five rows show `agree = ✓`. The `sneaky_marginal` row
in particular should show **Δ_D ≈ 0** while Δ_A and Δ_B are positive — that
single failure on Null D is the methodology's contribution.

**Breaking point to watch for:** if `sneaky_marginal` shows `agree = ✗
MISMATCH` (i.e., the gate PASSes it), that is a real methodological hole and
exactly the class of report the previous bug bounty would have paid for.
Open an issue with the full output.

---

## Tier 5 — Boundary conditions and mathematical limits

These are designed to break things. Some will give graceful errors; some
will give wrong answers; some will hang. The point is to map the
methodology's edge.

### 5a. `k > pool_size` — degenerate Null C

```python
# Null C samples K items at random from the pool. If K > |pool|, this is
# undefined. The library should either: (a) raise a clear error, or
# (b) return Δ_C = 0 with a warning. Anything else is a bug.
from falsify_eval import four_null_gate
res = four_null_gate([["A","B","C","D","E"]] * 10, ["A"]*10, [3]*10,
                     lambda r,g,rel: 1.0 if g in r[:5] else 0.0,
                     item_pool=["A","B","C"], k=5, n_trials=10, tau=0.05, seed=1)
print(res["deltas"])   # what does C show?
```

### 5b. Single-label benchmark — Null D ≡ Null A

```python
# When every query has the same gold label, the marginal collapses to a
# delta function and Null D becomes mathematically equivalent to Null A.
# The gate should still produce a coherent verdict.
from falsify_eval import four_null_gate
LABELS = list("ABCDEFGH")
gold = ["A"] * 200
retrieved = [["A","B","C","D","E"] for _ in range(200)]
res = four_null_gate(retrieved, gold, [3]*200, lambda r,g,rel: 1.0 if g in r[:5] else 0.0,
                     item_pool=LABELS, k=5, n_trials=50, tau=0.05, seed=1)
print("ΔA vs ΔD:", res["deltas"]["A"], res["deltas"]["D"])  # should be ≈ equal
```

### 5c. Sparse-marginal stress — Null D's marginal estimator can't get a sample

```python
# 50 queries, 1000 labels, perfectly uniform. Each label appears ≤ 1 time.
# Null D needs to sample from the marginal distribution; with N << pool, the
# marginal is essentially indistinguishable from uniform → Null D ≈ Null B.
import random
from falsify_eval import four_null_gate
random.seed(42)
LABELS = [f"L{i:04d}" for i in range(1000)]
gold = random.sample(LABELS, 50)   # each label appears at most once
retrieved = [random.sample(LABELS, 5) for _ in gold]
res = four_null_gate(retrieved, gold, [3]*50, lambda r,g,rel: 1.0 if g in r[:5] else 0.0,
                     item_pool=LABELS, k=5, n_trials=50, tau=0.05, seed=1)
print("ΔB vs ΔD:", res["deltas"]["B"], res["deltas"]["D"])  # should be ≈ equal
```

### 5d. Clustered queries — bootstrap CI assumption violated

Bootstrap confidence intervals assume queries are i.i.d. If queries cluster
(every 10 queries are paraphrases of each other), the CI is anti-conservative
by ~√cluster_size. The library does not currently detect this. Don't run as
code — note it as a methodological limit:

> The harness's null distributions and bootstrap CI assume independent
> queries. If your benchmark contains paraphrase clusters, near-duplicates,
> or temporally correlated queries, treat the resulting confidence intervals
> as optimistic by a factor of roughly √(average cluster size). This is a
> known limit, not a bug — and is the cleanest direction for a v0.2
> contribution.

### 5e. Empty retrieval

```python
# Some queries return empty top-K. Library should not crash; should treat
# them as 0-score queries.
from falsify_eval import four_null_gate
res = four_null_gate([[]] * 100 + [["A","B","C","D","E"]] * 100,
                     ["A"]*200, [3]*200,
                     lambda r,g,rel: 1.0 if g in r[:5] else 0.0,
                     item_pool=list("ABCDEFGH"), k=5, n_trials=20, tau=0.05, seed=1)
print("real_mean (should be ~0.5):", res["real_mean"])
```

---

## What to send back

For each tier:
1. The full stdout of the script.
2. `python3 -V` and `pip show numpy falsify-eval | grep -E '^(Name|Version)'`.
3. Wall-clock time.
4. For Tier 4 specifically: the verdict-vs-expected agreement column.
5. For Tier 5: which sub-tests crashed, which gave wrong answers, which
   gave answers that look numerically reasonable.

The interesting findings are:

- **Tier 4 sneaky_marginal escape** — would be a methodological flaw worth
  publishing about.
- **Tier 5a/5e crashes** — engineering bugs we'll fix in the next patch.
- **Tier 5c divergence** — known limit; the size of the divergence tells us
  how badly small-N benchmarks are vulnerable to false PASS.

Document everything you find. The goal is not "it works" — the goal is to
draw the boundary of where it stops working, in writing.

— Bhardwaj &amp; Sons · 2026-05-04
