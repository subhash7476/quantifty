"""
MM.7A — T1: F&O entry-script wiring acceptance + current-absence characterization.

The MM.7 wiring review (MM7_LIVE_WIRING_REVIEW.md §0/§6 W1) found that NO
production module constructs a live `LoopDriver` — it is built only in tests, and
there is no production `SignalSource` to inject. This file does two things:

1. Documents the current absence (the G1 closeout audit's call-graph finding:
   "no live LoopDriver is constructed outside tests/"). The absence test is a
   tripwire — it goes RED the moment an F&O entry script lands in scripts/, at
   which point the contract predicate below becomes that script's real acceptance
   check.
2. Pins the acceptance contract the future entry script MUST satisfy as an
   executable predicate (`_fno_live_contract`): Mode.LIVE, has_derivatives,
   execution present, master_readiness present, source present — demonstrated
   GREEN against a correctly-wired driver built from the shared test doubles, and
   shown to REJECT each missing piece.

No entry script, no SignalSource, no production code is created here.
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
# CURRENT ABSENCE: no production module under scripts/ constructs a live
# LoopDriver. Tripwire — flips when the F&O entry script lands.
# --------------------------------------------------------------------------- #
def test_no_scripts_module_constructs_a_loopdriver():
    offenders = [
        p.relative_to(_REPO_ROOT).as_posix()
        for p in (_REPO_ROOT / "scripts").glob("*.py")
        if "LoopDriver(" in p.read_text(encoding="utf-8")
    ]
    assert offenders == [], (
        f"F&O entry script may now exist ({offenders}) — convert "
        "_fno_live_contract into its real acceptance assertion (MM.7A T1)."
    )


def test_no_runner_script_exists_yet():
    # The MM.7 review's W1: there is no scripts/*runner*/trade-loop entry point.
    runners = sorted(p.name for p in (_REPO_ROOT / "scripts").glob("*runner*.py"))
    assert runners == []


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
