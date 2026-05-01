# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions CI matrix (Python 3.10/3.11/3.12 × ubuntu/macos)
- Issue and PR templates
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`
- `PREPRINT.md` and `SUPPLEMENTARY.md` shipped in-repo
- README `## Preprint` section with anchor

## [0.1.0] — 2026-05-01

### Added
- Initial public release.
- Four-null falsification gate: `four_null_gate`, `null_a_permuted`,
  `null_b_uniform`, `null_c_random_retrieval`, `null_d_marginal_matched`.
- Cryptographic state lock: `lock_state`, `verify_state`.
- Statistical reporting: `bootstrap_ci`, `bootstrap_diff_ci`,
  `paired_permutation_p`, `cohens_d_paired`, `power_n_required`.
- 50-query synthetic demo (`examples/synthetic_demo.py`) covering oracle,
  constant predictor, and plausible mock engine.
- 8 unit tests covering gate correctness, statistical primitives, and lock
  round-trip.

[Unreleased]: https://github.com/spalsh-spec/falsify-eval/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/spalsh-spec/falsify-eval/releases/tag/v0.1.0
