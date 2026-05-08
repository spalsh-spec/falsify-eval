# Mutation testing — deferred to v0.2

Mutation testing was attempted on 2026-05-08 (`gate.py` only, the layer
where the four-null gate's epistemic weight lives). Both attempts hit
upstream tool bugs on the host's Python 3.14:

- **mutmut 3.5.0** — `FileNotFoundError: '/.VolumeIcon.icns'` during
  `copy_src_dir()`. Tries to copy the macOS volume root.
- **mutmut 2.x** — `TypeError: cannot pickle 'itertools.count' object`
  during the deepcopy phase of mutation generation. Predates Python 3.14's
  changes to pickle internals.

Neither is a defect in this package. Both are upstream issues that resolve
when one of these holds:

- A future mutmut release ships 3.14 compatibility (tracked at
  https://github.com/boxed/mutmut/issues).
- The CI matrix is run on Python 3.12 / 3.13 where mutmut 2.x is known to
  work; `mutmut run` can be added as a CI job there.

**Plan for v0.2.** Add a `mutation-test` job to `.github/workflows/ci.yml`
that runs on Python 3.12 only, against `gate.py`, and reports the survival
score as a comment on the PR. Pin `mutmut>=2.4,<3.0` until the upstream
3.x macOS regression is fixed. The corresponding pyproject section already
exists under `[tool.mutmut]`.

The configuration that will be used (already in `pyproject.toml`):

```toml
[tool.mutmut]
paths_to_mutate = "falsify_eval/gate.py"
tests_dir = "tests/"
runner = "python3 -m pytest tests/ -x --tb=no -q --override-ini='addopts='"
```

**Why this is being documented and deferred rather than dropped.** A
mutation-testing score is the second-strongest rigor signal a falsification
package can carry (after the property-based suite added in v0.1.6.6). It's
the answer to a reviewer's "okay, but how good are these tests at catching
bugs *you* didn't think of?" — which is one of the questions the package's
own methodology asks of its users. Skipping it permanently would be
inconsistent with the stated discipline. Skipping it until the toolchain
works is the right kind of deferred.
