# arXiv submission checklist — falsify-eval

## TL;DR

```bash
./tools/build_arxiv.sh
# → arxiv/falsify-eval-arxiv-submission.tar.gz
# Upload at https://arxiv.org/submit
```

## Pre-submission checklist

Run through this once, top-to-bottom, before clicking "submit" at arXiv.

### Categorisation

- **Primary:** `cs.IR` (Information Retrieval). The paper is methodology
  for evaluating retrieval systems; this is the on-topic category.
- **Cross-list:** `cs.LG` (Machine Learning). The four-null gate's
  positive-control logic is general statistical-validation methodology,
  not retrieval-specific. Cross-listing widens the audience beyond IR.
- **Do NOT cross-list to** `stat.ML`. The paper is methodological but
  doesn't make a new statistical contribution beyond the application;
  cross-listing there invites the wrong reviewer pool.

### Endorsement

You may need a `cs.IR` endorser if this is your first arXiv submission
in that category. Check at https://arxiv.org/help/endorsement. If you
need one, ask a co-author of any cs.IR paper from the last 5 years
who has previously submitted to cs.IR — Hamel Husain, Jason Liu, or
Eugene Yan are all approachable on this. The endorsement request goes
through arXiv's interface, not direct email.

### Title and abstract

Title (currently in PREPRINT.md):
> **Calibrated Falsification Harnesses for Retrieval Evaluation:
> Methodology, Soundness, Self-Validation, and Bench-Expansion to N≈10,000**

This is fine for arXiv. If you want a tighter version for the submission
form: drop the colon-clause and use:
> **Calibrated Falsification Harnesses for Retrieval Evaluation**

Abstract: PREPRINT.md's existing abstract is ~600 words, which is fine
for arXiv (no hard limit). Don't shrink it — the abstract is the only
thing most readers will see, and the four-null framing is the lead.

### Author block

```
Sparsh Sharma
Independent Researcher
sparshsharma219@gmail.com
ORCID: <fill in if you have one; create at https://orcid.org if not>
```

Get an ORCID before submitting if you don't have one. It's free, takes
2 minutes, and lets future papers be associated with you cleanly.

### Comments field (arXiv form)

Fill the "Comments" field with:

> 30 pages incl. seven empirical hardening experiments at N=21 → N=10,000.
> Code: github.com/spalsh-spec/falsify-eval (Apache 2.0). External
> replication invited; case studies CS01 (NFCorpus) and CS02 (SciFact)
> reproducible in 5 minutes on a laptop. v0.1.6.9 of the reference
> implementation is the version of record at submission time.

### License

The paper itself: **CC BY 4.0**. Pick this in the arXiv form. It lets
the methodology be reproduced and built on without permission, which
is the point of releasing it.

The code: already Apache 2.0 in the repo.

### Code & reproducibility (mandatory)

arXiv increasingly requires a code link. Provide:

- Repo: https://github.com/spalsh-spec/falsify-eval
- Pinned version at submission: `v0.1.6.9` (or whatever's current when
  you click submit)
- Reproduction commands: already in PREPRINT.md §8.

### Replacements / versions

arXiv versioning is `v1`, `v2`, etc. Match it to the package version:

- arXiv v1 ↔ falsify-eval v0.1.6.9 (initial submission)
- arXiv v2 ↔ falsify-eval v0.2.x (after CS03 lands + PyPI publish)
- arXiv v3 ↔ falsify-eval v0.3.x (LLM-output extension)

Each replacement requires a "comments" entry summarising the diff
since the previous version. Don't pile up replacements — submit a
real version when something material has changed (new case study, new
methodology, found bug).

## Cover letter (for reviewers if you submit to a venue)

If you also submit to a peer-reviewed venue (SIGIR, ACL, EMNLP, RecSys),
the cover letter should be three paragraphs:

> **Para 1 — what this paper is.** A retrieval-evaluation methodology
> that catches a class of failure mode the standard practice misses:
> systems matched to the empirical gold-marginal that score
> non-trivially on aggregate metrics without using the query. We
> formalise the failure mode, propose a four-null gate that catches it,
> and demonstrate empirically across three benchmarks of increasing
> scale (N=21 internal Sanskrit corpus, N=323 NFCorpus, N=300 SciFact,
> with a projection to N=10,000).
>
> **Para 2 — what's new.** The novel contribution is Null D
> (gold-marginal-matched random retrieval) and the demonstration that
> Nulls A and B can false-positive on constant-predictor systems while
> Null D rejects them. We also contribute a positive-control validation
> protocol (§5.5) that runs deliberately-broken predictors through
> the gate to verify the gate accepts and rejects correctly, and a
> Hypothesis-fuzzed property suite that empirically supports the
> equivariance of the gate under order-preserving label-set bijections.
>
> **Para 3 — what's not new.** We do not make a new statistical
> contribution beyond the application. The bootstrap CIs, paired
> permutation tests, and Cohen's d are standard. The novelty is in
> their packaging into a falsification harness with a calibration
> requirement and a positive-control protocol — neither of which is
> standard practice in retrieval-evaluation papers as of 2026.

## What to do AFTER arXiv accepts (priority claim is timestamped)

The same day:

1. Tweet a 4-tweet thread linking the arXiv URL. Format suggestion in
   `docs/SOCIAL_LAUNCH.md` (when written).
2. Post to two relevant Slack workspaces: ML Collective, EleutherAI
   evals channel.
3. Email the package URL to anyone who's commented on a related thread
   in the last 6 months. Don't mass-tag; do warm individual outreach.

## What this submission does NOT achieve

- It is **not** peer review. arXiv is a preprint server. Citations gain
  weight only after peer review at a venue.
- It is **not** a venue submission. To submit to SIGIR/ACL/EMNLP/RecSys,
  format the paper to that venue's template and submit separately. arXiv
  and venue submissions are not mutually exclusive — most papers do both,
  in that order.
- It is **not** a guarantee of attention. Most arXiv papers in cs.IR get
  fewer than 50 views in their first month. The paper has to earn
  attention via the case studies, the code, and external testers
  reproducing the result.
