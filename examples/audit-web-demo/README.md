# audit-web-demo

Small public demo for the local-first audit workbench in `apps/web`.

Use it when reviewing the Phase 3 public-readiness flow:

```bash
cd /Users/sparshsharma/falsify-eval-prep
npm run build:cli --workspace apps/web
node apps/web/dist-cli/falsify-audit.mjs run \
  --dataset examples/audit-web-demo/dataset.jsonl \
  --system examples/audit-web-demo/system-output.jsonl \
  --corpus examples/audit-web-demo/corpus.jsonl \
  --config examples/audit-web-demo/config.yaml \
  --out /tmp/falsify-audit-web-demo.json \
  --pack-out /tmp/falsify-audit-web-demo-pack
```

Expected CLI summary:

```text
WARN 1.000000 /tmp/falsify-audit-web-demo.json
```

The WARN is intentional. This sample has only 3 queries, so the app passes the evidence checks but warns that the benchmark is too small for a strong public claim.

Files:

- `dataset.jsonl`: 3 RAG retrieval queries with gold document IDs
- `corpus.jsonl`: 7 public-safe toy documents
- `system-output.jsonl`: candidate retriever output
- `baseline-output.json`: generated BM25 baseline output for review
- `config.yaml`: claim configuration
- `expected-report.md`: expected readable report shape

