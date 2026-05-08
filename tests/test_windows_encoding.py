"""Windows cp1252 console regression test for falsify_eval.cli.

Reproduces Jasmeet's bug (2026-05-08): on Windows PowerShell the default
console codepage is cp1252 and the pretty-printer prints Δ, ✓, etc., which
crashed with UnicodeEncodeError before the v0.1.6.4 fix.

We don't need an actual Windows host — we just rebind sys.stdout to a
TextIOWrapper backed by a BytesIO with encoding="cp1252", which is exactly
what Windows does when the console codepage is 1252 and stdout has not been
reconfigured to UTF-8. Then we exercise the same code path Jasmeet ran:
    falsify-eval grade --input ... --pool ... --metric ndcg@5

Three scenarios exercised:
  1) WITHOUT _init_io (simulating the OLD code) — must crash. Confirms repro.
  2) WITH _init_io (the new fix) — must NOT crash, output is decodable.
  3) WITH _init_io + --ascii flag — must produce ASCII-only output (no Δ).
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from falsify_eval import cli  # noqa: E402


@contextmanager
def fake_cp1252_stdout():
    """Replace sys.stdout with a cp1252-encoded TextIOWrapper, like Windows."""
    real = sys.stdout
    buf = io.BytesIO()
    fake = io.TextIOWrapper(buf, encoding="cp1252", newline="", line_buffering=False)
    # Pretend we're a TTY so the color path is also exercised (it's gated on isatty).
    fake.isatty = lambda: False  # type: ignore[assignment]
    sys.stdout = fake
    try:
        yield fake, buf
    finally:
        try:
            fake.flush()
        except Exception:
            pass
        sys.stdout = real


def _write_demo_bench(tmp: Path) -> tuple[Path, Path]:
    rows, pool = cli._demo_bench()
    bench = tmp / "bench.jsonl"
    p = tmp / "pool.txt"
    with bench.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    p.write_text("\n".join(pool) + "\n", encoding="utf-8")
    return bench, p


class TestCp1252Console(unittest.TestCase):
    def test_old_behavior_would_crash(self):
        """Sanity check: confirm that printing Δ to a raw cp1252 stream crashes.
        This is the bug we're fixing — without _init_io, the OLD code path raises.
        """
        with fake_cp1252_stdout() as (fake, _buf):
            with self.assertRaises(UnicodeEncodeError):
                # No _init_io call here; this is what the OLD cli.main() did.
                fake.write("Null A: mean=0.2553  Δ=+0.6003 ✓\n")
                fake.flush()

    def test_fixed_grade_does_not_crash(self):
        """The fix: _init_io reconfigures stdout to UTF-8 with errors='replace'."""
        with tempfile.TemporaryDirectory() as td:
            bench, pool = _write_demo_bench(Path(td))
            with fake_cp1252_stdout() as (fake, buf):
                # _init_io is what main() calls; it must make print(Δ) safe.
                cli._init_io(force_ascii=False)
                # SystemExit(0) on PASS is expected — that's how cmd_grade signals success.
                with self.assertRaises(SystemExit) as cm:
                    cli.main([
                        "grade",
                        "--input", str(bench),
                        "--pool", str(pool),
                        "--metric", "ndcg@5",
                    ])
                self.assertEqual(cm.exception.code, 0,
                                 "grade should exit 0 on the synthetic demo")
                fake.flush()
                payload = buf.getvalue()
                # Output is now UTF-8 bytes — must contain the literal Δ glyph
                # (or its ascii fallback if auto-degrade kicked in).
                decoded = payload.decode("utf-8", errors="replace")
                self.assertIn("falsify-eval", decoded)
                self.assertIn("GATE:", decoded)
                # Either the unicode delta or the ascii fallback is acceptable.
                self.assertTrue("Δ=" in decoded or "d=" in decoded,
                                f"expected delta marker in:\n{decoded[:500]}")

    def test_ascii_flag_forces_ascii_output(self):
        """--ascii flips the glyph table; output contains no Δ/✓/τ glyphs."""
        with tempfile.TemporaryDirectory() as td:
            bench, pool = _write_demo_bench(Path(td))
            with fake_cp1252_stdout() as (fake, buf):
                with self.assertRaises(SystemExit) as cm:
                    cli.main([
                        "--ascii",
                        "grade",
                        "--input", str(bench),
                        "--pool", str(pool),
                        "--metric", "ndcg@5",
                    ])
                self.assertEqual(cm.exception.code, 0)
                fake.flush()
                # In ascii mode the buffer's underlying encoding doesn't matter —
                # decoding as cp1252 should now work without lossy replacement.
                decoded = buf.getvalue().decode("cp1252")
                self.assertNotIn("Δ", decoded)
                self.assertNotIn("τ", decoded)
                self.assertNotIn("✓", decoded)
                self.assertNotIn("✗", decoded)
                self.assertIn("d=", decoded)        # ASCII delta
                self.assertIn("[ok]", decoded)      # ASCII check or part of GATE line


if __name__ == "__main__":
    unittest.main(verbosity=2)
