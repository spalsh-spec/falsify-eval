# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.6.2] — 2026-05-07

### Fixed — Mayank Singh round-3 polish (negative-seed validation)

Mayank ran a 25-probe round-3 review against v0.1.6.1 and reported 23/25 PASS.
The two non-PASS items both traced to flaws in his own test fixtures, except
one polish item we honour here: negative seed values fell through to
`numpy.random.default_rng(-1)` which raises an unhelpful internal error.

- `_validate_inputs` now rejects non-int and negative seeds up-front with a
  contextual `ValueError: seed must be a non-negative integer, got <repr>`.
- New regression test `test_d15_negative_or_non_int_seed_raises_clean_error`
  parametrised across 5 bad seeds (-1, -100, 0.5, "2026", None).

Credit: Mayank Singh — third clean round in 48 hours.

## [0.1.6.1] — 2026-05-07

### Fixed — Mayank Singh round-2 review (CLI stdin sentinel)

- `falsify-eval grade --input -` now reads JSONL from stdin (UNIX convention).
  v0.1.5.1 wrapped `args.input` in `Path()` before opening, which turned `-`
  into a literal filename and crashed with `FileNotFoundError: '-'`. v0.1.6.1
  threads `-` through `load_jsonl()` directly and dispatches to `sys.stdin`.
- Error messages now label stdin as `<stdin>` (e.g. `<stdin>:2: invalid JSON`)
  instead of leaking a misleading filename.
- `--input` help text now documents the `-` sentinel.
- 4 new regression tests in `tests/test_cli_stdin.py` exercise the fix via
  subprocess against the actual CLI entry point: stdin streaming success,
  empty-stdin clean failure (the v0.1.5.1 regression must not return),
  malformed-stdin error labelling, and file-input no-regression.

Credit: Mayank Singh — re-ran the full battery on v0.1.5.1 against the
six round-2 surfaces and surfaced this one cleanly with a one-line repro.

### Closed via v0.1.6 (Mayank's round-2 finding #2)

Mayank's round-2 also flagged the PREPRINT abstract still naming features
not shipped in the public library. v0.1.6 (shipped earlier today) already
addressed this: the abstract was rewritten to clearly separate shipped
vs methodology-spec items, and `bonferroni()` was added to the public
`stats` API. Mayank tested v0.1.5.1, which predates that fix.

## [0.1.6] — 2026-05-07

### Added — Lewi gap closure (consolidation pass)

Lewi Stone reviewed the brand site on 2026-05-07 and identified three real
gaps: (1) the empirical case was missing — no demonstration of the gate
working on a real, public benchmark; (2) the documentation promised evidence
and delivered analogy; (3) the framing conflated *AI systems* broadly with
*retrieval and ranking systems* specifically. This release closes all three.

- **`bonferroni()` helper** in `falsify_eval.stats` — the PREPRINT abstract
  has promised *Bonferroni-corrected paired tests* since v0.1.0 but the
  public library did not ship the helper. It does now. Returns family-wise
  adjusted p-values, per-test α, and a per-test reject decision.
- **`tests/test_stats_vs_scipy.py`** — 11 cross-check tests that reconcile
  our pure-numpy `bootstrap_ci`, `paired_permutation_p`, `cohens_d_paired`,
  and `bonferroni` against scipy on identical fixed-seed inputs. Closes
  Mayank attack-surface #4 ahead of his next round.
- **`tests/test_property_based.py`** — 4 property-based tests via
  `hypothesis`: determinism under same seed, oracle always passes,
  constant cheater always fails Δ_D, query-order permutation invariance.
  Each test runs ~15 randomly generated benches per property.

### Changed — copy + scope honesty

- `EXPLAINER_simple.html` — title, og tags, and three body sections rewritten
  from "AI systems" to "search and ranking systems". Added explicit
  **scope-honesty callout block** at the top: tests retrieval-and-ranking,
  does NOT test generative LLM outputs. Both case-study links inline.
- `PREPRINT.md` abstract — struck the *cryptographic record* framing
  (corrected to *integrity-check record (SHA-256 + git commit)* per v0.1.5
  calibration discipline). Added explicit shipped-vs-planned column for the
  five-part harness so a reader knows exactly what is in the public library
  vs what is methodology spec only. Replaced the *generalises to LLM
  behavioural eval pipelines* claim with a sober *candidate research
  direction* phrasing. Added a paragraph documenting the empirical CS01
  result and the metric-sensitivity finding.
- `README.md` — links to CS02 alongside CS01, status section updated.

### Added — case study CS02 (SciFact triangulation)

`case_studies/cs02_scifact/` — second BEIR slice, 300 queries × 5,183 docs,
sparse relevance (~1.1 docs/query). Confirms the gate works AND triangulates
the CS01 metric-sensitivity finding: on sparse-relevance benchmarks both
metrics give clean separation, on dense-relevance only the single-gold
metric does. Joint CS01+CS02 picture provides empirical foundation across
two relevance regimes.

### Tests
- 58 passing on a fresh clone (was 43 in v0.1.5.2):
  smoke 8 + validation 9 + Mayank battery 26 + scipy cross-check 11 +
  property-based 4. All run in <3 seconds.

## [0.1.5.2] — 2026-05-06

### Added — `progress=True` flag (Akosh-AI 5-hour incident)

Mayank reported the gate had been running 5 hours under Akosh AI's harness
with no visible progress. Profiling confirmed the gate itself is fast
(N=5,000 × pool=100k × n_trials=50 finishes in <2s with a cheap metric).
The 5-hour runtime is fully explained by an LLM-judge metric at ~200 ms /
call: ``N * (1 + 4 * n_trials)`` calls = ~100k for N=500, n_trials=50,
which at 200 ms each is ~5.6 hours.

The library can't speed up a slow user metric, but it can stop running
silently. v0.1.5.2 adds:

- `four_null_gate(..., progress=True)` — prints per-stage timing to stderr
  with the expected number of `metric_fn` calls, so the user can tell
  whether the run is making progress, see which stage is the bottleneck,
  and decide whether to lower `n_trials` or kill the run.
- `result["stage_seconds"]` — populated when `progress=True`. Lets
  downstream tooling collect timing without reparsing stderr.
- README "Why is my run taking so long?" troubleshooting section with the
  exact `N * (1 + 4 * n_trials)` formula.

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
