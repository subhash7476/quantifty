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
