"""The nightly download must archive the NSE SPAN settlement file.

Nothing scheduled `fetch_span_params.py` after the 2026-08-06 archive, so every
NiftyShield session from 2026-09-07 ran without SPAN and sized on the broker's
basket margin (NIFTY_SHIELD_PAPER_BOOK_AUDIT_2026-09-25 F3 / R4).
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import scripts.download_all_data as D  # noqa: E402


def _record_runs(monkeypatch):
    calls = []

    def fake_run(script_path, args=None, label="", timeout=None):
        calls.append((Path(script_path).name, list(args or []), label))
        return True

    monkeypatch.setattr(D, "_run", fake_run)
    monkeypatch.setattr(D, "_download_1m_candles", lambda full, lookback: True)
    monkeypatch.setattr(D, "_incremental_start", lambda db, table, lb: (date(2026, 9, 1), True))
    monkeypatch.setattr(D, "_warn_unresolved_calendar", lambda start: None)
    monkeypatch.setattr(D, "_max_index_date", lambda: date(2026, 9, 25))
    return calls


def test_download_archives_span_as_a_resumable_backfill_over_the_lookback(monkeypatch):
    calls = _record_runs(monkeypatch)

    assert D.download_data(full=False, lookback=10)

    span = [c for c in calls if c[0] == "fetch_span_params.py"]
    assert len(span) == 1
    _, args, label = span[0]
    assert label == "span"
    assert args == ["--backfill", "--start",
                    (date.today() - timedelta(days=10)).isoformat()]


def test_a_failed_span_fetch_fails_the_download(monkeypatch):
    calls = _record_runs(monkeypatch)
    monkeypatch.setattr(
        D, "_run",
        lambda script_path, args=None, label="", timeout=None:
            calls.append(label) or label != "span")

    assert D.download_data(full=False, lookback=10) is False
