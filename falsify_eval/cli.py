"""Command-line interface — `falsify-eval` (or `python -m falsify_eval`).

Designed for developers who want to validate their retrieval pipeline in
under a minute, without writing any Python. Every subcommand prints
helpful next-step hints; `quickstart` and `doctor` are designed to make
first-run zero-friction.

Try:
    falsify-eval doctor               # confirm the install works end-to-end
    falsify-eval quickstart           # write a sample bench you can grade
    falsify-eval grade --demo         # run the gate against an embedded demo
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import textwrap
from pathlib import Path

from .gate import four_null_gate


# ── ANSI helpers (auto-disable when not a TTY or NO_COLOR is set) ─────────
_USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text

def bold(t):    return _c("1", t)
def dim(t):     return _c("2", t)
def red(t):     return _c("31", t)
def green(t):   return _c("32", t)
def yellow(t):  return _c("33", t)
def cyan(t):    return _c("36", t)


# ── Built-in metrics ──────────────────────────────────────────────────────
def ndcg_at_k(retrieved, gold, rel, k):
    rels = [rel if r == gold else 0 for r in retrieved[:k]]
    ideal = sorted(rels, reverse=True)
    idcg = sum(rr / math.log2(i + 2) for i, rr in enumerate(ideal[:k]))
    if idcg == 0:
        return 0.0
    dcg = sum(rr / math.log2(i + 2) for i, rr in enumerate(rels[:k]))
    return dcg / idcg


def recall_at_k(retrieved, gold, rel, k):
    return 1.0 if gold in retrieved[:k] else 0.0


def mrr_at_k(retrieved, gold, rel, k):
    for i, r in enumerate(retrieved[:k]):
        if r == gold:
            return 1.0 / (i + 1)
    return 0.0


METRICS = {"ndcg": ndcg_at_k, "recall": recall_at_k, "mrr": mrr_at_k}


# ── Loaders ───────────────────────────────────────────────────────────────
def load_jsonl(path: Path):
    rows = []
    with path.open() as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(red(f"{path}:{n}: invalid JSON ({e.msg})\n") +
                                 dim(f"  hint: each line must be a complete JSON object like\n") +
                                 dim('  {"retrieved":["A","B","C"], "gold":"A", "rel":3}'))
    return rows


def load_pool(path: Path | None):
    if path is None:
        return None
    text = path.read_text().strip()
    if text.startswith("["):
        return json.loads(text)
    return [line.strip() for line in text.splitlines() if line.strip()]


# ── Embedded demo bench (used by --demo, doctor, quickstart) ──────────────
def _demo_bench(n: int = 50, seed: int = 2026):
    """Synthetic 50-query bench with 12 labels, oracle-with-noise retriever."""
    rng = random.Random(seed)
    labels = [f"L{i:02d}" for i in range(12)]
    weights = [6, 4, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1]
    rows = []
    for i in range(n):
        gold = rng.choices(labels, weights=weights, k=1)[0]
        if rng.random() < 0.7:
            retrieved = [gold] + rng.sample([l for l in labels if l != gold], 4)
        else:
            retrieved = rng.sample(labels, 5)
        rows.append({"retrieved": retrieved, "gold": gold, "rel": 3})
    return rows, labels


# ── Pretty-printer for grade results ─────────────────────────────────────
def _print_result(res: dict, n_queries: int, metric_label: str):
    print()
    print(bold(f"falsify-eval · {metric_label} on {n_queries} queries"))
    print(f"  real mean = {bold(f'{res[\"real_mean\"]:.4f}')}")
    for x in "ABCD":
        passed = res["passes"][x]
        verdict = green("✓") if passed else red("✗")
        delta_s = f"{res['deltas'][x]:+.4f}"
        delta_c = green(delta_s) if passed else red(delta_s)
        print(f"  Null {x}: mean={res['null_means'][x]:.4f}  Δ={delta_c}  {verdict}")
    if res["gate_passes"]:
        print(f"  GATE: {green('✓ PASS')}  {dim(f'(τ={res[\"tau\"]})')}")
    else:
        print(f"  GATE: {red('✗ FAIL')}  {dim(f'(τ={res[\"tau\"]})')}")
    for w in res.get("warnings", []):
        print(f"  {yellow('⚠ warning:')} {w}")


def _print_post_grade_hints(res: dict):
    """Claude-Code-style 'what's next?' footer."""
    print()
    print(dim("─" * 60))
    if res["gate_passes"]:
        print(dim("Next steps:"))
        print(dim("  • Lock your bench artifacts:  ") + cyan("falsify-eval lock ./data -o lock.json"))
        print(dim("  • Try a stricter τ:           ") + cyan("falsify-eval grade ... --tau 0.10"))
        print(dim("  • More null trials for a tighter CI: ") + cyan("--n-trials 200"))
        print(dim("  • Output JSON for CI:        ") + cyan("--json | jq"))
    else:
        # Failure-mode hints
        failed = [x for x in "ABCD" if not res["passes"][x]]
        worst = min("ABCD", key=lambda x: res["deltas"][x])
        print(dim("Diagnosis hints:"))
        if "D" in failed:
            print(dim("  • Failing Null D specifically suggests your engine is matching"))
            print(dim("    the gold marginal without using the query. Try the smallest"))
            print(dim("    constant-prediction sanity check on your top-K outputs."))
        if "C" in failed:
            print(dim("  • Failing Null C means your engine isn't beating random retrieval."))
            print(dim("    Either the engine is broken or k is too large for your pool."))
        if "A" in failed and "B" in failed:
            print(dim("  • Failing both A and B suggests the metric is saturated; try"))
            print(dim("    a stricter k (e.g. k=1 for top-1 accuracy)."))
        print(dim(f"  • Worst null: {worst} (Δ={res['deltas'][worst]:+.4f})"))


# ── Commands ──────────────────────────────────────────────────────────────
def cmd_grade(args):
    if args.demo:
        rows, pool = _demo_bench()
        print(dim("(running against embedded synthetic demo bench: 50 queries, 12 labels)"))
    else:
        if not args.input:
            raise SystemExit(red("error: --input required (or use --demo)\n") +
                             dim("  hint: try `falsify-eval quickstart` to generate a sample bench file"))
        rows = load_jsonl(Path(args.input))
        if not rows:
            raise SystemExit(red(f"{args.input}: no rows loaded"))
        pool = load_pool(Path(args.pool)) if args.pool else None

    retrieved = [r["retrieved"] for r in rows]
    gold = [r["gold"] for r in rows]
    rel = [r.get("rel", 3) for r in rows]

    name, _, k_str = args.metric.partition("@")
    if name not in METRICS:
        raise SystemExit(red(f"unknown metric '{name}'\n") +
                         dim(f"  choices: {', '.join(METRICS)} (e.g. ndcg@5, recall@10, mrr@5)"))
    if not k_str.isdigit():
        raise SystemExit(red(f"metric must be 'name@K' (e.g. 'ndcg@5'), got '{args.metric}'"))
    k = int(k_str)
    metric_fn = lambda r, g, rl: METRICS[name](r, g, rl, k)

    try:
        res = four_null_gate(retrieved, gold, rel, metric_fn,
                             item_pool=pool, k=k,
                             n_trials=args.n_trials, tau=args.tau, seed=args.seed)
    except ValueError as e:
        msg = str(e)
        hint = ""
        if "k=" in msg and "len(item_pool)" in msg:
            hint = "\n" + dim("  hint: increase --pool or decrease the K in your --metric")
        elif "gold label" in msg and "not present" in msg:
            hint = "\n" + dim("  hint: --pool is missing some labels that appear in --input;\n"
                              "        common cause is label-set drift between train and eval")
        elif "length mismatch" in msg:
            hint = "\n" + dim("  hint: every JSONL row must have retrieved + gold + rel "
                              "(rel defaults to 3 if omitted)")
        raise SystemExit(red(f"INPUT ERROR: {e}") + hint)

    if args.json:
        print(json.dumps(res, indent=2, default=float))
        return 0 if res["gate_passes"] else 1

    _print_result(res, n_queries=len(rows), metric_label=args.metric)
    if not args.quiet:
        _print_post_grade_hints(res)
    return 0 if res["gate_passes"] else 1


def cmd_lock(args):
    from .lock import lock_state
    directory = Path(args.directory)
    if not directory.exists():
        raise SystemExit(red(f"{directory}: not found"))
    lock = lock_state(directory)
    out = json.dumps(lock, indent=2, default=str)
    if args.output:
        Path(args.output).write_text(out)
        print(green(f"✓ wrote lock to {args.output}") +
              dim(f"  ({len(lock['artifacts'])} artifacts, git={lock.get('git_commit','none')[:8]})"))
        print(dim("  next: ") + cyan(f"falsify-eval verify --lock {args.output} {directory}"))
    else:
        print(out)
    return 0


def cmd_verify(args):
    from .lock import verify_state
    lock = json.loads(Path(args.lock).read_text())
    diff = verify_state(lock, Path(args.directory))
    if diff["matches"]:
        print(green(f"✓ {args.directory} matches {args.lock}"))
        return 0
    print(red(f"✗ {args.directory} differs from {args.lock}"))
    for c in diff.get("changed", [])[:10]:
        print(f"  {yellow('CHANGED')}  {c['path']}")
    for m in diff.get("missing", [])[:10]:
        print(f"  {red('MISSING')}  {m}")
    for n in diff.get("added", [])[:10]:
        print(f"  {cyan('NEW')}      {n}")
    return 2


def cmd_quickstart(args):
    """Write a sample bench.jsonl + pool.txt and print the next command."""
    out_dir = Path(args.directory)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, pool = _demo_bench(n=50)
    bench_path = out_dir / "bench.jsonl"
    pool_path = out_dir / "pool.txt"
    with bench_path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    pool_path.write_text("\n".join(pool) + "\n")
    print(green("✓ wrote sample bench files:"))
    print(f"  {bench_path}  ({len(rows)} queries)")
    print(f"  {pool_path}  ({len(pool)} labels)")
    print()
    print(dim("Try it now:"))
    print("  " + cyan(f"falsify-eval grade --input {bench_path} --pool {pool_path} --metric ndcg@5"))
    print()
    print(dim("Bench file format (one JSON object per line):"))
    print(dim('  {"retrieved": ["A","B","C","D","E"], "gold": "A", "rel": 3}'))
    return 0


def cmd_doctor(args):
    """End-to-end install check. Runs gate against embedded demo, reports each step."""
    print(bold("falsify-eval doctor — checking install"))
    print()
    print(f"  python:        {sys.version.split()[0]}")
    try:
        import numpy as np
        print(f"  numpy:         {np.__version__}  {green('✓')}")
    except ImportError:
        print(f"  numpy:         {red('NOT INSTALLED')}")
        return 1
    try:
        from . import __version__
        print(f"  falsify-eval:  {__version__}  {green('✓')}")
    except Exception:
        print(f"  falsify-eval:  installed but version unreadable")

    print()
    print(dim("Running embedded demo bench through the four-null gate..."))
    rows, pool = _demo_bench()
    retrieved = [r["retrieved"] for r in rows]
    gold = [r["gold"] for r in rows]
    rel = [r["rel"] for r in rows]
    metric_fn = lambda r, g, rl: ndcg_at_k(r, g, rl, 5)
    try:
        res = four_null_gate(retrieved, gold, rel, metric_fn,
                             item_pool=pool, k=5, n_trials=30, tau=0.05, seed=2026)
    except Exception as e:
        print(red(f"✗ gate raised: {e}"))
        return 1
    if not res["gate_passes"]:
        print(red(f"✗ gate FAILED on demo bench (this should never happen)"))
        return 1
    print(green(f"✓ gate PASS on demo  (real_mean={res['real_mean']:.4f}, "
                f"min Δ = {min(res['deltas'].values()):+.4f})"))
    print()
    print(green(bold("All systems green. ")) + dim("You're ready to use falsify-eval."))
    print()
    print(dim("Quickstart:  ") + cyan("falsify-eval quickstart ./my-bench"))
    print(dim("Demo grade:  ") + cyan("falsify-eval grade --demo"))
    print(dim("Real bench:  ") + cyan("falsify-eval grade --input ./bench.jsonl --pool ./pool.txt"))
    return 0


# ── Main ──────────────────────────────────────────────────────────────────
EPILOG = textwrap.dedent("""\
    Examples:
      falsify-eval doctor                        # confirm install works
      falsify-eval quickstart ./my-bench         # write a sample bench file
      falsify-eval grade --demo                  # grade an embedded demo bench
      falsify-eval grade --input bench.jsonl --pool pool.txt --metric ndcg@5
      falsify-eval grade --input bench.jsonl --pool pool.txt --json | jq

    Documentation: https://github.com/spalsh-spec/falsify-eval
    Released by Bhardwaj & Sons under Apache 2.0.
""")


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="falsify-eval",
        description="Calibrated falsification harness for retrieval evaluation.\n"
                    "Catches false positives standard aggregate-metric reporting accepts.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True, metavar="COMMAND")

    g = sub.add_parser("grade", help="Run the four-null gate on a benchmark",
                       epilog="example: falsify-eval grade --input bench.jsonl --pool pool.txt --metric ndcg@5",
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    g.add_argument("--input", "-i", default=None,
                   help="JSONL file: one {retrieved, gold, rel} per line")
    g.add_argument("--demo", action="store_true",
                   help="ignore --input and run against embedded synthetic bench (50 queries)")
    g.add_argument("--metric", "-m", default="ndcg@5",
                   help="metric@K (default: ndcg@5; choices: ndcg, recall, mrr)")
    g.add_argument("--pool", "-p", default=None,
                   help="text or JSON file listing the item-pool")
    g.add_argument("--n-trials", type=int, default=50,
                   help="null-trial count (default: 50; tighter CI with 100-500)")
    g.add_argument("--tau", type=float, default=0.05,
                   help="per-null Δ threshold (default: 0.05)")
    g.add_argument("--seed", type=int, default=2026)
    g.add_argument("--json", action="store_true", help="emit full result as JSON (machine-readable)")
    g.add_argument("--quiet", action="store_true", help="suppress next-step hints")
    g.set_defaults(func=cmd_grade)

    Q = sub.add_parser("quickstart", help="Write a sample bench file you can grade right away",
                       epilog="example: falsify-eval quickstart ./my-bench",
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    Q.add_argument("directory", nargs="?", default=".",
                   help="directory to write bench.jsonl + pool.txt into (default: .)")
    Q.set_defaults(func=cmd_quickstart)

    D = sub.add_parser("doctor", help="Verify the install end-to-end against an embedded demo")
    D.set_defaults(func=cmd_doctor)

    L = sub.add_parser("lock", help="Hash a directory of artifacts to a lock file",
                       epilog="example: falsify-eval lock ./data -o data.lock.json",
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    L.add_argument("directory")
    L.add_argument("--output", "-o", default=None,
                   help="write lock to this path (default: print to stdout)")
    L.set_defaults(func=cmd_lock)

    V = sub.add_parser("verify", help="Verify a directory against a previously-emitted lock",
                       epilog="example: falsify-eval verify --lock data.lock.json ./data",
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    V.add_argument("--lock", required=True)
    V.add_argument("directory")
    V.set_defaults(func=cmd_verify)

    args = p.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
