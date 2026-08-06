"""Carry PAPER runner — path-resolution test.

Regression guard for the `parents[2]` off-by-one in
scripts/carry_paper_runner.py: the module's ROOT resolved to F:\\ and both
DB constants pointed at files that do not exist, so the entry point could
never start. The test imports the REAL module and asserts the REAL resolved
values — it does not reimplement the path logic.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import carry_paper_runner as runner  # noqa: E402


@pytest.fixture(scope="module")
def module_constants():
    return runner.ROOT, runner.FACTS_DB, runner.BHAVCOPY_DB


def test_root_is_repo_root(module_constants):
    root, _, _ = module_constants
    assert root == ROOT.resolve(), (
        f"carry_paper_runner.ROOT resolved to {root}, expected repo root {ROOT}"
    )


def test_facts_db_exists_and_inside_repo(module_constants):
    root, facts_db, _ = module_constants
    assert facts_db.is_absolute()
    assert root in facts_db.parents, f"FACTS_DB outside repo root: {facts_db}"
    assert facts_db.exists(), f"FACTS_DB does not exist: {facts_db}"


def test_bhavcopy_db_exists_and_inside_repo(module_constants):
    root, _, bhavcopy_db = module_constants
    assert bhavcopy_db.is_absolute()
    assert root in bhavcopy_db.parents, f"BHAVCOPY_DB outside repo root: {bhavcopy_db}"
    assert bhavcopy_db.exists(), f"BHAVCOPY_DB does not exist: {bhavcopy_db}"
