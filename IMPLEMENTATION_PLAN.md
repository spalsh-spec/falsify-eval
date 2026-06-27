# falsify-eval audit tool implementation plan

## Goal
Build a local-first audit tool that checks whether benchmark claims are credible, not just whether a system scored higher.

## Boundaries
- `apps/web/src/app`: UI and API routes only.
- `apps/web/src/lib/audit`: pure audit logic. No filesystem, database, or UI imports.
- `apps/web/src/lib/security`: upload validation, JSON parsing, redaction, path safety.
- `apps/web/src/lib/rate-limit`: local in-memory route limiter.
- `apps/web/src/lib/storage`: local persistence and raw upload isolation.
- `apps/web/src/lib/report`: JSON and Markdown report generation.

## Steps
1. Inspect the existing Python package and keep it intact.
2. Add a Next.js app in `apps/web`.
3. Implement pure TypeScript audit metrics and checks first.
4. Add unit tests for metrics, null checks, leakage, duplicate detection, and verdicts.
5. Implement security helpers with file limits, extension checks, safe JSON parsing, redaction, and filename hardening.
6. Add tests for invalid files, oversized files, bad JSON, redaction, and rate limits.
7. Implement report generation without mutating audit results.
8. Implement local storage with private raw upload paths and generated job IDs.
9. Implement API routes that validate input, call services, and return typed responses.
10. Build a quiet dashboard for upload, status, verdict, evidence, and downloads.
11. Add README, `.env.example`, and `NEXT.md` notes for deferred YAML/native CLI work.
12. Run lint, typecheck, tests, and build. Fix failures.
13. Start the local dev server and provide the URL.

## Verification gates
- `npm run lint --workspace apps/web`
- `npm run typecheck --workspace apps/web`
- `npm run test --workspace apps/web`
- `npm run build --workspace apps/web`
