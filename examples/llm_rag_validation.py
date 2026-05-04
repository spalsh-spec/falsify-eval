"""Validate any LLM-backed RAG pipeline with falsify-eval.

This example wraps a Claude-API call as a retriever and runs the
four-null gate on its output. To use a different provider (GPT-4, Llama,
Mistral, Gemini, etc.), swap the body of `claude_retriever` for whatever
SDK call returns top-K document IDs. Everything else stays identical.

USAGE:
    pip install anthropic
    export ANTHROPIC_API_KEY=...
    python examples/llm_rag_validation.py

If you don't have API access, this script falls back to a deterministic
keyword-matching retriever so you can still see the gate in action.

CALIBRATION NOTE:
    A "good" RAG retriever should pass all four nulls with Δ ≥ +0.05.
    A "broken" RAG retriever — one that's matching the gold marginal
    rather than understanding the query — will pass A/B/C but fail Null D.
    A "completely random" retriever will fail all four. The gate's
    contribution is making each of those three regimes distinguishable.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Make the example runnable from the repo root without `pip install -e .`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from falsify_eval import four_null_gate


# ── Toy corpus and queries (replace with your real bench in production) ──
CORPUS = {
    "doc_renewable":   "Renewable energy includes solar, wind, hydro, geothermal, and biomass.",
    "doc_solar":       "Solar panels convert sunlight into electricity using photovoltaic cells.",
    "doc_wind":        "Wind turbines convert kinetic energy from wind into electrical power.",
    "doc_hydro":       "Hydroelectric power uses flowing water to spin turbines.",
    "doc_nuclear":     "Nuclear fission releases energy by splitting heavy atomic nuclei.",
    "doc_fossil":      "Fossil fuels include coal, oil, and natural gas.",
    "doc_battery":     "Lithium-ion batteries store electrical energy chemically.",
    "doc_grid":        "The electrical grid distributes power from generators to consumers.",
    "doc_climate":     "Climate change is driven primarily by greenhouse gas emissions.",
    "doc_efficiency":  "Energy efficiency reduces consumption without reducing output.",
    "doc_carbon":      "Carbon capture removes CO2 from industrial exhaust streams.",
    "doc_ev":          "Electric vehicles use batteries instead of internal combustion engines.",
}

# Each query has one gold-truth document ID.
QUERIES = [
    ("How do solar panels work?",                "doc_solar"),
    ("What is wind power?",                       "doc_wind"),
    ("Tell me about hydroelectric energy",        "doc_hydro"),
    ("What is nuclear energy?",                   "doc_nuclear"),
    ("How does the electrical grid work?",        "doc_grid"),
    ("What are fossil fuels?",                    "doc_fossil"),
    ("How are batteries used to store energy?",   "doc_battery"),
    ("What causes climate change?",               "doc_climate"),
    ("What is energy efficiency?",                "doc_efficiency"),
    ("How is carbon captured?",                   "doc_carbon"),
    ("What is an EV?",                            "doc_ev"),
    ("List renewable energy types",               "doc_renewable"),
] * 5  # 60 queries total


# ── Retriever implementations ────────────────────────────────────────────
def claude_retriever(query: str, k: int = 5) -> list[str]:
    """Use Claude to rank documents for a query.

    To swap in OpenAI / Llama / Mistral / Gemini: replace the API call
    body. Input: a query string. Output: a list of K document IDs from
    CORPUS, ranked best-first.
    """
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("pip install anthropic")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("set ANTHROPIC_API_KEY")
    client = anthropic.Anthropic()
    docs_block = "\n".join(f"- {k}: {v}" for k, v in CORPUS.items())
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": f"Rank the top {k} most relevant documents for this query.\n\n"
                       f"Query: {query}\n\nDocuments:\n{docs_block}\n\n"
                       f"Reply with exactly {k} doc IDs, one per line, no explanation."
        }]
    )
    text = msg.content[0].text
    candidates = [line.strip().lstrip("-* ").split(":")[0].strip()
                  for line in text.splitlines() if line.strip()]
    return [c for c in candidates if c in CORPUS][:k]


def keyword_fallback_retriever(query: str, k: int = 5) -> list[str]:
    """Deterministic baseline: rank docs by overlap of query words with doc text."""
    q_words = set(query.lower().split())
    scored = sorted(CORPUS.items(),
                    key=lambda kv: -len(q_words & set(kv[1].lower().split())))
    return [doc_id for doc_id, _ in scored[:k]]


def random_baseline_retriever(query: str, k: int = 5) -> list[str]:
    """Negative control: random doc selection (gate should reject this)."""
    import random
    rng = random.Random(hash(query))
    return rng.sample(list(CORPUS), k)


# ── Run the gate against any retriever ───────────────────────────────────
def grade_retriever(name: str, retriever_fn):
    print(f"\n=== {name} ===")
    queries = [q for q, _ in QUERIES]
    gold = [g for _, g in QUERIES]
    rel = [3] * len(QUERIES)
    pool = list(CORPUS.keys())

    print(f"  retrieving {len(queries)} queries (this may take a minute for live API)...")
    retrieved = [retriever_fn(q, k=5) for q in queries]

    def recall_at_5(r, g, _rel):
        return 1.0 if g in r[:5] else 0.0

    res = four_null_gate(retrieved, gold, rel, recall_at_5,
                         item_pool=pool, k=5, n_trials=50, tau=0.05, seed=2026)
    print(f"  real recall@5 = {res['real_mean']:.4f}")
    for x in "ABCD":
        v = "✓" if res["passes"][x] else "✗"
        print(f"    Null {x}: Δ={res['deltas'][x]:+.4f}  {v}")
    print(f"  GATE: {'✓ PASS' if res['gate_passes'] else '✗ FAIL'}")
    return res


def main():
    print("falsify-eval LLM-RAG validation example")
    print(f"  corpus: {len(CORPUS)} docs, queries: {len(QUERIES)}")

    grade_retriever("random_baseline (should FAIL)", random_baseline_retriever)
    grade_retriever("keyword_fallback (should PASS modestly)", keyword_fallback_retriever)

    if os.environ.get("ANTHROPIC_API_KEY"):
        grade_retriever("claude (should PASS strongly)", claude_retriever)
    else:
        print("\n[skipping Claude — set ANTHROPIC_API_KEY to enable the real-LLM run]")
        print("  to test other LLMs: replace `claude_retriever` body with your provider's SDK")

    print("\nThe four-null gate is metric/engine-agnostic. To validate any other")
    print("LLM-backed retriever (GPT-4, Llama, Mistral, Gemini, Cohere, ...),")
    print("write a function that takes (query, k) and returns a list of K doc IDs,")
    print("then pass it to grade_retriever() above. Everything else is identical.")


if __name__ == "__main__":
    main()
