"""The nightly 1m step must re-mark CAS carry-forward bars it re-fetches.

fetch_upstox_historical.py upserts with is_synthetic = FALSE, so every session in
its trailing window lost its marks, and nothing in the pipeline put them back:
2026-09-04 onward carried 0 marks (CAS_SYNTHETIC_MARKS_RESET_2026-10-26.md).
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import scripts.download_all_data as D  # noqa: E402
from scripts.cas import build_cas_category, mark_synthetic_bars  # noqa: E402

STORE_HEAD = date(2026, 10, 23)


def _pipeline(monkeypatch, fetch_ok=True):
    events = []
    head = {"max": STORE_HEAD}

    def fake_fetch(full, lookback):
        events.append("fetch")
        head["max"] = date(2026, 10, 26)     # the fetch advances the store head
        return fetch_ok

    monkeypatch.setattr(D, "_run", lambda script_path, args=None, label="", timeout=None: True)
    monkeypatch.setattr(D, "_download_1m_candles", fake_fetch)
    monkeypatch.setattr(D, "_max_1m_date", lambda: head["max"])
    monkeypatch.setattr(D, "_mark_cas_synthetic", lambda since: events.append(("mark", since)) or True)
    monkeypatch.setattr(D, "_incremental_start", lambda db, table, lb: (date(2026, 10, 16), True))
    monkeypatch.setattr(D, "_warn_unresolved_calendar", lambda start: None)
    monkeypatch.setattr(D, "_max_index_date", lambda: STORE_HEAD)
    monkeypatch.setattr(sys, "argv", ["download_all_data.py"])
    return events


def test_marks_from_the_start_the_fetch_used(monkeypatch):
    events = _pipeline(monkeypatch)

    assert D.download_data(full=False, lookback=7)

    assert events == ["fetch", ("mark", date(2026, 10, 16))]


def test_marks_even_when_the_fetch_fails(monkeypatch):
    """A partial or timed-out upsert has still reset the rows it wrote."""
    events = _pipeline(monkeypatch, fetch_ok=False)

    assert D.download_data(full=False, lookback=7) is False
    assert ("mark", date(2026, 10, 16)) in events


def test_skip_1m_skips_the_mark(monkeypatch):
    events = _pipeline(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["download_all_data.py", "--skip-1m"])

    assert D.download_data(full=False, lookback=7)
    assert events == []


def test_a_failed_mark_fails_the_download(monkeypatch):
    _pipeline(monkeypatch)
    monkeypatch.setattr(D, "_mark_cas_synthetic", lambda since: False)

    assert D.download_data(full=False, lookback=7) is False


def test_full_marks_from_thirty_days_back(monkeypatch):
    events = _pipeline(monkeypatch)

    D.download_data(full=True, lookback=7)

    assert ("mark", date(2026, 9, 23)) in events


def test_mark_step_rebuilds_the_category_before_marking(monkeypatch):
    calls = []
    monkeypatch.setattr(build_cas_category, "build", lambda: calls.append("build") or 370)
    monkeypatch.setattr(mark_synthetic_bars, "run",
                        lambda apply, since: calls.append(("run", apply, since)) or
                        {"sessions": 5, "bars_flagged": 14000})

    assert D._mark_cas_synthetic(date(2026, 10, 16)) is True
    assert calls == ["build", ("run", True, date(2026, 10, 16))]


def test_mark_step_fails_loud_on_a_marker_error(monkeypatch):
    def refuse(apply, since):
        raise RuntimeError("no Cat-I symbols resolved for 2026-10-26")

    monkeypatch.setattr(build_cas_category, "build", lambda: 370)
    monkeypatch.setattr(mark_synthetic_bars, "run", refuse)

    assert D._mark_cas_synthetic(date(2026, 10, 16)) is False
