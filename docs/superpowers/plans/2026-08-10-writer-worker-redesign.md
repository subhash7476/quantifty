# Writer-Worker Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the three linked ingestion faults (F1/F3/F4) from the 2026-08-10 shakedown with one architecture: a single `LiveBufferWriter` worker thread that is the sole read-write owner of the live buffer during the live session.

**Architecture:** The asyncio WS handler enqueues raw protobuf frames only (no parse, no DB) — closing the event-loop starvation (F3). A dedicated worker thread drains a bounded queue and performs short-lived, per-file open→write→close cycles for tick-append, candle aggregation, recovery, and purge — so cross-process readers of `candles_today.duckdb` get open windows via bounded retry (F4). The WS connects first and recovery runs asynchronously, feeding the same queue (F1).

**Tech Stack:** Python 3.10+, DuckDB, `websockets`, protobuf (`MarketDataFeedV3_pb2`), `queue.Queue`, `threading`. Tests: pytest.

**Design spec:** `docs/superpowers/specs/2026-08-10-writer-worker-redesign-design.md` (read it first).

## Global Constraints

- **Single-writer invariant (live session only):** within the live `market_ingestor` process, only the `LiveBufferWriter` worker thread opens `ticks_today.duckdb` / `candles_today.duckdb` read-write. Offline callers in other processes (`core/database/writers.py::MarketDataWriter`, `scripts/fetch_upstox_historical.py`) run when the ingestor is not live and are **out of scope** — leave them and `DatabaseManager.live_buffer_writer()` untouched.
- **No live-buffer write on the asyncio loop.** `_handle_message` must not parse protobuf, convert timestamps, or open any DB.
- **Short-lived writes only:** no live-buffer RW open may span more than one small chunk (one coalesced tick batch, or one symbol's candle write). Never one hold for the whole ~200-symbol batch.
- **Per-file narrowing:** the tick path opens `ticks` only; the candle/aggregate/recovery paths open `candles` only. Only `Purge` opens both.
- **Reader retry template:** the bounded-retry pattern is already committed in `core/execution/options/nifty_shield_marks.py::ChainSnapshotMarksSource._connect` — reuse its shape (retry small bounded count on a transient "used by another process" / "Conflicting lock" / "Cannot open file" error; raise after the bound).
- **Backpressure = drop-oldest tick frames** (operator decision). `Aggregate`/`RecoverBars`/`Purge` are never dropped.
- **Shutdown drains** buffered ticks before exit.
- **Naming:** timestamps stored naive IST (matches today). Candle precedence unchanged: recovery `INSERT OR IGNORE ... is_synthetic=TRUE`, aggregator `ON CONFLICT DO UPDATE ... is_synthetic=FALSE`.
- **Conventions:** no docstrings/comments on code you didn't change; delete dead code fully; read a file before editing it.

## File Structure

| File | Responsibility |
|---|---|
| `core/database/manager.py` (modify) | Add `bootstrap_live_buffer()`, `live_ticks_writer()`, `live_candles_writer()` (narrow, DDL-free, short-lived). Add bounded retry to `live_buffer_reader()` candles open. |
| `core/database/ingestors/live_buffer_writer.py` (**new**) | Worker thread + bounded queue + command types. Sole RW owner. Parses frames, coalesces tick batches, dispatches Aggregate/RecoverBars/Purge. |
| `core/database/ingestors/db_tick_aggregator.py` (modify) | Aggregation reshaped to write one symbol at a time via `live_candles_writer()`, invoked by the worker. |
| `core/database/ingestors/websocket_ingestor.py` (modify) | Remove `TickBuffer`; `_handle_message` enqueues raw frames; hoist tz to module level; set explicit ping params. |
| `core/database/ingestors/recovery_manager.py` (modify) | Enqueue recovered bars to the worker instead of a direct `live_buffer_writer()` write. |
| `scripts/market_ingestor.py` (modify) | Own the worker lifecycle; connect-then-async-backfill; post periodic `Aggregate`; route purge through the worker; drain on stop. |
| `tests/database/ingestors/` (**new dir**) | Unit + integration tests per task. |

---

### Task 1: Narrow live-buffer access + reader retry + DDL-once (`manager.py`)

**Files:**
- Modify: `core/database/manager.py` (live-buffer section, ~lines 222-272)
- Test: `tests/database/ingestors/test_manager_live_buffer.py` (create)

**Interfaces:**
- Produces:
  - `DatabaseManager.bootstrap_live_buffer() -> None` — runs `MARKET_TICKS_SCHEMA` on `ticks_today.duckdb` and `MARKET_CANDLES_SCHEMA` on `candles_today.duckdb` once.
  - `DatabaseManager.live_ticks_writer()` — context manager yielding one RW `duckdb` connection to `ticks_today.duckdb`, no DDL.
  - `DatabaseManager.live_candles_writer()` — context manager yielding one RW `duckdb` connection to `candles_today.duckdb`, no DDL.
  - `DatabaseManager.live_buffer_reader()` — unchanged signature; candles open now bounded-retries on transient collision.

- [ ] **Step 1: Write the failing test**

```python
# tests/database/ingestors/test_manager_live_buffer.py
import duckdb, pytest
from pathlib import Path
from core.database.manager import DatabaseManager

def _mk(tmp_path) -> DatabaseManager:
    return DatabaseManager(tmp_path, read_only=False)

def test_bootstrap_creates_tick_and_candle_tables(tmp_path):
    db = _mk(tmp_path)
    db.bootstrap_live_buffer()
    tconn = duckdb.connect(str(tmp_path / "live_buffer" / "ticks_today.duckdb"), read_only=True)
    assert tconn.execute("SELECT count(*) FROM ticks").fetchone()[0] == 0
    tconn.close()
    cconn = duckdb.connect(str(tmp_path / "live_buffer" / "candles_today.duckdb"), read_only=True)
    assert cconn.execute("SELECT count(*) FROM candles").fetchone()[0] == 0
    cconn.close()

def test_ticks_writer_opens_ticks_only(tmp_path):
    db = _mk(tmp_path)
    db.bootstrap_live_buffer()
    with db.live_ticks_writer() as conn:
        conn.execute("INSERT INTO ticks (symbol, timestamp, price, volume) VALUES ('X', now(), 1.0, 1)")
    # candles file must remain openable RW by another connection immediately (not held)
    c = duckdb.connect(str(tmp_path / "live_buffer" / "candles_today.duckdb"), read_only=False)
    c.close()

def test_reader_retries_transient_then_returns(tmp_path, monkeypatch):
    db = _mk(tmp_path)
    db.bootstrap_live_buffer()
    calls = {"n": 0}
    real_connect = db._duckdb_connect
    def flaky(path, read_only=False):
        if "candles_today" in str(path) and read_only and calls["n"] < 2:
            calls["n"] += 1
            raise duckdb.IOException("Cannot open file: being used by another process")
        return real_connect(path, read_only=read_only)
    monkeypatch.setattr(db, "_duckdb_connect", flaky)
    with db.live_buffer_reader() as conns:
        assert "candles" in conns
    assert calls["n"] == 2  # retried twice, then succeeded
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/database/ingestors/test_manager_live_buffer.py -v`
Expected: FAIL — `AttributeError: 'DatabaseManager' object has no attribute 'bootstrap_live_buffer'`.

- [ ] **Step 3: Implement the manager changes**

In `core/database/manager.py`, add after `live_buffer_reader()` (keep `live_buffer_writer()` as-is for offline callers). Add near the top of the live-buffer section:

```python
    _LIVE_READ_RETRIES = 5
    _LIVE_READ_RETRY_DELAY_S = 0.05

    def _live_paths(self):
        base = self.data_root / 'live_buffer'
        base.mkdir(parents=True, exist_ok=True)
        return base / 'ticks_today.duckdb', base / 'candles_today.duckdb'

    def bootstrap_live_buffer(self) -> None:
        self._check_duckdb_write_permission()
        from core.database.schema import MARKET_TICKS_SCHEMA, MARKET_CANDLES_SCHEMA
        ticks_path, candles_path = self._live_paths()
        with self._get_thread_lock('live_buffer'):
            tc = self._duckdb_connect(ticks_path, read_only=False)
            try:
                tc.execute(MARKET_TICKS_SCHEMA)
            finally:
                tc.close()
            cc = self._duckdb_connect(candles_path, read_only=False)
            try:
                cc.execute(MARKET_CANDLES_SCHEMA)
            finally:
                cc.close()

    @contextmanager
    def live_ticks_writer(self):
        self._check_duckdb_write_permission()
        ticks_path, _ = self._live_paths()
        with self._get_thread_lock('live_buffer'):
            conn = self._duckdb_connect(ticks_path, read_only=False)
            try:
                yield conn
            finally:
                conn.close()

    @contextmanager
    def live_candles_writer(self):
        self._check_duckdb_write_permission()
        _, candles_path = self._live_paths()
        with self._get_thread_lock('live_buffer'):
            conn = self._duckdb_connect(candles_path, read_only=False)
            try:
                yield conn
            finally:
                conn.close()
```

Then harden the candles open inside `live_buffer_reader()`. Replace the existing candles-open block (currently `if candles_path.exists(): conns['candles'] = self._duckdb_connect(candles_path, read_only=True)`) with a bounded retry:

```python
                if candles_path.exists():
                    for attempt in range(self._LIVE_READ_RETRIES):
                        try:
                            conns['candles'] = self._duckdb_connect(candles_path, read_only=True)
                            break
                        except Exception as exc:
                            transient = (
                                "being used by another process" in str(exc)
                                or "Conflicting lock" in str(exc)
                                or "Cannot open file" in str(exc)
                            )
                            if not transient or attempt == self._LIVE_READ_RETRIES - 1:
                                raise
                            time.sleep(self._LIVE_READ_RETRY_DELAY_S)
```

(`time` and `contextmanager` are already imported in this module.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/database/ingestors/test_manager_live_buffer.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add core/database/manager.py tests/database/ingestors/test_manager_live_buffer.py
git commit -m "feat(ingestor): narrow live-buffer writers + reader bounded-retry + DDL-once bootstrap"
```

---

### Task 2: `LiveBufferWriter` worker — lifecycle, queue, backpressure, tick-append

**Files:**
- Create: `core/database/ingestors/live_buffer_writer.py`
- Test: `tests/database/ingestors/test_live_buffer_writer.py` (create)

**Interfaces:**
- Consumes: `DatabaseManager.bootstrap_live_buffer()`, `live_ticks_writer()` (Task 1).
- Produces:
  - Command types: `TickFrame(raw: bytes)`, `Aggregate(symbols: list[str])`, `RecoverBars(rows: list[tuple])`, `Purge(cutoff: datetime)` — plain dataclasses in this module.
  - `LiveBufferWriter(db_manager, aggregator=None, zmq_publisher=None, max_queue=50000)`.
  - `.start()`, `.stop(timeout=5.0)`, `.enqueue_frame(raw: bytes)`, `.submit(cmd)`, `.dropped_frames: int`.
  - `RecoverBars.rows` tuple shape: `(symbol, timestamp, open, high, low, close, volume)` — all synthetic candles.

- [ ] **Step 1: Write the failing tests**

```python
# tests/database/ingestors/test_live_buffer_writer.py
import duckdb, time
from datetime import datetime
from core.database.manager import DatabaseManager
from core.database.ingestors.live_buffer_writer import (
    LiveBufferWriter, TickFrame, Purge,
)
from core.data.MarketDataFeedV3_pb2 import FeedResponse

def _frame(symbol, ltp, ltt_ms, ltq):
    fr = FeedResponse()
    f = fr.feeds[symbol]
    f.ltpc.ltp = ltp
    f.ltpc.ltt = ltt_ms
    f.ltpc.ltq = ltq
    return fr.SerializeToString()

def _ticks(tmp_path):
    return duckdb.connect(str(tmp_path / "live_buffer" / "ticks_today.duckdb"), read_only=True)

def test_enqueued_frame_persists_tick(tmp_path):
    db = DatabaseManager(tmp_path, read_only=False)
    w = LiveBufferWriter(db)
    w.start()
    w.enqueue_frame(_frame("NSE_INDEX|Nifty 50", 24000.0, 1723276800000, 5))
    w.stop()  # drains
    c = _ticks(tmp_path)
    row = c.execute("SELECT symbol, price, volume FROM ticks").fetchone()
    c.close()
    assert row == ("NSE_INDEX|Nifty 50", 24000.0, 5)

def test_tick_path_never_opens_candles(tmp_path):
    db = DatabaseManager(tmp_path, read_only=False)
    opened = []
    real = db._duckdb_connect
    def spy(path, read_only=False):
        opened.append(str(path))
        return real(path, read_only=read_only)
    db._duckdb_connect = spy
    w = LiveBufferWriter(db)
    w.start()
    w.enqueue_frame(_frame("X", 1.0, 1723276800000, 1))
    w.stop()
    assert not any("candles_today" in p for p in opened if "read_only=False")  # see note
    assert any("ticks_today" in p for p in opened)

def test_drop_oldest_backpressure(tmp_path):
    db = DatabaseManager(tmp_path, read_only=False)
    w = LiveBufferWriter(db, max_queue=10)
    # do NOT start the worker; fill the queue past bound
    for i in range(25):
        w.enqueue_frame(_frame("X", float(i), 1723276800000, 1))
    assert w.dropped_frames >= 15
    assert w._ticks.qsize() <= 10

def test_stop_drains_all_buffered_ticks(tmp_path):
    db = DatabaseManager(tmp_path, read_only=False)
    w = LiveBufferWriter(db)
    w.start()
    for i in range(50):
        w.enqueue_frame(_frame("X", float(i), 1723276800000 + i * 1000, 1))
    w.stop()
    c = _ticks(tmp_path)
    n = c.execute("SELECT count(*) FROM ticks").fetchone()[0]
    c.close()
    assert n == 50
```

Note for the `test_tick_path_never_opens_candles` assertion: the spy records the path only; assert no `candles_today` path is opened at all during a tick-only run:
```python
    assert not any("candles_today" in p for p in opened)
    assert any("ticks_today" in p for p in opened)
```
Use this simpler form in the actual test.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/database/ingestors/test_live_buffer_writer.py -v`
Expected: FAIL — `ModuleNotFoundError: core.database.ingestors.live_buffer_writer`.

- [ ] **Step 3: Implement the worker**

```python
# core/database/ingestors/live_buffer_writer.py
import logging
import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

import pytz

from core.data.MarketDataFeedV3_pb2 import FeedResponse
from core.database.manager import DatabaseManager

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


@dataclass
class TickFrame:
    raw: bytes


@dataclass
class Aggregate:
    symbols: List[str]


@dataclass
class RecoverBars:
    rows: List[Tuple]  # (symbol, timestamp, open, high, low, close, volume)


@dataclass
class Purge:
    cutoff: datetime


_SENTINEL = object()
_TICK_COALESCE_MAX = 500


class LiveBufferWriter:
    """Sole read-write owner of the live buffer during the live session."""

    def __init__(self, db_manager: DatabaseManager, aggregator=None,
                 zmq_publisher=None, max_queue: int = 50000):
        self.db = db_manager
        self.aggregator = aggregator
        self.zmq_publisher = zmq_publisher
        self._ticks: "queue.Queue" = queue.Queue(maxsize=max_queue)
        self._control: "queue.Queue" = queue.Queue()  # unbounded; control never dropped
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.dropped_frames = 0

    def start(self):
        if self._running:
            return
        self.db.bootstrap_live_buffer()
        self._running = True
        self._thread = threading.Thread(target=self._run, name="live-buffer-writer", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0):
        if not self._running:
            return
        self._running = False
        self._control.put_nowait(_SENTINEL)
        if self._thread:
            self._thread.join(timeout=timeout)

    def enqueue_frame(self, raw: bytes):
        # Tick queue only ever holds TickFrames, so drop-oldest can never touch
        # a control command.
        try:
            self._ticks.put_nowait(TickFrame(raw))
        except queue.Full:
            try:
                self._ticks.get_nowait()  # drop oldest tick
                self.dropped_frames += 1
            except queue.Empty:
                pass
            try:
                self._ticks.put_nowait(TickFrame(raw))
            except queue.Full:
                self.dropped_frames += 1

    def submit(self, cmd):
        # Control commands are never dropped and never block the caller
        # (unbounded control queue → put_nowait cannot raise Full).
        self._control.put_nowait(cmd)

    def _run(self):
        while True:
            # 1. Drain ALL pending control commands first (never dropped).
            while True:
                try:
                    cmd = self._control.get_nowait()
                except queue.Empty:
                    break
                if cmd is _SENTINEL:
                    self._final_drain()
                    return
                try:
                    self._dispatch(cmd)
                except Exception as e:
                    logger.error(f"LiveBufferWriter control command failed: {e}")
            # 2. Coalesce + flush ticks; brief block so we don't busy-spin and so
            #    stop() (sentinel on the control queue) is seen within ~50 ms.
            try:
                first = self._ticks.get(timeout=0.05)
            except queue.Empty:
                continue
            try:
                self._coalesce_ticks(first)
            except Exception as e:
                logger.error(f"LiveBufferWriter tick flush failed: {e}")

    def _final_drain(self):
        pending = []
        while True:
            try:
                pending.append(self._ticks.get_nowait())
            except queue.Empty:
                break
        if pending:
            try:
                self._flush_ticks(pending)
            except Exception as e:
                logger.error(f"LiveBufferWriter drain tick flush failed: {e}")
        while True:
            try:
                cmd = self._control.get_nowait()
            except queue.Empty:
                break
            if cmd is _SENTINEL:
                continue
            try:
                self._dispatch(cmd)
            except Exception as e:
                logger.error(f"LiveBufferWriter drain control failed: {e}")

    def _coalesce_ticks(self, first: TickFrame):
        frames = [first]
        while len(frames) < _TICK_COALESCE_MAX:
            try:
                frames.append(self._ticks.get_nowait())
            except queue.Empty:
                break
        self._flush_ticks(frames)

    def _dispatch(self, item):
        if isinstance(item, Aggregate):
            if self.aggregator:
                self.aggregator.aggregate(item.symbols, self.db, self.zmq_publisher)
        elif isinstance(item, RecoverBars):
            self._handle_recover(item)
        elif isinstance(item, Purge):
            self._handle_purge(item)

    def _flush_ticks(self, frames: List[TickFrame]):
        rows = []
        for fr in frames:
            rows.extend(self._parse(fr.raw))
        if not rows:
            return
        with self.db.live_ticks_writer() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO ticks (symbol, timestamp, price, volume) VALUES (?, ?, ?, ?)",
                rows,
            )

    def _parse(self, raw: bytes) -> List[Tuple]:
        out = []
        try:
            resp = FeedResponse()
            resp.ParseFromString(raw)
        except Exception:
            return out
        for symbol, feed in resp.feeds.items():
            ltp_data = self._extract_ltp(feed)
            if not ltp_data:
                continue
            ltp, ltt_ms, ltq = ltp_data
            if ltp == 0:
                continue
            ts = datetime.fromtimestamp(ltt_ms / 1000.0, tz=IST).replace(tzinfo=None)
            out.append((symbol, ts, ltp, int(ltq)))
        return out

    @staticmethod
    def _extract_ltp(feed):
        try:
            u = feed.WhichOneof("FeedUnion")
            if u == "ltpc":
                return feed.ltpc.ltp, feed.ltpc.ltt, feed.ltpc.ltq
            if u == "fullFeed":
                ff = feed.fullFeed.WhichOneof("FullFeedUnion")
                if ff == "marketFF":
                    l = feed.fullFeed.marketFF.ltpc
                    return l.ltp, l.ltt, l.ltq
                if ff == "indexFF":
                    l = feed.fullFeed.indexFF.ltpc
                    return l.ltp, l.ltt, 0
            if u == "firstLevelWithGreeks":
                l = feed.firstLevelWithGreeks.ltpc
                return l.ltp, l.ltt, l.ltq
        except Exception:
            pass
        return None

    def _handle_recover(self, cmd: RecoverBars):
        if not cmd.rows:
            return
        with self.db.live_candles_writer() as conn:
            for symbol, ts, o, h, l, c, v in cmd.rows:
                conn.execute(
                    "INSERT OR IGNORE INTO candles "
                    "(symbol, timeframe, timestamp, open, high, low, close, volume, is_synthetic) "
                    "VALUES (?, '1m', ?, ?, ?, ?, ?, ?, TRUE)",
                    [symbol, ts, o, h, l, c, int(v)],
                )

    def _handle_purge(self, cmd: Purge):
        with self.db.live_ticks_writer() as conn:
            conn.execute("DELETE FROM ticks WHERE timestamp < ?", [cmd.cutoff])
        with self.db.live_candles_writer() as conn:
            conn.execute("DELETE FROM candles WHERE timestamp < ?", [cmd.cutoff])
```

(The `Aggregate` path calls `self.aggregator.aggregate(...)`, added in Task 3. It is guarded by `if self.aggregator`, so Task 2 tests — which pass no aggregator — never hit it.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/database/ingestors/test_live_buffer_writer.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add core/database/ingestors/live_buffer_writer.py tests/database/ingestors/test_live_buffer_writer.py
git commit -m "feat(ingestor): LiveBufferWriter worker — queue, parse, coalesced tick-append, drain, backpressure"
```

---

### Task 3: `Aggregate` command — chunked candle aggregation on the worker

**Files:**
- Modify: `core/database/ingestors/db_tick_aggregator.py`
- Test: `tests/database/ingestors/test_aggregator_chunked.py` (create)

**Interfaces:**
- Consumes: `DatabaseManager.live_buffer_reader()` (ticks read), `live_candles_writer()` (Task 1).
- Produces: `DBTickAggregator.aggregate(symbols: list[str], db_manager, zmq_publisher) -> None` — reads ticks read-only, writes candles **one symbol per short-lived `live_candles_writer()` open**, publishes each new bar via zmq. Keeps the existing SQL and the "skip current incomplete minute" rule.

- [ ] **Step 1: Write the failing test**

```python
# tests/database/ingestors/test_aggregator_chunked.py
import duckdb
from datetime import datetime
from core.database.manager import DatabaseManager
from core.database.ingestors.db_tick_aggregator import DBTickAggregator

def _seed_ticks(tmp_path, symbol, base_minute):
    db = DatabaseManager(tmp_path, read_only=False)
    db.bootstrap_live_buffer()
    with db.live_ticks_writer() as conn:
        # three ticks in one completed minute
        for i, price in enumerate([100.0, 105.0, 102.0]):
            conn.execute(
                "INSERT INTO ticks (symbol, timestamp, price, volume) VALUES (?, ?, ?, ?)",
                [symbol, base_minute.replace(second=i * 10), price, 10],
            )
    return db

def test_aggregate_writes_ohlc_for_completed_minute(tmp_path):
    base = datetime(2020, 1, 1, 10, 0, 0)  # far in the past -> always "completed"
    db = _seed_ticks(tmp_path, "X", base)
    agg = DBTickAggregator(db_manager=db)
    agg.aggregate(["X"], db, None)
    c = duckdb.connect(str(tmp_path / "live_buffer" / "candles_today.duckdb"), read_only=True)
    row = c.execute("SELECT open, high, low, close, volume, is_synthetic FROM candles WHERE symbol='X'").fetchone()
    c.close()
    assert row == (100.0, 105.0, 100.0, 102.0, 30, False)

def test_aggregate_opens_candles_per_symbol_not_batch(tmp_path):
    base = datetime(2020, 1, 1, 10, 0, 0)
    db = _seed_ticks(tmp_path, "A", base)
    with db.live_ticks_writer() as conn:
        conn.execute("INSERT INTO ticks (symbol, timestamp, price, volume) VALUES ('B', ?, 5.0, 1)", [base])
    opens = {"candles": 0}
    real = db.live_candles_writer
    from contextlib import contextmanager
    @contextmanager
    def counting():
        opens["candles"] += 1
        with real() as conn:
            yield conn
    db.live_candles_writer = counting
    agg = DBTickAggregator(db_manager=db)
    agg.aggregate(["A", "B"], db, None)
    assert opens["candles"] == 2  # one short-lived open per symbol, not one batch hold
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/database/ingestors/test_aggregator_chunked.py -v`
Expected: FAIL — `AttributeError: 'DBTickAggregator' object has no attribute 'aggregate'`.

- [ ] **Step 3: Implement `aggregate()`**

Add to `DBTickAggregator` (keep `__init__`; you may remove the old `aggregate_outstanding_ticks`/`_aggregate_symbol` batch path once Task 6 stops calling it — do that in Task 6, not here). Add:

```python
    def aggregate(self, symbols, db_manager, zmq_publisher):
        for symbol in symbols:
            try:
                self._aggregate_one(symbol, db_manager, zmq_publisher)
            except Exception as e:
                logger.error(f"Aggregation failed for {symbol}: {e}")

    def _aggregate_one(self, symbol, db_manager, zmq_publisher):
        with db_manager.live_buffer_reader() as conns:
            if 'ticks' not in conns:
                return
            ticks_conn = conns['ticks']
            last_bar_ts = None
            if 'candles' in conns:
                res = conns['candles'].execute(
                    "SELECT MAX(timestamp) FROM candles WHERE symbol=? AND timeframe='1m' AND is_synthetic=FALSE",
                    [symbol],
                ).fetchone()
                last_bar_ts = res[0] if res and res[0] else None
            start_ts = last_bar_ts if last_bar_ts else datetime(2000, 1, 1)
            rows = ticks_conn.execute(
                """
                SELECT date_trunc('minute', timestamp) AS bar_ts,
                       first(price ORDER BY timestamp ASC) AS op,
                       max(price) AS hi, min(price) AS lo,
                       last(price ORDER BY timestamp ASC) AS cl,
                       sum(volume) AS vol
                FROM ticks WHERE symbol=? AND timestamp>=? GROUP BY 1 ORDER BY 1 ASC
                """,
                [symbol, start_ts],
            ).fetchall()

        current_minute = datetime.now().replace(second=0, microsecond=0)
        completed = [r for r in rows if r[0] < current_minute and r[1] is not None and r[4] is not None]
        if not completed:
            return

        with db_manager.live_candles_writer() as candles_conn:
            for bar_ts, op, hi, lo, cl, vol in completed:
                candles_conn.execute(
                    """
                    INSERT INTO candles
                    (symbol, timeframe, timestamp, open, high, low, close, volume, is_synthetic)
                    VALUES (?, '1m', ?, ?, ?, ?, ?, ?, FALSE)
                    ON CONFLICT (symbol, timeframe, timestamp) DO UPDATE SET
                        open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                        close=EXCLUDED.close, volume=EXCLUDED.volume, is_synthetic=FALSE
                    """,
                    [symbol, bar_ts, op, hi, lo, cl, int(vol)],
                )

        if zmq_publisher:
            for bar_ts, op, hi, lo, cl, vol in completed:
                zmq_publisher.publish(
                    f"market.candle.1m.{symbol}", "market_candle",
                    {"symbol": symbol, "timeframe": "1m", "timestamp": bar_ts.isoformat(),
                     "open": float(op), "high": float(hi), "low": float(lo),
                     "close": float(cl), "volume": int(vol)},
                )
```

Ensure `from datetime import datetime` is present (it is).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/database/ingestors/test_aggregator_chunked.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add core/database/ingestors/db_tick_aggregator.py tests/database/ingestors/test_aggregator_chunked.py
git commit -m "feat(ingestor): chunked per-symbol candle aggregation via live_candles_writer"
```

---

### Task 4: `RecoverBars` enqueue path (`recovery_manager.py`)

**Files:**
- Modify: `core/database/ingestors/recovery_manager.py`
- Test: `tests/database/ingestors/test_recovery_enqueue.py` (create)

**Interfaces:**
- Consumes: `LiveBufferWriter.submit(RecoverBars(rows))` (Task 2), `live_buffer_reader()` for `_get_last_bar_timestamp` (unchanged).
- Produces: `RecoveryManager(upstox_client, db_manager, writer)` — new required `writer` param (the `LiveBufferWriter`). `run_recovery` and `_recover_symbol` build `RecoverBars` rows and call `writer.submit(...)` instead of opening `live_buffer_writer()` directly.

- [ ] **Step 1: Write the failing test**

```python
# tests/database/ingestors/test_recovery_enqueue.py
from datetime import datetime
from unittest.mock import MagicMock
from core.database.manager import DatabaseManager
from core.database.ingestors.recovery_manager import RecoveryManager
from core.database.ingestors.live_buffer_writer import RecoverBars

def test_recovery_submits_recoverbars_not_direct_write(tmp_path, monkeypatch):
    db = DatabaseManager(tmp_path, read_only=False)
    db.bootstrap_live_buffer()
    writer = MagicMock()
    client = MagicMock()
    # one candle strictly inside the recoverable window
    bar_ts = datetime(2020, 1, 1, 10, 5)  # past date; _recover_symbol gates on market open — patch it
    client.fetch_intraday_candles_v3.return_value = [
        {"timestamp": bar_ts, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10}
    ]
    rm = RecoveryManager(client, db_manager=db, writer=writer)
    # Force the "recoverable gap" branch deterministically
    monkeypatch.setattr(rm, "_should_recover", lambda symbol: (datetime(2020,1,1,10,0), datetime(2020,1,1,10,6)))
    rm._recover_symbol("X")
    assert writer.submit.called
    cmd = writer.submit.call_args[0][0]
    assert isinstance(cmd, RecoverBars)
    assert cmd.rows and cmd.rows[0][0] == "X"
```

(The `_should_recover(symbol) -> (last_ts, cutoff) | None` helper is introduced in Step 3 to make the market-open/gap decision testable in isolation; `None` means "nothing to recover".)

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/database/ingestors/test_recovery_enqueue.py -v`
Expected: FAIL — `TypeError: __init__() missing 1 required positional argument: 'writer'`.

- [ ] **Step 3: Implement the enqueue refactor**

In `recovery_manager.py`:
1. `__init__(self, upstox_client, db_manager, writer)` — store `self.writer = writer`.
2. Extract the market-open + gap decision into `_should_recover(self, symbol) -> Optional[tuple]` returning `(last_ts, cutoff)` or `None`, using the existing logic (market-closed → None; empty/stale buffer before open → None; gap < 2 min → None; else `(last_ts, now.replace(second=0, microsecond=0))`).
3. Replace the `with self.db.live_buffer_writer() as conns:` write block in `_recover_symbol` with:

```python
        decision = self._should_recover(symbol)
        if decision is None:
            return
        last_ts, cutoff = decision
        try:
            candles = self.client.fetch_intraday_candles_v3(instrument_key=symbol, unit="minutes", interval=1)
        except Exception as e:
            logger.error(f"[Recovery] {symbol}: fetch failed — {e}")
            return
        if not candles:
            logger.warning(f"[Recovery] {symbol}: API returned 0 candles.")
            return
        rows = []
        for candle in candles:
            ts = candle['timestamp']
            if ts > last_ts and ts < cutoff:
                rows.append((symbol, ts, candle['open'], candle['high'],
                             candle['low'], candle['close'], int(candle['volume'])))
        if rows:
            self.writer.submit(RecoverBars(rows))
            logger.info(f"[Recovery] {symbol}: enqueued {len(rows)} bars.")
```

Add `from core.database.ingestors.live_buffer_writer import RecoverBars` at the top. Remove the now-dead retry/`time.sleep` write loop.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/database/ingestors/test_recovery_enqueue.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add core/database/ingestors/recovery_manager.py tests/database/ingestors/test_recovery_enqueue.py
git commit -m "feat(ingestor): recovery enqueues RecoverBars to the writer instead of direct RW write"
```

---

### Task 5: WS handler enqueues raw frames (`websocket_ingestor.py`)

**Files:**
- Modify: `core/database/ingestors/websocket_ingestor.py`
- Test: `tests/database/ingestors/test_ws_handler_enqueue.py` (create)

**Interfaces:**
- Consumes: `LiveBufferWriter.enqueue_frame(bytes)` (Task 2).
- Produces: `WebSocketIngestor(symbols, access_token, writer, ping_interval=10.0, ping_timeout=30.0)` — takes the `LiveBufferWriter` (renamed from `db_manager`). `_handle_message(raw)` calls `writer.enqueue_frame(raw)` and nothing else. `TickBuffer` class removed. Module-level `IST` constant. `websockets.connect` receives `ping_interval`/`ping_timeout`.

- [ ] **Step 1: Write the failing test**

```python
# tests/database/ingestors/test_ws_handler_enqueue.py
from unittest.mock import MagicMock
from core.database.ingestors.websocket_ingestor import WebSocketIngestor

def test_handle_message_only_enqueues_raw_bytes():
    writer = MagicMock()
    ing = WebSocketIngestor(["X"], access_token="t", writer=writer)
    ing._handle_message(b"\x08\x01raw-bytes")
    writer.enqueue_frame.assert_called_once_with(b"\x08\x01raw-bytes")

def test_ping_params_stored():
    writer = MagicMock()
    ing = WebSocketIngestor(["X"], access_token="t", writer=writer,
                            ping_interval=10.0, ping_timeout=30.0)
    assert ing.ping_interval == 10.0 and ing.ping_timeout == 30.0

def test_tickbuffer_removed():
    import core.database.ingestors.websocket_ingestor as mod
    assert not hasattr(mod, "TickBuffer")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/database/ingestors/test_ws_handler_enqueue.py -v`
Expected: FAIL — `__init__` signature mismatch / `TickBuffer` still present.

- [ ] **Step 3: Implement the handler changes**

In `websocket_ingestor.py`:
1. Delete the entire `TickBuffer` class.
2. Add module-level `IST = pytz.timezone('Asia/Kolkata')` (parse no longer happens here, but keep the import tidy — remove `pytz` usage from the handler).
3. Change `__init__` to `def __init__(self, symbols, access_token, writer, ping_interval=10.0, ping_timeout=30.0)`; store `self.writer`, `self.ping_interval`, `self.ping_timeout`; drop `self._tick_buffer`.
4. In `stop()`, remove the `self._tick_buffer.close()` call (the worker owns draining now).
5. Replace `_handle_message` body with:

```python
    def _handle_message(self, message: bytes):
        self.writer.enqueue_frame(message)
```

6. Delete `_extract_ltp_from_feed` (moved to the worker).
7. In `_connect_and_ingest`, change the connect line to:

```python
                async with websockets.connect(
                    wss_url, ping_interval=self.ping_interval, ping_timeout=self.ping_timeout
                ) as ws:
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/database/ingestors/test_ws_handler_enqueue.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add core/database/ingestors/websocket_ingestor.py tests/database/ingestors/test_ws_handler_enqueue.py
git commit -m "feat(ingestor): WS handler enqueues raw frames; remove TickBuffer; explicit ping params"
```

---

### Task 6: Wire the worker into `market_ingestor.py` (connect-then-async-backfill)

**Files:**
- Modify: `scripts/market_ingestor.py`
- Modify: `core/database/ingestors/db_tick_aggregator.py` (remove the dead `aggregate_outstanding_ticks`/`_aggregate_symbol` batch path)
- Test: `tests/database/ingestors/test_market_ingestor_wiring.py` (create)

**Interfaces:**
- Consumes: `LiveBufferWriter` (Task 2), reshaped `WebSocketIngestor` (Task 5), `RecoveryManager` (Task 4), `DBTickAggregator.aggregate` (Task 3).
- Produces: `market_ingestor` owns one `LiveBufferWriter`, starts it before connecting; `_try_connect` starts the WS **first**, then launches recovery on a background thread; the main loop posts `Aggregate(self.symbols)` each cycle via `writer.submit`; purge posts `Purge(cutoff)`; `stop()` stops the writer (drain).

- [ ] **Step 1: Write the failing test**

```python
# tests/database/ingestors/test_market_ingestor_wiring.py
from unittest.mock import MagicMock, patch
import scripts.market_ingestor as mi

def test_try_connect_starts_ws_before_recovery(tmp_path):
    order = []
    daemon = mi.MarketIngestorDaemon.__new__(mi.MarketIngestorDaemon)
    daemon.symbols = ["X"]
    daemon.db_manager = MagicMock()
    daemon.writer = MagicMock()
    daemon._update_websocket_status = lambda *a, **k: None

    fake_ws = MagicMock()
    fake_ws.start.side_effect = lambda: order.append("ws_start")

    with patch.object(mi, "WebSocketIngestor", return_value=fake_ws), \
         patch.object(mi, "UpstoxClient", MagicMock()), \
         patch.object(mi, "RecoveryManager") as RM, \
         patch.object(mi, "threading") as th:
        # capture recovery thread creation as the "recovery" marker
        th.Thread.side_effect = lambda *a, **k: order.append("recovery_thread") or MagicMock()
        daemon._try_connect("token")

    assert order.index("ws_start") < order.index("recovery_thread")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/database/ingestors/test_market_ingestor_wiring.py -v`
Expected: FAIL (current `_try_connect` runs recovery before WS and takes no `writer`).

- [ ] **Step 3: Implement the wiring**

In `scripts/market_ingestor.py`:
1. Import: `from core.database.ingestors.live_buffer_writer import LiveBufferWriter, Aggregate, Purge`.
2. In `__init__`, after `self.aggregator = DBTickAggregator(...)`, add:
   `self.writer = LiveBufferWriter(self.db_manager, aggregator=self.aggregator, zmq_publisher=self.zmq_publisher)` and remove the `zmq_publisher` arg reliance elsewhere as needed. Start it in `run()` before any connect: `self.writer.start()`.
3. Rewrite `_try_connect`:

```python
    def _try_connect(self, token: str):
        upstox_client = UpstoxClient(access_token=token)
        self.ingestor = WebSocketIngestor(self.symbols, access_token=token, writer=self.writer)
        self.ingestor.start()
        self._update_websocket_status("OPEN")
        logger.info("WebSocket ingestor started successfully.")

        def _backfill():
            try:
                RecoveryManager(upstox_client, db_manager=self.db_manager, writer=self.writer).run_recovery(self.symbols)
            except Exception as e:
                logger.warning(f"Recovery failed (non-blocking): {e}")
        threading.Thread(target=_backfill, name="recovery-backfill", daemon=True).start()
```

4. Replace both `self.aggregator.aggregate_outstanding_ticks(self.symbols)` calls in the main loop with `self.writer.submit(Aggregate(self.symbols))`.
5. Replace `_purge_stale_live_buffer` body's `with self.db_manager.live_buffer_writer()...` with `self.writer.submit(Purge(cutoff))` (keep the `_last_cleanup_date` bookkeeping).
6. In `stop()`, add `self.writer.stop()` (before closing zmq) so buffered ticks drain.
7. In `db_tick_aggregator.py`, delete `aggregate_outstanding_ticks`, `_aggregate_symbol`, `_table_exists`, `_get_last_bar_timestamp` — all superseded by `aggregate()` from Task 3. Keep `__init__` and `aggregate`/`_aggregate_one`. **Scope guard:** `RecoveryManager._get_last_bar_timestamp` (`recovery_manager.py:141`) is a *separate* method in a different file that Task 4's `_should_recover` still depends on — **do not touch it**. Only the copy in `db_tick_aggregator.py` is deleted.

- [ ] **Step 4: Run test + regression to verify**

Run: `python -m pytest tests/database/ingestors/test_market_ingestor_wiring.py -v`
Expected: PASS.
Run: `python -m pytest tests/database/ingestors/ -v`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add scripts/market_ingestor.py core/database/ingestors/db_tick_aggregator.py tests/database/ingestors/test_market_ingestor_wiring.py
git commit -m "feat(ingestor): wire LiveBufferWriter — connect-then-async-backfill, Aggregate/Purge via worker"
```

---

### Task 7: Integration proof + cleanup + full suite

**Files:**
- Test: `tests/database/ingestors/test_reader_no_contention.py` (create)
- Verify only (no functional change): grep for stale references.

**Interfaces:** none new. This task proves the F4 outcome end-to-end and confirms nothing stale remains.

- [ ] **Step 1: Write the cross-process reader-contention integration test**

This must be a **genuine separate process** — a same-process reader is serialized by `_get_thread_lock('live_buffer')` and never hits the DuckDB cross-process file lock that F4 is about. A child process (mirroring the design-phase probe) is the only honest proof.

```python
# tests/database/ingestors/test_reader_no_contention.py
import subprocess, sys, textwrap, threading, time
from datetime import datetime
from core.database.manager import DatabaseManager
from core.database.ingestors.live_buffer_writer import LiveBufferWriter, Aggregate
from core.database.ingestors.db_tick_aggregator import DBTickAggregator
from core.data.MarketDataFeedV3_pb2 import FeedResponse

def _frame(sym, ltp, ms):
    fr = FeedResponse(); f = fr.feeds[sym]; f.ltpc.ltp = ltp; f.ltpc.ltt = ms; f.ltpc.ltq = 1
    return fr.SerializeToString()

def test_cross_process_reader_lands_during_active_writing(tmp_path):
    db = DatabaseManager(tmp_path, read_only=False)
    db.bootstrap_live_buffer()
    candles_path = str(tmp_path / "live_buffer" / "candles_today.duckdb")

    w = LiveBufferWriter(db, aggregator=DBTickAggregator(db))
    w.start()
    stop = threading.Event()
    def load():
        base = int(datetime(2020, 1, 1, 10, 0).timestamp() * 1000)
        i = 0
        while not stop.is_set():
            w.enqueue_frame(_frame("X", 100.0 + (i % 5), base + i * 1000))
            w.submit(Aggregate(["X"]))
            i += 1
            time.sleep(0.005)
    t = threading.Thread(target=load); t.start()

    # Separate OS process: open candles read-only with the same bounded-retry
    # shape the reader hardening uses (5 x 50ms).
    child = textwrap.dedent(f"""
        import duckdb, time
        ok = fail = 0
        for _ in range(50):
            for attempt in range(5):
                try:
                    c = duckdb.connect(r"{candles_path}", read_only=True)
                    c.execute("SELECT count(*) FROM candles").fetchone(); c.close()
                    ok += 1; break
                except Exception:
                    if attempt == 4: fail += 1
                    else: time.sleep(0.05)
            time.sleep(0.01)
        print(f"{{ok}} {{fail}}")
    """)
    proc = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True, timeout=30)
    stop.set(); t.join(); w.stop()
    assert proc.stdout.strip(), f"child produced no output; stderr={proc.stderr[:400]}"
    ok, fail = map(int, proc.stdout.split())
    assert ok >= 48, f"cross-process reader failed too often: ok={ok} fail={fail} stderr={proc.stderr[:300]}"
```

- [ ] **Step 2: Run it**

Run: `python -m pytest tests/database/ingestors/test_reader_no_contention.py -v`
Expected: PASS (near-total reader success; bounded retry absorbs the rare collision).

- [ ] **Step 3: Grep for stale references and confirm scope**

Run:
```bash
grep -rn "aggregate_outstanding_ticks\|TickBuffer\|_tick_buffer" core scripts tests | grep -v __pycache__
grep -rn "live_buffer_writer" core scripts | grep -v __pycache__ | grep -v "def live_buffer_writer"
```
Expected: the first returns nothing (all removed). The second returns only `core/database/writers.py` and `scripts/fetch_upstox_historical.py` (out-of-scope offline callers) — confirm those two are the only ones and were intentionally left.

- [ ] **Step 4: Run the ingestor suite + a broad regression**

Run: `python -m pytest tests/database/ tests/nifty_shield_paper/ tests/execution/test_nifty_shield_paper_execution.py -v`
Expected: all green.

Also run the ops preflight import/collection to confirm nothing it depends on moved:
Run: `python -m pytest tests/ops/ -v`
Expected: all green (preflight's VIX BLOCK check reads the live buffer via the same reader path Task 1 hardened).

- [ ] **Step 5: Commit**

```bash
git add tests/database/ingestors/test_reader_no_contention.py
git commit -m "test(ingestor): cross-process reader lands during active writing (F4 proof)"
```

- [ ] **Step 6: Record the live-morning verification checklist (do not close F4 without it)**

The two concrete cross-process readers F4 exists to unblock cannot run headless (they need the real `data/live_buffer` and a live feed). They MUST be confirmed on the next live-morning shakedown, before this branch is trusted for a live window. Add these to the shakedown doc `docs/reports/OPS_SHAKEDOWN_2026-08-10_INGESTION_FAULTS.md` as F3/F4 close-out checks:
  1. With the ingestor + worker under real load, run `python scripts/ops/preflight.py` and confirm the **VIX BLOCK check reads through** (no "being used by another process") and goes warm.
  2. At/near 13:00, confirm `scripts/daytype/publish_live_fact.py` opens `candles_today.duckdb` read-only and publishes the day-type fact without a lock error.
  3. Confirm the WS stays connected through the open with **no `1011 keepalive ping timeout`** reconnect in the ingestor log (F3 closed).

No commit for this step — it is a checklist entry; DeepSeek notes it in the shakedown doc and the operator runs it live.

---

## Self-Review

**Spec coverage:**
- §2 single-writer invariant → Tasks 2, 6 (worker is sole RW owner; wiring routes all writes through it). ✓
- §3 F3 off-loop (enqueue raw, parse on worker, tz hoist, ping params) → Tasks 2 (parse+tz), 5 (enqueue, tz hoist, ping). ✓
- §4 F4 (ticks-only tick path, chunked candle writes, reader retry, DDL-once) → Tasks 1 (retry, DDL-once, narrow writers), 2 (ticks-only), 3 (chunked). ✓
- §5 F1 connect-then-async-backfill → Task 6. ✓
- §2.2 command model (TickFrame/Aggregate/RecoverBars/Purge) → Task 2 (types), 3/4/6 (producers). ✓
- §2.3 drop-oldest + shutdown drain → Task 2 (both, tested). ✓
- §6 precedence order-safe, no guard → honored (recovery IGNORE-TRUE, aggregate UPDATE-FALSE); no guard added. ✓
- §7 tests (handler enqueues, worker parse, ticks-only, chunked, drop-oldest, drain, cross-process reader, connect ordering) → Tasks 2/3/5/6/7. ✓
- §8 blast radius files → all covered across Tasks 1-7; offline callers explicitly out of scope. ✓

**Placeholder scan:** no TBD/TODO; every code step shows full code; ping values pinned (10.0/30.0); chunk granularity pinned (per-symbol).

**Type consistency:** `LiveBufferWriter(db_manager, aggregator, zmq_publisher, max_queue)`, `enqueue_frame(bytes)`, `submit(cmd)`, `aggregate(symbols, db_manager, zmq_publisher)`, `RecoveryManager(client, db_manager, writer)`, `WebSocketIngestor(symbols, access_token, writer, ping_interval, ping_timeout)`, `RecoverBars.rows = (symbol, ts, o, h, l, c, v)` — consistent across producing and consuming tasks.

**Note for the implementer on `test_tick_path_never_opens_candles` (Task 2):** use the simpler assertion form given in the note under Step 1 (`assert not any("candles_today" in p for p in opened)`), not the inline `if "read_only=False"` string which is illustrative only.
