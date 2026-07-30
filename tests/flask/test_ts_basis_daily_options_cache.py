"""Tests for the /ts-basis-daily options-contract cache in the Flask blueprint.

Regression: `_resolve_contracts()` cached `select_book_options(book)` keyed only
on `formation_date`, with no intraday invalidation. Once selection went live
(anchor + tradeability screen depend on the current quote), a page load before
market open would freeze the anchor/screen for the rest of the session, and a
reload never re-anchored. `force=True` (page load) must always re-resolve;
`force=False` (the 2s live tick) must keep reusing the cached contracts.
"""
from datetime import date

import flask_app.blueprints.ts_basis_daily as ts_basis_daily


FORMATION = date(2026, 7, 27)


class _FakeCon:
    def __init__(self, formation):
        self._formation = formation
        self.closed = False

    def execute(self, *_a, **_k):
        return self

    def fetchone(self):
        return (self._formation,)

    def close(self):
        self.closed = True


def _patch_resolution(monkeypatch, formation=FORMATION):
    """Stub the DuckDB + selection seams; return a call-count list for
    select_book_options."""
    calls = []

    def _fake_get_facts_con():
        return _FakeCon(formation)

    def _fake_load_book(_con, _formation):
        return [("WIPRO", "LONG")]

    def _fake_select_book_options(book):
        calls.append(book)
        return [{"ticker": "WIPRO", "quote_date": None}]

    monkeypatch.setattr(ts_basis_daily, "_get_facts_con", _fake_get_facts_con)
    monkeypatch.setattr(ts_basis_daily, "_load_book", _fake_load_book)
    monkeypatch.setattr(ts_basis_daily, "select_book_options", _fake_select_book_options)
    monkeypatch.setattr(ts_basis_daily, "_options_cache",
                        {"formation": None, "contracts": []})
    return calls


def test_repeated_live_calls_hit_the_cache_once(monkeypatch):
    calls = _patch_resolution(monkeypatch)

    ts_basis_daily._resolve_contracts()
    ts_basis_daily._resolve_contracts()

    assert len(calls) == 1, "same formation, force=False must not re-resolve twice"


def test_force_true_always_re_resolves(monkeypatch):
    calls = _patch_resolution(monkeypatch)

    ts_basis_daily._resolve_contracts()
    assert len(calls) == 1

    ts_basis_daily._resolve_contracts(force=True)
    assert len(calls) == 2, "force=True (page reload) must re-anchor/re-screen"

    ts_basis_daily._resolve_contracts()
    assert len(calls) == 2, "the 2s live tick after a reload must reuse the fresh cache"


def test_force_true_updates_the_cache_contents(monkeypatch):
    calls = _patch_resolution(monkeypatch)

    formation1, contracts1, err1 = ts_basis_daily._resolve_contracts()
    assert err1 is None
    assert contracts1 == [{"ticker": "WIPRO", "quote_date": None}]

    formation2, contracts2, err2 = ts_basis_daily._resolve_contracts(force=True)
    assert err2 is None
    assert formation2 == formation1
    assert len(calls) == 2
    assert ts_basis_daily._options_cache["contracts"] == contracts2
