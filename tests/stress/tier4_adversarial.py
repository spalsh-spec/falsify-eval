import math, random
from collections import Counter
from falsify_eval import four_null_gate

random.seed(2026)
N, POOL_SIZE, K = 1000, 30, 10
LABELS = [f'L{i:02d}' for i in range(POOL_SIZE)]
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
    'constant': lambda g: [ranked_labels[0]] * K,
    'marginal_rank': lambda g: ranked_labels[:K],
    'sneaky_marginal': lambda g: random.Random(hash(g)).sample(ranked_labels, K),
    'plausible': lambda g: ([g] + random.Random(hash(g)).sample([l for l in LABELS if l != g], K-1)
                            if random.Random(hash(g)).random() < 0.55
                            else random.Random(hash(g)).sample(LABELS, K)),
    'oracle': lambda g: [g] + random.Random(hash(g)).sample([l for l in LABELS if l != g], K-1),
}
EXPECTED = {'constant':'FAIL','marginal_rank':'FAIL','sneaky_marginal':'FAIL','plausible':'PASS','oracle':'PASS'}

print(f"{'predictor':<18}{'real':>8}{'ΔA':>8}{'ΔB':>8}{'ΔC':>8}{'ΔD':>8}{'verdict':>9}{'expected':>10}{'agree':>7}")
for name, fn in predictors.items():
    retrieved = [fn(g) for g in gold]
    res = four_null_gate(retrieved, gold, rels, ndcg,
                         item_pool=LABELS, k=K, n_trials=80, tau=0.05, seed=2026)
    verdict = 'PASS' if res['gate_passes'] else 'FAIL'
    agree = '✓' if verdict == EXPECTED[name] else '✗ MISMATCH'
    print(f"{name:<18}{res['real_mean']:8.4f}{res['deltas']['A']:+8.4f}{res['deltas']['B']:+8.4f}{res['deltas']['C']:+8.4f}{res['deltas']['D']:+8.4f}{verdict:>9}{EXPECTED[name]:>10}{agree:>7}")
