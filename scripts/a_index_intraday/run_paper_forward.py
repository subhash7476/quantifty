"""A — forward PAPER runner for the frozen w45 family book.

Validates the RETIRED construct forward per the operator-commissioned record
(A_HOLDOUT_CLOSURE.md §forward paper run): ≥ 3 months of forward sessions,
trades recorded through Trade Intelligence, then a decision to retire
permanently. **Not a path back to SEALED; not a resurrection mechanism.**

Frozen book (A_PHASE0_PRE_REGISTRATION.md, D1-D6):
  - w45 window: opening print (09:15 bar open) -> 10:00 bar close (feature),
    entry at the 10:01 bar OPEN, exit at the 15:14 bar CLOSE
  - sign pinned +1 continuation; one position per session; Rs 2Cr canonical
    notional; EOD flat
  - fills at ACTUAL live-bar prices (the backtest's slippage lanes do not
    apply to paper fills); era-accurate futures fees at fills; basis mean
    report-only, basis dispersion a standing caveat (D5)
  - no parameter edits, no early abort on eyeballed P&L; any discretionary
    change restarts the 3-month clock and is logged in the trial ledger

Fills route through the execution fill seam (`_handle_broker_fill`) with a
registered order, so position tracking, the universal TradeRecorder (TI v2),
and the TLP trade save all fire. Restart-safe: session state is persisted
and re-injected fills are idempotent in the recorder.

Usage: python scripts/a_index_intraday/run_paper_forward.py [--dry-run]
"""
from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import scripts.a_index_intraday.common as cm  # noqa: E402
from core.database.manager import DatabaseManager  # noqa: E402
from core.database.queries import MarketDataQuery  # noqa: E402
from core.clock import ReplayClock  # noqa: E402
from core.brokers.paper_broker import PaperBroker  # noqa: E402
from core.execution.handler import ExecutionHandler, ExecutionConfig, \
    ExecutionMode  # noqa: E402
from core.execution.order_models import NormalizedOrder, OrderSide, OrderType  # noqa: E402
from core.execution.order_lifecycle import FillEvent  # noqa: E402
from core.database.utils.market_hours import MarketHours  # noqa: E402
from core.execution.futures.futures_fees import (  # noqa: E402
    brokerage_flat, exchange_txn_rate, gst_rate, stamp_duty_rate,
    stt_futures_rate, SEBI_FEE_RATE,
)

_logger = logging.getLogger("a_paper_forward")

NF = "NSE_INDEX|Nifty 50"
CANONICAL = 20_000_000.0
STRATEGY_ID = "A_W45_PAPER"
POLL_INTERVAL_S = 30
ENTRY_MINUTE = 46          # bar index from the opening print (10:01 native label)
WINDOW_END_MINUTE = 45     # bar index of the window-end close (10:00 native label)
EXIT_HHMM = "15:14"
ENTRY_TIMEOUT = dtime(10, 35)   # no entry bar by then -> session skipped (logged)
EXIT_TIMEOUT = dtime(15, 25)    # no 15:14 bar by then -> emergency exit at last bar
STATE_FILE = ROOT / "data" / "a_index_intraday" / "paper_state.json"
LEDGER = ROOT / "data" / "a_index_intraday" / "trial_ledger.jsonl"
PAPER_DB = ROOT / "data" / "a_index_intraday" / "paper_trades.duckdb"


# --------------------------------------------------------------------------- pure

def leg_fee_rs(side: str, trade_value: float, d: date) -> float:
    """One leg's era-accurate futures fees in Rs at `trade_value` notional."""
    g = gst_rate(d)
    br = brokerage_flat(trade_value)
    stt = trade_value * stt_futures_rate(d) if side == "SELL" else 0.0
    txn = trade_value * exchange_txn_rate(d)
    sebi = trade_value * SEBI_FEE_RATE
    stamp = trade_value * stamp_duty_rate(d) if side == "BUY" else 0.0
    gst = g * (br + txn + sebi)
    return br + stt + txn + sebi + stamp + gst


def decide(open_price: float, window_end_close: float,
           entry_open: float) -> tuple:
    """Frozen decision: (side, qty). side in {'BUY','SELL'}; None if flat."""
    if open_price <= 0 or window_end_close <= 0 or entry_open <= 0:
        return None, 0
    feature = (window_end_close - open_price) / open_price
    if feature == 0.0:
        return None, 0
    side = "BUY" if feature > 0 else "SELL"
    qty = int(CANONICAL / entry_open) or 1
    return side, qty


def session_record(d: date, side, entry_price, exit_price, qty,
                   entry_fee_rs, exit_fee_rs) -> dict:
    """Per-session bookkeeping: gross/net bp, fees bp, era."""
    era = cm.era_of(d)
    sign = 1.0 if side == "BUY" else -1.0
    gross_bp = sign * (exit_price - entry_price) / entry_price * 1e4
    fee_bp = (entry_fee_rs + exit_fee_rs) / (qty * entry_price) * 1e4
    return {"date": d.isoformat(), "side": side, "era": era,
            "entry_price": entry_price, "exit_price": exit_price, "qty": qty,
            "entry_fee_rs": entry_fee_rs, "exit_fee_rs": exit_fee_rs,
            "gross_bp": gross_bp, "fee_bp": fee_bp,
            "net_bp": gross_bp - fee_bp}


# ----------------------------------------------------------------------- runner

def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_state(state: dict):
    if state.get("_dry_run"):
        return
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state), encoding="utf-8")


def _bars_of(query, d: date) -> list:
    """Today's live 1m bars for the index (live buffer), ordered by time."""
    df = query.get_ohlcv(NF, start_time=datetime.combine(d, dtime(9, 0)),
                         timeframe="1m")
    if df is None or df.empty:
        return []
    out = []
    for _, row in df.iterrows():
        out.append({
            "ts": row["timestamp"],
            "open": float(row["open"]), "close": float(row["close"]),
        })
    out.sort(key=lambda b: b["ts"])
    return out


def _bar_at(bars, hhmm: str):
    for b in bars:
        if b["ts"].time().strftime("%H:%M") == hhmm:
            return b
    return None


class ForwardRunner:
    def __init__(self, execution, query, dry_run: bool = False):
        self.execution = execution
        self.query = query
        self.dry_run = dry_run

    def inject_fill(self, side: str, price: float, qty: int, ts: datetime,
                    fee_rs: float, tag: str) -> FillEvent:
        signal_id = f"{ts.date().isoformat()}_{tag}"
        order = NormalizedOrder(
            symbol=NF, side=OrderSide(side), quantity=qty,
            order_type=OrderType.MARKET, strategy_id=STRATEGY_ID,
            signal_id=signal_id, timestamp=ts,
        )
        fill = FillEvent(
            fill_id=str(uuid.uuid4()), order_id=str(order.correlation_id),
            symbol=NF, quantity=qty, price=price, timestamp=ts,
            side=side, fee=fee_rs,
        )
        if self.dry_run:
            _logger.info("DRY-RUN fill: %s %d @ %.2f fee=%.2f (%s)",
                         side, qty, price, fee_rs, tag)
            return fill
        self.execution.order_tracker.add_order(order)
        self.execution._handle_broker_fill(fill)
        _logger.info("fill: %s %d @ %.2f fee=%.2f (%s) fill_id=%s",
                     side, qty, price, fee_rs, tag, fill.fill_id)
        return fill

    def run_session(self, d: date):
        st = _load_state()
        if self.dry_run:
            st = {"date": d.isoformat(), "state": "WAIT_OPEN",
                  "_dry_run": True}
        if st.get("date") == d.isoformat() and st.get("state") == "DONE":
            return
        if st.get("date") != d.isoformat():
            st = {"date": d.isoformat(), "state": "WAIT_OPEN"}
            _save_state(st)

        bars = _bars_of(self.query, d)
        first = bars[0] if bars else None
        now = datetime.now()

        if st["state"] == "WAIT_OPEN":
            if first is None or first["ts"].time().strftime("%H:%M") != "09:15":
                if now.time() > ENTRY_TIMEOUT:
                    self._log_session(d, note="skipped: no opening print")
                    st["state"] = "DONE"
                    _save_state(st)
                return
            entry_bar = _bar_at(bars, "10:01")
            if entry_bar is None:
                if now.time() > ENTRY_TIMEOUT:
                    self._log_session(d, note="skipped: no entry bar")
                    st["state"] = "DONE"
                    _save_state(st)
                return
            window_bar = _bar_at(bars, "10:00")
            if window_bar is None:
                return
            side, qty = decide(first["open"], window_bar["close"],
                               entry_bar["open"])
            if side is None:
                self._log_session(d, note="flat (feature == 0)")
                st["state"] = "DONE"
                _save_state(st)
                return
            fee = leg_fee_rs(side, qty * entry_bar["open"], d)
            fill = self.inject_fill(side, entry_bar["open"], qty,
                                    datetime.combine(d, dtime(10, 1)), fee,
                                    "entry")
            st.update({"state": "HOLDING", "side": side, "qty": qty,
                       "entry_price": entry_bar["open"],
                       "entry_fee_rs": fee, "entry_fill_id": fill.fill_id,
                       "entry_ts": fill.timestamp.isoformat()})
            _save_state(st)

        if st["state"] == "HOLDING":
            exit_bar = _bar_at(bars, EXIT_HHMM)
            if exit_bar is None:
                if now.time() > EXIT_TIMEOUT:
                    last = bars[-1]
                    _logger.warning("emergency exit at last bar %s",
                                    last["ts"])
                    self._exit(st, d, last["close"], last["ts"],
                               note="emergency: no 15:14 bar")
                    st["state"] = "DONE"
                    _save_state(st)
                return
            self._exit(st, d, exit_bar["close"],
                       datetime.combine(d, dtime(15, 14)), note=None)
            st["state"] = "DONE"
            _save_state(st)

    def _exit(self, st: dict, d: date, price: float, ts: datetime, note):
        side = "SELL" if st["side"] == "BUY" else "BUY"
        fee = leg_fee_rs(side, st["qty"] * price, d)
        self.inject_fill(side, price, st["qty"], ts, fee, "exit")
        rec = session_record(d, st["side"], st["entry_price"], price,
                             st["qty"], st["entry_fee_rs"], fee)
        rec["note"] = note
        self._write_record(rec)

    def _write_record(self, rec: dict):
        if self.dry_run:
            _logger.info("DRY-RUN session record suppressed (no write): %s",
                         rec.get("note") or rec.get("date"))
            return
        import duckdb
        PAPER_DB.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(str(PAPER_DB))
        con.execute(
            "CREATE TABLE IF NOT EXISTS paper_sessions (date VARCHAR, side "
            "VARCHAR, era VARCHAR, entry_price DOUBLE, exit_price DOUBLE, "
            "qty BIGINT, entry_fee_rs DOUBLE, exit_fee_rs DOUBLE, gross_bp "
            "DOUBLE, fee_bp DOUBLE, net_bp DOUBLE, note VARCHAR)")
        con.execute(
            "INSERT INTO paper_sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [rec["date"], rec.get("side"), rec["era"], rec["entry_price"],
             rec["exit_price"], rec["qty"], rec["entry_fee_rs"],
             rec["exit_fee_rs"], rec["gross_bp"], rec["fee_bp"],
             rec["net_bp"], rec.get("note")])
        con.close()
        with open(LEDGER, "a", encoding="utf-8") as lf:
            lf.write(json.dumps({"event": "paper_session", "run_id": run_id,
                                 **rec}) + "\n")
        _logger.info("paper session %s: %s gross %.2f bp net %.2f bp%s",
                     rec["date"], rec.get("side"), rec["gross_bp"],
                     rec["net_bp"],
                     f" ({rec['note']})" if rec.get("note") else "")

    def _log_session(self, d: date, note: str):
        rec = {"date": d.isoformat(), "side": None, "era": cm.era_of(d),
               "entry_price": None, "exit_price": None, "qty": 0,
               "entry_fee_rs": 0.0, "exit_fee_rs": 0.0, "gross_bp": None,
               "fee_bp": None, "net_bp": None, "note": note}
        self._write_record(rec)


run_id = ""


def main() -> int:
    global run_id
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    dry_run = "--dry-run" in sys.argv
    import subprocess
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        commit = "unknown"
    run_id = f"a-paper-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    print("=" * 72)
    print("A — forward PAPER runner (frozen w45 family book)")
    print(f"run_id={run_id} commit={commit} dry_run={dry_run}")
    print(f"book: sign=+1 window=0..45 entry=10:01 exit=15:14 "
          f"notional=Rs{CANONICAL:,.0f} strategy={STRATEGY_ID}")
    print("TI recording: trade_intelligence.duckdb via the execution fill seam")
    print("=" * 72)

    with open(LEDGER, "a", encoding="utf-8") as lf:
        lf.write(json.dumps({"event": "run_start", "run_id": run_id,
                             "gate": "PAPER_FORWARD", "strategy": STRATEGY_ID,
                             "commit": commit, "dry_run": dry_run,
                             "prereg_sha": cm.PREREG_SHA,
                             "frozen_book": {"sign": 1, "window_bars": 46,
                                             "entry_bar": 46, "exit": "15:14",
                                             "notional": CANONICAL}})
                 + "\n")

    clock = ReplayClock(start_time=datetime.combine(date.today(), dtime(9, 0)))
    db_manager = DatabaseManager(data_root="data", read_only=False)
    # TLP v1: the trading ledger (data/trading/trading.db) is bootstrapped by
    # the app entry points, not by a bare DatabaseManager — create the schema
    # so the fill seam's trade save works for the paper run (idempotent).
    from core.database.schema import (  # noqa: E402
        TRADING_TRADES_SCHEMA, TRADING_TRADE_CONTEXT_SCHEMA)
    with db_manager.trading_writer() as tconn:
        tconn.execute(TRADING_TRADES_SCHEMA)
        tconn.execute(TRADING_TRADE_CONTEXT_SCHEMA)
    broker = PaperBroker(clock=clock)
    execution = ExecutionHandler(
        db_manager=db_manager, clock=clock, broker=broker,
        config=ExecutionConfig(mode=ExecutionMode.PAPER),
        initial_capital=CANONICAL, load_db_state=False,
    )
    query = MarketDataQuery(db_manager)
    runner = ForwardRunner(execution, query, dry_run=dry_run)

    try:
        while True:
            today = date.today()
            if MarketHours.is_trading_day(
                    datetime.combine(today, dtime(12, 0))):
                runner.run_session(today)
                now = datetime.now()
                if now.time() < dtime(15, 35):
                    time.sleep(POLL_INTERVAL_S)
                else:
                    time.sleep(600)
            else:
                _logger.info("non-trading day %s — sleeping", today)
                time.sleep(3600)
    except KeyboardInterrupt:
        print("\nstopped cleanly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
