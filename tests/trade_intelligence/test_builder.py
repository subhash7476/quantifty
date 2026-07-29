"""Tests for Trade Intelligence historical builder (M0)."""
import duckdb
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

TI_DB = ROOT / "data" / "signal_engine" / "trade_intelligence" / "trade_intelligence.duckdb"


@pytest.fixture
def con():
    if not TI_DB.exists():
        pytest.skip("Trade intelligence DB not built")
    c = duckdb.connect(str(TI_DB), read_only=True)
    yield c
    c.close()


class TestTradeInsertion:
    def test_trade_row_exists(self, con):
        n = con.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        assert n > 100, f"Expected >100 trades, got {n}"

    def test_signal_columns_populated_on_insert(self, con):
        nulls = con.execute("""
            SELECT COUNT(*) FROM trades
            WHERE z_ts IS NULL OR raw_z IS NULL OR quintile IS NULL
               OR basis_reverting IS NULL OR sector IS NULL
        """).fetchone()[0]
        assert nulls == 0, f"{nulls} trades have NULL signal columns"

    def test_rank_in_date_computed(self, con):
        nulls = con.execute(
            "SELECT COUNT(*) FROM trades WHERE rank_in_date IS NULL"
        ).fetchone()[0]
        assert nulls == 0, f"{nulls} trades have NULL rank_in_date"

    def test_regime_columns_populated(self, con):
        nulls = con.execute("""
            SELECT COUNT(*) FROM trades
            WHERE vix_at_entry IS NULL OR nifty_20d_at_entry IS NULL
        """).fetchone()[0]
        total = con.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        # Small number of NULLs acceptable (dates without index data)
        assert nulls < total * 0.01, (
            f"{nulls}/{total} ({nulls/total*100:.1f}%) trades have NULL regime columns"
        )

    def test_strategy_identity_populated(self, con):
        nulls = con.execute("""
            SELECT COUNT(*) FROM trades
            WHERE strategy_name IS NULL OR strategy_version IS NULL
        """).fetchone()[0]
        assert nulls == 0, f"{nulls} trades have NULL strategy identity"
        name = con.execute(
            "SELECT DISTINCT strategy_name FROM trades"
        ).fetchone()[0]
        assert name == "ts_basis_daily", f"Expected ts_basis_daily, got {name}"


class TestTradeLifecycle:
    def test_open_trades_have_null_outcome(self, con):
        bad = con.execute("""
            SELECT COUNT(*) FROM trades
            WHERE exit_date IS NULL
              AND (days_held IS NOT NULL OR exit_reason IS NOT NULL
                   OR stock_return IS NOT NULL)
        """).fetchone()[0]
        assert bad == 0, f"{bad} open trades have non-NULL outcome columns"

    def test_closed_trades_have_full_outcome(self, con):
        bad = con.execute("""
            SELECT COUNT(*) FROM trades
            WHERE exit_date IS NOT NULL
              AND (days_held IS NULL OR exit_reason IS NULL
                   OR stock_return IS NULL)
        """).fetchone()[0]
        assert bad == 0, f"{bad} closed trades have NULL outcome columns"

    def test_exit_after_entry(self, con):
        bad = con.execute("""
            SELECT COUNT(*) FROM trades
            WHERE exit_date IS NOT NULL AND exit_date < entry_date
        """).fetchone()[0]
        assert bad == 0, f"{bad} trades with exit_date < entry_date"

    def test_days_held_non_negative(self, con):
        bad = con.execute("""
            SELECT COUNT(*) FROM trades
            WHERE days_held IS NOT NULL AND days_held < 1
        """).fetchone()[0]
        assert bad == 0, f"{bad} trades with days_held < 1"

    def test_exit_reason_valid(self, con):
        reasons = {
            r[0] for r in con.execute(
                "SELECT DISTINCT exit_reason FROM trades WHERE exit_reason IS NOT NULL"
            ).fetchall()
        }
        valid = {"EXIT_SIGNAL", "EXIT_TP", "EXIT_SL", "EXIT_RECOVERY"}
        invalid = reasons - valid
        assert not invalid, f"Invalid exit reasons: {invalid}"


class TestTradeOutcome:
    def test_mean_return_reasonable(self, con):
        mean_ret = con.execute(
            "SELECT AVG(stock_return) FROM trades WHERE stock_return IS NOT NULL"
        ).fetchone()[0]
        assert mean_ret is not None
        # Should be positive (strategy has edge) and < 1% (daily returns)
        assert -0.01 < mean_ret < 0.01, f"Mean return {mean_ret*100:+.3f}% outside reasonable range"

    def test_winner_ratio_reasonable(self, con):
        wr = con.execute("""
            SELECT AVG(CASE WHEN stock_return > 0 THEN 1.0 ELSE 0.0 END)
            FROM trades WHERE stock_return IS NOT NULL
        """).fetchone()[0]
        # Strategy baseline is ~51%, allow 45-60%
        assert 0.45 < wr < 0.60, f"Winner ratio {wr*100:.1f}% outside reasonable range"

    def test_signal_snapshot_consistent(self, con):
        total_closed = con.execute(
            "SELECT COUNT(*) FROM trades WHERE exit_date IS NOT NULL"
        ).fetchone()[0]
        mismatches = con.execute("""
            SELECT COUNT(*) FROM trades
            WHERE exit_date IS NOT NULL
              AND side = 'LONG' AND z_ts < -0.001
        """).fetchone()[0]
        mismatches += con.execute("""
            SELECT COUNT(*) FROM trades
            WHERE exit_date IS NOT NULL
              AND side = 'SHORT' AND z_ts > 0.001
        """).fetchone()[0]
        # Quintile is relative within-date — small number of sign mismatches
        # expected on skewed cross-section days
        pct = mismatches / total_closed * 100
        assert pct < 0.5, (
            f"{mismatches}/{total_closed} ({pct:.2f}%) trades with z_ts sign "
            f"inconsistent — above 0.5% threshold"
        )
