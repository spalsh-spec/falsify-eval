#!/usr/bin/env bash
# Build the arXiv-submittable LaTeX bundle from PREPRINT.md.
#
# Output: arxiv/preprint.tex + arxiv/preprint.pdf (if a TeX engine is
# installed). The .tex is what arXiv actually wants — they re-compile
# server-side. The local PDF is for sanity-checking before submission.
#
# Requires: pandoc (already installed on the dev box).
# Optional: xelatex or pdflatex for local PDF preview. Install via:
#   brew install --cask basictex     # ~100MB, fast
#   brew install --cask mactex       # ~5GB, full distribution
set -euo pipefail

ROOT="$(cd "$(dirname "$0")"/.. && pwd)"
cd "$ROOT"

mkdir -p arxiv

# 1. Convert markdown → LaTeX.
echo "→ pandoc PREPRINT.md → arxiv/preprint.tex"
pandoc PREPRINT.md \
    --standalone \
    --to=latex \
    --output=arxiv/preprint.tex \
    --metadata title="Calibrated Falsification Harnesses for Retrieval Evaluation" \
    --metadata author="Sparsh Sharma" \
    --metadata date="$(date +%Y-%m-%d)"

# 2. Optional: compile to PDF if a TeX engine is available.
TEX_ENGINE=""
for engine in xelatex pdflatex lualatex; do
    if command -v "$engine" >/dev/null 2>&1; then
        TEX_ENGINE="$engine"
        break
    fi
done

if [ -n "$TEX_ENGINE" ]; then
    echo "→ $TEX_ENGINE arxiv/preprint.tex → arxiv/preprint.pdf"
    cd arxiv
    "$TEX_ENGINE" -interaction=nonstopmode preprint.tex >/dev/null 2>&1 || {
        echo "  (warnings expected on first pass — running second pass for refs)"
        "$TEX_ENGINE" -interaction=nonstopmode preprint.tex >/dev/null 2>&1 || true
    }
    cd ..

    if [ -f arxiv/preprint.pdf ]; then
        echo "✓ arxiv/preprint.pdf built ($(du -h arxiv/preprint.pdf | cut -f1))"
    else
        echo "✗ PDF build failed — inspect arxiv/preprint.log for details"
        exit 1
    fi
else
    echo "ℹ no TeX engine installed; producing .tex only."
    echo "  install BasicTeX with: brew install --cask basictex"
    echo "  then re-run this script for the local PDF preview."
fi

# 3. Pack the arXiv submission tarball.
echo "→ packing arxiv/falsify-eval-arxiv-submission.tar.gz"
tar -czf arxiv/falsify-eval-arxiv-submission.tar.gz -C arxiv preprint.tex
echo "✓ submission tarball ready: arxiv/falsify-eval-arxiv-submission.tar.gz"

echo
echo "Next: upload arxiv/falsify-eval-arxiv-submission.tar.gz to https://arxiv.org/submit"
echo "       Categories: cs.IR (primary), cs.LG (cross-list)"
echo "       Checklist:  see docs/ARXIV_SUBMISSION.md"
