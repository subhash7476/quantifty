"""NiftyShield E008 window identity (AUDIT_2026-09-25 R3).

The first 18 PAPER round-trips (2026-08-19 -> 09-25) ran under three exit and
sizing regimes, so they are a count, not a sample. The window restarts at
WINDOW_START on one frozen execution identity: a content hash over the files
that decide what a session trades, sizes, and exits. Each session's recorder
stamps the hash of the code it ran; `assemble_report` counts a session only on
or after WINDOW_START with a matching stamp.

Changing any file below is a new identity. Re-pin FROZEN_EXECUTION_HASH and
WINDOW_START together, declared BEFORE the new window's first session (runbook
§8.1), and ledger the change under E008.
"""
from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

WINDOW_START = date(2026, 9, 28)
FROZEN_EXECUTION_HASH = "d66838c91120beda090426bbc8ecb05d3ce581e1108cbdad6a137361be5ed0e6"

EXECUTION_GLOBS = (
    "strategies/nifty_shield_v1/*.py",
    "core/execution/options/nifty_shield_*.py",
    "core/execution/options/fees.py",
    "core/execution/handler.py",
    "scripts/nifty_shield_paper_runner.py",
)


def _execution_files(root: Path) -> list:
    files = set()
    for pattern in EXECUTION_GLOBS:
        files.update(p.relative_to(root).as_posix() for p in root.glob(pattern))
    return sorted(files)


def execution_hash(root: Path, files: Optional[Iterable[str]] = None) -> str:
    """SHA-256 over (path, content) of the execution files, CRLF normalised
    to LF so a Windows checkout hashes the same as the committed blob."""
    root = Path(root)
    digest = hashlib.sha256()
    for rel in sorted(files) if files is not None else _execution_files(root):
        digest.update(rel.encode("utf-8") + b"\0")
        digest.update((root / rel).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return digest.hexdigest()
