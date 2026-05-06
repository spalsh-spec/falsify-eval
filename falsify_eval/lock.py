"""Integrity-check state lock — pure-stdlib, vendor-free.

Walk a directory, hash every tracked artifact with SHA-256, write/verify a JSON
lock; bind the lock to a git commit and (optionally) a verified bench score.

Threat model (per Mayank-defect #4): this is an integrity-check primitive,
NOT a tamper-proof cryptographic seal. SHA-256 + git-commit binding detect
*accidental* drift (file mutated, regenerated, partially overwritten) and
catch *honest* reproducibility failures. They do not defend against an
adversary with write access to both the artifacts and the lock file — such
an adversary regenerates both. For tamper-proof attestation, sign the lock
JSON externally (gpg, sigstore, in-toto) and store the signature out-of-band.

Default tracked extensions cover binary scientific artifacts (.db, .bin,
.json, .pkl, .npy, .npz, .parquet). Source files (.py, .md, .txt, .csv,
.yaml, .yml) are intentionally NOT tracked by default — they live in git
already and the git-commit binding covers them. To track those explicitly,
pass `tracked_extensions=DEFAULT_TRACKED | {".py", ".md", ".csv"}` etc.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

DEFAULT_TRACKED = {".db", ".bin", ".json", ".pkl", ".npy", ".npz", ".parquet"}
DEFAULT_SKIP_PREFIXES = (".fuse_hidden",)
DEFAULT_SKIP_SUFFIXES = (".db-wal", ".db-shm")


def _sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _git_state(repo: Path) -> dict:
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
        ).strip()
        branch = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
        dirty = bool(subprocess.check_output(
            ["git", "-C", str(repo), "status", "--porcelain"], text=True
        ).strip())
        return {"commit": commit, "branch": branch, "dirty": dirty}
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return {"error": str(e)}


def lock_state(artifact_dir: str | Path,
               *,
               git_repo: str | Path | None = None,
               tracked_extensions: Iterable[str] = DEFAULT_TRACKED,
               skip_prefixes: tuple = DEFAULT_SKIP_PREFIXES,
               skip_suffixes: tuple = DEFAULT_SKIP_SUFFIXES,
               bench_score: float | None = None,
               extra_meta: dict | None = None) -> dict:
    """Walk artifact_dir, hash every tracked file, return the lock dict."""
    artifact_dir = Path(artifact_dir)
    git_repo = Path(git_repo) if git_repo is not None else artifact_dir
    artifacts: dict[str, dict] = {}
    for p in sorted(artifact_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix not in tracked_extensions:
            continue
        if any(p.name.startswith(pref) for pref in skip_prefixes):
            continue
        if any(p.name.endswith(suf) for suf in skip_suffixes):
            continue
        artifacts[p.relative_to(artifact_dir).as_posix()] = {
            "sha256":     _sha256(p),
            "size_bytes": p.stat().st_size,
        }
    lock = {
        "version":      1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git":          _git_state(git_repo),
        "artifacts":    artifacts,
    }
    if bench_score is not None:
        lock["bench"] = {"score": float(bench_score)}
    if extra_meta:
        lock["meta"] = dict(extra_meta)
    return lock


def verify_state(lock: dict | str | Path,
                 artifact_dir: str | Path,
                 *,
                 tracked_extensions: Iterable[str] = DEFAULT_TRACKED,
                 skip_prefixes: tuple = DEFAULT_SKIP_PREFIXES,
                 skip_suffixes: tuple = DEFAULT_SKIP_SUFFIXES) -> dict:
    """Compare on-disk state to lock; return diff report.

    Returns:
        {
          "matches":       bool,
          "missing":       [...]   # in lock, not on disk
          "extra":         [...]   # on disk, not in lock
          "changed":       [{relpath, expected_sha256, actual_sha256}, ...]
          "git_drift":     str | None
        }
    """
    if isinstance(lock, (str, Path)):
        lock = json.loads(Path(lock).read_text())
    current = lock_state(
        artifact_dir,
        tracked_extensions=tracked_extensions,
        skip_prefixes=skip_prefixes,
        skip_suffixes=skip_suffixes,
    )
    cur_arts = current["artifacts"]
    locked_arts = lock["artifacts"]
    missing = sorted(set(locked_arts) - set(cur_arts))
    extra = sorted(set(cur_arts) - set(locked_arts))
    changed = []
    for rel in sorted(set(locked_arts) & set(cur_arts)):
        if locked_arts[rel]["sha256"] != cur_arts[rel]["sha256"]:
            changed.append({
                "path":             rel,
                "expected_sha256":  locked_arts[rel]["sha256"],
                "actual_sha256":    cur_arts[rel]["sha256"],
            })
    git_drift = None
    locked_commit = lock.get("git", {}).get("commit")
    cur_commit = current.get("git", {}).get("commit")
    if locked_commit and cur_commit and locked_commit != cur_commit:
        git_drift = f"{locked_commit[:8]} -> {cur_commit[:8]}"
    return {
        "matches":   not (missing or extra or changed or git_drift),
        "missing":   missing,
        "extra":     extra,
        "changed":   changed,
        "git_drift": git_drift,
    }
