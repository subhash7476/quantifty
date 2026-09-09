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
# Seconds of ticks to accumulate before touching the DB. Every flush opens a
# connection and closes it (the cross-process lock leaves no choice), and each
# close checkpoints the whole table including its primary-key index — measured
# at 265 MB per 1,000 checkpoints. Draining on the 0.05 s queue timeout meant
# ~38,000 checkpoints a session, which is how ticks_today.duckdb reached 10 GB
# holding under 1 MB of rows. At 3 s that is ~7,800 flushes a session.
# The buffer is bounded by _TICK_COALESCE_MAX regardless, so a burst still
# flushes early and the queue cannot back up.
_TICK_FLUSH_INTERVAL_S = 3.0


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
        self._pending: List[TickFrame] = []
        self._last_flush = 0.0
        self._last_tick: dict = {}

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
            #    Coalesce redundant Aggregates: an Aggregate re-reads current
            #    state, so N piled ones are identical to the last — running only
            #    the newest keeps candle writes from starving the tick flush.
            drained = []
            saw_sentinel = False
            while True:
                try:
                    cmd = self._control.get_nowait()
                except queue.Empty:
                    break
                if cmd is _SENTINEL:
                    saw_sentinel = True
                    break
                drained.append(cmd)
            control = self._coalesce_control(drained)
            # An Aggregate builds 1m bars by reading the ticks table, so any
            # tick still sitting in the interval buffer has to land first —
            # otherwise a bar closed right on the minute boundary is written
            # short and INSERT OR IGNORE makes that permanent.
            if any(isinstance(c, Aggregate) for c in control):
                self._force_flush()
            for cmd in control:
                try:
                    self._dispatch(cmd)
                except Exception as e:
                    logger.error(f"LiveBufferWriter control command failed: {e}")
            if saw_sentinel:
                self._final_drain()
                return
            # 2. Coalesce + flush ticks; brief block so we don't busy-spin and so
            #    stop() (sentinel on the control queue) is seen within ~50 ms.
            try:
                first = self._ticks.get(timeout=0.05)
            except queue.Empty:
                first = None
            try:
                self._coalesce_ticks(first)
            except Exception as e:
                logger.error(f"LiveBufferWriter tick flush failed: {e}")

    def _final_drain(self):
        # whatever the interval was still holding must not die with the thread
        pending = self._pending
        self._pending = []
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

    @staticmethod
    def _coalesce_control(cmds):
        last_agg = -1
        for i, c in enumerate(cmds):
            if isinstance(c, Aggregate):
                last_agg = i
        return [c for i, c in enumerate(cmds)
                if not (isinstance(c, Aggregate) and i != last_agg)]

    def _force_flush(self):
        if not self._pending:
            return
        frames, self._pending = self._pending, []
        self._last_flush = time.monotonic()
        try:
            self._flush_ticks(frames)
        except Exception as e:
            logger.error(f"LiveBufferWriter forced tick flush failed: {e}")

    def _coalesce_ticks(self, first: Optional[TickFrame]):
        """Accumulate ticks; write only once per _TICK_FLUSH_INTERVAL_S.

        `first` is None when the queue timed out — an idle tick still has to run
        so a partial batch is not stranded waiting for the next frame to arrive.
        """
        if first is not None:
            self._pending.append(first)
        while len(self._pending) < _TICK_COALESCE_MAX:
            try:
                self._pending.append(self._ticks.get_nowait())
            except queue.Empty:
                break
        if not self._pending:
            return
        now = time.monotonic()
        if (len(self._pending) < _TICK_COALESCE_MAX
                and now - self._last_flush < _TICK_FLUSH_INTERVAL_S):
            return
        frames, self._pending = self._pending, []
        self._last_flush = now
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
        rows = self._drop_unchanged(rows)
        if not rows:
            return
        with self.db.live_ticks_writer() as conn:
            # plain INSERT: the table no longer carries a (symbol, timestamp)
            # key, so a second update inside the same second is kept instead of
            # being silently dropped (see MARKET_TICKS_SCHEMA).
            conn.executemany(
                "INSERT INTO ticks (symbol, timestamp, price, volume) VALUES (?, ?, ?, ?)",
                rows,
            )

    def _drop_unchanged(self, rows: List[Tuple]) -> List[Tuple]:
        """Drop a tick identical to the previous one for that symbol.

        Removing the primary key removed the only thing suppressing repeats, and
        the feed re-sends the current state on every reconnect (three of them in
        the 2026-09-04 session). An identical (timestamp, price, volume) carries
        no new information and would double-count in the aggregator's
        sum(volume), so it is dropped here rather than by a key that also threw
        away the genuinely different updates.
        """
        out = []
        for row in rows:
            symbol = row[0]
            if self._last_tick.get(symbol) == row[1:]:
                continue
            self._last_tick[symbol] = row[1:]
            out.append(row)
        return out

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
        # Rebuild-and-swap rather than DELETE: a DELETE drops the rows but hands
        # every allocated block to the next session, which is how a buffer
        # holding one day of data reached 4 GB. rotate_live_buffer verifies the
        # retained row count before swapping and leaves the original in place if
        # it would lose anything.
        kept = self.db.rotate_live_buffer(cmd.cutoff)
        logger.info("live buffer rotated at %s: %s", cmd.cutoff,
                    ", ".join(f"{t}={n} kept" for t, n in kept.items()) or "nothing to rotate")
