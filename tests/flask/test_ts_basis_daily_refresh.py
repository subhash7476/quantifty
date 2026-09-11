"""/ts-basis-daily refresh and freshness.

Regression (TS_BASIS_DAILY_SIGNAL_AUDIT_2026-09-11 F8): the panel's refresh ran its own
build + the insert-only publisher, skipped the recovery filter, and reported success
even when publishing failed.
"""
import sys

import duckdb

import flask_app.blueprints.ts_basis_daily as ts_basis_daily


def test_refresh_runs_the_shared_pipeline_for_ts_basis_daily_only():
    cmd = ts_basis_daily._refresh_command()
    assert cmd[0] == sys.executable
    assert cmd[1].endswith("refresh_all_strategies.py")
    assert cmd[2:] == ["--skip-carry", "--skip-ts-basis"]


def test_unreadable_futures_store_reports_unknown_freshness(monkeypatch):
    def locked(_formation):
        raise duckdb.IOException("Could not set lock on file")

    monkeypatch.setattr(ts_basis_daily, "stale_message", locked)
    assert ts_basis_daily._stale(None).startswith("Freshness unknown")
