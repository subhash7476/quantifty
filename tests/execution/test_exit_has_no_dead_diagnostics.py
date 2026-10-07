"""
A closing fill must not run the MAE/MFE diagnostics path.

`_compute_exit_diagnostics` selected `intended_entry` and `entry_timestamp` from
`trade_context`, which has neither column, so every exit since it was written
logged "Exit diagnostics failed: no such column: intended_entry" and stored
mae_mfe=None. It also reads equity 1m candles, which option legs never have.
"""

from core.database.schema import TRADING_TRADE_CONTEXT_SCHEMA, TRADING_TRADES_SCHEMA
from core.events import SignalType

from test_kill_switch_exit_bypass import _build_handler, _signal


def test_closing_fill_logs_no_diagnostics_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    handler = _build_handler(tmp_path, monkeypatch)
    with handler.db_manager.trading_writer() as conn:
        conn.execute(TRADING_TRADES_SCHEMA)
        conn.execute(TRADING_TRADE_CONTEXT_SCHEMA)
    warnings = []
    monkeypatch.setattr(handler.logger, "warning", lambda msg, *a, **k: warnings.append(str(msg)))

    opened = handler.process_signal(_signal("NSE_EQ|FRESH", SignalType.BUY, "OPEN"),
                                    current_price=100.0)
    assert opened is not None
    closed = handler.process_signal(_signal("NSE_EQ|FRESH", SignalType.EXIT, "CLOSE"),
                                    current_price=101.0)
    assert closed is not None

    assert not [w for w in warnings if w.startswith("Exit diagnostics failed")]
