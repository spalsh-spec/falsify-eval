> *सत्यमेव जयते.* Calibrated, never inflated.

## What

One-sentence summary of the change.

## Why

What problem does this solve? Link any related issues.

## How tested

- [ ] `python -m pytest tests/` — all 43+ tests pass locally
- [ ] `python examples/synthetic_demo.py` — produces the expected gate verdicts
- [ ] If touching gate logic: documented which null distribution is affected and why
- [ ] If touching `metric_fn` semantics: parametrised tests across `str`, `int`, `np.int64`, `float`, `tuple`, dataclass labels (regression suite for Mayank-defect class)

## Backwards compatibility

- [ ] No public symbol removed or renamed
- [ ] OR: deprecation note added to `CHANGELOG.md` with at least one minor version of warning

## Methodology note (if applicable)

If this PR changes statistical behaviour (null construction, p-value, CI, gate
threshold defaults, sort key for label sets), summarise in 2–3 sentences how
the new behaviour differs and why it is preferable. Link supporting references.

## Audit cost

Lines added: ___ · Lines removed: ___ · New runtime dependencies: ___

The library is intentionally small so adopters can read the whole thing before
trusting it. Keep that surface tight.

---

*Released by **[Bhardwaj &amp; Sons](https://bhardwajandsons.com)** under Apache 2.0.*
