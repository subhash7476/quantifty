"""Sequential runner for the post-download strategy chain.

Aborts at the first non-zero exit: the chain is a real dependency (options
selection reads what the signal refresh produced), so continuing would emit
authoritative-looking options built on stale signals.
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"

CHAIN_STEPS = [
    ("refresh_all_strategies.py", SCRIPTS / "refresh_all_strategies.py"),
    ("ts_basis_daily_signals.py", SCRIPTS / "ts_basis_daily_signals.py"),
    ("ts_basis_daily_options.py", SCRIPTS / "ts_basis_daily_options.py"),
]

STDERR_TAIL_LINES = 20


@dataclass
class StepResult:
    label: str
    ok: bool
    stdout: str
    stderr_tail: str


def run_step(label: str, script: Path, timeout: int = 3600) -> StepResult:
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},  # child stdout pipe is cp1252 otherwise
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return StepResult(label, False, "", f"TIMEOUT after {timeout}s")
    tail = "\n".join((proc.stderr or "").strip().splitlines()[-STDERR_TAIL_LINES:])
    return StepResult(label, proc.returncode == 0, proc.stdout or "", tail)


def run_chain(steps=None) -> list[StepResult]:
    results = []
    for label, script in (steps if steps is not None else CHAIN_STEPS):
        result = run_step(label, script)
        results.append(result)
        if not result.ok:
            break
    return results
