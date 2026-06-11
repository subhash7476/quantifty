"""
MM.7A — T1: F&O entry-script wiring acceptance (CONVERTED from tripwire to
acceptance by MM7E).

The MM.7 wiring review (MM7_LIVE_WIRING_REVIEW.md §0/§6 W1) found that NO
production module constructed a live `LoopDriver`. MM7E landed
`scripts/fno_runner.py` — the composition root (Design B / ADR-MM7E-1) — so the
original absence tripwires are now CONSCIOUSLY FLIPPED to their acceptance form:

1. The entry script now EXISTS and IS the runner entry point (was: assert it does
   not exist).
2. The acceptance contract (`_fno_live_contract`: Mode.LIVE, has_derivatives,
   execution present, master_readiness present, source present) is now asserted
   against the driver the PRODUCTION root actually builds (was: asserted only
   against a doubles-wired driver). The doubles-based predicate + rejection cases
   are retained as the executable spec of each clause.
"""

import sys
from datetime import date
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
# Reuse the shared runtime doubles (pytest prepends each test file's OWN dir to
# sys.path, so tests/runtime/_doubles is not otherwise importable from here).
sys.path.insert(0, str(_REPO_ROOT / "tests" / "runtime"))

from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.instrument_scope import has_derivatives
from core.instruments.master_readiness import ReadinessState, ReadinessVerdict

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      FakeSignalSource, bar_series)

_DERIV = "NSE_FO|53001"
_EQ = "NSE_EQ|INE002A01018"
_FRESH = ReadinessVerdict(ReadinessState.FRESH, None, date(2026, 6, 8), date(2026, 6, 8))


def _fno_live_contract(driver: LoopDriver) -> dict:
    """The acceptance contract the future F&O entry script must satisfy. Returns
    each clause's boolean so a test can assert all-true (acceptance) or pinpoint a
    missing clause (rejection)."""
    return {
        "mode_live": driver.config.is_live,
        "has_derivatives": has_derivatives(driver.config.symbols),
        "execution_present": driver._execution is not None,
        "master_readiness_present": driver._master_readiness is not None,
        "source_present": driver._source is not None,
    }


def _build(symbols=(_DERIV,), *, execution=True, source=True,
           master_readiness=True, mode=Mode.LIVE):
    """Construct a LoopDriver from the shared doubles, optionally omitting a
    contract clause to exercise rejection."""
    cfg = DriverConfig(mode=mode, symbols=list(symbols), max_bars=2,
                       poll_interval_s=0.25)
    return LoopDriver(
        cfg, clock=FakeClock(),
        provider=FakeMarketDataProvider({symbols[0]: bar_series(symbols[0], 3)},
                                        live=cfg.is_live),
        execution=FakeExecutionHandler(reconcile_alerts=[]) if execution else None,
        source=FakeSignalSource() if source else None,
        broker_positions=lambda: [],
        master_readiness=(lambda: _FRESH) if master_readiness else None,
    )


@pytest.fixture
def alerts(monkeypatch):
    """Silence the driver's alerter — no Telegram I/O."""
    class _Rec:
        def info(self, m): pass
        def warning(self, m): pass
        def critical(self, m): pass
    monkeypatch.setattr("core.runtime.driver.alerter", _Rec())


# --------------------------------------------------------------------------- #
# CONVERTED ACCEPTANCE (MM7E): the F&O entry script now EXISTS and IS the runner
# entry point — the two absence tripwires are consciously flipped, and the
# predicate is asserted against the driver the PRODUCTION root actually builds.
# --------------------------------------------------------------------------- #
def test_fno_entry_script_now_exists_and_builds_a_loopdriver():
    runner = _REPO_ROOT / "scripts" / "fno_runner.py"
    assert runner.exists()
    assert "LoopDriver(" in runner.read_text(encoding="utf-8")


def test_fno_runner_is_the_runner_entry_point():
    runners = sorted(p.name for p in (_REPO_ROOT / "scripts").glob("*runner*.py"))
    assert "fno_runner.py" in runners


def test_production_root_built_driver_satisfies_full_contract(alerts, tmp_path, monkeypatch):
    # The predicate converted from a doubles-only spec into the PRODUCTION root's
    # real acceptance: the driver scripts.fno_runner.build_runner builds for a live
    # F&O universe satisfies every contract clause (Mode.LIVE, has_derivatives,
    # execution, master_readiness, source).
    from _runner_harness import DERIV, NoopSource, build, make_master
    master = make_master(tmp_path)
    d = build(tmp_path, monkeypatch, source=NoopSource(), symbols=(DERIV,),
              underlyings=["NIFTY"], master_db_path=master)
    contract = _fno_live_contract(d)
    assert all(contract.values()), contract


# --------------------------------------------------------------------------- #
# ACCEPTANCE TARGET: a correctly-wired driver satisfies every contract clause AND
# actually runs end-to-end to a clean STOPPED. This is what the entry script must
# reproduce.
# --------------------------------------------------------------------------- #
def test_correctly_wired_driver_satisfies_full_contract(alerts):
    d = _build()
    contract = _fno_live_contract(d)
    assert all(contract.values()), contract


def test_correctly_wired_driver_runs_to_stopped(alerts):
    d = _build()
    d.run()
    assert d.state is RuntimeState.STOPPED
    assert d.bars_processed == 2


# --------------------------------------------------------------------------- #
# REJECTION: the predicate flags each missing clause — documenting WHAT the
# entry script must wire by showing what its absence looks like.
# --------------------------------------------------------------------------- #
def test_contract_rejects_replay_mode(alerts):
    assert _fno_live_contract(_build(mode=Mode.REPLAY))["mode_live"] is False


def test_contract_rejects_equity_only_universe(alerts):
    assert _fno_live_contract(_build(symbols=(_EQ,)))["has_derivatives"] is False


def test_contract_rejects_missing_execution(alerts):
    assert _fno_live_contract(_build(execution=False))["execution_present"] is False


def test_contract_rejects_missing_master_readiness(alerts):
    assert _fno_live_contract(_build(master_readiness=False))["master_readiness_present"] is False


def test_contract_rejects_missing_source(alerts):
    assert _fno_live_contract(_build(source=False))["source_present"] is False
