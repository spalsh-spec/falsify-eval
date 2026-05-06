---
name: Bug report
about: A reproducible defect in the library
title: "[bug] "
labels: bug
assignees: ''
---

> *सत्यमेव जयते — truth alone prevails.*
> Bring the smallest case that fails. Calibrated reports get fixed faster.

## Summary

One sentence describing what's wrong.

## Reproduction

```python
from falsify_eval import four_null_gate
# Minimal code that triggers the bug.
# Smaller is better. If you can reduce it to <20 lines, please do.
```

## Expected

What you expected to happen.

## Actual

What actually happened. Include the full traceback if there is one.

## Environment

```text
falsify-eval version: python -c "import falsify_eval; print(falsify_eval.__version__)"
Python version:       python --version
numpy version:        python -c "import numpy; print(numpy.__version__)"
OS:
```

## Notes

Anything else that helps diagnosis — unusual gold-label distributions, very small *N*, mixed label types, custom `metric_fn` that calls an LLM, etc.

---

*Released by **[Bhardwaj &amp; Sons](https://bhardwajandsons.com)** under Apache 2.0. The methodology is free, public, and citable.*
