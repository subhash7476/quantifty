"""
NiftyShield — option-chain poller tests (E7-4 marks populator, implementation
prompt §4). New files only; synthetic/stub chain — no network.

- §2.1 concurrent read-while-write: the reader NEVER raises
  `MarksSourceUnavailable` and sees marks for known legs — the load-bearing test.
- §2.2 one `snapshot_timestamp` per cycle; the reader returns ALL present legs.
- bootstrap: an empty-but-valid cache passes `check_available()` and returns
  `{}` (F3), not a raise.
- atomic swap: a retried/interrupted replace always leaves a readable
  single-snapshot target (never partial, never deleted).
"""
from __future__ import annotations

import os
import threading
import time

import duckdb
import pytest

from core.data.options_provider import OptionChainRow
from core.execution.options.nifty_shield_marks import (
    ChainSnapshotMarksSource, MarksSourceUnavailable,
)

from scripts.nifty_shield_paper.chain_poller import ChainPoller

EXPIRY = "2026-08-11"
UNDERLYING = "NSE_INDEX|Nifty 50"
_STRIKES = [24000, 24050, 24100, 24150]


def _synthetic_rows() -> list:
    rows = []
    for strike in _STRIKES:
        for ot, ltp in (("CE", 100.0), ("PE", 60.0)):
            rows.append(OptionChainRow(
                strike=float(strike),
                option_type=ot,
                instrument_key=f"NSE_INDEX|{ot}{strike}",
                tradingsymbol=f"NIFTY11AUG26{strike}{ot}",
                expiry=EXPIRY,
                ltp=ltp, oi=100, volume=10,
                iv=0.14, delta=0.5, lot_size=75, underlying_ltp=24100.0,
            ))
    return rows


LEG_SYMBOLS = [r.tradingsymbol for r in _synthetic_rows()]


def _make_poller(tmp_path) -> ChainPoller:
    cache = tmp_path / "chain_cache.duckdb"
    return ChainPoller(cache_path=str(cache))


# --------------------------------------------------------------------------- #
# §2.1 — the load-bearing guarantee: concurrent read while writing never raises
# --------------------------------------------------------------------------- #
def test_concurrent_read_never_raises(tmp_path):
    """Genuine stressor (R1 re-review gate): ≥30 write cycles at ≤5 ms spacing.
    Pre-fix this fails most runs on Windows (rename-vs-open race -> reader's
    `_connect` raises "Cannot open file ... being used by another process" ->
    MarksSourceUnavailable); post-fix the bounded reader retry rides it through,
    so the test gates the guarantee deterministically instead of ~1/3 of runs."""
    poller = _make_poller(tmp_path)
    poller.bootstrap()
    rows = _synthetic_rows()

    stop = threading.Event()
    errors: list = []
    seen_marks: list = []
    src = ChainSnapshotMarksSource(str(poller.cache_path))

    def _reader() -> None:
        while not stop.is_set():
            try:
                marks = src.marks(LEG_SYMBOLS)
            except MarksSourceUnavailable as exc:
                errors.append(exc)
            else:
                if marks:
                    seen_marks.append(marks)

    reader = threading.Thread(target=_reader, name="chain-reader")
    reader.start()
    try:
        for _ in range(30):
            poller.write_cycle(rows, EXPIRY, underlying=UNDERLYING)
            time.sleep(0.005)                # ≤5 ms spacing between cycles
    finally:
        stop.set()
        reader.join(timeout=60)

    assert not errors, f"reader hit MarksSourceUnavailable: {errors[:3]}"
    assert seen_marks, "reader never observed a populated cache"
    assert len(seen_marks[-1]) == len(LEG_SYMBOLS)


# --------------------------------------------------------------------------- #
# §2.2 — one explicit snapshot_timestamp per cycle; all legs priceable
# --------------------------------------------------------------------------- #
def test_one_snapshot_timestamp_per_cycle(tmp_path):
    poller = _make_poller(tmp_path)
    poller.bootstrap()
    rows = _synthetic_rows()
    poller.write_cycle(rows, EXPIRY, underlying=UNDERLYING)

    con = duckdb.connect(str(poller.cache_path), read_only=True)
    try:
        timestamps = con.execute(
            "SELECT DISTINCT snapshot_timestamp FROM option_chain_snapshot"
        ).fetchall()
        total = con.execute(
            "SELECT COUNT(*) FROM option_chain_snapshot").fetchone()[0]
    finally:
        con.close()
    assert len(timestamps) == 1, \
        f"expected one snapshot timestamp, got {len(timestamps)}"
    assert total == len(rows)

    src = ChainSnapshotMarksSource(str(poller.cache_path))
    marks = src.marks(LEG_SYMBOLS)
    assert len(marks) == len(LEG_SYMBOLS), \
        "reader must price EVERY present leg (not just the MAX-timestamp row)"


# --------------------------------------------------------------------------- #
# F3 — bootstrap yields a valid-but-empty cache
# --------------------------------------------------------------------------- #
def test_bootstrap_empty_cache_check_available(tmp_path):
    poller = _make_poller(tmp_path)
    poller.bootstrap()
    src = ChainSnapshotMarksSource(str(poller.cache_path))
    src.check_available()                    # must NOT raise
    assert src.marks(LEG_SYMBOLS) == {}      # valid empty -> {}, not a raise


def test_bootstrap_rebuilds_corrupt_cache(tmp_path):
    poller = _make_poller(tmp_path)
    poller.cache_path.parent.mkdir(parents=True, exist_ok=True)
    poller.cache_path.write_bytes(b"not a duckdb file at all")
    poller.bootstrap()
    src = ChainSnapshotMarksSource(str(poller.cache_path))
    src.check_available()
    assert src.marks(LEG_SYMBOLS) == {}


# --------------------------------------------------------------------------- #
# Atomic swap — retried/interrupted replace always leaves a valid target
# --------------------------------------------------------------------------- #
def test_atomic_swap_retry_leaves_valid_db(tmp_path, monkeypatch):
    poller = _make_poller(tmp_path)
    poller.bootstrap()
    rows = _synthetic_rows()

    real_replace = os.replace
    calls = {"n": 0}

    def flaky(src, dst):
        calls["n"] += 1
        if calls["n"] <= 2:                 # transient sharing violations
            raise PermissionError("simulated sharing violation")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", flaky)
    poller.write_cycle(rows, EXPIRY, underlying=UNDERLYING)
    assert calls["n"] >= 3, "replace should have been retried"

    src = ChainSnapshotMarksSource(str(poller.cache_path))
    marks = src.marks(LEG_SYMBOLS)
    assert len(marks) == len(LEG_SYMBOLS)   # readable, never partial/deleted


def test_interrupted_tmp_recovered(tmp_path):
    """A leftover partial tmp from an interrupted cycle must be overwritten, not
    accumulate or corrupt the next cycle."""
    poller = _make_poller(tmp_path)
    poller.bootstrap()
    poller._tmp_path.write_bytes(b"garbage from an interrupted cycle")
    poller.write_cycle(_synthetic_rows(), EXPIRY, underlying=UNDERLYING)

    src = ChainSnapshotMarksSource(str(poller.cache_path))
    assert len(src.marks(LEG_SYMBOLS)) == len(LEG_SYMBOLS)
    con = duckdb.connect(str(poller.cache_path), read_only=True)
    try:
        total = con.execute(
            "SELECT COUNT(*) FROM option_chain_snapshot").fetchone()[0]
    finally:
        con.close()
    assert total == len(LEG_SYMBOLS)        # single snapshot, no accumulation


# --------------------------------------------------------------------------- #
# R1 — reader-side bounded retry on the Windows rename-vs-open race (F3 kept)
# --------------------------------------------------------------------------- #
def _patch_connect(monkeypatch):
    import core.execution.options.nifty_shield_marks as marks_mod
    return marks_mod


def test_connect_retries_transient_then_succeeds(tmp_path, monkeypatch):
    """R1: an open that collides with the poller's atomic swap (transient
    "being used by another process") is retried, not raised."""
    poller = _make_poller(tmp_path)
    poller.bootstrap()                       # a valid cache exists at the target
    src = ChainSnapshotMarksSource(str(poller.cache_path))
    marks_mod = _patch_connect(monkeypatch)
    real_connect = marks_mod.duckdb.connect
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise IOError('IO Error: Cannot open file "...chain_cache.duckdb": '
                          "The process cannot access the file because it is "
                          "being used by another process.")
        return real_connect(*a, **k)

    monkeypatch.setattr(marks_mod.duckdb, "connect", flaky)
    con = src._connect()
    con.close()
    assert calls["n"] == 3


def test_connect_raises_after_transient_bound(tmp_path, monkeypatch):
    """R1: a persistently contended/unavailable cache still raises (F3) — after
    the retry bound, never a silent success."""
    poller = _make_poller(tmp_path)
    poller.bootstrap()
    src = ChainSnapshotMarksSource(str(poller.cache_path))
    marks_mod = _patch_connect(monkeypatch)
    calls = {"n": 0}

    def always_fail(*a, **k):
        calls["n"] += 1
        raise IOError("IO Error: Cannot open file: The process cannot access "
                      "the file because it is being used by another process.")

    monkeypatch.setattr(marks_mod.duckdb, "connect", always_fail)
    with pytest.raises(MarksSourceUnavailable):
        src._connect()
    assert calls["n"] == ChainSnapshotMarksSource._CONNECT_RETRIES


def test_connect_raises_immediately_on_non_transient(tmp_path, monkeypatch):
    """R1: a non-transient failure (e.g. corrupt DB) raises on the FIRST attempt
    — no pointless retry, F3 loudness preserved."""
    poller = _make_poller(tmp_path)
    poller.bootstrap()
    src = ChainSnapshotMarksSource(str(poller.cache_path))
    marks_mod = _patch_connect(monkeypatch)
    calls = {"n": 0}

    def non_transient(*a, **k):
        calls["n"] += 1
        raise IOError("Failed to deserialize the database file")

    monkeypatch.setattr(marks_mod.duckdb, "connect", non_transient)
    with pytest.raises(MarksSourceUnavailable):
        src._connect()
    assert calls["n"] == 1
