"""
Finding 2 (MASTER_MATERIALIZATION_READINESS.md) — OptionsProvider is a second,
snapshot-blind reader of the instrument master file.

`get_lot_size` / `get_available_strikes` / `get_expiry_list` / `get_weekly_expiry`
query `instruments` by raw SQL with no `snapshot_date` filter. Harmless at one
snapshot; once daily snapshots accumulate the queries span ALL snapshots —
`DISTINCT strike/expiry` returns a cross-snapshot UNION and `lot_size … LIMIT 1`
returns an arbitrary snapshot's lot. The fix scopes each read to the latest
snapshot. This must land before snapshots accumulate (4C.7 hard blocker).

Fixture: an OLD (stale) snapshot + a NEW snapshot for NIFTY, built through the
real 4C.1 ingest pipeline. Correct reads return ONLY the newest snapshot.
"""
from datetime import date

import pytest

import core.data.options_provider as op_mod
from core.data.options_provider import OptionsProvider
from scripts.fetch_instrument_master import parse_instruments, write_snapshot


def _ce(ikey, strike, expiry, lot):
    return {"segment": "NSE_FO", "instrument_key": ikey,
            "tradingsymbol": f"NIFTY{int(strike)}CE", "name": "NIFTY",
            "instrument_type": "CE", "expiry": expiry,
            "strike_price": strike, "lot_size": lot, "tick_size": 5}


@pytest.fixture
def provider(tmp_path, monkeypatch):
    master = tmp_path / "instruments.duckdb"
    # OLD snapshot (stale): lot 50, strikes {22000,22500} @ 2026-06-25,
    # plus an earlier future expiry 2026-03-25 and a long-past expiry.
    old = [
        _ce("NSE_FO|1", 22000, "2026-06-25", 50),
        _ce("NSE_FO|2", 22500, "2026-06-25", 50),
        _ce("NSE_FO|3", 22000, "2026-03-25", 50),
        _ce("NSE_FO|4", 22000, "2024-12-25", 50),
    ]
    # NEW snapshot: lot 75, strikes {23000,23500} @ 2026-06-25 only.
    new = [
        _ce("NSE_FO|5", 23000, "2026-06-25", 75),
        _ce("NSE_FO|6", 23500, "2026-06-25", 75),
    ]
    write_snapshot(parse_instruments(old, "2024-01-01"), db_path=master)
    write_snapshot(parse_instruments(new, "2026-06-01"), db_path=master)

    monkeypatch.setattr(op_mod, "INSTRUMENT_DB_PATH", master)
    return OptionsProvider(db_path=tmp_path / "cache.duckdb", read_only=True)


def test_lot_size_uses_latest_snapshot(provider):
    # Unfiltered LIMIT 1 over {50,75} can return the stale 50.
    assert provider.get_lot_size("NIFTY") == 75


def test_strikes_are_latest_snapshot_only(provider):
    # Unfiltered DISTINCT unions both snapshots → 4 strikes.
    assert provider.get_available_strikes("NIFTY", "2026-06-25") == [23000.0, 23500.0]


def test_expiry_list_is_latest_snapshot_only(provider):
    # Unfiltered DISTINCT unions stale expiries (2024-12-25, 2026-03-25).
    assert provider.get_expiry_list("NIFTY", count=10) == ["2026-06-25"]


def test_weekly_expiry_ignores_stale_snapshot(provider):
    # Stale snapshot's nearer future expiry (2026-03-25) must not win;
    # the latest snapshot only lists 2026-06-25.
    nearest = provider.get_weekly_expiry("NSE_INDEX|Nifty 50", date(2026, 1, 1))
    assert nearest == "2026-06-25"


def _named_ce(name, ikey, strike, expiry, lot):
    return {"segment": "NSE_FO", "instrument_key": ikey,
            "tradingsymbol": f"{name}{int(strike)}CE", "name": name,
            "instrument_type": "CE", "expiry": expiry,
            "strike_price": strike, "lot_size": lot, "tick_size": 5}


@pytest.fixture
def multi_index_provider(tmp_path, monkeypatch):
    """Master with three distinct lot sizes so a per-underlying miss is visible."""
    master = tmp_path / "instruments.duckdb"
    rows = [
        _named_ce("NIFTY", "NSE_FO|N", 23000, "2026-09-10", 65),
        _named_ce("BANKNIFTY", "NSE_FO|B", 50000, "2026-09-10", 30),
        _named_ce("SENSEX", "NSE_FO|S", 76000, "2026-09-10", 20),
    ]
    write_snapshot(parse_instruments(rows, "2026-09-01"), db_path=master)
    monkeypatch.setattr(op_mod, "INSTRUMENT_DB_PATH", master)
    return OptionsProvider(db_path=tmp_path / "cache.duckdb", read_only=True)


def _chain_payload(underlying_key):
    return [{"expiry": "2026-09-10", "strike_price": 100, "underlying_key": underlying_key,
             "underlying_spot_price": 100.0,
             "call_options": {"instrument_key": "c", "market_data": {"ltp": 1}},
             "put_options": {"instrument_key": "p", "market_data": {"ltp": 1}}}]


@pytest.mark.parametrize("key,expected", [
    ("NSE_INDEX|Nifty 50", 65),
    ("NSE_INDEX|Nifty Bank", 30),
    ("BSE_INDEX|SENSEX", 20),
])
def test_parsed_chain_carries_master_lot_size(multi_index_provider, key, expected):
    # The Upstox chain payload has no per-strike lot_size; every row must take
    # the underlying's master lot size, never the stale hardcoded 75.
    rows, _ = multi_index_provider._parse_option_chain_response(
        _chain_payload(key), "2026-09-10")
    assert rows and {r.lot_size for r in rows} == {expected}


def test_get_lot_size_handles_sensex(multi_index_provider):
    # SENSEX was absent from the name_map → silently returned 75.
    assert multi_index_provider.get_lot_size("SENSEX") == 20


# 2026-09-22: a transient lock on the instrument master (another process writing
# it) made the expiry lookup fall back to `as_of + 1 day`, skipping the expiring
# series, and the memo then held that answer for the whole session. The same
# lock pinned NIFTY lot_size at 75 (true 65) for the day.

def _lock_master_once(monkeypatch):
    real_connect = op_mod.duckdb.connect
    calls = {"n": 0}

    def flaky_connect(path, *args, **kwargs):
        if str(path) == str(op_mod.INSTRUMENT_DB_PATH) and calls["n"] == 0:
            calls["n"] += 1
            raise op_mod.duckdb.IOException("file is being used by another process")
        return real_connect(path, *args, **kwargs)

    monkeypatch.setattr(op_mod.duckdb, "connect", flaky_connect)


def test_fallback_expiry_includes_today_on_expiry_day(tmp_path, monkeypatch):
    monkeypatch.setattr(op_mod, "INSTRUMENT_DB_PATH", tmp_path / "missing.duckdb")
    provider = OptionsProvider(db_path=tmp_path / "cache.duckdb", read_only=True)
    # 2026-09-22 is a Tuesday — NIFTY's expiry day.
    assert provider.get_weekly_expiry("NSE_INDEX|Nifty 50", date(2026, 9, 22)) == "2026-09-22"


def test_locked_master_does_not_poison_expiry_memo(multi_index_provider, monkeypatch):
    _lock_master_once(monkeypatch)
    as_of = date(2026, 9, 8)  # master's only NIFTY expiry is Thu 2026-09-10
    multi_index_provider.get_weekly_expiry("NSE_INDEX|Nifty 50", as_of)
    assert multi_index_provider.get_weekly_expiry("NSE_INDEX|Nifty 50", as_of) == "2026-09-10"


def test_locked_master_does_not_poison_lot_size_cache(multi_index_provider, monkeypatch):
    _lock_master_once(monkeypatch)
    multi_index_provider._lot_size_for_symbol("NSE_INDEX|Nifty 50")
    assert multi_index_provider._lot_size_for_symbol("NSE_INDEX|Nifty 50") == 65
