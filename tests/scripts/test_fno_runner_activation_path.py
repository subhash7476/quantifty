"""
MM7E §5/§6 — the E5 G1-protected activation sequence, driven by the production
root (not a test-local harness).

Two proofs:
  1. A FRESH F&O run sequences master-readiness -> restore-canonicalization
     (positions #7-as-restored + orders #8) -> reconciliation, via the REAL
     build_master_readiness over a fixture master. The no-op source keeps the
     loop trade-free so the sequence fires on the restored ledger without sizing
     a derivative order (F4 stays out of MM7E).
  2. The paper rung reaches a clean STOPPED end-to-end: the MM7D.1 BUY/EXIT
     equity spine, now driven by scripts.fno_runner.build_runner, persists the
     round-trip and flattens.

Built with the MM7C/MM7D.1 isolation construction. No real data / live provider /
RealTimeClock is touched.
"""

import json
from pathlib import Path

import pytest

from core.execution.position_models import PositionSide
from core.runtime.config import Mode
from core.runtime.driver import RuntimeState
from core.runtime.event_journal import RuntimeEventJournal

from _runner_harness import (DERIV, EQUITY, BuyExitSource, NoopSource, build,
                             make_master)


@pytest.fixture
def alerts(monkeypatch):
    """Silence + capture the driver's alerter — no Telegram I/O."""
    class _Rec:
        def __init__(self):
            self.levels = []

        def info(self, m):
            self.levels.append("info")

        def warning(self, m):
            self.levels.append("warning")

        def critical(self, m):
            self.levels.append("critical")

    rec = _Rec()
    monkeypatch.setattr("core.runtime.driver.alerter", rec)
    return rec


def _events(path: Path):
    return [json.loads(l)["event_type"] for l in path.read_text().splitlines()]


def test_fresh_fno_run_sequences_readiness_canonicalize_reconcile(
        tmp_path, monkeypatch, alerts):
    master = make_master(tmp_path)
    journal = RuntimeEventJournal(path=str(tmp_path / "gate.jsonl"))
    d = build(tmp_path, monkeypatch, source=NoopSource(), symbols=(DERIV,),
              underlyings=["NIFTY"], master_db_path=master,
              broker_positions=lambda: [], journal=journal, max_bars=2)

    # Record the gate's call order by wrapping each step (the real checker still
    # returns FRESH so the gate proceeds through canonicalize and reconcile).
    seq = []
    real_checker = d._master_readiness
    d._master_readiness = lambda: (seq.append("READINESS"), real_checker())[1]
    monkeypatch.setattr(d._execution, "canonicalize_restored_positions",
                        lambda: seq.append("CANONICALIZE_POSITIONS"))
    monkeypatch.setattr(d._execution, "canonicalize_restored_orders",
                        lambda: seq.append("CANONICALIZE_ORDERS"))
    real_reconcile = d._execution.reconciliation.reconcile
    monkeypatch.setattr(d._execution.reconciliation, "reconcile",
                        lambda bp: (seq.append("RECONCILE"), real_reconcile(bp))[1])

    d.run()

    assert seq == ["READINESS", "CANONICALIZE_POSITIONS",
                   "CANONICALIZE_ORDERS", "RECONCILE"]
    ev = _events(tmp_path / "gate.jsonl")
    assert "RECONCILIATION_PASS" in ev and "RUNNING" in ev
    assert d.state is RuntimeState.STOPPED


def test_paper_rung_runs_to_clean_stopped(tmp_path, monkeypatch, alerts):
    d = build(tmp_path, monkeypatch, source=BuyExitSource(EQUITY), symbols=(EQUITY,),
              broker_positions=lambda: [], max_bars=3, n_bars=3)
    d.run()

    assert d.config.mode is Mode.LIVE
    assert d.state is RuntimeState.STOPPED
    # The BUY/EXIT round-trip persisted through the real handler + PaperBroker.
    assert len(d._execution.order_repo.get_all()) == 2
    assert len(d._execution.fill_repo.get_all()) == 2
    assert d._execution.position_tracker.get_position(EQUITY).side is PositionSide.FLAT
