"""Model Context Protocol (MCP) server — exposes the four-null gate as a
tool any MCP client (Claude Code, Claude Desktop, custom enterprise apps)
can invoke directly.

Run:
    pip install "falsify-eval[mcp]"
    python -m falsify_eval.mcp_server

In your MCP client config (e.g. Claude Code):
    {
      "mcpServers": {
        "falsify-eval": {
          "command": "python",
          "args": ["-m", "falsify_eval.mcp_server"]
        }
      }
    }

The server exposes one tool:
    grade_retrieval — run the four-null gate on supplied bench data.
"""
from __future__ import annotations

import json
import math
import sys
from typing import Any

from .gate import four_null_gate


def _ndcg(retrieved, gold, rel, k):
    rels = [rel if r == gold else 0 for r in retrieved[:k]]
    ideal = sorted(rels, reverse=True)
    idcg = sum(rr / math.log2(i + 2) for i, rr in enumerate(ideal[:k]))
    if idcg == 0:
        return 0.0
    return sum(rr / math.log2(i + 2) for i, rr in enumerate(rels[:k])) / idcg


def _recall(retrieved, gold, rel, k):
    return 1.0 if gold in retrieved[:k] else 0.0


def _mrr(retrieved, gold, rel, k):
    for i, r in enumerate(retrieved[:k]):
        if r == gold:
            return 1.0 / (i + 1)
    return 0.0


METRICS = {"ndcg": _ndcg, "recall": _recall, "mrr": _mrr}


# ── Tool implementation (transport-agnostic) ──────────────────────────────
def grade_retrieval(retrieved: list[list[Any]],
                    gold: list[Any],
                    metric: str = "ndcg@5",
                    item_pool: list[Any] | None = None,
                    rel: list[int] | None = None,
                    n_trials: int = 50,
                    tau: float = 0.05,
                    seed: int = 2026) -> dict:
    """Grade a retrieval system's output against the four-null gate.

    Args:
        retrieved:  per-query top-K item lists (list of lists)
        gold:       per-query gold-truth label
        metric:     "name@K" string; choices: "ndcg@K", "recall@K", "mrr@K"
        item_pool:  full label/item universe (required for Null C, gold-validation)
        rel:        per-query relevance score (default 3 for all)
        n_trials:   null-trial count (default 50)
        tau:        per-null Δ threshold the gate requires (default 0.05)
        seed:       RNG seed for reproducibility

    Returns:
        Full gate result dict (real_mean, null_means, deltas, passes,
        gate_passes, warnings).
    """
    name, _, k_str = metric.partition("@")
    if name not in METRICS:
        raise ValueError(f"unknown metric '{name}'; choices: {list(METRICS)}")
    if not k_str.isdigit():
        raise ValueError(f"metric must be 'name@K' (e.g. 'ndcg@5'), got '{metric}'")
    k = int(k_str)
    metric_fn = lambda r, g, rl: METRICS[name](r, g, rl, k)

    if rel is None:
        rel = [3] * len(gold)

    return four_null_gate(retrieved, gold, rel, metric_fn,
                          item_pool=item_pool, k=k,
                          n_trials=n_trials, tau=tau, seed=seed)


# ── MCP transport (stdio JSON-RPC, minimal handshake) ────────────────────
TOOL_DEFINITION = {
    "name": "grade_retrieval",
    "description": (
        "Run the falsify-eval four-null gate on a retrieval system's output. "
        "Catches false positives that standard aggregate-metric reporting "
        "silently accepts (e.g., predictors that exploit gold-label marginals). "
        "Use when validating any RAG system, search ranker, or "
        "retrieval evaluation before publishing or shipping the numbers."
    ),
    "inputSchema": {
        "type": "object",
        "required": ["retrieved", "gold"],
        "properties": {
            "retrieved": {
                "type": "array",
                "items": {"type": "array"},
                "description": "Per-query top-K retrieved item lists."
            },
            "gold": {
                "type": "array",
                "description": "Per-query gold-truth label."
            },
            "metric": {
                "type": "string",
                "default": "ndcg@5",
                "description": "Metric in 'name@K' form: ndcg, recall, or mrr."
            },
            "item_pool": {
                "type": "array",
                "description": "Full label/item universe (required for Null C)."
            },
            "rel": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Per-query relevance score (defaults to 3)."
            },
            "n_trials": {"type": "integer", "default": 50, "minimum": 1},
            "tau": {"type": "number", "default": 0.05, "minimum": 0, "maximum": 1},
            "seed": {"type": "integer", "default": 2026},
        },
    },
}


def _send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _handle(req):
    method = req.get("method")
    rid = req.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "falsify-eval", "version": "0.1.3"},
        }}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": [TOOL_DEFINITION]}}
    if method == "tools/call":
        params = req.get("params", {})
        if params.get("name") != "grade_retrieval":
            return {"jsonrpc": "2.0", "id": rid, "error": {
                "code": -32601, "message": f"unknown tool: {params.get('name')}"}}
        args = params.get("arguments", {})
        try:
            result = grade_retrieval(**args)
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": json.dumps(result, indent=2, default=float)}],
                "isError": False,
            }}
        except (ValueError, TypeError) as e:
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": f"INPUT ERROR: {e}"}],
                "isError": True,
            }}
    return {"jsonrpc": "2.0", "id": rid, "error": {
        "code": -32601, "message": f"unknown method: {method}"}}


def serve_stdio():
    """Minimal stdio JSON-RPC loop. Production deployments may prefer
    `mcp`-package's Server class; this stub avoids the extra dependency."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = _handle(req)
        if resp is not None:
            _send(resp)


if __name__ == "__main__":
    serve_stdio()
