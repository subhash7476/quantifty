"""The gate (b) scope-exclusion register must stay internally consistent: every
listed move carries a reason, every reason has detail text, and the two demerger
symbols the operator named are present."""

import importlib.util
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "ingest_ca", ROOT / "scripts" / "csmp" / "ingest_corporate_actions.py")
ingest_ca = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ingest_ca)

SCOPE_EXCLUSIONS = ingest_ca.SCOPE_EXCLUSIONS
EXCLUSION_DETAIL = ingest_ca.EXCLUSION_DETAIL


def test_every_exclusion_reason_has_detail_text():
    for symbol, move_date, reason in SCOPE_EXCLUSIONS:
        assert reason in EXCLUSION_DETAIL, f"{symbol} has undocumented reason {reason}"


def test_no_orphan_detail_entries():
    used = {reason for _, _, reason in SCOPE_EXCLUSIONS}
    assert set(EXCLUSION_DETAIL) == used


def test_exclusion_rows_are_well_formed():
    for symbol, move_date, reason in SCOPE_EXCLUSIONS:
        assert symbol == symbol.upper()
        assert isinstance(move_date, date)
        assert reason.islower()


def test_no_duplicate_exclusion_keys():
    keys = [(s, d) for s, d, _ in SCOPE_EXCLUSIONS]
    assert len(keys) == len(set(keys))


def test_the_named_dev_window_demergers_are_excluded():
    dev_demergers = {("ORIENTPPR", date(2013, 3, 7)), ("FOURSOFT", date(2013, 10, 17)),
                     ("SINTEX", date(2017, 5, 25)), ("DCM", date(2019, 5, 30))}
    listed = {(s, d) for s, d, r in SCOPE_EXCLUSIONS
              if r == "out_of_scope_corporate_action"}
    assert dev_demergers <= listed


def test_the_two_non_demerger_exceptions_are_distinctly_reasoned():
    by_key = {(s, d): r for s, d, r in SCOPE_EXCLUSIONS}
    assert by_key[("AHLEAST", date(2022, 10, 6))] == "disputed_ratio"
    assert by_key[("ICICIMOM30", date(2022, 8, 12))] == "unidentified_instrument"
