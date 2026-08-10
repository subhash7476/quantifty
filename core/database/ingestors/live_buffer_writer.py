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
