"""
MM.4 — instrument-master readiness verdict (MASTER_MATERIALIZATION_POLICY.md §4).

Coverage is the hard gate; date is the early-warning proxy (§4) — a master dated
today but missing its derivative contracts BLOCKs regardless of date. The resolver
supplies facts (segment_row_count / active_expiry_present); this module owns the
FRESH/WARN/BLOCK judgment (MM.4_DESIGN_REVIEW.md §3-impl).

Fixtures are built through the real ingest pipeline (parse_instruments +
write_snapshot) — never the network (policy §7).
"""
from datetime import date, datetime

import pytest

from scripts.fetch_instrument_master import parse_instruments, write_snapshot
from core.database.utils.market_hours import MarketHours
from core.instruments.resolver import InstrumentResolver
from core.instruments.master_freshness import expected_snapshot_date
from core.instruments.master_readiness import (
    ReadinessState, ReadinessVerdict, evaluate, assess,
)

# A fixed "now": Mon 2026-06-08 09:00 IST (trading day, past the 08:30 cutoff),
# so expected_snapshot_date(now) == 2026-06-08. Previous trading day == Fri
# 2026-06-05; two trading days back == Thu 2026-06-04.
_NOW = MarketHours.IST.localize(datetime(2026, 6, 8, 9, 0))
_EXPECTED = date(2026, 6, 8)
_PREV_TD = date(2026, 6, 5)
_TWO_TD_BACK = date(2026, 6, 4)


def _derivative_rows(expiry="2026-06-25"):
    """A minimally-complete derivative master: a NIFTY future + option + one EQ."""
    return [
        {"segment": "NSE_EQ", "instrument_key": "NSE_EQ|INE002A01018",
         "tradingsymbol": "RELIANCE", "name": "RELIANCE INDUSTRIES",
         "instrument_type": "EQ", "lot_size": 1, "tick_size": 0.05,
         "isin": "INE002A01018"},
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|53001",
         "tradingsymbol": "NIFTYFUT", "name": "NIFTY", "expiry": expiry,
         "instrument_type": "FUT", "lot_size": 75, "tick_size": 0.05},
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|54710",
         "tradingsymbol": "NIFTY22500CE", "name": "NIFTY", "expiry": expiry,
         "strike_price": 22500.0, "instrument_type": "CE",
         "lot_size": 75, "tick_size": 0.05},
    ]


def _write(tmp_path, rows, snapshot_date):
    path = tmp_path / "instruments.duckdb"
    write_snapshot(parse_instruments(rows, snapshot_date), db_path=path)
    return path


# --------------------------------------------------------------------------- #
# evaluate() — pure verdict from facts (§4 precedence)
# --------------------------------------------------------------------------- #
def test_evaluate_fresh_when_latest_equals_expected_and_coverage_ok():
    v = evaluate(_EXPECTED, _EXPECTED, coverage_ok=True)
    assert v.state is ReadinessState.FRESH
    assert v.reason is None


def test_evaluate_warn_when_one_trading_day_behind_and_coverage_ok():
    v = evaluate(_PREV_TD, _EXPECTED, coverage_ok=True)
    assert v.state is ReadinessState.WARN


def test_evaluate_block_absent_when_latest_none():
    v = evaluate(None, _EXPECTED, coverage_ok=False)
    assert v.state is ReadinessState.BLOCK
    assert v.reason == "absent"


def test_evaluate_block_stale_when_two_trading_days_behind():
    v = evaluate(_TWO_TD_BACK, _EXPECTED, coverage_ok=True)
    assert v.state is ReadinessState.BLOCK
    assert v.reason == "stale"


def test_evaluate_block_coverage_overrides_fresh_date():
    # Dated today, but coverage failed → BLOCK(coverage), not FRESH (§4 headline).
    v = evaluate(_EXPECTED, _EXPECTED, coverage_ok=False)
    assert v.state is ReadinessState.BLOCK
    assert v.reason == "coverage"


def test_evaluate_carries_dates_in_verdict():
    v = evaluate(_PREV_TD, _EXPECTED, coverage_ok=True)
    assert v.latest == _PREV_TD and v.expected == _EXPECTED


# --------------------------------------------------------------------------- #
# Resolver coverage FACTS (facts only — no verdict)
# --------------------------------------------------------------------------- #
def test_segment_row_count_counts_latest_snapshot(tmp_path):
    r = InstrumentResolver(db_path=_write(tmp_path, _derivative_rows(), "2026-06-08"))
    assert r.segment_row_count("NSE_FO") == 2
    assert r.segment_row_count("NSE_EQ") == 1
    assert r.segment_row_count("MCX_FO") == 0


def test_active_expiry_present_true_when_future_contract_exists(tmp_path):
    r = InstrumentResolver(db_path=_write(tmp_path, _derivative_rows("2026-06-25"), "2026-06-08"))
    assert r.active_expiry_present("NIFTY", _EXPECTED) is True


def test_active_expiry_present_false_when_all_contracts_expired(tmp_path):
    r = InstrumentResolver(db_path=_write(tmp_path, _derivative_rows("2026-05-28"), "2026-06-08"))
    assert r.active_expiry_present("NIFTY", _EXPECTED) is False


def test_coverage_facts_on_absent_master(tmp_path):
    r = InstrumentResolver(db_path=tmp_path / "missing.duckdb")
    assert r.segment_row_count("NSE_FO") == 0
    assert r.active_expiry_present("NIFTY", _EXPECTED) is False


# --------------------------------------------------------------------------- #
# assess() — facts gathered from a real resolver → verdict
# --------------------------------------------------------------------------- #
def test_assess_fresh_with_current_complete_master(tmp_path):
    r = InstrumentResolver(db_path=_write(tmp_path, _derivative_rows(), "2026-06-08"))
    v = assess(r, underlyings=["NIFTY"], now=_NOW)
    assert v.state is ReadinessState.FRESH


def test_assess_warn_with_one_day_stale_complete_master(tmp_path):
    r = InstrumentResolver(db_path=_write(tmp_path, _derivative_rows(), "2026-06-05"))
    v = assess(r, underlyings=["NIFTY"], now=_NOW)
    assert v.state is ReadinessState.WARN


def test_assess_block_stale_with_two_day_stale_master(tmp_path):
    r = InstrumentResolver(db_path=_write(tmp_path, _derivative_rows(), "2026-06-04"))
    v = assess(r, underlyings=["NIFTY"], now=_NOW)
    assert v.state is ReadinessState.BLOCK
    assert v.reason == "stale"


def test_assess_block_absent_when_master_missing(tmp_path):
    r = InstrumentResolver(db_path=tmp_path / "missing.duckdb")
    v = assess(r, underlyings=["NIFTY"], now=_NOW)
    assert v.state is ReadinessState.BLOCK
    assert v.reason == "absent"


def test_assess_block_coverage_when_no_derivative_rows(tmp_path):
    # Dated TODAY but equity-only — the headline §4 case a date-only gate misses.
    equity_only = [{"segment": "NSE_EQ", "instrument_key": "NSE_EQ|INE002A01018",
                    "tradingsymbol": "RELIANCE", "name": "RELIANCE INDUSTRIES",
                    "instrument_type": "EQ", "lot_size": 1, "tick_size": 0.05,
                    "isin": "INE002A01018"}]
    r = InstrumentResolver(db_path=_write(tmp_path, equity_only, "2026-06-08"))
    v = assess(r, underlyings=["NIFTY"], now=_NOW)
    assert v.state is ReadinessState.BLOCK
    assert v.reason == "coverage"


def test_assess_block_coverage_when_active_expiry_missing(tmp_path):
    # Derivative rows exist but every contract already expired before `expected`.
    r = InstrumentResolver(db_path=_write(tmp_path, _derivative_rows("2026-05-28"), "2026-06-08"))
    v = assess(r, underlyings=["NIFTY"], now=_NOW)
    assert v.state is ReadinessState.BLOCK
    assert v.reason == "coverage"
