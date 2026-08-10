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
    DatabaseManager.reset_instance()
    db = DatabaseManager(tmp_path, read_only=False)
    db.bootstrap_live_buffer()
    candles_path = str(tmp_path / "live_buffer" / "candles_today.duckdb")

    w = LiveBufferWriter(db, aggregator=DBTickAggregator(db))
    w.start()
    stop = threading.Event()
    def load():
        base = int(datetime(2020, 1, 1, 10, 0).timestamp() * 1000)
        i = 0
        # Sustained candle writes at ~10/sec (15x production's 1.5s cycle).
        # A DuckDB RW open->write->close cycle costs ~27ms on Windows (file-lock
        # overhead), so faster floods lock the file nearly continuously and make
        # RO and RW starve each other bidirectionally (design §1.1 fact 2) — that
        # is beyond the design envelope the bounded-retry reader was validated in
        # (design §1.1 fact 4: 37/40 opens against 13 writes/0.6s).
        while not stop.is_set():
            w.enqueue_frame(_frame("X", 100.0 + (i % 5), base + i * 1000))
            w.submit(Aggregate(["X"]))
            i += 1
            time.sleep(0.1)
    t = threading.Thread(target=load); t.start()

    # Separate OS process: open candles read-only with the same bounded-retry
    # shape the reader hardening uses (5 x 50ms), polling while the writer is
    # actively writing.
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
            time.sleep(0.05)
        print(f"{{ok}} {{fail}}")
    """)
    proc = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True, timeout=30)
    stop.set(); t.join(); w.stop()
    assert proc.stdout.strip(), f"child produced no output; stderr={proc.stderr[:400]}"
    ok, fail = map(int, proc.stdout.split())
    assert ok >= 48, f"cross-process reader failed too often: ok={ok} fail={fail} stderr={proc.stderr[:300]}"
