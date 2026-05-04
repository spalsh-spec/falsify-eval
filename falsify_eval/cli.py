"""Command-line interface — `python -m falsify_eval grade ...`.

Lets non-Python users (or anyone with a CI pipeline) run the four-null gate
on a benchmark expressed as JSONL files. Built-in metrics: ndcg, recall, mrr.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from .gate import four_null_gate


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


# ── JSONL loaders ─────────────────────────────────────────────────────────
def load_jsonl(path: Path):
    """Each line: {"retrieved": [...], "gold": "X", "rel": 3} (rel optional)."""
    rows = []
    with path.open() as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"{path}:{n}: invalid JSON ({e.msg})")
    return rows


def load_pool(path: Path | None):
    if path is None:
        return None
    text = path.read_text().strip()
    if text.startswith("["):
        return json.loads(text)
    return [line.strip() for line in text.splitlines() if line.strip()]


# ── Main ──────────────────────────────────────────────────────────────────
def cmd_grade(args):
    rows = load_jsonl(Path(args.input))
    if not rows:
        raise SystemExit(f"{args.input}: no rows loaded")

    retrieved = [r["retrieved"] for r in rows]
    gold = [r["gold"] for r in rows]
    rel = [r.get("rel", 3) for r in rows]

    metric_name, _, k_str = args.metric.partition("@")
    if metric_name not in METRICS:
        raise SystemExit(f"unknown metric '{metric_name}' (choices: {list(METRICS)})")
    if not k_str.isdigit():
        raise SystemExit(f"metric must be of form 'name@K' (e.g. 'ndcg@5'), got '{args.metric}'")
    k = int(k_str)
    metric_fn = lambda r, g, rl: METRICS[metric_name](r, g, rl, k)

    pool = load_pool(Path(args.pool)) if args.pool else None

    try:
        res = four_null_gate(retrieved, gold, rel, metric_fn,
                             item_pool=pool, k=k,
                             n_trials=args.n_trials, tau=args.tau, seed=args.seed)
    except ValueError as e:
        raise SystemExit(f"INPUT ERROR: {e}")

    if args.json:
        print(json.dumps(res, indent=2, default=float))
        return 0 if res["gate_passes"] else 1

    print(f"falsify-eval · {args.metric} on {len(rows)} queries")
    print(f"  real mean = {res['real_mean']:.4f}")
    for x in "ABCD":
        verdict = "✓" if res["passes"][x] else "✗"
        print(f"  Null {x}: mean={res['null_means'][x]:.4f}  Δ={res['deltas'][x]:+.4f}  {verdict}")
    print(f"  GATE: {'✓ PASS' if res['gate_passes'] else '✗ FAIL'}  (τ={res['tau']})")
    for w in res.get("warnings", []):
        print(f"  ⚠ warning: {w}")
    return 0 if res["gate_passes"] else 1


def cmd_lock(args):
    from .lock import lock_state
    lock = lock_state(Path(args.directory))
    out = json.dumps(lock, indent=2, default=str)
    if args.output:
        Path(args.output).write_text(out)
        print(f"wrote lock to {args.output} ({len(lock['artifacts'])} artifacts)")
    else:
        print(out)
    return 0


def cmd_verify(args):
    from .lock import verify_state
    lock = json.loads(Path(args.lock).read_text())
    diff = verify_state(lock, Path(args.directory))
    print(f"verify {args.directory} against {args.lock}")
    print(f"  matches: {diff['matches']}")
    if not diff["matches"]:
        for c in diff.get("changed", [])[:10]:
            print(f"    CHANGED  {c['path']}")
        for m in diff.get("missing", [])[:10]:
            print(f"    MISSING  {m}")
        for n in diff.get("added", [])[:10]:
            print(f"    NEW      {n}")
    return 0 if diff["matches"] else 2


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="falsify-eval",
        description="Calibrated falsification harness for retrieval evaluation.")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("grade", help="Run the four-null gate on a JSONL benchmark")
    g.add_argument("--input", "-i", required=True,
                   help="JSONL file: one {retrieved, gold, rel} per line")
    g.add_argument("--metric", "-m", default="ndcg@5",
                   help="metric@K (default: ndcg@5; choices: ndcg, recall, mrr)")
    g.add_argument("--pool", "-p", default=None,
                   help="text or JSON file listing the item-pool (one id per line, or JSON array)")
    g.add_argument("--n-trials", type=int, default=50)
    g.add_argument("--tau", type=float, default=0.05)
    g.add_argument("--seed", type=int, default=2026)
    g.add_argument("--json", action="store_true", help="output full result as JSON")
    g.set_defaults(func=cmd_grade)

    L = sub.add_parser("lock", help="Hash a directory of artifacts to a lock file")
    L.add_argument("directory")
    L.add_argument("--output", "-o", default=None)
    L.set_defaults(func=cmd_lock)

    V = sub.add_parser("verify", help="Verify a directory against a previously-emitted lock")
    V.add_argument("--lock", required=True)
    V.add_argument("directory")
    V.set_defaults(func=cmd_verify)

    args = p.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
