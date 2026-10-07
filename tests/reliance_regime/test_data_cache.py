"""build_panel() must not re-read ~3,500 per-date index files on every call.

load_index_context opens one DuckDB file per session date (3,563 of them), 150-230 s
a call, and the suite called build_panel() at least seven times - the reliance_regime
tests alone took 25 minutes and looked like a hang at 66% of the full run.
"""
import pandas as pd

import scripts.reliance_regime.data as data


def _stub_loaders(monkeypatch):
    calls = {"rel": 0, "ctx": 0}
    idx = pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]).date

    def rel():
        calls["rel"] += 1
        return pd.DataFrame({"close": [100.0, 101.0, 102.0]}, index=idx)

    def ctx():
        calls["ctx"] += 1
        return pd.DataFrame({"nifty": [1.0, 2.0, 3.0], "vix": [9.0, 9.5, 9.1]}, index=idx)

    monkeypatch.setattr(data, "load_reliance_daily", rel)
    monkeypatch.setattr(data, "load_index_context", ctx)
    data._cached_panel.cache_clear()
    return calls


def test_build_panel_loads_each_source_once_per_process(monkeypatch):
    calls = _stub_loaders(monkeypatch)
    data.build_panel()
    data.build_panel()
    assert calls == {"rel": 1, "ctx": 1}
    data._cached_panel.cache_clear()


def test_build_panel_returns_independent_copies(monkeypatch):
    _stub_loaders(monkeypatch)
    a = data.build_panel()
    a["close"] = 0.0
    a["extra"] = 1
    b = data.build_panel()
    assert b["close"].iloc[0] == 100.0 and "extra" not in b.columns
    data._cached_panel.cache_clear()
