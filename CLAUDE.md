# CLAUDE.md — falsify-eval orientation

> **Read `~/bhardwaj-private/CLAUDE.md` FIRST** for the firm-level rules,
> calibration discipline, and brand voice. This file is the project-specific
> overlay for falsify-eval only.

**Verified-fresh date:** 2026-05-04
**HEAD:** `7b742e4`
**pyproject version:** 0.1.4
**Latest tag on GitHub:** v0.1.0 (older — newer versions awaiting tag push)

## 1. What this project is

`falsify-eval` is a calibrated falsification harness for **retrieval and
ranking evaluation**. The core contribution is the **four-null Δ-metric
gate** — testing engine output against four orthogonal null distributions:

- **Null A** — gold-permuted (bijection π over distinct labels)
- **Null B** — gold-uniform-random
- **Null C** — random retrieval over item_pool
- **Null D** — gold-marginal-matched random *(novel; the contribution)*

Null D catches predictors matched to the empirical class marginal that
A and B can false-positive. Documented in `PREPRINT.md` §10.

## 2. What this project IS NOT

These are explicit non-goals. Do not let the user pull you toward them
without invoking the calibration push-back from CALIBRATION_DISCIPLINE.md.

- ✗ Not a general-purpose AI evaluation library — it's calibrated for
  retrieval/ranking specifically. LLM text-generation, multi-document
  summarisation, classification, RAG generation-side need their own null
  distributions (planned v0.3+).
- ✗ Not a benchmark — it's a *meta-evaluation* tool that grades any
  benchmark.
- ✗ Not bundled with retrieval engines — it accepts top-K output from
  whatever engine you bring.
- ✗ Not a SaaS — it's an Apache-2.0 library + CLI + MCP server.

## 3. Architecture

```
falsify_eval/
├── __init__.py          ← public API exports + __version__
├── gate.py              ← four_null_gate() + four null implementations
├── stats.py             ← bootstrap_ci, paired_permutation_p, cohens_d_paired,
│                          power_n_required, bootstrap_diff_ci
├── lock.py              ← lock_state() + verify_state() — artifact hashing
├── cli.py               ← argparse: doctor / quickstart / grade / lock / verify
└── mcp_server.py        ← MCP stdio server exposing grade_retrieval

tests/
├── test_smoke.py        ← 8 tests (gate behaviour + stats correctness)
├── test_validation.py   ← 9 tests (input-validation guards from v0.1.3)
└── stress/              ← Tier 4 + 5 from STRESS_TEST_LADDER.md

examples/
├── synthetic_demo.py    ← embedded 50-query toy bench
└── llm_rag_validation.py ← Claude-Haiku worked example

docs/
├── README.md            ← user-facing entry point (PUBLIC)
├── PREPRINT.md          ← methodology paper (PUBLIC)
├── SUPPLEMENTARY.md     ← preprint appendix (PUBLIC)
├── CHANGELOG.md         ← per-version history (PUBLIC)
├── STRESS_TEST_LADDER.md ← 5-tier external validation guide (PUBLIC)
├── CONTRIBUTING.md      ← (PUBLIC)
├── CODE_OF_CONDUCT.md   ← (PUBLIC)
└── SECURITY.md          ← (PUBLIC)
```

## 4. Verifiable state (re-check before any release)

Run these and confirm the outputs:

```bash
cd ~/falsify-eval-prep
git rev-parse HEAD                    # expect: 7b742e4 or descendant
grep '^version' pyproject.toml        # expect: version = "0.1.4" or higher
grep '__version__' falsify_eval/__init__.py  # must match pyproject

source .venv/bin/activate
python -m pytest tests/test_smoke.py tests/test_validation.py -v
# expect: 17 passed

falsify-eval doctor
# expect: All systems green
```

If any of those fail, **stop and investigate**. Do not paper over.

## 5. Hard rules specific to this project

1. **Apache 2.0 forever.** No proprietary forks, no commercial-license
   carve-out. The library being free *is the moat*. Standard I.
2. **No pre-1.0 API stability promises.** Breaking changes allowed in
   minor bumps (0.x.0) until v1.0. Document in CHANGELOG.
3. **Numpy is the only runtime dependency.** Adding any other dep
   requires a documented architectural reason. The 50-KB-wheel
   discipline is a feature.
4. **Every new public function gets a docstring with a statistical
   interpretation paragraph.** Not a one-liner.
5. **No CI/CD service that costs money.** GitHub Actions free tier only.
6. **Verification on fresh clone before any release.** RUN_RELEASE.md
   step "second fresh-clone Akosh-simulation" exists for this reason.
7. **Reporters of bugs get credited in CHANGELOG by name.** This is the
   cohort flywheel; do not skip.

## 6. Release workflow (use the runbook, do not improvise)

Use `~/bhardwaj-private/runbooks/RUN_RELEASE.md` for any release. The
automated path:

```bash
~/bhardwaj-private/pipelines/auto_release.sh patch "summary"
```

The script refuses to release if working tree dirty, tests fail, doctor
reports issues, or CHANGELOG missing the new heading. **Trust the
script's refusals. Do not bypass.**

## 7. Open issues / known limits (be honest about these in user-facing copy)

| Issue | Surfaced where | Status |
|---|---|---|
| LLM text-gen domain not yet supported | README scope statement | v0.3+ planned |
| Sneaky-marginal predictor classification (Tier 4 in STRESS_TEST_LADDER) | passes 5/5 today but methodology has known limit on clustered queries | documented |
| Bootstrap CI assumes iid queries; clustered queries → optimistic CI | STRESS_TEST_LADDER §5d | known limit, no fix planned |
| Cash bug bounty suspended | SECURITY.md, CHANGELOG v0.1.2 | will reinstate after broader validation |

## 8. The Akosh canonical case

External user Akosh in India (2026-05-04) reported "failed basic bench
tests." Three install-path bugs in README + pyproject.toml. Resolution
in 45 min via RUN_INCIDENT.md → v0.1.2. Documented in
`~/bhardwaj-private/dossiers/INCIDENT_LOG.md`.

**Treat every external bug report this way.** Reproduce on fresh clone,
fix the smallest scope, ship a patch release, credit the reporter,
update the runbook if a new pattern emerged.

## 9. What ships in the next release (v0.2 milestone)

- First PyPI publish (name `falsify-eval` is reserved as of 2026-05-04)
- Zenodo DOI for citation
- arXiv submission (after endorsement secured)
- Resume the cash bug bounty programme — only after Akosh stress-ladder
  completes successfully

Do not ship v0.2 until each of those is verifiably done.

## 10. End-of-session protocol

1. Run `python -m pytest tests/` — must be 17 passed
2. Run `falsify-eval doctor` — must be All systems green
3. Verify `git status` clean
4. Update `~/bhardwaj-private/crm/data.json` if any project state changed
5. Update master `~/bhardwaj-private/CLAUDE.md` §2 if HEAD/version changed

## 11. BOUNDARIES — files Claude must NOT read or enumerate

This section is enforced by `.claude/settings.json` and `.claudeignore` in
this directory. Listed here so the discipline is also visible to any
Claude session that loads this CLAUDE.md.

**Never enumerate (do not run `find .` or `ls -R` or broad globs):**
- `./.git/`, `./.venv/`, `./.pytest_cache/`, `./__pycache__/`
- `./build/`, `./dist/`, `./*.egg-info/`

**Hard-denied — paths outside this project:**
- `/Users/sparshsharma/bhardwaj-private/**` — strategic vault (compartmentation)
- `/Users/sparshsharma/vak_engine/**` — private retrieval engine
- These cross-project reads are denied at the settings-permission layer.
  If you genuinely need information from those projects, START a new
  Claude Code session inside that project — do not reach across boundaries.

**Edit requires confirmation:**
- `pyproject.toml`, `CHANGELOG.md`, `SECURITY.md`, `PREPRINT.md`, this `CLAUDE.md`

**Ask before:**
- `git push:*` — public-facing repo, but verify intent
- `twine upload:*` — irreversible PyPI publish
- `python -m build:*` — only for release flow

**To navigate this project efficiently, use the architecture map in §3 above**
rather than enumerating files.
