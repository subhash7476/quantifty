"""
Backtest Facade
---------------
Bridge between Flask UI and the LoopDriver replay backtest engine.
Runs backtests asynchronously, returns trades and metrics.
"""
import os
import sys
import threading
import traceback
import uuid
from datetime import date, datetime, timedelta, time
from pathlib import Path
from typing import Any

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data")).resolve()
sys.path.insert(0, str(DATA_ROOT.parent.resolve()))


class BacktestFacade:
    _running_jobs: dict[str, dict] = {}
    _results: dict[str, dict] = {}
    _lock = threading.Lock()

    STRATEGIES = [
        {
            "id": "carry",
            "name": "Carry",
            "description": "Cross-sectional residual futures basis — short high carry, long low carry",
            "asset_class": "futures",
            "default_start": "2016-03-31",
            "default_end": (date.today() - timedelta(days=1)).isoformat(),
        },
    ]

    def list_strategies(self) -> list[dict]:
        return self.STRATEGIES

    def get_futures_symbols(self) -> list[str]:
        try:
            import duckdb
            db = DATA_ROOT / "market_data" / "futures_bhavcopy.duckdb"
            if not db.exists():
                return []
            conn = duckdb.connect(str(db), read_only=True)
            rows = conn.execute(
                "SELECT DISTINCT underlying FROM futures_bhavcopy WHERE inst_type='FUTSTK' ORDER BY underlying"
            ).fetchall()
            conn.close()
            return [r[0] for r in rows]
        except Exception:
            return []

    def run_backtest(self, strategy_id: str, start_date: str, end_date: str,
                     params: dict | None = None) -> dict:
        job_id = str(uuid.uuid4())[:8]

        job = {
            "job_id": job_id,
            "strategy_id": strategy_id,
            "status": "running",
            "started": datetime.now().isoformat(),
            "progress": 0,
        }

        with self._lock:
            self._running_jobs[job_id] = job

        threading.Thread(
            target=self._run_backtest_thread,
            args=(job_id, strategy_id, start_date, end_date, params or {}),
            daemon=True,
        ).start()

        return job

    def get_job_status(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._running_jobs.get(job_id)
            result = self._results.get(job_id)
            if result:
                return {"status": "completed", "result": result}
            if job:
                return job
            return None

    def _run_backtest_thread(self, job_id: str, strategy_id: str,
                              start_date: str, end_date: str, params: dict):
        lo = date.fromisoformat(start_date)
        hi = date.fromisoformat(end_date)
        strategy_name = "carry"

        try:
            result = self._run_replay(strategy_name, lo, hi)
            with self._lock:
                self._results[job_id] = result
                if job_id in self._running_jobs:
                    del self._running_jobs[job_id]
        except Exception as e:
            with self._lock:
                self._results[job_id] = {
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
                if job_id in self._running_jobs:
                    del self._running_jobs[job_id]

    def _run_replay(self, strategy_name: str, lo: date, hi: date) -> dict:
        from core.database.providers.daily_bhavcopy import DailyBhavcopyProvider
        from core.runtime.config import DriverConfig, Mode
        from core.runtime.driver import LoopDriver
        from core.clock import ReplayClock
        from core.execution.handler import ExecutionHandler
        from core.execution.handler import ExecutionConfig, ExecutionMode
        from core.brokers.paper_broker import PaperBroker
        from core.database.manager import DatabaseManager

        symbols = self.get_futures_symbols()
        if not symbols:
            return {"error": "No futures symbols found"}

        FUT_DB = DATA_ROOT / "market_data" / "futures_bhavcopy.duckdb"
        FACTS_DB = DATA_ROOT / "signal_engine" / "carry" / "facts.duckdb"

        provider = DailyBhavcopyProvider(
            underlyings=symbols,
            bhavcopy_db=str(FUT_DB),
            start_date=lo,
            end_date=hi,
        )

        clock = ReplayClock(start_time=datetime.combine(lo, time.min))
        db_manager = DatabaseManager(data_root="data", read_only=True)
        broker = PaperBroker(clock=clock)

        exec_config = ExecutionConfig(
            mode=ExecutionMode.DRY_RUN,
            default_quantity=1.0,
            max_position_size=float("inf"),
            slippage_model="fixed",
            slippage_value=0.0005,
        )

        execution = ExecutionHandler(
            db_manager=db_manager,
            clock=clock,
            broker=broker,
            config=exec_config,
            initial_capital=10_000_000,
            load_db_state=False,
        )

        from scripts.signal_engine.carry.replay_parity_check import ParityRebalancerHook, RebalanceRecord

        captured_fills: list = []

        class RecordingParityHook(ParityRebalancerHook):
            def _build_fill(self, underlying, side, trade_val, trade_date, ts):
                fill = super()._build_fill(underlying, side, trade_val, trade_date, ts)
                captured_fills.append({
                    "symbol": fill.symbol,
                    "side": fill.side,
                    "quantity": int(fill.quantity),
                    "price": float(fill.price),
                    "fees": float(fill.fee),
                    "timestamp": str(ts),
                    "pnl": 0.0,  # realized at close
                })
                return fill

        records: list = []

        hook = RecordingParityHook(
            facts_db_path=str(FACTS_DB),
            execution_handler=execution,
            bhavcopy_db_path=str(FUT_DB),
            records=records,
        )

        driver_config = DriverConfig(
            mode=Mode.REPLAY,
            symbols=symbols,
            max_bars=500_000,
        )

        driver = LoopDriver(
            config=driver_config,
            clock=clock,
            provider=provider,
            source=None,
            execution=execution,
            rebalance_hook=hook.__call__,
        )

        driver.run()

        trades = captured_fills
        total_fees = sum(t["fees"] for t in trades)
        total_volume = sum(abs(t["quantity"]) * t["price"] for t in trades) if trades else 0
        rebalance_count = len(records)

        # Extract per-symbol PnL from positions if available
        pos_pnl = 0.0
        try:
            for sym, pos in execution.position_tracker.get_all_positions().items():
                pos_pnl += getattr(pos, "realized_pnl", 0.0) or 0.0
        except Exception:
            pass

        metrics = {
            "total_trades": len(trades),
            "total_fees": round(total_fees, 2),
            "total_volume": round(total_volume, 2),
            "rebalance_count": rebalance_count,
            "date_range": f"{lo} -> {hi}",
            "symbols_count": len(symbols),
        }

        return {"metrics": metrics, "trades": trades}
