---
name: Bug bounty submission
about: Claim against the methodology paper bug bounty (USD 2000)
title: "[bounty] "
labels: bug-bounty
assignees: ''
---

## Bounty class

Which class of claim are you submitting? (See README §Bug bounty)

- [ ] Class 1: A retrieval system that PASSes the four-null gate (τ=0.05, N_trials=50) *and* whose top-K output can be shown via separate evidence to not actually use the query.
- [ ] Class 2: A counterexample to Proposition 1's Hoeffding + Bonferroni argument.
- [ ] Class 3: A reproducible drift between the demo's published numbers and a third-party run on identical artifacts.

## Reproduction

Provide a minimal repository, script, or notebook that demonstrates the claim.
We must be able to clone or download it and reproduce within 10 minutes.

```
# Steps to reproduce
```

## Evidence

For Class 1: how do we verify the engine does not use the query?
For Class 2: state the construction and the violated inequality precisely.
For Class 3: paste the divergent numbers and the lock hash mismatch.

## Payment details

We will reach out via the email associated with your GitHub account if the
claim is verified. Verification typically takes 1–2 weeks.
