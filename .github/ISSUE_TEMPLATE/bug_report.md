---
name: Bug report
about: A reproducible defect in the library
title: "[bug] "
labels: bug
assignees: ''
---

## Summary

One sentence describing what's wrong.

## Reproduction

```python
# Minimal code that triggers the bug
from falsify_eval import four_null_gate
...
```

## Expected

What you expected to happen.

## Actual

What actually happened. Include the full traceback if there is one.

## Environment

- falsify-eval version (`python -c "import falsify_eval; print(falsify_eval.__version__)"`):
- Python version:
- OS:
- numpy version:

## Notes

Anything else that might help diagnosis (e.g. unusual gold-label distributions, very small N, etc.).
