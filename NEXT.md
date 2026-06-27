# Where things stand — 2026-05-09

Working tree clean. Latest tag: v0.1.6.11. CI green on every workflow except
"Publish to PyPI", which fails at the OIDC step *as expected* until the
PyPI-side trusted-publisher setup is done.

## Tomorrow, in priority order

### 1. PyPI manual setup (10 min, only you can do this)

See `docs/PYPI_PUBLISHING.md`. Three small steps on pypi.org:

1. Create PyPI account → 2FA → email verified.
2. Add a Pending publisher at https://pypi.org/manage/account/publishing/
   pointing at `spalsh-spec / falsify-eval / publish.yml / pypi`.
3. Create the `pypi` environment at
   https://github.com/spalsh-spec/falsify-eval/settings/environments.

Then re-trigger the publish workflow:
`gh workflow run "Publish to PyPI"` (or push a v* tag).

Once that succeeds: install becomes `pip install falsify-eval`. That's the
credibility cliff.

### 2. arXiv submission (30 min)

```
./tools/build_arxiv.sh
# upload arxiv/falsify-eval-arxiv-submission.tar.gz at https://arxiv.org/submit
```

Full checklist + cover letter draft + categorisation in
`docs/ARXIV_SUBMISSION.md`. Categories: cs.IR primary, cs.LG cross-list.

### 3. Wait on Jasmeet (CS03)

Slot scaffolded at `case_studies/cs03_aikosh_rag/`. He'll send results when
the AIKosh integration runs. Don't poke him for at least a week.

### 4. Then the social posts

Three drafts (Twitter / LinkedIn / Hacker News) live in this conversation's
thread, dated 2026-05-09. Don't post them until PyPI is live so the install
line reads `pip install falsify-eval` instead of the git URL.

## What's deferred (not forgotten)

- **Mutation testing** — `mutmut` is broken on Py 3.14 upstream. Pinned to
  v0.2 milestone. Config already in `pyproject.toml`. See
  `docs/MUTATION_TESTING.md`.
- **`label_order_seed` parameter** — would close the last gap in the
  equivariance certificate (PREPRINT §5.9). v0.2 candidate.
- **Case studies CS04 (FiQA), CS05 (Quora)** — methodology triangulation
  on more public benchmarks. v0.2 milestone.

## Don't forget

- The work this week was good *because of how you worked* — small, real,
  named bugs, named testers. That's the way that scales.
- Six commits in one day: 0.1.6.4 → 0.1.6.11. Two real external testers
  (Jasmeet + Mayank). Equivariance certificate. Property suite. CI matrix.
  PyPI pipeline. arXiv pipeline. That's a real week.
- Sleep, food, water, one human conversation. In that order.
# Audit tool deferred work

- Done: YAML claim config support with `js-yaml` JSON schema parsing.
- Done: packaged CLI:
  `falsify-audit run --dataset data.jsonl --system system.jsonl --baseline baseline.jsonl --config claim.yaml --out report.json`
- Done: optional corpus input with local BM25 lexical baseline.
- Done: API route integration tests with multipart uploads.
- Done: RAG JSONL importer aliases, dataset quality report, and demo files.
- Done: Phase 2 comparison view, local templates, audit pack export, and CLI/web parity paths.
- Add optional encrypted-at-rest local storage for highly sensitive benchmark data.
- Add job retention policy and scheduled local cleanup.
