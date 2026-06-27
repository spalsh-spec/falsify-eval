# falsify-eval audit web app

Local-first audit workbench for retrieval and RAG ranking claims.

Best for retrieval, ranking, and RAG retrieval-side audits. It is not a free-text generation judge.

## Run

```bash
cd /Users/sparshsharma/falsify-eval-prep
npm install
npm run dev --workspace apps/web
```

Open `http://localhost:3000`.

## Inputs

- Dataset: `.json` or `.jsonl`
- System output: `.json` or `.jsonl`
- Baseline output: `.json` or `.jsonl`
- Optional corpus: `.json` or `.jsonl` with document `id` and `text`
- Claim config: JSON or YAML

If a corpus is uploaded, the app builds a real BM25 lexical baseline and uses it as the comparison baseline. If no corpus is uploaded, upload a baseline output file.

## RAG JSONL importer

Native dataset row:

```json
{"id":"q1","query":"What is BM25?","expected_answer":"A lexical ranker","relevant_ids":["doc1"]}
```

Common RAG aliases are accepted:

```json
{"question":"What is BM25?","ground_truth":"A lexical ranker","contexts":["BM25 passage"]}
```

Corpus row:

```json
{"id":"doc1","text":"BM25 is a lexical ranking baseline."}
```

Corpus aliases accepted: `doc_id`, `document_id`, `content`, `page_content`, and `body`.

## Demo

Browser:

1. Run the app.
2. Click `Try sample audit`.
3. Export JSON or Markdown from the report panel.

CLI:

```bash
cd /Users/sparshsharma/falsify-eval-prep
npm run build:cli --workspace apps/web
node apps/web/dist-cli/falsify-audit.mjs run \
  --dataset examples/audit-web-demo/dataset.jsonl \
  --system examples/audit-web-demo/system-output.jsonl \
  --corpus examples/audit-web-demo/corpus.jsonl \
  --config examples/audit-web-demo/config.yaml \
  --out /tmp/falsify-audit-demo.json \
  --pack-out /tmp/falsify-audit-pack
```

Reference inputs and the expected Markdown report live in `examples/audit-web-demo/`.

## Templates

```bash
node apps/web/dist-cli/falsify-audit.mjs template --template rag_search --out /tmp/rag-claim.yaml
node apps/web/dist-cli/falsify-audit.mjs template --template support_docs_qa --out /tmp/support-claim.yaml
node apps/web/dist-cli/falsify-audit.mjs template --template sanskrit_retrieval --out /tmp/sanskrit-claim.yaml
node apps/web/dist-cli/falsify-audit.mjs template --template academic_retrieval --out /tmp/academic-claim.yaml
```

The same templates are available as buttons in the claim config panel.

## Compare

Use the same dataset, config, and baseline/corpus with two system outputs:

```bash
node apps/web/dist-cli/falsify-audit.mjs compare \
  --dataset apps/web/examples/rag-dataset.jsonl \
  --system apps/web/examples/rag-system-v1.jsonl \
  --right-system apps/web/examples/rag-system.jsonl \
  --corpus apps/web/examples/rag-corpus.jsonl \
  --config apps/web/examples/claim.yaml \
  --mode system_v1_vs_v2 \
  --out /tmp/falsify-comparison.json
```

The same comparison flow exists in the web workbench.

## Audit Pack

`--pack-out` writes:

- `report.md`
- `report.json`
- `inputs.lock.json`
- `config.yaml`
- `hashes.json`
- `inputs/dataset.json`
- `inputs/system.json`
- `inputs/baseline.json`
- `inputs/corpus.json` when a corpus was provided

## Verify

```bash
npm run test --workspace apps/web
npm run typecheck --workspace apps/web
npm run lint --workspace apps/web
npm run build --workspace apps/web
python3 -m pytest -q
```

## Deployment

See `docs/AUDIT_WEB_DEPLOYMENT.md` for local-first and Vercel notes. Use Vercel for public demo data only unless storage and access control are added first.
