import random
from falsify_eval import four_null_gate

def safe_run(name, fn):
    print(f'─── {name} ───')
    try:
        fn()
    except Exception as e:
        print(f'  CRASH: {type(e).__name__}: {e}')
    print()

def t5a():
    res = four_null_gate([['A','B','C']] * 10, ['A']*10, [3]*10,
                         lambda r,g,rel: 1.0 if g in r[:3] else 0.0,
                         item_pool=['A','B','C'], k=5, n_trials=10, tau=0.05, seed=1)
    print(f'  k>pool: deltas = {res["deltas"]}')

def t5b():
    LABELS = list('ABCDEFGH')
    gold = ['A'] * 200
    retrieved = [['A','B','C','D','E'] for _ in range(200)]
    res = four_null_gate(retrieved, gold, [3]*200, lambda r,g,rel: 1.0 if g in r[:5] else 0.0,
                         item_pool=LABELS, k=5, n_trials=50, tau=0.05, seed=1)
    print(f'  ΔA={res["deltas"]["A"]:.4f}  ΔD={res["deltas"]["D"]:.4f}  diff={abs(res["deltas"]["A"]-res["deltas"]["D"]):.4f}')

def t5c():
    random.seed(42)
    LABELS = [f'L{i:04d}' for i in range(1000)]
    gold = random.sample(LABELS, 50)
    retrieved = [random.sample(LABELS, 5) for _ in gold]
    res = four_null_gate(retrieved, gold, [3]*50, lambda r,g,rel: 1.0 if g in r[:5] else 0.0,
                         item_pool=LABELS, k=5, n_trials=50, tau=0.05, seed=1)
    print(f'  ΔB={res["deltas"]["B"]:.4f}  ΔD={res["deltas"]["D"]:.4f}  diff={abs(res["deltas"]["B"]-res["deltas"]["D"]):.4f}')

def t5e():
    res = four_null_gate([[]] * 100 + [['A','B','C','D','E']] * 100,
                         ['A']*200, [3]*200,
                         lambda r,g,rel: 1.0 if g in r[:5] else 0.0,
                         item_pool=list('ABCDEFGH'), k=5, n_trials=20, tau=0.05, seed=1)
    print(f'  real_mean = {res["real_mean"]:.4f} (expect ~0.5)')

def t5f_negative():
    # gold not in pool — silent failure or crash?
    LABELS = ['A','B','C']
    gold = ['Z'] * 50  # 'Z' is not in LABELS
    retrieved = [['A','B','C']] * 50
    res = four_null_gate(retrieved, gold, [3]*50, lambda r,g,rel: 1.0 if g in r[:3] else 0.0,
                         item_pool=LABELS, k=3, n_trials=20, tau=0.05, seed=1)
    print(f'  gold-not-in-pool: real={res["real_mean"]:.4f}  ΔD={res["deltas"]["D"]:.4f}')

def t5g_extreme_metric():
    # metric returns extreme values
    res = four_null_gate([['A']]*50, ['A']*50, [3]*50,
                         lambda r,g,rel: 1e15 if g in r else 0.0,
                         item_pool=['A','B','C'], k=1, n_trials=20, tau=0.05, seed=1)
    print(f'  extreme metric: real={res["real_mean"]:.2e}  ΔD={res["deltas"]["D"]:.2e}')

safe_run('5a. k > pool_size', t5a)
safe_run('5b. single-label (ΔA should ≈ ΔD)', t5b)
safe_run('5c. sparse marginal (ΔB should ≈ ΔD)', t5c)
safe_run('5e. empty retrieval', t5e)
safe_run('5f. gold not in pool (silent error?)', t5f_negative)
safe_run('5g. extreme metric values (1e15)', t5g_extreme_metric)
