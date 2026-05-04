# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] — 2026-05-04

### Fixed
- **`k > len(item_pool)` now raises a clear `ValueError`** instead of crashing
  with a raw numpy "Cannot take a larger sample than population" error from
  inside Null C. Caught by the public stress-test ladder (Tier 5a).
- **Gold labels not present in `item_pool` now raise a clear `ValueError`**
  instead of silently producing all-zero output that read as "everything fails
  the gate." The error names the missing labels (first 5 + count). Caught by
  the public stress-test ladder (Tier 5f).

### Added
- **`falsify-eval` CLI.** Non-Python users can now drive the four-null gate
  from JSONL files: `falsify-eval grade --input bench.jsonl --metric ndcg@5`.
  Built-in metrics: `ndcg`, `recall`, `mrr` at any K. Subcommands `lock` and
  `verify` wrap `lock_state` / `verify_state`.
- **MCP server (`python -m falsify_eval.mcp_server`).** Exposes
  `grade_retrieval` as a tool any MCP client (Claude Code, Claude Desktop,
  custom enterprise apps) can invoke directly. Stdio JSON-RPC; no extra
  dependencies beyond the base library.
- **Result dict now includes a `warnings` list.** Soft signals that the gate
  ran successfully but the *interpretation* needs care:
  - single-class benchmark (Null A and Null D mathematically collapse)
  - sparse marginal (Null D's marginal estimator is noisy when N < 2·|pool|)
- Comprehensive input-validation tests in `tests/test_validation.py`.
- Public stress-test ladder (`STRESS_TEST_LADDER.md`) with five tiers from
  smoke test to mathematical-edge cases, plus runnable scripts in
  `tests/stress/`.

### Scope statement (added in response to user request)
- falsify-eval is a methodology for **retrieval / ranking evaluation**.
  Generalising the four-null gate to LLM text-generation, classification, RAG,
  or recommender-system evaluation requires *new null distributions designed
  for those domains*. That is v0.3+ work; we will not claim universal coverage
  before doing it. Standard II of the house.

## [0.1.2] — 2026-05-04

### Fixed
- **README hero install command was broken.** Removed `pip install falsify-eval`
  (package is not yet published to PyPI; would have produced
  "No matching distribution found"). Replaced with the source-install path
  that actually works today, plus a one-line note that PyPI is planned for v0.2.
- **README hero demo command was broken** (`python -m falsify_eval.examples.synthetic_demo`
  failed with `ModuleNotFoundError: No module named 'falsify_eval.examples'`
  because the `examples/` directory is at the repo root, not inside the
  package). Replaced with `python3 examples/synthetic_demo.py`.
- **README "Quick demo" git-clone URL contained a literal `<your-handle>`
  placeholder** that any real user would have copy-pasted verbatim and seen
  fail. Replaced with the real `spalsh-spec/falsify-eval` URL.
- **`pyproject.toml` Homepage and Issues URLs pointed at non-existent
  `github.com/sparshsharma/falsify-eval`** (HTTP 404). Corrected to
  `github.com/spalsh-spec/falsify-eval` and added explicit `Repository` URL
  for completeness.
- Suspended the cash bug-bounty programme pending further internal validation
  (removed from README, CONTRIBUTING, SECURITY, issue template, and
  config.yml; preserved as academic record in PREPRINT §10 with status note).

### Reported by
- External user (Akosh, India, 2026-05-04). All four blockers were
  reproducible on a fresh clone with Python 3.14 + numpy 2.4.4.

## [0.1.1] — 2026-05-01

### Fixed
- Export `bootstrap_diff_ci` and `power_n_required` from top-level package
  (`from falsify_eval import bootstrap_diff_ci` was previously broken despite
  being documented in the README; caught by the new CI import-smoke job).

### Added
- GitHub Actions CI matrix (Python 3.10/3.11/3.12 × ubuntu/macos)
- Issue and PR templates
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`
- `PREPRINT.md` and `SUPPLEMENTARY.md` shipped in-repo
- README `## Preprint` section with anchor

## [0.1.0] — 2026-05-01

### Added
- Initial public release.
- Four-null falsification gate: `four_null_gate`, `null_a_permuted`,
  `null_b_uniform`, `null_c_random_retrieval`, `null_d_marginal_matched`.
- Cryptographic state lock: `lock_state`, `verify_state`.
- Statistical reporting: `bootstrap_ci`, `bootstrap_diff_ci`,
  `paired_permutation_p`, `cohens_d_paired`, `power_n_required`.
- 50-query synthetic demo (`examples/synthetic_demo.py`) covering oracle,
  constant predictor, and plausible mock engine.
- 8 unit tests covering gate correctness, statistical primitives, and lock
  round-trip.

[Unreleased]: https://github.com/spalsh-spec/falsify-eval/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/spalsh-spec/falsify-eval/releases/tag/v0.1.0
