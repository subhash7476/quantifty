"""
MM.6 — Instrument-master refresh job (MM.6_REFRESH_JOB_PLAN.md).

Drives the validated, fail-safe daily refresh: IST-correct snapshot stamping,
Option A staging-validate-promote (never publish a bad snapshot), the
contract-shape guard, transactional snapshot writes, trading-day skip, and
failure handling. The network download is never under test — a fake downloader
is injected; coverage is validated through the real ingest + resolver path.
"""
from datetime import date, datetime

import duckdb
import pytest
import pytz

from scripts.fetch_instrument_master import (
    parse_instruments, write_snapshot, validate_and_publish, run_refresh,
    ist_snapshot_date, RefreshResult, DEFAULT_UNDERLYINGS,
)
from core.database.utils.market_hours import MarketHours
from core.instruments.resolver import InstrumentResolver

# Mon 2026-06-08 09:00 IST — a trading day past the 08:30 cutoff, so
# expected_snapshot_date(now) == 2026-06-08. (Sun 2026-06-07 is a non-trading day.)
_NOW = MarketHours.IST.localize(datetime(2026, 6, 8, 9, 0))
_TODAY = "2026-06-08"
_FUTURE_EXPIRY = "2026-06-25"


def _complete_raw(expiry=_FUTURE_EXPIRY, underlying="NIFTY"):
    """A minimally-complete derivative master: FUT + CE + PE + one EQ."""
    return [
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|1", "tradingsymbol": "NIFTYFUT",
         "name": underlying, "expiry": expiry, "instrument_type": "FUT",
         "lot_size": 75, "tick_size": 5},
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|2", "tradingsymbol": "NIFTYCE",
         "name": underlying, "expiry": expiry, "strike_price": 22500.0,
         "instrument_type": "CE", "lot_size": 75, "tick_size": 5},
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|3", "tradingsymbol": "NIFTYPE",
         "name": underlying, "expiry": expiry, "strike_price": 22500.0,
         "instrument_type": "PE", "lot_size": 75, "tick_size": 5},
        {"segment": "NSE_EQ", "instrument_key": "NSE_EQ|INE002A01018",
         "tradingsymbol": "RELIANCE", "name": "RELIANCE INDUSTRIES",
         "instrument_type": "EQ", "lot_size": 1, "tick_size": 5,
         "isin": "INE002A01018"},
    ]


def _rows(raw, sd=_TODAY):
    return parse_instruments(raw, sd)


# --------------------------------------------------------------------------- #
# IST date stamping (§5 — fixes MM.5 operational finding #1)
# --------------------------------------------------------------------------- #
def test_ist_snapshot_date_uses_ist_not_machine_local():
    # 2026-06-08 23:30 UTC == 2026-06-09 05:00 IST — the date differs by a day.
    utc_dt = pytz.utc.localize(datetime(2026, 6, 8, 23, 30))
    assert ist_snapshot_date(utc_dt) == "2026-06-09"


# --------------------------------------------------------------------------- #
# validate_and_publish — Option A: stage → validate → promote
# --------------------------------------------------------------------------- #
def test_valid_master_is_published(tmp_path):
    db = tmp_path / "m.duckdb"
    res = validate_and_publish(_rows(_complete_raw()), _TODAY, db,
                               underlyings=("NIFTY",), now=_NOW)
    assert isinstance(res, RefreshResult)
    assert res.published is True
    r = InstrumentResolver(db_path=db)
    assert r.latest_snapshot_date() == date(2026, 6, 8)
    assert r.segment_row_count("NSE_FO") == 3


def test_equity_only_is_not_published_prior_preserved(tmp_path):
    db = tmp_path / "m.duckdb"
    # A prior good snapshot already on disk.
    write_snapshot(_rows(_complete_raw(), "2026-06-05"), db_path=db)
    equity_only = [{"segment": "NSE_EQ", "instrument_key": "NSE_EQ|INE002A01018",
                    "tradingsymbol": "RELIANCE", "name": "RELIANCE INDUSTRIES",
                    "instrument_type": "EQ", "lot_size": 1, "tick_size": 5,
                    "isin": "INE002A01018"}]
    res = validate_and_publish(_rows(equity_only), _TODAY, db,
                               underlyings=("NIFTY",), now=_NOW)
    assert res.published is False
    assert res.reason == "coverage"
    # The prior snapshot is still the latest — the bad download never landed.
    assert InstrumentResolver(db_path=db).latest_snapshot_date() == date(2026, 6, 5)


def test_expired_contracts_are_not_published(tmp_path):
    db = tmp_path / "m.duckdb"
    res = validate_and_publish(_rows(_complete_raw(expiry="2026-05-28")), _TODAY, db,
                               underlyings=("NIFTY",), now=_NOW)
    assert res.published is False
    assert res.reason == "coverage"
    assert not db.exists()  # nothing published at all


def test_stray_derivative_type_is_rejected_by_shape_guard(tmp_path):
    db = tmp_path / "m.duckdb"
    raw = _complete_raw()
    raw.append({"segment": "NSE_FO", "instrument_key": "NSE_FO|9",
                "tradingsymbol": "WEIRD", "name": "NIFTY", "expiry": _FUTURE_EXPIRY,
                "instrument_type": "XX", "lot_size": 75})
    res = validate_and_publish(_rows(raw), _TODAY, db,
                               underlyings=("NIFTY",), now=_NOW)
    assert res.published is False
    assert res.reason == "shape"
    assert not db.exists()


def test_missing_option_type_is_rejected_by_shape_guard(tmp_path):
    # A derivative master with futures but no options (the 0-OPTION-rows schema shift).
    db = tmp_path / "m.duckdb"
    fut_only = [{"segment": "NSE_FO", "instrument_key": "NSE_FO|1",
                 "tradingsymbol": "NIFTYFUT", "name": "NIFTY", "expiry": _FUTURE_EXPIRY,
                 "instrument_type": "FUT", "lot_size": 75, "tick_size": 5}]
    res = validate_and_publish(_rows(fut_only), _TODAY, db,
                               underlyings=("NIFTY",), now=_NOW)
    assert res.published is False
    assert res.reason == "shape"


def test_default_underlyings_is_nifty_and_banknifty():
    assert DEFAULT_UNDERLYINGS == ("NIFTY", "BANKNIFTY")


# --------------------------------------------------------------------------- #
# Transactional snapshot writes (§6#5 / policy §8#3)
# --------------------------------------------------------------------------- #
def test_failed_insert_rolls_back_delete(tmp_path):
    """A failed INSERT must not leave the prior same-date snapshot deleted."""
    db = tmp_path / "m.duckdb"
    write_snapshot(_rows(_complete_raw(), _TODAY), db_path=db)
    # Two rows sharing (instrument_key, snapshot_date) → PK violation on INSERT,
    # which fires AFTER the per-date DELETE.
    dup = _rows([
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|DUP", "tradingsymbol": "A",
         "name": "NIFTY", "expiry": _FUTURE_EXPIRY, "instrument_type": "FUT", "lot_size": 75},
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|DUP", "tradingsymbol": "B",
         "name": "NIFTY", "expiry": _FUTURE_EXPIRY, "instrument_type": "FUT", "lot_size": 75},
    ], _TODAY)
    with pytest.raises(Exception):
        write_snapshot(dup, db_path=db)
    con = duckdb.connect(str(db), read_only=True)
    n = con.execute("SELECT COUNT(*) FROM instruments WHERE snapshot_date = ?",
                    [_TODAY]).fetchone()[0]
    con.close()
    assert n == 4  # the original snapshot survived (DELETE rolled back)


# --------------------------------------------------------------------------- #
# run_refresh — orchestration: trading-day guard + download + validate + publish
# --------------------------------------------------------------------------- #
def test_run_refresh_publishes_on_trading_day(tmp_path):
    db = tmp_path / "m.duckdb"
    rc = run_refresh(db_path=db, now=_NOW, underlyings=("NIFTY",),
                     download=lambda sd: _rows(_complete_raw(), sd))
    assert rc == 0
    assert InstrumentResolver(db_path=db).latest_snapshot_date() == date(2026, 6, 8)


def test_run_refresh_skips_non_trading_day(tmp_path):
    db = tmp_path / "m.duckdb"
    sunday = MarketHours.IST.localize(datetime(2026, 6, 7, 9, 0))
    calls = []
    rc = run_refresh(db_path=db, now=sunday,
                     download=lambda sd: calls.append(sd) or _rows(_complete_raw(), sd))
    assert rc == 0          # a skip is not a failure
    assert calls == []      # download never attempted
    assert not db.exists()  # nothing written


def test_run_refresh_download_error_preserves_prior(tmp_path):
    db = tmp_path / "m.duckdb"
    write_snapshot(_rows(_complete_raw(), "2026-06-05"), db_path=db)

    def boom(sd):
        raise RuntimeError("CDN 503")

    rc = run_refresh(db_path=db, now=_NOW, download=boom)
    assert rc != 0
    assert InstrumentResolver(db_path=db).latest_snapshot_date() == date(2026, 6, 5)


def test_run_refresh_coverage_failure_returns_nonzero_and_preserves_prior(tmp_path):
    db = tmp_path / "m.duckdb"
    write_snapshot(_rows(_complete_raw(), "2026-06-05"), db_path=db)
    rc = run_refresh(db_path=db, now=_NOW, underlyings=("NIFTY",),
                     download=lambda sd: _rows(_complete_raw(expiry="2026-05-28"), sd))
    assert rc != 0
    assert InstrumentResolver(db_path=db).latest_snapshot_date() == date(2026, 6, 5)
