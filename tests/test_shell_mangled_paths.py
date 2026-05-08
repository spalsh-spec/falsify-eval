"""Regression test: shell-mangled Windows paths produce a helpful error.

Bug 2026-05-08 (Parth):
  Copy-pasting `--input my-bench\bench.jsonl` from a Windows tutorial into zsh
  on macOS yields `--input my-benchbench.jsonl` because zsh's '\' is an escape
  character, not a path separator. The native FileNotFoundError is correct but
  unhelpful. We now (a) raise SystemExit with a clean message, and (b) when
  the mangled path can be unambiguously decoded, suggest the corrected form.
"""
from __future__ import annotations
import json
import os
import tempfile
import unittest
from pathlib import Path

from falsify_eval import cli


class TestShellMangledPaths(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        # Realistic layout: a quickstart-style my-bench/ directory.
        Path("my-bench").mkdir()
        rows, pool = cli._demo_bench()
        with open("my-bench/bench.jsonl", "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        Path("my-bench/pool.txt").write_text("\n".join(pool) + "\n", encoding="utf-8")

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def test_suggester_recovers_zsh_mangled_input(self):
        # Exactly what zsh does: my-bench\bench.jsonl -> my-benchbench.jsonl
        self.assertEqual(
            cli._suggest_shell_mangled_path("my-benchbench.jsonl"),
            "my-bench/bench.jsonl",
        )

    def test_suggester_recovers_zsh_mangled_pool(self):
        self.assertEqual(
            cli._suggest_shell_mangled_path("my-benchpool.txt"),
            "my-bench/pool.txt",
        )

    def test_suggester_returns_none_when_path_already_has_separator(self):
        # If user typed forward slashes, no recovery needed.
        self.assertIsNone(cli._suggest_shell_mangled_path("my-bench/bench.jsonl"))
        self.assertIsNone(cli._suggest_shell_mangled_path("my-bench\\bench.jsonl"))

    def test_suggester_returns_none_when_no_match(self):
        self.assertIsNone(cli._suggest_shell_mangled_path("totally-fake-thing.jsonl"))

    def test_grade_emits_did_you_mean_for_mangled_input(self):
        with self.assertRaises(SystemExit) as cm:
            cli.main([
                "grade",
                "--input", "my-benchbench.jsonl",
                "--pool", "my-bench/pool.txt",
                "--metric", "ndcg@5",
            ])
        msg = str(cm.exception.code) + str(cm.exception)
        self.assertIn("did you mean --input my-bench/bench.jsonl", msg)
        self.assertIn("'\\' as an escape", msg)

    def test_grade_emits_did_you_mean_for_mangled_pool(self):
        with self.assertRaises(SystemExit) as cm:
            cli.main([
                "grade",
                "--input", "my-bench/bench.jsonl",
                "--pool", "my-benchpool.txt",
                "--metric", "ndcg@5",
            ])
        msg = str(cm.exception.code) + str(cm.exception)
        self.assertIn("did you mean --pool my-bench/pool.txt", msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
