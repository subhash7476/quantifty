"""TS Basis Daily pipeline wiring and book freshness.

Regressions from TS_BASIS_DAILY_SIGNAL_AUDIT_2026-09-11: `--force` still ran the
incremental build (F2); the recovery filter's exit code was ignored; and every book
consumer took MAX(formation_date) with no check that it was current (F6).
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import refresh_all_strategies as RS  # noqa: E402
import ts_basis_daily_options as O  # noqa: E402
import ts_basis_daily_signals as S  # noqa: E402

D1 = date(2026, 9, 9)
D2 = date(2026, 9, 10)


def _refresh(monkeypatch, argv, fail=None):
    calls = []

    def fake_run(script_path, args=None, label=""):
        calls.append((script_path.name, args))
        return script_path.name != fail

    monkeypatch.setattr(RS, "_run", fake_run)
    monkeypatch.setattr(RS, "_latest_source_date", lambda: D2)
    monkeypatch.setattr(RS, "_needs_rebuild", lambda *a, **k: True)
    monkeypatch.setattr(sys, "argv", ["refresh_all_strategies.py", "--skip-carry", "--skip-ts-basis", *argv])
    return RS.main(), calls


def test_force_runs_a_full_daily_rebuild_then_publish_then_filter(monkeypatch):
    rc, calls = _refresh(monkeypatch, ["--force"])
    assert rc == 0
    assert calls == [("build_ts_basis_daily.py", None), ("publish_facts.py", None),
                     ("apply_recovery_filter.py", None)]


def test_stale_store_runs_the_incremental_build(monkeypatch):
    rc, calls = _refresh(monkeypatch, [])
    assert rc == 0
    assert calls[0] == ("build_ts_basis_daily.py", ["--incremental"])


@pytest.mark.parametrize("step", ["publish_facts.py", "apply_recovery_filter.py"])
def test_a_failed_daily_step_fails_the_refresh(monkeypatch, step):
    rc, calls = _refresh(monkeypatch, [], fail=step)
    assert rc == 1
    assert calls[-1][0] == step


def _stores(tmp_path, formation, source):
    facts = duckdb.connect(str(tmp_path / "facts.duckdb"))
    facts.execute("CREATE TABLE carry_facts (formation_date DATE, underlying VARCHAR, z_carry_neut DOUBLE, "
                  "quintile TINYINT, eligible BOOLEAN, raw_z DOUBLE, basis_reverting BOOLEAN)")
    facts.execute("INSERT INTO carry_facts VALUES (?, 'AAA', 3.0, 5, TRUE, 3.2, FALSE)", [formation])
    facts.close()
    sig = duckdb.connect(str(tmp_path / "sig.duckdb"))
    sig.execute("CREATE TABLE signals (formation_date DATE, underlying VARCHAR, z_ts DOUBLE, liquid BOOLEAN)")
    sig.execute("INSERT INTO signals VALUES (?, 'AAA', 3.0, TRUE)", [formation])
    sig.close()
    fut = duckdb.connect(str(tmp_path / "fut.duckdb"))
    fut.execute("CREATE TABLE futures_bhavcopy (trade_date DATE, inst_type VARCHAR)")
    fut.execute("INSERT INTO futures_bhavcopy VALUES (?, 'FUTSTK'), (DATE '2026-01-01', 'FUTIDX')", [source])
    fut.close()


@pytest.fixture
def cli(tmp_path, monkeypatch):
    def setup(formation, source, *argv):
        _stores(tmp_path, formation, source)
        monkeypatch.setattr(O, "FACTS_DB", tmp_path / "facts.duckdb")
        monkeypatch.setattr(O, "FUT_DB", tmp_path / "fut.duckdb")
        monkeypatch.setattr(O, "select_book_options", lambda book, min_dte=None: [])
        monkeypatch.setattr(S, "FACTS_DB", tmp_path / "facts.duckdb")
        monkeypatch.setattr(S, "SIG_DB", tmp_path / "sig.duckdb")
        monkeypatch.setattr(sys, "argv", ["cli", *argv])
    return setup


@pytest.mark.parametrize("module", [O, S])
def test_latest_book_refuses_when_the_futures_store_is_ahead(cli, capsys, module):
    cli(D1, D2)
    assert module.main() == 2
    assert "STALE" in capsys.readouterr().err


@pytest.mark.parametrize("module", [O, S])
def test_latest_book_prints_when_current(cli, module):
    cli(D2, D2)
    assert module.main() == 0


@pytest.mark.parametrize("module", [O, S])
def test_an_explicit_date_is_a_historical_lookup(cli, module):
    cli(D1, D2, str(D1))
    assert module.main() == 0
