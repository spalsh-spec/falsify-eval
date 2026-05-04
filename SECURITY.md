# Security Policy

## Reporting a vulnerability

If you discover a security issue in `falsify-eval`, please email the maintainer
directly at **sparshsharma219@gmail.com** with the subject prefix
`[falsify-eval security]` rather than opening a public issue.

For non-security bugs, please use the regular bug-report template at
[issues/new/choose](https://github.com/spalsh-spec/falsify-eval/issues/new/choose).

## What counts as a security issue

For this library specifically:

- Any way to cause `verify_state` to return success on artifacts that have
  actually drifted (a hash collision, a timing attack, or a logic bug that
  bypasses the check).
- Any way to make the four-null gate return PASS on a predictor that should
  fail under the published protocol (a bug in `null_a_permuted`,
  `null_b_uniform`, `null_c_random_retrieval`, or the novel
  `null_d_marginal_matched`).
- Any data-exfiltration vector through the harness (the library is pure
  stdlib + numpy by design specifically to minimise this surface).
- Path-traversal or arbitrary-write bugs in `lock_state` when given a
  hostile directory path.

## Disclosure timeline

- Initial response: within 5 business days
- Triage and confirmation: within 14 days
- Coordinated disclosure window: 90 days from confirmation, or earlier if a
  fix is shipped

## Acknowledgement

Confirmed security reports will be credited in the changelog under the
reporter's preferred attribution unless the reporter requests anonymity.

## Supported versions

| Version | Security updates |
| ------- | ---------------- |
| 0.1.x   | Yes              |
| < 0.1   | n/a (no releases) |
