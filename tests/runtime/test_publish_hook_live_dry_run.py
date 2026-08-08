"""
nifty_shield_v1 — Stage-2 prerequisite live/PAPER dry-run (acceptance §6.1).

The end-to-end wire test: a LoopDriver (REPLAY, deterministic) drives a
synthetic session; the DS2-2 pre-signal publish hook writes the session's
13pm live fact (produced_by=live, intraday VIX per DS2-3) before on_bar; and
the source — which no longer snapshots facts at startup (DS2-1) — reads that
fact at the 13:00 bar and emits the structure's legs. This is the exact
ordering the live prerequisite depends on: write the fact, then the source
reads it, in-process, single thread.
"""
from __future__ import annotations

from datetime import date, time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from core.events import OHLCVBar
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver

from strategies.nifty_shield_v1 import build_signal_source

from _doubles import FakeClock, FakeMarketDataProvider

ROOT = Path(__file__).resolve().parents[2]
NF_SYMBOL = "NSE_INDEX|Nifty 50"
SESSION = date(2026, 6, 5)


def _model_present() -> bool:
    return (ROOT / "models" / "daytype" / "logistic_13pm_prod" / "model.pkl").exists()


def _session_bars(seed: int, base: float) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    closes = base + np.cumsum(rng.normal(0, 3, 226))
    opens = np.concatenate([[closes[0]], closes[:-1]])
    times = pd.date_range(f"{SESSION} 09:15", periods=226, freq="1min")
    return pd.DataFrame({
        "timestamp": times, "open": opens,
        "high": np.maximum(opens, closes) + 1.0,
        "low": np.minimum(opens, closes) - 1.0,
        "close": closes, "volume": np.full(226, 1000.0),
    })


def _stable_vix() -> pd.DataFrame:
    """A near-flat India VIX 1m series (~14.5) so vix_at_checkpoint stays below
    vix_skip_above (20) and the 13:00 entry fires."""
    times = pd.date_range(f"{SESSION} 09:15", periods=226, freq="1min")
    return pd.DataFrame({
        "timestamp": times, "open": 14.5, "high": 14.5, "low": 14.5,
        "close": 14.5, "volume": np.full(226, 1000.0),
    })


def _write_candle_db(path: Path, rows: dict) -> None:
    con = duckdb.connect(str(path))
    con.execute("""
        CREATE TABLE candles (
            symbol VARCHAR, timestamp TIMESTAMP, open DOUBLE, high DOUBLE,
            low DOUBLE, close DOUBLE, volume BIGINT
        )
    """)
    for symbol, df in rows.items():
        con.executemany(
            "INSERT INTO candles VALUES (?,?,?,?,?,?,?)",
            [(symbol, ts.to_pydatetime(), float(o), float(h), float(l),
              float(c), int(v))
             for ts, o, h, l, c, v in zip(
                 df["timestamp"], df["open"], df["high"], df["low"],
                 df["close"], df["volume"])],
        )
    con.close()


@pytest.mark.skipif(not _model_present(), reason="models/daytype not present")
def test_live_dry_run_fact_written_before_on_bar_and_read(tmp_path, monkeypatch):
    import scripts.daytype.publish_live_fact as live

    nf = _session_bars(seed=1, base=24000.0)
    bn = _session_bars(seed=2, base=52000.0)
    vix = _stable_vix()

    candle_dir = tmp_path / "candles_1m"
    candle_dir.mkdir()
    _write_candle_db(candle_dir / f"{SESSION.isoformat()}.duckdb", {
        "NSE_INDEX|Nifty 50": nf, "NSE_INDEX|Nifty Bank": bn,
        "NSE_INDEX|India VIX": vix,
    })
    monkeypatch.setattr(live, "CANDLE_DIR_1M", candle_dir)
    monkeypatch.setattr(live, "LIVE_BUFFER", tmp_path / "no_live_buffer.duckdb")

    facts_db = tmp_path / "facts.duckdb"
    source = build_signal_source({"facts_db_path": str(facts_db)})
    hook = live.make_driver_hook(facts_db)

    bars = [
        OHLCVBar(symbol=NF_SYMBOL, timestamp=ts.to_pydatetime(),
                 open=float(o), high=float(h), low=float(l),
                 close=float(c), volume=float(v))
        for ts, o, h, l, c, v in zip(nf["timestamp"], nf["open"], nf["high"],
                                     nf["low"], nf["close"], nf["volume"])
    ]
    config = DriverConfig(mode=Mode.REPLAY, symbols=[NF_SYMBOL], poll_interval_s=0.5)
    driver = LoopDriver(config, clock=FakeClock(),
                        provider=FakeMarketDataProvider({NF_SYMBOL: bars}),
                        source=source,
                        publish_hook=hook,
                        publish_checkpoint_time=time(13, 0))
    driver.run()

    # The fact exists, produced live, intraday VIX populated, EOD close NULL.
    con = duckdb.connect(str(facts_db), read_only=True)
    row = con.execute(
        "SELECT produced_by, vix_close, vix_at_checkpoint, regime "
        "FROM day_type_facts WHERE session_date = ?", [SESSION]
    ).fetchone()
    con.close()
    assert row is not None
    assert row[0].startswith("live@")
    assert row[1] is None
    assert row[2] is not None
    assert row[3] in {"BullTrend", "BearTrend", "Choppy"}

    # The source read the live fact at the 13:00 bar and emitted the structure.
    assert driver.signals_pulled >= 2            # a structure has >= 2 legs
