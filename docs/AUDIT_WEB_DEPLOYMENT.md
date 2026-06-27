# Audit Web Deployment Notes

The audit web app is local-first by default. Use Vercel only for a public demo surface, not for private customer data.

## Local-first

```bash
cd /Users/sparshsharma/falsify-eval-prep
npm install
npm run dev --workspace apps/web
```

Open `http://localhost:3000`.

Local behavior:

- Raw uploads are written under `apps/web/.local-audits/` by default.
- Set `AUDIT_STORAGE_DIR=/absolute/private/path` to move audit storage outside the repo.
- Do not commit `.local-audits/`, generated packs, customer datasets, or private benchmark outputs.
- The app does not need external APIs, hosted storage, auth, or LLM judging for the included demo flow.

## Vercel demo

Vercel can host the app shell and API routes for public demo data.

Suggested settings:

- Root directory: `apps/web`
- Install command: `npm install`
- Build command: `npm run build`
- Output: Next.js default
- Environment: set `AUDIT_STORAGE_DIR=/tmp/falsify-audits`

Limits:

- Vercel filesystem writes are ephemeral. Treat reports as temporary.
- Do not upload customer data to a public Vercel deployment.
- For persistent team use, wire storage to a private volume or database first.
- Keep the public deployment scoped to retrieval, ranking, and RAG retrieval-side audits.

## Commit hygiene

Safe to commit:

- `examples/audit-web-demo/*`
- docs and README updates
- small screenshot assets under `docs/screenshots/`

Do not commit:

- `.local-audits/`
- `/tmp` reports
- generated audit packs from private data
- `.env` files with storage paths or secrets

