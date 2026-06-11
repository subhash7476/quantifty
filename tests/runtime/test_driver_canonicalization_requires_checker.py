"""
MM.7A — W4 characterization: the master-readiness checker is the activation
switch for the G1 restore-canonicalization pass, not just the readiness gate.

`LoopDriver._canonicalize_restored_ledger` gates on the SAME condition as MM.4 —
`is_live ∧ has_derivatives(symbols) ∧ master_readiness is not None`
(driver.py:439-444). So omitting the checker silently disables BOTH halves of the
G1 restore canonicalization (positions #7-as-restored + orders #8) that the
identity-architecture program just closed — the restored ledger stays legacy-typed
on a live F&O run (MM7_LIVE_WIRING_REVIEW.md finding W4).

These tests pin that coupling end-to-end, driving the gate with the REAL
resolver-backed `build_master_readiness(...)` factory (not a hand-written verdict
lambda): WITHOUT a checker the pass never fires; WITH the real factory it fires
once for each half. The carve-out tests pin that the checker alone is NOT
sufficient — REPLAY and equity-only universes still skip canonicalization even
when a checker is injected. No runtime code is modified.

The canonicalization calls themselves are recorded by the FakeExecutionHandler
(`canonicalize_calls` / `canonicalize_order_calls`), mirroring the real
ExecutionHandler.canonicalize_restored_{positions,orders} the driver triggers.
"""

import pytest

from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.event_journal import RuntimeEventJournal

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      bar_series)

_DERIV = "NSE_FO|53001"
_EQ = "NSE_EQ|INE002A01018"


@pytest.fixture
def alerts(monkeypatch):
    """Silence the driver's alerter — no Telegram I/O."""
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


@pytest.fixture
def real_checker(tmp_path):
    """The production resolver-backed checker over a freshly-materialized master
    fixture (today's snapshot → FRESH). Mirrors the MM.7 integration fixture
    (test_driver_master_readiness.py) so the gate is driven by the real factory,
    not a verdict lambda."""
    from scripts.fetch_instrument_master import parse_instruments, write_snapshot
    from core.instruments.master_readiness import build_master_readiness
    from core.instruments.master_freshness import expected_snapshot_date
    from core.database.utils.market_hours import MarketHours

    today = expected_snapshot_date(MarketHours.get_ist_now()).isoformat()
    master = tmp_path / "instruments.duckdb"
    write_snapshot(parse_instruments([
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|53001", "tradingsymbol": "NIFTYFUT",
         "name": "NIFTY", "expiry": "2027-12-31", "instrument_type": "FUT",
         "lot_size": 75, "tick_size": 0.05},
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|54710", "tradingsymbol": "NIFTYCE",
         "name": "NIFTY", "expiry": "2027-12-31", "strike_price": 22500.0,
         "instrument_type": "CE", "lot_size": 75, "tick_size": 0.05},
    ], today), db_path=master)
    return build_master_readiness(["NIFTY"], db_path=master)


def _driver(tmp_path, symbols, master_readiness, mode=Mode.LIVE):
    cfg = DriverConfig(mode=mode, symbols=list(symbols), max_bars=2,
                       poll_interval_s=0.25)
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler(reconcile_alerts=[])
    d = LoopDriver(
        cfg, clock=FakeClock(),
        provider=FakeMarketDataProvider({symbols[0]: bar_series(symbols[0], 3)},
                                        live=cfg.is_live),
        journal=journal, execution=handler,
        broker_positions=lambda: [],
        master_readiness=master_readiness,
    )
    return d, handler


# --------------------------------------------------------------------------- #
# WITHOUT a checker: the restore canonicalization pass never activates (vacuous),
# even on a LIVE + derivative run.
# --------------------------------------------------------------------------- #
def test_canonicalization_inactive_without_checker(tmp_path, alerts):
    d, handler = _driver(tmp_path, [_DERIV], None)
    d.run()
    assert d.state is RuntimeState.STOPPED and d.bars_processed == 2
    assert handler.canonicalize_calls == 0
    assert handler.canonicalize_order_calls == 0


# --------------------------------------------------------------------------- #
# WITH the real build_master_readiness(...) factory: both halves activate once.
# --------------------------------------------------------------------------- #
def test_canonicalization_active_with_real_factory(tmp_path, alerts, real_checker):
    d, handler = _driver(tmp_path, [_DERIV], real_checker)
    d.run()
    assert d.state is RuntimeState.STOPPED and d.bars_processed == 2
    # The checker is the activation switch: positions (#7-as-restored) + orders (#8).
    assert handler.canonicalize_calls == 1
    assert handler.canonicalize_order_calls == 1


# --------------------------------------------------------------------------- #
# The checker alone is NOT sufficient — REPLAY skips canonicalization even with a
# real checker injected (staleness/identity gate is a live concept).
# --------------------------------------------------------------------------- #
def test_canonicalization_inactive_in_replay_with_checker(tmp_path, alerts, real_checker):
    d, handler = _driver(tmp_path, [_DERIV], real_checker, mode=Mode.REPLAY)
    d.run()
    assert d.state is RuntimeState.STOPPED and d.bars_processed == 2
    assert handler.canonicalize_calls == 0
    assert handler.canonicalize_order_calls == 0


# --------------------------------------------------------------------------- #
# The checker alone is NOT sufficient — an equity-only universe skips
# canonicalization even on LIVE with a real checker (has_derivatives is False).
# --------------------------------------------------------------------------- #
def test_canonicalization_inactive_equity_only_with_checker(tmp_path, alerts, real_checker):
    d, handler = _driver(tmp_path, [_EQ], real_checker)
    d.run()
    assert d.state is RuntimeState.STOPPED and d.bars_processed == 2
    assert handler.canonicalize_calls == 0
    assert handler.canonicalize_order_calls == 0
