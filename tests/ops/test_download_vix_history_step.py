"""The nightly download must top up NiftyShield's India VIX history cache.

`vix_percentile.refresh()` was documented as an EOD-chain step but nothing ever
called it, and the EOD chain itself has been disabled since 2026-09-11. The
cache froze at 2026-09-07, so every live 13:00 fact computed `vix_pctile`
against a trailing window a month stale
(docs/reports/NIFTY_SHIELD_VIX_HISTORY_STALE_2026-10-09.md).
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import scripts.download_all_data as D  # noqa: E402


def _record_runs(monkeypatch, failing_label=None):
    calls = []

    def fake_run(script_path, args=None, label="", timeout=None):
        calls.append((Path(script_path).relative_to(ROOT).as_posix(), label))
        return label != failing_label

    monkeypatch.setattr(D, "_run", fake_run)
    monkeypatch.setattr(D, "_download_1m_candles", lambda full, lookback: True)
    monkeypatch.setattr(D, "_incremental_start", lambda db, table, lb: (date(2026, 9, 1), True))
    monkeypatch.setattr(D, "_warn_unresolved_calendar", lambda start: None)
    monkeypatch.setattr(D, "_max_index_date", lambda: date(2026, 9, 25))
    return calls


def test_download_refreshes_vix_history_once_after_the_index_ingest(monkeypatch):
    calls = _record_runs(monkeypatch)

    assert D.download_data(full=False, lookback=7)

    labels = [label for _, label in calls]
    assert labels.count("vix-history") == 1
    assert labels.index("vix-history") > labels.index("index-history")
    assert ("scripts/daytype/vix_percentile.py", "vix-history") in calls


def test_a_failed_vix_history_refresh_fails_the_download(monkeypatch):
    _record_runs(monkeypatch, failing_label="vix-history")

    assert D.download_data(full=False, lookback=7) is False
