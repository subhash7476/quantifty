"""Tests for SE-3 forward spread collection — store schema, append-only PK,
sweep counting with a fake market-data feed (no live credentials)."""
import datetime

import pandas as pd
import pytest

from scripts.se3 import collect_option_spreads as s


class FakeMarketData:
    """Returns a fixed bid/ask per key. Stateless unless `sweeps` given."""

    def __init__(self, quote_map, sweeps=None):
        self.quote_map = quote_map
        self.sweeps = sweeps
        self.calls = 0

    def fetch_quotes_batch(self, keys):
        self.calls += 1
        if self.sweeps is not None and self.calls > self.sweeps:
            return {"quotes": {}, "error": "feed exhausted"}
        out = {}
        for k in keys:
            if k in self.quote_map:
                out[k] = dict(self.quote_map[k])
        return {"quotes": out, "error": None}


class FakeRows:
    def __init__(self, d):
        self._d = d

    def get(self, key, default=None):
        return self._d.get(key, default)

    def __getitem__(self, key):
        return self._d[key]

    def __setitem__(self, key, value):
        self._d[key] = value


@pytest.fixture()
def store(tmp_path):
    con = s._init_store(tmp_path / "spreads.duckdb")
    yield con
    con.close()


def _row_map():
    return {
        "NSE_FO|RELIANCE": {
            "best_bid": 40.0, "best_ask": 40.5, "ltp": 40.25, "oi": 500, "volume": 1200,
        },
        "NSE_FO|TCS": {
            "best_bid": 80.0, "best_ask": 80.5, "ltp": 80.25, "oi": 800, "volume": 900,
        },
    }


def _row_map_wide_spread():
    # RELIANCE quote fails the 5% spread screen; TCS passes.
    return {
        "NSE_FO|RELIANCE": {
            "best_bid": 40.0, "best_ask": 44.0, "ltp": 42.0, "oi": 500, "volume": 1200,
        },
        "NSE_FO|TCS": {
            "best_bid": 80.0, "best_ask": 80.5, "ltp": 80.25, "oi": 800, "volume": 900,
        },
    }


def _patch_pick(monkeypatch, rows):
    fake = [FakeRows(r) for r in rows]
    monkeypatch.setattr(s, "_pick_contracts", lambda: fake)


class TestStoreSchema:
    def test_init_creates_table(self, store):
        cols = {r[0] for r in store.execute("DESCRIBE spread_observations").fetchall()}
        for c in ("trade_date", "observed_at", "underlying", "expiry_dt", "option_type",
                  "strike", "instrument_key", "best_bid", "best_ask", "spread_pct",
                  "screen", "screen_reason"):
            assert c in cols

    def test_append_and_count(self, store):
        store.execute(
            "INSERT INTO spread_observations (trade_date, observed_at, underlying, "
            "expiry_dt, option_type, strike, instrument_key, best_bid, best_ask, "
            "spread_pct, screen, screen_reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [datetime.date(2026, 8, 5), datetime.datetime(2026, 8, 5, 10, 0, 0),
             "RELIANCE", datetime.date(2026, 8, 27), "CE", 2900.0,
             "NSE_FO|RELIANCE", 40.0, 40.5, 0.0124, "pass", None],
        )
        assert store.execute("SELECT COUNT(*) FROM spread_observations").fetchone()[0] == 1


class TestCollectOnce:
    def test_observes_quoted_keys(self, store, monkeypatch):
        rows = [
            {"instrument_key": "NSE_FO|RELIANCE", "ticker": "RELIANCE",
             "expiry": datetime.date(2026, 8, 27), "opt_type": "CE", "strike": 2900.0},
            {"instrument_key": "NSE_FO|TCS", "ticker": "TCS",
             "expiry": datetime.date(2026, 8, 27), "opt_type": "CE", "strike": 4400.0},
            {"instrument_key": None, "ticker": "MISSING", "expiry": None,
             "opt_type": "CE", "strike": None},
        ]
        _patch_pick(monkeypatch, rows)
        md = FakeMarketData(_row_map())
        n_obs, n_skip, err = s._collect_once(store, md)
        assert n_obs == 2
        assert n_skip == 1  # no instrument_key
        assert err == 0
        assert store.execute("SELECT COUNT(*) FROM spread_observations").fetchone()[0] == 2

    def test_skips_no_quote(self, store, monkeypatch):
        rows = [{"instrument_key": "NSE_FO|RELIANCE", "ticker": "RELIANCE",
                 "expiry": datetime.date(2026, 8, 27), "opt_type": "CE", "strike": 2900.0}]
        _patch_pick(monkeypatch, rows)
        md = FakeMarketData({})  # no quote for the key
        n_obs, n_skip, err = s._collect_once(store, md)
        assert n_obs == 0
        assert n_skip == 1
        assert store.execute("SELECT COUNT(*) FROM spread_observations").fetchone()[0] == 0

    def test_append_only_pk_dedupes_re_run(self, store, monkeypatch):
        rows = [{"instrument_key": "NSE_FO|RELIANCE", "ticker": "RELIANCE",
                 "expiry": datetime.date(2026, 8, 27), "opt_type": "CE", "strike": 2900.0}]
        _patch_pick(monkeypatch, rows)
        md = FakeMarketData(_row_map())
        s._collect_once(store, md)
        # A second call with the same key but a DIFFERENT observed_at is a new
        # observation (append-only); the PK is (observed_at, instrument_key).
        s._collect_once(store, md)
        assert store.execute("SELECT COUNT(*) FROM spread_observations").fetchone()[0] == 2
        # Exactly the same (observed_at, key) pair cannot be inserted twice.
        with pytest.raises(Exception, match="Duplicate key"):
            store.execute(
                "INSERT INTO spread_observations (trade_date, observed_at, underlying, "
                "expiry_dt, option_type, strike, instrument_key, best_bid, best_ask, "
                "spread_pct, screen, screen_reason) "
                "SELECT trade_date, observed_at, underlying, expiry_dt, option_type, "
                "strike, instrument_key, best_bid, best_ask, spread_pct, screen, screen_reason "
                "FROM spread_observations LIMIT 1")
        assert store.execute("SELECT COUNT(*) FROM spread_observations").fetchone()[0] == 2


class TestFailureModes:
    """A failed fetch must be counted as an ERROR, never as a skip, and a
    fully-failed sweep must surface a non-zero exit — never a silent 0."""

    def test_fetch_error_counts_as_error_not_skip(self, store, monkeypatch):
        rows = [{"instrument_key": "NSE_FO|RELIANCE", "ticker": "RELIANCE",
                 "expiry": datetime.date(2026, 8, 27), "opt_type": "CE", "strike": 2900.0}]
        _patch_pick(monkeypatch, rows)

        class FailingMarketData:
            def fetch_quotes_batch(self, keys):
                return {"quotes": {}, "error": "Upstox HTTP 401"}

        n_obs, n_skip, err = s._collect_once(store, FailingMarketData())
        assert n_obs == 0
        assert n_skip == 0
        assert err == 1
        assert store.execute("SELECT COUNT(*) FROM spread_observations").fetchone()[0] == 0

    def test_exit_code_1_on_fetch_error(self, monkeypatch):
        assert s._exit_code(0, 5) == 1

    def test_sweeps_mode_accumulates_exit_code(self, monkeypatch, tmp_path):
        """A multi-sweep run must surface the ACCUMULATED failure, not a
        hardcoded 0 — the freshness assertion applies to every mode."""
        seen = {"n": 0}

        def fake_collect(con, market_data):
            seen["n"] += 1
            if seen["n"] % 2 == 0:
                return 0, 0, 1  # one failing sweep among successes
            return 3, 0, 0

        class FakeStore:
            def close(self):
                pass

        monkeypatch.setattr(s, "_collect_once", fake_collect)
        monkeypatch.setattr(s, "_init_store", lambda *a, **k: FakeStore())
        monkeypatch.setattr(
            "core.database.utils.market_hours.MarketHours.is_market_open",
            staticmethod(lambda: True),
        )

        class FakeMD:
            pass

        monkeypatch.setattr(
            "core.brokers.upstox_market_data.UpstoxMarketData",
            lambda *a, **k: FakeMD(),
        )
        monkeypatch.setattr(s.time, "sleep", lambda _s: None)
        assert s.run(2, None, False) == 1  # 3 obs, 1 err -> exit 1

    def test_minutes_mode_accumulates_exit_code(self, monkeypatch):
        """--minutes must also surface accumulated errors (exit 1), not 0."""
        seen = {"n": 0}

        def fake_collect(con, market_data):
            seen["n"] += 1
            return 0, 0, 1

        def fake_time():
            if seen["n"] == 0:
                return 100.0
            return 200.0  # beyond deadline (100 + minutes*60)

        def fake_sleep(_s):
            pass

        class FakeStore:
            def close(self):
                pass

        monkeypatch.setattr(s, "_collect_once", fake_collect)
        monkeypatch.setattr(s, "_init_store", lambda *a, **k: FakeStore())
        monkeypatch.setattr(s.time, "time", fake_time)
        monkeypatch.setattr(s.time, "sleep", fake_sleep)

        class FakeMD:
            pass

        monkeypatch.setattr(
            "core.brokers.upstox_market_data.UpstoxMarketData",
            lambda *a, **k: FakeMD(),
        )
        assert s.run(None, 1, False) == 1  # 0 obs, 1 err -> exit 1

    def test_exit_code_2_when_market_open_and_zero_observed(self, monkeypatch):
        monkeypatch.setattr(
            "core.database.utils.market_hours.MarketHours.is_market_open",
            staticmethod(lambda: True),
        )
        assert s._exit_code(0, 0) == 2

    def test_exit_code_0_on_success(self, monkeypatch):
        monkeypatch.setattr(
            "core.database.utils.market_hours.MarketHours.is_market_open",
            staticmethod(lambda: True),
        )
        assert s._exit_code(5, 0) == 0

    def test_exit_code_0_when_market_closed(self, monkeypatch):
        monkeypatch.setattr(
            "core.database.utils.market_hours.MarketHours.is_market_open",
            staticmethod(lambda: False),
        )
        assert s._exit_code(0, 0) == 0
