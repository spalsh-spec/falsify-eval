"""CS03 — AI Kosh internal RAG retriever — run script (placeholder).

This is a scaffolded slot. When Jasmeet provides the AI Kosh bench
(`data/queries.jsonl` + `data/pool.txt`) and a Python callable that wraps
the AI Kosh retriever to return top-K item ids per query, this script
runs the four-null gate against it under two metrics and writes
`results/cs03_results.json`.

Until those inputs land, calling this script raises a clear NotImplemented
error rather than silently producing fake numbers.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


HERE = Path(__file__).parent
DATA = HERE / "data"
RESULTS = HERE / "results"


def _missing_inputs() -> list[str]:
    needed = [DATA / "queries.jsonl", DATA / "pool.txt", DATA / "retriever.py"]
    return [str(p.relative_to(HERE)) for p in needed if not p.exists()]


def main() -> int:
    p = argparse.ArgumentParser(description="Run CS03 (AI Kosh RAG) case study.")
    p.add_argument("--metric", action="append", default=None,
                   help="metric@K, may be passed multiple times "
                        "(default: ndcg@10 + recall@5)")
    p.add_argument("--n-trials", type=int, default=200,
                   help="null-trial count (default: 200, publishable-grade)")
    p.add_argument("--tau", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--force", action="store_true",
                   help="overwrite existing results/cs03_results.json")
    args = p.parse_args()

    metrics = args.metric or ["ndcg@10", "recall@5"]
    out = RESULTS / "cs03_results.json"

    missing = _missing_inputs()
    if missing:
        print("CS03 is not yet runnable — required inputs are missing:",
              file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        print("\nThis is the expected state until Jasmeet (AI Kosh) provides:",
              file=sys.stderr)
        print("  data/queries.jsonl   — JSONL of {query_id, query_text, gold_ids}",
              file=sys.stderr)
        print("  data/pool.txt        — newline-separated item-id pool",
              file=sys.stderr)
        print("  data/retriever.py    — exports retrieve(query_text, k) -> list[item_id]",
              file=sys.stderr)
        return 2

    if out.exists() and not args.force:
        print(f"refusing to overwrite {out} — pass --force to regenerate",
              file=sys.stderr)
        return 2

    # Real run lives here once inputs land. Skeleton:
    #
    #   sys.path.insert(0, str(DATA))
    #   from retriever import retrieve  # provided by AI Kosh
    #   queries = [json.loads(line) for line in (DATA / "queries.jsonl").open()]
    #   pool = [line.strip() for line in (DATA / "pool.txt").open() if line.strip()]
    #   ...
    #   for metric_label in metrics:
    #       res = four_null_gate(retrieved, gold, rel, metric_fn,
    #                            item_pool=pool, k=k, n_trials=args.n_trials,
    #                            tau=args.tau, seed=args.seed)
    #   ...
    #   json.dump({"version": __version__, "metrics": all_results}, out.open("w"))
    raise NotImplementedError(
        "Inputs are present but the run logic is the slot waiting to be filled. "
        "Tracked under CS03 scaffold; do not back-fill until AI Kosh provides "
        "their retriever wrapper to avoid a dependency on speculative numbers."
    )


if __name__ == "__main__":
    sys.exit(main())
