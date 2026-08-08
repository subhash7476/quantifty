"""
nifty_shield_v1 — DS2-1 read-timing re-certification tests.

Covers the two behavioral changes that keep the re-cert a provable offline no-op
while enabling live (NIFTY_SHIELD_STAGE2_PREREQ_IMPLEMENTATION_PROMPT §3):

- DS2-1 lazy reader: the source does not snapshot the facts table in on_start;
  a session's 13:00 fact published *after* startup is visible at the 13:00 bar
  (the live flow — the pre-signal hook writes it before on_bar, DS2-2).
- DS2-3 VIX gate: `vix_at_checkpoint or vix_close` — the intraday 13:00 India
  VIX wins on live rows; stores without the column (the frozen corpus) fall back
  to the EOD `vix_close`, which is what keeps the corpus stream byte-identical.
"""
from datetime import datetime, time
from pathlib import Path

import duckdb
import pytest

from core.events import OHLCVBar

from strategies.nifty_shield_v1 import build_signal_source
from strategies.nifty_shield_v1.facts import RegimeFactsReader

UTC_TS = datetime(2026, 6, 5, 13, 0, 0)        # the 13:00 checkpoint bar


def _bar(hour: int, minute: int) -> OHLCVBar:
    return OHLCVBar(symbol="NSE_INDEX|Nifty 50",
                    timestamp=datetime(2026, 6, 5, hour, minute, 0),
                    open=24000.0, high=24000.0, low=24000.0,
                    close=24000.0, volume=0.0)


def _make_facts_db(path: Path, rows, with_checkpoint_col: bool = True) -> None:
    """Write (drop-and-recreate) a day_type_facts table; each row is a dict."""
    con = duckdb.connect(str(path))
    cols = ["session_date", "checkpoint", "regime", "regime_confidence",
            "vix_close", "regime_fact_version", "model_hash",
            "produced_by", "trained_on"]
    if with_checkpoint_col:
        cols.append("vix_at_checkpoint")
    con.execute("DROP TABLE IF EXISTS day_type_facts")
    con.execute("CREATE TABLE day_type_facts ("
                + ", ".join(f"{c} VARCHAR" for c in cols) + ")")
    for row in rows:
        values = [str(row.get(c)) if row.get(c) is not None else None
                  for c in cols]
        con.execute(f"INSERT INTO day_type_facts VALUES ({', '.join('?' for _ in cols)})",
                    values)
    con.close()


def _fact_row(regime="Choppy", conf=0.70, vix_close=15.0,
              vix_at_checkpoint=None, session="2026-06-05"):
    row = {
        "session_date": session, "checkpoint": "13pm", "regime": regime,
        "regime_confidence": conf, "vix_close": vix_close,
        "regime_fact_version": "dt-v2.0-train_thru2025",
        "model_hash": "x" * 64, "produced_by": "offline@test",
        "trained_on": "test",
    }
    if vix_at_checkpoint is not None:
        row["vix_at_checkpoint"] = vix_at_checkpoint
    return row


def _drive(source, bars):
    source.on_start()
    try:
        return [source.on_bar(b) for b in bars]
    finally:
        source.on_stop()


# --------------------------------------------------------------------------- #
# DS2-1: a fact published after on_start is visible at the 13:00 bar
# --------------------------------------------------------------------------- #
def test_lazy_reader_sees_fact_published_after_on_start(tmp_path):
    db = tmp_path / "facts.duckdb"
    _make_facts_db(db, [])                       # empty at startup
    cfg = {"facts_db_path": str(db)}
    source = build_signal_source(cfg)
    source.on_start()

    assert source.on_bar(_bar(9, 15)) == []      # nothing yet this session

    _make_facts_db(db, [_fact_row()])            # live publish happens now
    out = source.on_bar(_bar(13, 0))
    assert out                                     # the 13:00 fact was seen
    assert all(s.timestamp.time() == time(13, 0) for s in out)
    source.on_stop()


def test_reader_requeries_on_miss(tmp_path):
    db = tmp_path / "facts.duckdb"
    _make_facts_db(db, [])
    reader = RegimeFactsReader(str(db))
    assert reader.fact(UTC_TS.date()) is None     # miss cached
    _make_facts_db(db, [_fact_row()])             # fact arrives later
    assert reader.fact(UTC_TS.date()) is not None  # re-query sees it


# --------------------------------------------------------------------------- #
# DS2-3: the VIX gate reads vix_at_checkpoint when present, else vix_close
# --------------------------------------------------------------------------- #
def test_vix_at_checkpoint_gates_skip(tmp_path):
    db = tmp_path / "facts.duckdb"
    _make_facts_db(db, [_fact_row(vix_close=15.0, vix_at_checkpoint=21.0)])
    out = _drive(build_signal_source({"facts_db_path": str(db)}), [_bar(13, 0)])
    assert out == [[]]                            # 21.0 > vix_skip_above(20) -> skip


def test_vix_at_checkpoint_overrides_eod_vix_close(tmp_path):
    # EOD vix_close says 21 (would skip); the live 13:00 value 15 is below the
    # skip gate -> the source must NOT skip (the checkpoint VIX is authoritative).
    db = tmp_path / "facts.duckdb"
    _make_facts_db(db, [_fact_row(vix_close=21.0, vix_at_checkpoint=15.0)])
    out = _drive(build_signal_source({"facts_db_path": str(db)}), [_bar(13, 0)])
    assert out[0]                                  # entry fired


def test_falls_back_to_vix_close_without_checkpoint_column(tmp_path):
    # Store without vix_at_checkpoint (the frozen-corpus shape): the reader
    # returns None for it and the source gates on the EOD vix_close.
    db = tmp_path / "facts.duckdb"
    _make_facts_db(db, [_fact_row(vix_close=15.0)],
                   with_checkpoint_col=False)
    out = _drive(build_signal_source({"facts_db_path": str(db)}), [_bar(13, 0)])
    assert out[0]                                  # 15 < 20 -> entry


def test_vix_at_checkpoint_above_reduce_still_emits_with_flag(tmp_path):
    # 16 < vix_reduce_above threshold crossing: vix_at_checkpoint=17 on a
    # strangle structure still emits (vix_reduce is non-strangle only) — the
    # checkpoint VIX flows into structure selection and vix_reduce metadata.
    db = tmp_path / "facts.duckdb"
    _make_facts_db(db, [_fact_row(regime="Choppy", vix_close=17.0,
                                  vix_at_checkpoint=17.0)])
    out = _drive(build_signal_source({"facts_db_path": str(db)}), [_bar(13, 0)])
    assert out[0]
    assert out[0][0].metadata["structure"] == "short_strangle"
