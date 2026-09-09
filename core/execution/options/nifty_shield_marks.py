"""NiftyShield — option-marks feed (E007 E7-4, datasheet §11 open item).

The PAPER fill price for a struck option leg must be a REAL option-chain mark —
never the underlying's bar close and never a synthetic/flat-IV mark. The
external backtest's Sharpe 9.40 was flagged optimistic precisely for synthetic
marks; PAPER must not repeat that.

This module defines the marks-seam the execution layer prices legs against:

- `OptionMarksSource` — the seam (per-leg `marks(symbols)` -> price map).
- `StaticMarksSource` — deterministic marks (tests, smoke run).
- `ChainSnapshotMarksSource` — REAL Upstox V3 option-chain marks read from the
  latest `option_chain_snapshot` DuckDB cache (tradingsymbol -> ltp).

F3 (loud infra failures): `ChainSnapshotMarksSource` distinguishes TWO absence
classes, because the two mean different things and one of them must be LOUD:

- **Cache unavailable** (file missing, DB corrupt, query/parse failure) — raises
  `MarksSourceUnavailable`. A misconfigured live window must not silently skip
  every entry as "missing marks" (the repo's documented "bare except turns 'we
  failed' into 'the source doesn't have it'" pitfall).
- **Market closed / strikes not in the snapshot** (cache valid, query succeeds,
  no rows) — returns `{}` (a legitimate no-mark, journaled as an entry skip).

`check_available()` is the startup validation the runner calls before a live
window opens: a broken cache refuses to start, it never silently runs.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

import duckdb


class MarksSourceUnavailable(RuntimeError):
    """The marks cache is absent/corrupt/unreadable — infra, not market state."""


class OptionMarksSource(ABC):
    """Per-symbol option premium marks for a set of struck legs."""

    @abstractmethod
    def marks(self, symbols: List[str]) -> Dict[str, float]:
        """Return the current premium for each symbol it can price (subset of
        `symbols`); symbols without a real mark are simply absent."""

    @abstractmethod
    def implied_vols(self, symbols: List[str]) -> Dict[str, float]:
        """Per-symbol implied vol as a DECIMAL (0.1103, not 11.03), from the
        same snapshot as `marks`.

        The credit gate's reference price needs the vol of the legs it is
        pricing. It used to be handed India VIX flat across every leg, which
        overstates a 6-DTE vertical by ~30% — VIX is a 30-day variance-swap
        strip, not an ATM vol, and one flat number cannot sit on both legs of a
        spread (`NIFTY_SHIELD_CREDIT_FLOOR_CALIBRATION_2026-09-09.md`).

        ABSTRACT ON PURPOSE, for the reason `instrument_keys` records below: a
        concrete `return {}` default is inherited silently by wrappers, and the
        gate would then read as permanently unavailable instead of failing loudly
        at construction.
        """

    @abstractmethod
    def instrument_keys(self, symbols: List[str]) -> Dict[str, str]:
        """Broker instrument keys for the symbols this source can identify.

        Needed to ask the broker for the structure's basket margin; a source
        with no broker identity returns {}, and the caller then treats the
        margin as unavailable rather than guessing a key.

        ABSTRACT ON PURPOSE. This began as a concrete `return {}` default, and
        `RecordingMarksSource` — the wrapper every recorded LIVE session runs
        through — inherited it instead of forwarding. The live window then
        reported no keys for legs whose keys were sitting in the cache, and
        skipped its 13:00 entry as "broker basket margin unavailable"
        (2026-09-08, entry lost). A default that means "absent" lets a
        partial decorator answer on behalf of a source that has the data.
        Abstract turns that into a TypeError the moment the class is
        constructed, which is a startup crash instead of a missed trade.
        """

    @abstractmethod
    def snapshot_age_s(self, now: Optional[datetime] = None) -> Optional[float]:
        """Seconds since this source's newest data, or None if it has no clock.

        Abstract for the same reason as `instrument_keys` — see there.
        """


class StaticMarksSource(OptionMarksSource):
    """A fixed mark table — deterministic, for tests and the REPLAY smoke run."""

    def __init__(self, marks: Dict[str, float],
                 implied_vols: Optional[Dict[str, float]] = None):
        self._marks = dict(marks)
        self._ivs = dict(implied_vols or {})

    def marks(self, symbols: List[str]) -> Dict[str, float]:
        return {s: self._marks[s] for s in symbols if s in self._marks}

    def implied_vols(self, symbols: List[str]) -> Dict[str, float]:
        return {s: self._ivs[s] for s in symbols if s in self._ivs}

    def instrument_keys(self, symbols: List[str]) -> Dict[str, str]:
        return {}                    # no broker identity, stated explicitly

    def snapshot_age_s(self, now: Optional[datetime] = None) -> Optional[float]:
        return None                  # no clock, stated explicitly


class ChainSnapshotMarksSource(OptionMarksSource):
    """Real option-chain marks from the latest option_chain_snapshot snapshot.

    Reads `ltp` for each requested `tradingsymbol` from the most recent
    `snapshot_timestamp` in the cache DB. Raises `MarksSourceUnavailable` when
    the cache itself is unavailable (F3); returns {} only for a VALID cache with
    no rows for the requested symbols (market closed / strikes absent).

    R1 (chain-poller review): the poller publishes each snapshot via an atomic
    `os.replace` into this file. On Windows, when that rename overlaps a fresh
    `duckdb.connect(read_only=True)` here, the OS hands the sharing violation to
    whichever side loses — occasionally THIS open. That transient millisecond
    collision must not read as "cache unavailable" (fatal under F3 at the 13:00
    entry checkpoint and every exit). `_connect()` therefore retries a small
    bounded number of times for a transient open failure, and raises
    `MarksSourceUnavailable` only after the bound (or immediately for a
    non-transient error) — a persistently unavailable cache still raises, so F3
    is preserved.
    """

    _CONNECT_RETRIES = 5
    _CONNECT_RETRY_DELAY_S = 0.05

    def __init__(self, db_path: str, table: str = "option_chain_snapshot"):
        self._db_path = db_path
        self._table = table

    def check_available(self) -> None:
        """Startup gate: raise MarksSourceUnavailable if the cache cannot open."""
        self._connect()

    def _connect(self):
        last = None
        for attempt in range(self._CONNECT_RETRIES):
            try:
                return duckdb.connect(self._db_path, read_only=True)
            except Exception as exc:
                last = exc
                transient = (
                    "being used by another process" in str(exc)
                    or "Conflicting lock" in str(exc)
                    or "Cannot open file" in str(exc)
                )
                if not transient or attempt == self._CONNECT_RETRIES - 1:
                    raise MarksSourceUnavailable(
                        f"option-chain cache unavailable at {self._db_path}: {exc}"
                    ) from exc
                time.sleep(self._CONNECT_RETRY_DELAY_S)
        raise MarksSourceUnavailable(str(last))  # unreachable; defensive

    def _latest_timestamp(self, con) -> object:
        try:
            row = con.execute(
                f"SELECT MAX(snapshot_timestamp) FROM {self._table}"
            ).fetchone()
        except Exception as exc:
            raise MarksSourceUnavailable(
                f"option-chain cache query failed (table {self._table!r}): {exc}"
            ) from exc
        return row[0] if row else None

    def marks(self, symbols: List[str]) -> Dict[str, float]:
        if not symbols:
            return {}
        con = self._connect()
        try:
            latest = self._latest_timestamp(con)
            if latest is None:
                return {}                    # valid cache, no snapshot yet
            placeholders = ", ".join("?" for _ in symbols)
            try:
                rows = con.execute(
                    f"SELECT tradingsymbol, ltp FROM {self._table} "
                    f"WHERE snapshot_timestamp = ? "
                    f"AND tradingsymbol IN ({placeholders})",
                    [latest] + list(symbols),
                ).fetchall()
            except Exception as exc:
                raise MarksSourceUnavailable(
                    f"option-chain cache query failed: {exc}") from exc
        finally:
            con.close()
        return {sym: float(ltp) for sym, ltp in rows
                if ltp is not None and float(ltp) > 0.0}

    def implied_vols(self, symbols: List[str]) -> Dict[str, float]:
        """Per-leg IV from the same snapshot the marks come from.

        The feed publishes IV in PERCENT (11.03); the gate's Black-Scholes wants
        a decimal, so it is divided here — at the one place that knows the feed's
        unit — rather than at the call site.
        """
        if not symbols:
            return {}
        con = self._connect()
        try:
            latest = self._latest_timestamp(con)
            if latest is None:
                return {}                    # valid cache, no snapshot yet
            placeholders = ", ".join("?" for _ in symbols)
            try:
                rows = con.execute(
                    f"SELECT tradingsymbol, iv FROM {self._table} "
                    f"WHERE snapshot_timestamp = ? "
                    f"AND tradingsymbol IN ({placeholders})",
                    [latest] + list(symbols),
                ).fetchall()
            except Exception as exc:
                raise MarksSourceUnavailable(
                    f"option-chain cache query failed: {exc}") from exc
        finally:
            con.close()
        return {sym: float(iv) / 100.0 for sym, iv in rows
                if iv is not None and float(iv) > 0.0}

    def snapshot_age_s(self, now: Optional[datetime] = None) -> Optional[float]:
        """Seconds since the newest snapshot, or None if the cache has none.

        The exit manager needs this from 15:29 to 15:35: the underlying stops
        printing at the auction, so bars no longer prove the feed is alive and
        the snapshot becomes the SOLE input to a TP/SL decision. A stalled
        poller would otherwise be priced as a flat market.
        """
        con = self._connect()
        try:
            latest = self._latest_timestamp(con)
        finally:
            con.close()
        if latest is None:
            return None
        return (now or datetime.now()).timestamp() - latest.timestamp()

    def instrument_keys(self, symbols: List[str]) -> Dict[str, str]:
        """Upstox instrument_key per tradingsymbol, from the latest snapshot.

        Read in its own query against `MAX(snapshot_timestamp)` rather than
        alongside the marks: a leg's instrument_key is a property of the
        contract, not of the tick, so a poller write landing between the two
        reads cannot make the pair disagree the way two price reads could.
        """
        if not symbols:
            return {}
        con = self._connect()
        try:
            latest = self._latest_timestamp(con)
            if latest is None:
                return {}
            placeholders = ", ".join("?" for _ in symbols)
            try:
                rows = con.execute(
                    f"SELECT tradingsymbol, instrument_key FROM {self._table} "
                    f"WHERE snapshot_timestamp = ? "
                    f"AND tradingsymbol IN ({placeholders})",
                    [latest] + list(symbols),
                ).fetchall()
            except Exception as exc:
                raise MarksSourceUnavailable(
                    f"option-chain cache query failed: {exc}") from exc
        finally:
            con.close()
        return {sym: key for sym, key in rows if key}
