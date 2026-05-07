"""CLI regression tests — including stdin streaming.

Mayank-defect 2026-05-07: `falsify-eval grade --input - --pool pool.txt`
should read JSONL from stdin (the conventional UNIX `-` sentinel).
v0.1.5.1 tried to open a file literally named '-' and crashed with
FileNotFoundError. v0.1.6.1 routes `-` through sys.stdin instead.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def synthetic_bench(tmp_path):
    """Create a tiny pool + JSONL bench that we know passes the gate."""
    pool = tmp_path / "pool.txt"
    pool.write_text("\n".join(f"L{i}" for i in range(8)))

    rows = []
    for i in range(60):
        gold = f"L{i % 8}"
        retrieved = [gold] + [f"L{(i + j) % 8}" for j in range(1, 5)]
        rows.append({"retrieved": retrieved, "gold": gold, "rel": 3})
    bench_jsonl = "\n".join(json.dumps(r) for r in rows)

    return pool, bench_jsonl


def test_cli_stdin_dash_streams_jsonl(synthetic_bench):
    """`falsify-eval grade --input - --pool ...` must read from stdin."""
    pool, bench_jsonl = synthetic_bench
    result = subprocess.run(
        [sys.executable, "-m", "falsify_eval.cli", "grade",
         "--input", "-", "--pool", str(pool), "--metric", "ndcg@5",
         "--n-trials", "10", "--json"],
        input=bench_jsonl,
        text=True, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, (
        f"CLI exit {result.returncode}\nstderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    )
    # --json mode prints the result dict to stdout
    payload = json.loads(result.stdout)
    assert "real_mean" in payload
    assert "deltas" in payload
    assert "gate_passes" in payload


def test_cli_stdin_empty_dash_input_fails_cleanly(synthetic_bench):
    """Empty stdin must produce the same 'no rows loaded' error path,
    NOT a FileNotFoundError on a file named '-'."""
    pool, _ = synthetic_bench
    result = subprocess.run(
        [sys.executable, "-m", "falsify_eval.cli", "grade",
         "--input", "-", "--pool", str(pool), "--metric", "ndcg@5"],
        input="",
        text=True, capture_output=True, timeout=10,
    )
    assert result.returncode != 0, "empty stdin should fail"
    assert "FileNotFoundError" not in result.stderr, (
        "v0.1.5.1 used to open '-' literally; the regression must not return"
    )
    assert "<stdin>" in result.stderr or "no rows" in result.stderr


def test_cli_stdin_malformed_jsonl_reports_line_number_with_stdin_label():
    """If stdin contains malformed JSONL, the error must label the source as
    <stdin> (not crash, not silently swallow)."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("L0\nL1\nL2\n")
        pool_path = f.name

    bad_jsonl = '{"retrieved": ["L0"], "gold": "L0", "rel": 3}\n{not valid json\n'
    result = subprocess.run(
        [sys.executable, "-m", "falsify_eval.cli", "grade",
         "--input", "-", "--pool", pool_path, "--metric", "recall@5"],
        input=bad_jsonl,
        text=True, capture_output=True, timeout=10,
    )
    Path(pool_path).unlink()
    assert result.returncode != 0
    assert "<stdin>:2" in result.stderr or "<stdin>" in result.stderr, (
        f"expected stdin error label, got:\n{result.stderr}"
    )


def test_cli_file_input_unchanged(synthetic_bench, tmp_path):
    """Sanity: regular file input still works — no regression on the
    common path while fixing the stdin path."""
    pool, bench_jsonl = synthetic_bench
    bench = tmp_path / "bench.jsonl"
    bench.write_text(bench_jsonl)
    result = subprocess.run(
        [sys.executable, "-m", "falsify_eval.cli", "grade",
         "--input", str(bench), "--pool", str(pool), "--metric", "ndcg@5",
         "--n-trials", "10", "--json"],
        text=True, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "real_mean" in payload
