# Contributing to falsify-eval

Thanks for considering a contribution. This library is intentionally small; the
goal is for adopters to be able to audit the entire codebase before depending
on it. That priority shapes everything below.

## Scope

In scope:

- New null distributions that catch a documented failure mode the existing four
  do not (with empirical evidence on the broken-predictor suite).
- Bug fixes in the statistical machinery.
- Performance improvements that do not change numerical results (provable to
  within float-tolerance on the demo).
- Documentation, tests, and examples.

Out of scope (please don't):

- Adding heavy dependencies (sklearn, torch, pandas at runtime). The whole
  point is `numpy`-only.
- Adding new metrics. Bring your own metric — `four_null_gate` is metric-
  agnostic by design.
- Wrapping retrieval engines. This is an evaluation library, not a retrieval
  one.

## Setup

```bash
git clone https://github.com/spalsh-spec/falsify-eval.git
cd falsify-eval
python -m venv .venv && source .venv/bin/activate
pip install -e .
pip install pytest
```

## Tests

```bash
python -m pytest tests/ -q
python examples/synthetic_demo.py
```

The demo's expected verdict is documented in its own header. If your change
alters the verdict, that is a deliberate methodological change and must be
justified in the PR description.

## Style

- Pure Python, no formatter lock-in. Match the existing style.
- Type hints on public functions. Internals can be untyped if it improves
  readability.
- Docstrings on every public function: one-line summary, then a paragraph
  explaining the statistical interpretation, then args/returns.

## PRs

Use the PR template. Small, focused PRs ship faster than big ones. If you're
proposing a methodological change, open a discussion first so we can avoid you
spending time on something that won't merge.

## Bug bounty

See README §Bug bounty. Bounty submissions go through the dedicated issue
template, not regular bug reports.

## Code of conduct

See `CODE_OF_CONDUCT.md`. The short version: be the kind of collaborator you
would want to work with.
