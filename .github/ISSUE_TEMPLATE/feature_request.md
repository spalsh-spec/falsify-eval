---
name: Feature request
about: Propose a new capability or null distribution
title: "[feat] "
labels: enhancement
assignees: ''
---

> *Calibrated additions, not features for their own sake.*
> The library is intentionally small so adopters can audit the whole thing
> before depending on it. Each new capability is a tax on that audit budget.

## What

One sentence describing the proposed feature.

## Why

What evaluation failure mode does this catch that the current four-null gate
does not? If proposing a new null distribution, describe the predictor class
it is designed to reject and why the existing nulls (A, B, C, D) miss it.

## Proposed interface

```python
# Sketch of the API change. Keep it minimal.
```

## Alternatives considered

What else did you think about, and why is this the right shape?

## Backwards compatibility

Does this break any existing public symbol? If so, propose a deprecation path
that keeps `v0.x` callers running for at least one minor version.

## Audit cost

How many lines does this add to the library? How many new dependencies?
The roof is `numpy` only at runtime — anything beyond that needs a strong case.

---

*Released by **[Bhardwaj &amp; Sons](https://bhardwajandsons.com)** under Apache 2.0.*
