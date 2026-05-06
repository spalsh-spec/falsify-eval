# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.5.1] — 2026-05-06

### Fixed — same defect class as Mayank #1, third null

- `null_a_permuted` was the last null still passing the label list directly
  to `np.random.default_rng().permutation()`. For tuple labels, numpy
  silently converts list-of-tuples to a 2D array; for frozen dataclass labels
  without `order=True`, the prerequisite `sorted(set(...))` raised TypeError.
  Both cases crashed the whole gate. Fix: same index-based permutation +
  `(type(x).__name__, repr(x))` sort key already used in null_b/null_d.
- Two new regression tests (`test_d1b_*`, `test_d1c_*`) cover tuple and
  frozen-dataclass labels end-to-end (oracle passes, constant cheater fails).

## [0.1.5] — 2026-05-06

### Fixed — Mayank Singh adversarial battery (14 defects, headline #1 catastrophic)

Credit: **Mayank Singh / Indian AI Lab** ran a 47-test stress battery against
v0.1.4 and surfaced 14 real defects. Every fix below is paired with a
regression test in `tests/test_mayank_battery.py`.

- **CRITICAL — `str()` cast catastrophe (Defect #1):** `null_b_uniform` and
  `null_d_marginal_matched` wrapped each random gold draw in `str(label)`.
  For any non-string label type (`int`, `float`, `np.int64`, tuple, dataclass)
  the comparator inside the user-supplied metric never matched, the null mean
  collapsed toward zero, Δ inflated to ≈ real_mean, and the gate's central
  guarantee was silently void. **Constant-most-frequent predictors PASSED
  the gate** for any non-string label set. Fix: type-preserving index-based
  sampling (sample indices into the sorted label list, then look up the
  original label object). Verified across `str`, `int`, `np.int64`, `float`.
- **Null C silently used the gold-label set as the pool (Defect #2):** v0.1.4
  defaulted `item_pool=None` to "use the gold set". On a real corpus this
  makes Null C ~|gold| / |pool| ≈ 1000× weaker than honest. v0.1.5 raises
  `ValueError` when `item_pool` is omitted; the caller must pass the actual
  chunk-id pool.
- **`k > len(item_pool)` raised raw numpy error (Defect #3):** now raises a
  contextual `ValueError` with the offending sizes.
- **"Cryptographic" overselling (Defect #4):** the lock primitive is SHA-256 +
  git-commit binding, an *integrity check* that catches accidental drift,
  not a tamper-proof seal against an adversary with write access to the
  artifacts and the lock. README and `lock.py` docstring corrected; explicit
  threat-model paragraph added.
- **`DEFAULT_TRACKED` extension list (Defect #5):** intentionally excludes
  `.py`, `.md`, `.csv`, `.yaml` because git already tracks them and the
  git-commit binding covers them — but v0.1.4 didn't say so. Docstring now
  documents the choice and shows the opt-in pattern
  (`tracked_extensions=DEFAULT_TRACKED | {".py", ".md"}`).
- **Empty inputs (Defect #6):** clean `ValueError` instead of RuntimeWarning + NaN.
- **Version drift (Defect #7):** `__init__.py` and `pyproject.toml` now sync-tested.
- **Single-class bench (Defect #8):** Null A and Null D collapse to identical
  distributions; v0.1.5 emits a warning so the caller knows ΔA and ΔD are one
  test, not two.
- **Sparse marginal (Defect #9):** when N < 2·|pool|, Null D's marginal estimator
  degenerates toward Null B; v0.1.5 emits a warning.
- **Order-stable label set across runs (Defect #10):** sort key is
  `(type(x).__name__, repr(x))` — total order even with mixed types.
- **`k` validation (Defect #11):** must be a positive integer; floats / zero /
  negative / strings / None all rejected up front.
- **`tau` validation (Defect #12):** must be in `[0, 1]`; values outside the
  interval rejected up front.
- **Gold not in pool (Defect #13):** previously produced silent all-zero
  output because Null C could never sample the gold. Now raises with a
  preview of the offending labels.
- **Length mismatch (Defect #14):** previously truncated to the shortest of
  the three lists. Now raises with all three lengths in the error message.

### Added
- `tests/test_mayank_battery.py` — 24 regression tests covering every defect
  above, parametrised across label types where relevant.
- `four_null_gate` result now includes a `warnings: list[str]` field for the
  single-class and sparse-marginal flags.

## [0.1.4] — 2026-05-04

### Added — terminal UX overhaul (Claude-Code-style hints)
- `falsify-eval doctor` — end-to-end install verification. Reports python +
  numpy + falsify-eval versions, runs the gate against an embedded demo
  bench, prints next-step commands. The right first command for any new user.
- `falsify-eval quickstart [DIR]` — writes a sample `bench.jsonl` and
  `pool.txt` and prints the exact `grade` command to run against them.
  Zero-friction first-run.
- `falsify-eval grade --demo` — grade an embedded 50-query synthetic bench
  with no input files needed. Useful for CI smoke-tests and "does this even
  work" checks.
- ANSI-coloured output (auto-disabled when not a TTY or when `NO_COLOR`
  env var is set, so CI logs stay clean).
- Post-grade "what's next?" hint footer suggesting the next command,
  conditional on PASS vs FAIL. On FAIL, diagnoses which null failed and
  suggests the most likely cause.
- Per-error contextual hints. `INPUT ERROR: k=99 > len(item_pool)=8` is
  followed by a `hint:` line suggesting `--pool` or smaller K in `--metric`.
  The "gold not in pool" error suggests label-set drift between train/eval.
- `--quiet` flag on `grade` to suppress hints (for piping/JSON consumers).
- Examples in every subcommand's `--help` output.

### Added — explicit compatibility statement
- README now lists every environment falsify-eval is known to install in
  with a one-line install command: local, Colab, Kaggle/Sagemaker, GitHub
  Actions, Docker, AWS Lambda, air-gapped. The library is pure Python +
  numpy with no native extensions, so the audit surface is tiny and the
  deployment surface is large.

### Added — LLM-RAG validation worked example
- `examples/llm_rag_validation.py` — wraps a Claude-Haiku call as a
  retriever and runs the four-null gate on its output. Includes a
  random-baseline negative control and a keyword-fallback positive control
  so the gate's three regimes (FAIL / modest PASS / strong PASS) are
  visible. To adapt to GPT-4, Llama, Mistral, Gemini, or any other LLM:
  swap the body of the retriever function. Everything else is identical.
- Documentation explicitly states that falsify-eval grades the
  *retrieval side* of any RAG pipeline, regardless of LLM vendor or stack
  (BM25, FAISS, Pinecone, Weaviate, Vespa, etc.).

### Honest non-claim
We do **not** claim "tested against every known AI model." That requires
hundreds of dollars in API costs and a multi-day study. We ship the
worked Claude example as a pattern; running it against other models is
one function-body swap and we encourage external validators to publish
the result of doing so.

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
