# CAS Adaptation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make this repo tell the truth about the post-2026-08-03 market structure — correct session windows per segment, honestly-labelled synthetic bars, live capture through the extended derivatives session, and research gates that cannot certify fabricated data as tradeable.

**Architecture:** One new date-keyed, segment-named session-schedule module becomes the single authority for "when is X open"; `MarketHours`/`MarketSession` delegate to it rather than holding constants. A point-in-time CAS-category table (derived from futures bhavcopy, which is genuinely PIT) tells us which symbols auction on which dates. The existing-but-lying `is_synthetic` column is then populated truthfully, both retroactively and going forward, and every downstream consumer filters on it.

**Tech Stack:** Python 3.10+, DuckDB, pytest. No new dependencies.

## Global Constraints

- **CAS effective date: 2026-08-03.** Pre-open alignment (2026-09-07) is out of scope for this plan.
- **Segment windows post-CAS:** cash Category I continuous 09:15–15:15; cash auction 15:15–15:35; cash Category II continuous 09:15–15:30; derivatives 09:15–15:40. Pre-CAS: cash 09:15–15:30, derivatives 09:15–15:30, no auction.
- **Never flip `MARKET_CLOSE` to a later bare constant.** `market_ingestor` gates equity aggregation on the same predicate; a later close fabricates more carry-forward bars. All widening must be segment-scoped.
- **Backfills are copy-first.** Snapshot before mutating any store — per the CLAUDE.md pitfall "take the baseline copy *before* the write." Mutate only from committed, re-runnable code.
- **No schema migration is needed.** `is_synthetic BOOLEAN` already exists in the per-day 1m store and is uniformly `FALSE`. The defect is population, not shape.
- **Shell is Unix syntax** (forward slashes, `/dev/null`).
- **Commits:** conventional-commit format (`feat:`, `fix:`, `test:`, `docs:`).
- Source of truth for what each item means: `docs/reports/CAS_ADAPTATION_REGISTER.md`. Register IDs (A1, B4, …) are cited per task.

---

## Phase 0 — Operator decisions — **BOTH RESOLVED 2026-08-27, no code required**

Revised after the `isd-program-reassessment` handoff (branch head `c3bb6bd`). Neither decision remains open; both outcomes are recorded here so the tasks downstream of them are correctly scoped.

### D1 · ISD SEALED window (register A5) — **MOOT**

The ISD battery **closed at TRAIN** (commit `05f5ed2`, both families FAIL — F1 sign negative, F4 net-spread gate). There is no sealed read to protect and no exit to re-pin, so the straddle analysis is history rather than a live risk. **Task 12 is withdrawn** (see below); the closure is recorded in the register instead.

### D2 · A-construct exit (register A6) — **RESOLVED: 15:14**

The operator pinned the exit at the **15:14 bar close** as decision **D6** (commit `d33e762`): "last continuous print all eras, auction window untraded." This is option 1 from the original slate — the era-based rule that register A2 requires, since the index carries `volume=0` always and the auction bar cannot be detected from index data.

The A construct itself was subsequently **retired at HOLDOUT** (commit `c72fa63`: TRAIN PASS at net +1.27 bp, p 0.003; HOLDOUT FAIL at net −0.22 bp, p 0.15), with its SEALED window (873 sessions) untouched. D6 nonetheless stands as the repo's settled convention for an index intraday exit, and **Task 11 still implements the `era_for()` boundary** — the era logic is needed by the certifier regardless of that one construct's fate.

> **Branch note:** `scripts/a_index_intraday/certify_index_slice.py` exists **only on `isd-program-reassessment`** (commits `b1f22f7`/`0f67798`); `main` has no `scripts/a_index_intraday/` at all. Execute this plan **on that branch**, or merge it to main first. Tasks 1–10 and 13–14 are branch-independent.

---

## File Structure

**New:**
- `core/market/__init__.py` — package marker
- `core/market/session_schedule.py` — date-keyed segment session windows (the single authority)
- `scripts/cas/__init__.py` — package marker
- `scripts/cas/build_cas_category.py` — PIT Category I/II membership from futures bhavcopy
- `scripts/cas/mark_synthetic_bars.py` — retroactive `is_synthetic` backfill over post-CAS 1m files
- `tests/market/test_session_schedule.py`
- `tests/cas/test_cas_category.py`
- `tests/cas/test_mark_synthetic.py`

**Modified:**
- `core/database/utils/market_hours.py` — delegate to schedule; add segment API
- `core/database/utils/market_session.py:41-42` — delegate session end
- `core/database/ingestors/db_tick_aggregator.py:57-69` — write truthful `is_synthetic`
- `scripts/market_ingestor.py:285` — gate on any-segment-open
- `scripts/nifty_shield_paper/chain_poller.py:375` — gate on derivatives
- `core/options_wall/poller.py:182` — gate on derivatives
- `core/runtime/driver.py:883` — segment-aware telemetry
- `scripts/ingest_reference_1m.py:47-48` — schedule-derived session end
- `scripts/isd/gate_contiguity.py` — tradeability arm
- `core/analytics/day_features.py:30-40` — exclude synthetic bars
- `scripts/a_index_intraday/certify_index_slice.py:179-181` — third era
- `scripts/isd/battery_features.py:32` — exit re-pin (gated on D1)
- `core/execution/equity/intraday_fees.py` — square-off deadline constant
- `CLAUDE.md`, `docs/reports/CAS_ADAPTATION_REGISTER.md`

---

## Phase 1 — Session-time authority

### Task 1: Session schedule module

Register: B1, B2, C1, C2.

**Files:**
- Create: `core/market/__init__.py`, `core/market/session_schedule.py`
- Test: `tests/market/test_session_schedule.py`

**Interfaces:**
- Consumes: nothing (leaf module, stdlib only).
- Produces: `CAS_EFFECTIVE: date`; `Segment` string literals `"cash_cat1" | "cash_cat2" | "cash_auction" | "derivatives"`; `session_window(segment: str, on: date) -> tuple[time, time] | None`; `is_open(segment: str, dt: datetime) -> bool`; `any_open(dt: datetime) -> bool`. All consumed by Tasks 2, 3, 7, 8, 9.

- [ ] **Step 1: Write the failing test**

Create `tests/market/test_session_schedule.py`:

```python
from datetime import date, datetime, time

import pytest

from core.market.session_schedule import (
    CAS_EFFECTIVE, any_open, is_open, session_window,
)


def test_cas_effective_date_is_2026_08_03():
    assert CAS_EFFECTIVE == date(2026, 8, 3)


def test_pre_cas_cash_closes_at_1530():
    assert session_window("cash_cat1", date(2026, 7, 31)) == (time(9, 15), time(15, 30))


def test_pre_cas_has_no_auction():
    assert session_window("cash_auction", date(2026, 7, 31)) is None


def test_pre_cas_derivatives_close_at_1530():
    assert session_window("derivatives", date(2026, 7, 31)) == (time(9, 15), time(15, 30))


def test_post_cas_cat1_continuous_ends_1515():
    assert session_window("cash_cat1", date(2026, 8, 3)) == (time(9, 15), time(15, 15))


def test_post_cas_cat2_continuous_still_ends_1530():
    assert session_window("cash_cat2", date(2026, 8, 3)) == (time(9, 15), time(15, 30))


def test_post_cas_auction_window():
    assert session_window("cash_auction", date(2026, 8, 3)) == (time(15, 15), time(15, 35))


def test_post_cas_derivatives_extend_to_1540():
    assert session_window("derivatives", date(2026, 8, 3)) == (time(9, 15), time(15, 40))


def test_is_open_excludes_end_boundary():
    assert is_open("cash_cat1", datetime(2026, 8, 3, 15, 14))
    assert not is_open("cash_cat1", datetime(2026, 8, 3, 15, 15))


def test_derivatives_open_while_cat1_cash_is_shut():
    dt = datetime(2026, 8, 3, 15, 35)
    assert not is_open("cash_cat1", dt)
    assert is_open("derivatives", dt)


def test_any_open_true_during_derivatives_only_window():
    assert any_open(datetime(2026, 8, 3, 15, 38))
    assert not any_open(datetime(2026, 8, 3, 15, 41))


def test_unknown_segment_raises():
    with pytest.raises(KeyError):
        session_window("equities", date(2026, 8, 3))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/market/test_session_schedule.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.market'`

- [ ] **Step 3: Write minimal implementation**

Create `core/market/__init__.py` (empty file).

Create `core/market/session_schedule.py`:

```python
"""Date-keyed, segment-named NSE session windows.

The single authority for "when is segment X open on date D". SEBI's Closing
Auction Session (circular 2026-01-16, operative 2026-08-03) split what used to
be one 09:15-15:30 session into four differently-bounded segments, so a single
MARKET_CLOSE constant can no longer express the truth.

Era-schedule shape mirrors core/execution/equity/intraday_fees.py's
_STT_INTRADAY_SCHEDULE: newest era last, resolved by scanning for the latest
entry whose effective date is <= the queried date.
"""
from __future__ import annotations

from datetime import date, datetime, time

CAS_EFFECTIVE = date(2026, 8, 3)

SEGMENTS = ("cash_cat1", "cash_cat2", "cash_auction", "derivatives")

_SCHEDULE = (
    (date(1900, 1, 1), {
        "cash_cat1": (time(9, 15), time(15, 30)),
        "cash_cat2": (time(9, 15), time(15, 30)),
        "cash_auction": None,
        "derivatives": (time(9, 15), time(15, 30)),
    }),
    (CAS_EFFECTIVE, {
        "cash_cat1": (time(9, 15), time(15, 15)),
        "cash_cat2": (time(9, 15), time(15, 30)),
        "cash_auction": (time(15, 15), time(15, 35)),
        "derivatives": (time(9, 15), time(15, 40)),
    }),
)


def session_window(segment: str, on: date):
    """(start, end) for `segment` on `on`, or None if the segment does not exist."""
    if segment not in SEGMENTS:
        raise KeyError(f"unknown segment {segment!r}; expected one of {SEGMENTS}")
    resolved = _SCHEDULE[0][1]
    for effective_from, windows in _SCHEDULE:
        if on >= effective_from:
            resolved = windows
    return resolved[segment]


def is_open(segment: str, dt: datetime) -> bool:
    """True if `segment` is open at `dt`. End boundary is exclusive."""
    window = session_window(segment, dt.date())
    if window is None:
        return False
    start, end = window
    return start <= dt.time() < end


def any_open(dt: datetime) -> bool:
    """True if any segment is open at `dt`."""
    return any(is_open(seg, dt) for seg in SEGMENTS)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/market/test_session_schedule.py -v`
Expected: PASS, 12 passed

- [ ] **Step 5: Commit**

```bash
git add core/market/__init__.py core/market/session_schedule.py tests/market/test_session_schedule.py
git commit -m "feat: date-keyed segment session schedule for CAS"
```

---

### Task 2: MarketHours delegates to the schedule

Register: B1, B7, C1, C2. **This task must not change `is_market_open()`'s meaning for pre-CAS dates** — `tests/runtime/test_driver_telemetry_publish.py:104` evaluates it against historical bar timestamps.

**Files:**
- Modify: `core/database/utils/market_hours.py:6-9` (docstring), `:44-47` (constants), `:132-153` (`is_market_open`), `:177-197` (`is_post_market`)
- Test: `tests/database/utils/test_market_hours_cas.py` (create)

**Interfaces:**
- Consumes: `core.market.session_schedule.{is_open, any_open, session_window}` from Task 1.
- Produces: `MarketHours.is_market_open(dt=None, segment="cash_cat1") -> bool`; `MarketHours.is_derivatives_open(dt=None) -> bool`; `MarketHours.is_any_open(dt=None) -> bool`. Consumed by Tasks 7, 8, 9.

- [ ] **Step 1: Write the failing test**

Create `tests/database/utils/test_market_hours_cas.py`:

```python
from datetime import datetime

from core.database.utils.market_hours import MarketHours


def test_pre_cas_behaviour_is_unchanged():
    # 2026-07-31 is a Friday, not an NSE holiday.
    assert MarketHours.is_market_open(datetime(2026, 7, 31, 15, 25))
    assert not MarketHours.is_market_open(datetime(2026, 7, 31, 15, 31))


def test_post_cas_cat1_cash_shuts_at_1515():
    # 2026-08-03 is a Monday, not an NSE holiday.
    assert MarketHours.is_market_open(datetime(2026, 8, 3, 15, 14))
    assert not MarketHours.is_market_open(datetime(2026, 8, 3, 15, 20))


def test_post_cas_derivatives_open_until_1540():
    assert MarketHours.is_derivatives_open(datetime(2026, 8, 3, 15, 38))
    assert not MarketHours.is_derivatives_open(datetime(2026, 8, 3, 15, 41))


def test_is_any_open_spans_the_derivatives_tail():
    assert MarketHours.is_any_open(datetime(2026, 8, 3, 15, 38))


def test_holidays_and_weekends_still_shut_every_segment():
    # 2026-08-15 is a Saturday.
    assert not MarketHours.is_market_open(datetime(2026, 8, 15, 11, 0))
    assert not MarketHours.is_derivatives_open(datetime(2026, 8, 15, 11, 0))
    assert not MarketHours.is_any_open(datetime(2026, 8, 15, 11, 0))
    # 2026-10-02 is Mahatma Gandhi Jayanti (in NSE_HOLIDAYS).
    assert not MarketHours.is_derivatives_open(datetime(2026, 10, 2, 11, 0))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/database/utils/test_market_hours_cas.py -v`
Expected: FAIL — `AttributeError: type object 'MarketHours' has no attribute 'is_derivatives_open'`, and `test_post_cas_cat1_cash_shuts_at_1515` fails because 15:20 still reads open.

- [ ] **Step 3: Write minimal implementation**

In `core/database/utils/market_hours.py`, replace the module docstring lines 6-9:

```
Indian market hours (IST). Segment-dependent since SEBI's Closing Auction
Session (2026-08-03) — see core/market/session_schedule.py, which is the
authority. The constants below are the pre-CAS cash session, retained because
callers still reference them for display.
```

Add the import after line 15 (`import logging`):

```python
from core.market.session_schedule import any_open as _any_open
from core.market.session_schedule import is_open as _is_open
```

Replace the body of `is_market_open` (lines 132-153) with:

```python
    @classmethod
    def is_market_open(cls, dt: Optional[datetime] = None, segment: str = "cash_cat1") -> bool:
        """Check whether `segment` is currently open.

        Default segment is cash Category I (F&O-eligible stocks) — the historical
        meaning of this method. Post-CAS that session ends at 15:15, not 15:30.
        """
        if dt is None:
            dt = cls.get_ist_now()
        else:
            dt = cls.to_ist(dt)

        if not cls.is_trading_day(dt):
            return False

        return _is_open(segment, dt.replace(tzinfo=None))

    @classmethod
    def is_derivatives_open(cls, dt: Optional[datetime] = None) -> bool:
        """Check whether the F&O segment is open — 15:40 close since CAS."""
        return cls.is_market_open(dt, segment="derivatives")

    @classmethod
    def is_any_open(cls, dt: Optional[datetime] = None) -> bool:
        """Check whether any segment (cash, auction, or derivatives) is open."""
        if dt is None:
            dt = cls.get_ist_now()
        else:
            dt = cls.to_ist(dt)

        if not cls.is_trading_day(dt):
            return False

        return _any_open(dt.replace(tzinfo=None))
```

Replace `is_post_market`'s comparison (line 197) so post-market follows the derivatives close rather than the bare constant:

```python
        current_time = dt.time()
        window = session_window("derivatives", dt.date())
        return bool(window) and window[1] <= current_time < cls.POST_MARKET_CLOSE
```

and add `session_window` to the import added above:

```python
from core.market.session_schedule import session_window
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/database/utils/test_market_hours_cas.py tests/runtime/test_driver_telemetry_publish.py -v`
Expected: PASS — the new file's 5 tests plus the existing driver telemetry test still green.

- [ ] **Step 5: Commit**

```bash
git add core/database/utils/market_hours.py tests/database/utils/test_market_hours_cas.py
git commit -m "feat: segment-aware MarketHours delegating to session schedule"
```

---

### Task 3: MarketSession and reference ingest follow the schedule

Register: B2, B3.

**Files:**
- Modify: `core/database/utils/market_session.py:38-42`, `:44-59`
- Modify: `scripts/ingest_reference_1m.py:47-48`
- Test: `tests/database/utils/test_market_session_cas.py` (create)

**Interfaces:**
- Consumes: `core.market.session_schedule.session_window` from Task 1.
- Produces: `MarketSession(session_date).end` now resolves per-date. No signature change.

- [ ] **Step 1: Write the failing test**

Create `tests/database/utils/test_market_session_cas.py`:

```python
from datetime import date, datetime

from core.database.utils.market_session import MarketSession


def test_pre_cas_session_ends_1530():
    assert MarketSession(date(2026, 7, 31)).end.strftime("%H:%M") == "15:30"


def test_post_cas_session_ends_1515_for_cat1_cash():
    assert MarketSession(date(2026, 8, 3)).end.strftime("%H:%M") == "15:15"


def test_contains_respects_the_post_cas_end():
    session = MarketSession(date(2026, 8, 3))
    assert session.contains(datetime(2026, 8, 3, 15, 14))
    assert not session.contains(datetime(2026, 8, 3, 15, 20))


def test_progress_reaches_one_at_the_new_close():
    session = MarketSession(date(2026, 8, 3))
    assert session.get_progress(datetime(2026, 8, 3, 15, 15)) == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/database/utils/test_market_session_cas.py -v`
Expected: FAIL — `test_post_cas_session_ends_1515_for_cat1_cash` reports `'15:30' != '15:15'`

- [ ] **Step 3: Write minimal implementation**

In `core/database/utils/market_session.py`, add after line 12 (`import pytz`):

```python
from core.market.session_schedule import session_window
```

Replace lines 40-42 (the `SESSION_START`/`SESSION_END` constants) with:

```python
    # Session bounds are date-resolved (CAS, 2026-08-03) — see
    # core/market/session_schedule.py. These constants are the pre-CAS values,
    # retained for `for_timestamp`'s "before open belongs to prior session" rule.
    SESSION_START = time(9, 15)
    SESSION_END = time(15, 30)
```

Replace the boundary computation in `__init__` (lines 53-59) with:

```python
        start, end = session_window("cash_cat1", session_date)
        self._start = self.IST.localize(datetime.combine(session_date, start))
        self._end = self.IST.localize(datetime.combine(session_date, end))
```

In `scripts/ingest_reference_1m.py`, replace lines 47-48:

```python
SESSION_END   = session_window("cash_cat1", date.today())[1]
EXPECTED_BARS = 375  # pre-CAS 09:15..15:29; post-CAS Cat-I tradeable minutes are 361
```

and add to that file's imports:

```python
from datetime import date
from core.market.session_schedule import session_window
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/database/utils/ -v`
Expected: PASS — all tests in the directory, including Task 2's.

- [ ] **Step 5: Commit**

```bash
git add core/database/utils/market_session.py scripts/ingest_reference_1m.py tests/database/utils/test_market_session_cas.py
git commit -m "feat: date-resolved MarketSession boundaries for CAS"
```

---

## Phase 2 — Substrate truth

### Task 4: Point-in-time CAS category

Register: A3. Category membership moves (16 continuous-trading symbols on 2026-08-03/04, 10 from 2026-08-13), so this is a PIT symbol attribute, not an era flag. Futures bhavcopy is genuinely point-in-time; the instrument master is a current snapshot and must not be used.

**Files:**
- Create: `scripts/cas/__init__.py`, `scripts/cas/build_cas_category.py`
- Test: `tests/cas/test_cas_category.py`

**Interfaces:**
- Consumes: `data/market_data/futures_bhavcopy.duckdb` (table `futures_bhavcopy`, columns `trade_date`, `symbol`).
- Produces: `is_cat1(symbol: str, on: date, con) -> bool` and `build(out_path: Path) -> int` writing table `cas_category(symbol VARCHAR, effective_from DATE, effective_to DATE)` to `data/cas/cas_category.duckdb`. Consumed by Task 5.

- [ ] **Step 1: Write the failing test**

Create `tests/cas/test_cas_category.py`:

```python
from datetime import date

import duckdb
import pytest

from scripts.cas.build_cas_category import build_intervals, is_cat1


@pytest.fixture
def futures_con(tmp_path):
    con = duckdb.connect(str(tmp_path / "fut.duckdb"))
    con.execute("CREATE TABLE futures_bhavcopy (trade_date DATE, symbol VARCHAR)")
    con.executemany(
        "INSERT INTO futures_bhavcopy VALUES (?, ?)",
        [(date(2026, 8, 3), "RELIANCE"), (date(2026, 8, 4), "RELIANCE"),
         (date(2026, 8, 3), "IRCTC")],
    )
    return con


def test_symbol_with_a_future_on_the_date_is_cat1(futures_con):
    assert is_cat1("RELIANCE", date(2026, 8, 4), futures_con)


def test_symbol_without_a_future_on_the_date_is_cat2(futures_con):
    assert not is_cat1("IRCTC", date(2026, 8, 4), futures_con)


def test_unknown_symbol_is_cat2(futures_con):
    assert not is_cat1("NOTLISTED", date(2026, 8, 3), futures_con)


def test_build_intervals_emits_one_row_per_contiguous_run(futures_con):
    rows = build_intervals(futures_con)
    reliance = [r for r in rows if r[0] == "RELIANCE"]
    assert reliance == [("RELIANCE", date(2026, 8, 3), date(2026, 8, 4))]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/cas/test_cas_category.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.cas'`

- [ ] **Step 3: Write minimal implementation**

Create `scripts/cas/__init__.py` (empty file).

Create `scripts/cas/build_cas_category.py`:

```python
"""Point-in-time CAS category (I = F&O-eligible, II = everything else).

SEBI's Closing Auction Session applies only to Category I stocks. Membership
changes over time, so this is a per-symbol interval table, not an era flag.

Derived from futures bhavcopy rather than the F&O instrument master: the master
is a current snapshot, and a snapshot cannot answer "was this symbol F&O-eligible
on 2026-08-04". The bhavcopy is genuinely point-in-time.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
FUTURES_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
OUT_DB = ROOT / "data" / "cas" / "cas_category.duckdb"


def is_cat1(symbol: str, on, con) -> bool:
    """True if `symbol` had a futures contract trading on `on`."""
    row = con.execute(
        "SELECT 1 FROM futures_bhavcopy WHERE symbol = ? AND trade_date = ? LIMIT 1",
        [symbol, on],
    ).fetchone()
    return row is not None


def build_intervals(con) -> list:
    """One (symbol, effective_from, effective_to) row per contiguous eligibility run."""
    rows = con.execute(
        "SELECT DISTINCT symbol, trade_date FROM futures_bhavcopy ORDER BY symbol, trade_date"
    ).fetchall()
    out = []
    current_symbol = None
    run_start = run_end = None
    for symbol, trade_date in rows:
        if symbol != current_symbol:
            if current_symbol is not None:
                out.append((current_symbol, run_start, run_end))
            current_symbol, run_start, run_end = symbol, trade_date, trade_date
        else:
            run_end = trade_date
    if current_symbol is not None:
        out.append((current_symbol, run_start, run_end))
    return out


def build(out_path: Path = OUT_DB) -> int:
    src = duckdb.connect(str(FUTURES_DB), read_only=True)
    try:
        intervals = build_intervals(src)
    finally:
        src.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    dst = duckdb.connect(str(out_path))
    try:
        dst.execute("DROP TABLE IF EXISTS cas_category")
        dst.execute(
            "CREATE TABLE cas_category "
            "(symbol VARCHAR, effective_from DATE, effective_to DATE)"
        )
        dst.executemany(
            "INSERT INTO cas_category VALUES (?, ?, ?)", intervals
        )
    finally:
        dst.close()
    return len(intervals)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_DB)
    args = parser.parse_args()
    print(f"wrote {build(args.out)} category intervals to {args.out}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/cas/test_cas_category.py -v`
Expected: PASS, 4 passed

Then build the real table:

Run: `python scripts/cas/build_cas_category.py`
Expected: prints a count in the high hundreds (363 stock underlyings exist in the futures store, so expect ≥ 363 intervals).

- [ ] **Step 5: Commit**

```bash
git add scripts/cas/__init__.py scripts/cas/build_cas_category.py tests/cas/test_cas_category.py
git commit -m "feat: point-in-time CAS category from futures bhavcopy"
```

---

### Task 5: Mark synthetic auction-window bars

Register: A1, A2. The predicate identifies a bar as fabricated when, on a post-CAS session, it sits in the auction window with zero volume, zero range, and a close identical to the 15:14 close of the same symbol. Category II symbols trade continuously (volume > 0) and are excluded both by the volume term and by the category filter.

**Files:**
- Create: `scripts/cas/mark_synthetic_bars.py`
- Test: `tests/cas/test_mark_synthetic.py`

**Interfaces:**
- Consumes: `core.market.session_schedule.CAS_EFFECTIVE` (Task 1); `data/cas/cas_category.duckdb` (Task 4).
- Produces: `mark_file(path: Path, session: date, cat1_symbols: set[str]) -> int` returning the number of bars flagged. Consumed by Task 6's shared predicate and Task 10's gate.

- [ ] **Step 1: Write the failing test**

Create `tests/cas/test_mark_synthetic.py`:

```python
from datetime import date, datetime

import duckdb
import pytest

from scripts.cas.mark_synthetic_bars import mark_file

SYM = "NSE_EQ|INE002A01018"


def _make_file(tmp_path, session, bars):
    path = tmp_path / f"{session.isoformat()}.duckdb"
    con = duckdb.connect(str(path))
    con.execute(
        "CREATE TABLE candles (symbol VARCHAR, instrument_key VARCHAR, "
        "timeframe VARCHAR, timestamp TIMESTAMP, open DOUBLE, high DOUBLE, "
        "low DOUBLE, close DOUBLE, volume BIGINT, is_synthetic BOOLEAN)"
    )
    con.executemany(
        "INSERT INTO candles VALUES (?, '', '1m', ?, ?, ?, ?, ?, ?, FALSE)", bars
    )
    con.close()
    return path


def test_flat_zero_volume_bars_in_the_auction_window_are_marked(tmp_path):
    session = date(2026, 8, 24)
    bars = [
        (SYM, datetime(2026, 8, 24, 15, 14), 1305.0, 1305.1, 1302.9, 1304.1, 68944),
        (SYM, datetime(2026, 8, 24, 15, 15), 1304.1, 1304.1, 1304.1, 1304.1, 0),
        (SYM, datetime(2026, 8, 24, 15, 16), 1304.1, 1304.1, 1304.1, 1304.1, 0),
        (SYM, datetime(2026, 8, 24, 15, 29), 1309.8, 1309.8, 1309.8, 1309.8, 377584),
    ]
    path = _make_file(tmp_path, session, bars)

    assert mark_file(path, session, {SYM}) == 2

    con = duckdb.connect(str(path), read_only=True)
    flagged = con.execute(
        "SELECT timestamp FROM candles WHERE is_synthetic ORDER BY timestamp"
    ).fetchall()
    con.close()
    assert [t[0].minute for t in flagged] == [15, 16]


def test_the_auction_print_is_never_marked(tmp_path):
    session = date(2026, 8, 24)
    bars = [
        (SYM, datetime(2026, 8, 24, 15, 14), 1305.0, 1305.1, 1302.9, 1304.1, 68944),
        (SYM, datetime(2026, 8, 24, 15, 29), 1309.8, 1309.8, 1309.8, 1309.8, 377584),
    ]
    path = _make_file(tmp_path, session, bars)

    assert mark_file(path, session, {SYM}) == 0


def test_pre_cas_sessions_are_untouched(tmp_path):
    session = date(2026, 7, 29)
    bars = [
        (SYM, datetime(2026, 7, 29, 15, 14), 1042.6, 1042.6, 1042.4, 1042.6, 2383),
        (SYM, datetime(2026, 7, 29, 15, 15), 1042.6, 1042.6, 1042.6, 1042.6, 0),
    ]
    path = _make_file(tmp_path, session, bars)

    assert mark_file(path, session, {SYM}) == 0


def test_category_two_symbols_are_not_marked(tmp_path):
    session = date(2026, 8, 24)
    bars = [
        (SYM, datetime(2026, 8, 24, 15, 14), 100.0, 100.0, 100.0, 100.0, 500),
        (SYM, datetime(2026, 8, 24, 15, 20), 100.0, 100.0, 100.0, 100.0, 0),
    ]
    path = _make_file(tmp_path, session, bars)

    assert mark_file(path, session, cat1_symbols=set()) == 0


def test_index_symbols_are_rejected_even_if_passed_in(tmp_path):
    # NSE_INDEX volume is always 0, so the equity predicate would mark the
    # index's real closing value as fabricated. The guard rejects them.
    idx = "NSE_INDEX|Nifty 50"
    session = date(2026, 8, 4)
    bars = [
        (idx, datetime(2026, 8, 4, 15, 14), 24462.9, 24466.1, 24451.1, 24463.45, 0),
        (idx, datetime(2026, 8, 4, 15, 20), 24463.45, 24463.45, 24463.45, 24463.45, 0),
        (idx, datetime(2026, 8, 4, 15, 29), 24614.9, 24614.9, 24614.9, 24614.9, 0),
    ]
    path = _make_file(tmp_path, session, bars)

    assert mark_file(path, session, {idx}) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/cas/test_mark_synthetic.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.cas.mark_synthetic_bars'`

- [ ] **Step 3: Write minimal implementation**

Create `scripts/cas/mark_synthetic_bars.py`:

```python
"""Populate `is_synthetic` for CAS auction-window carry-forward bars.

Since 2026-08-03 the Upstox feed keeps broadcasting a stale LTP (with
last-traded-quantity 0) through the 15:15-15:30 cash halt for Category I stocks.
DBTickAggregator faithfully bars those ticks, producing O=H=L=C, volume=0 rows
that look exactly like real data. The `is_synthetic` column already exists in
the per-day store and was uniformly FALSE — the flag was lying, not missing.

A bar is synthetic when, on a post-CAS session for a Category I symbol, it sits
in the auction window with zero volume, zero range, and a close identical to the
15:14 close. The auction print itself carries the whole auction volume and is
never marked.

Copy-first: --apply snapshots each file before mutating it.
"""
from __future__ import annotations

import argparse
import shutil
from datetime import date
from pathlib import Path

import duckdb

from core.market.session_schedule import CAS_EFFECTIVE, session_window

ROOT = Path(__file__).resolve().parents[2]
NATIVE_1M_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
CATEGORY_DB = ROOT / "data" / "cas" / "cas_category.duckdb"

# The 15:14 close per symbol is materialised into a temp table first. A
# correlated subquery against the UPDATE's own target table is ambiguous in
# DuckDB; a join against a precomputed anchor is unambiguous and faster.
_ANCHOR_SQL = """
CREATE TEMP TABLE anchor AS
SELECT symbol, close AS anchor_close FROM candles
WHERE hour(timestamp) * 60 + minute(timestamp) = ?
"""

_MARK_SQL = """
UPDATE candles SET is_synthetic = TRUE
WHERE symbol IN (SELECT symbol FROM cat1)
  AND volume = 0
  AND open = high AND high = low AND low = close
  AND (hour(timestamp) * 60 + minute(timestamp)) >= ?
  AND (hour(timestamp) * 60 + minute(timestamp)) < ?
  AND close IN (
      SELECT anchor_close FROM anchor WHERE anchor.symbol = candles.symbol
  )
"""


CAS_MARKABLE_PREFIX = "NSE_EQ|"


def mark_file(path: Path, session: date, cat1_symbols: set) -> int:
    """Flag carry-forward bars in one per-day file. Returns rows flagged.

    EQUITIES ONLY — see the NSE_EQ scoping note in the plan and in
    db_tick_aggregator.is_carry_forward. Index symbols are filtered out here
    even if a caller passes them in.
    """
    if session < CAS_EFFECTIVE:
        return 0
    cat1_symbols = {s for s in cat1_symbols if s.startswith(CAS_MARKABLE_PREFIX)}
    auction = session_window("cash_auction", session)
    if auction is None or not cat1_symbols:
        return 0

    start_min = auction[0].hour * 60 + auction[0].minute
    end_min = auction[1].hour * 60 + auction[1].minute
    last_continuous_min = start_min - 1

    con = duckdb.connect(str(path))
    try:
        con.execute("CREATE TEMP TABLE cat1 (symbol VARCHAR)")
        con.executemany("INSERT INTO cat1 VALUES (?)", [(s,) for s in cat1_symbols])
        con.execute(_ANCHOR_SQL, [last_continuous_min])
        before = con.execute(
            "SELECT count(*) FROM candles WHERE is_synthetic"
        ).fetchone()[0]
        con.execute(_MARK_SQL, [start_min, end_min])
        after = con.execute(
            "SELECT count(*) FROM candles WHERE is_synthetic"
        ).fetchone()[0]
    finally:
        con.close()
    return after - before


def cat1_isin_symbols(session: date) -> set:
    """Category I membership on `session`, as NSE_EQ|<isin> store symbols."""
    master = duckdb.connect(
        str(ROOT / "data" / "instruments" / "nse_fo_instruments.duckdb"), read_only=True
    )
    try:
        ticker_to_isin = dict(
            master.execute(
                "SELECT DISTINCT tradingsymbol, isin FROM instruments "
                "WHERE isin IS NOT NULL AND isin <> ''"
            ).fetchall()
        )
    finally:
        master.close()

    cat = duckdb.connect(str(CATEGORY_DB), read_only=True)
    try:
        tickers = {
            r[0]
            for r in cat.execute(
                "SELECT symbol FROM cas_category "
                "WHERE effective_from <= ? AND effective_to >= ?",
                [session, session],
            ).fetchall()
        }
    finally:
        cat.close()

    isins = {
        isin
        for ticker, isin in ticker_to_isin.items()
        if ticker.replace("-EQ", "") in tickers
    }
    return {f"NSE_EQ|{i}" for i in isins}


def run(apply: bool) -> dict:
    total = 0
    touched = 0
    for path in sorted(NATIVE_1M_DIR.glob("*.duckdb")):
        session = date.fromisoformat(path.stem)
        if session < CAS_EFFECTIVE:
            continue
        if apply:
            shutil.copy2(path, path.with_suffix(".duckdb.pre_cas_mark"))
        flagged = mark_file(path, session, cat1_isin_symbols(session)) if apply else 0
        total += flagged
        touched += 1
    return {"sessions": touched, "bars_flagged": total}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="mutate the store (snapshots each file first)")
    args = parser.parse_args()
    print(run(args.apply))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/cas/test_mark_synthetic.py -v`
Expected: PASS, 4 passed

Then run the real backfill:

Run: `python scripts/cas/mark_synthetic_bars.py --apply`
Expected: `{'sessions': 16, 'bars_flagged': N}` where N ≈ 16 sessions × ~187 Cat-I symbols × 13 slots ≈ 38,000. Verify the count is within 10% of that and that `.pre_cas_mark` snapshots exist beside each touched file.

- [ ] **Step 5: Commit**

```bash
git add scripts/cas/mark_synthetic_bars.py tests/cas/test_mark_synthetic.py
git commit -m "feat: mark CAS auction-window carry-forward bars as synthetic"
```

---

### Task 6: Aggregator writes truthful `is_synthetic` going forward

Register: A1, B4 (marking half). Without this, every future session re-introduces mislabelled bars and the Task 5 backfill has to be re-run forever.

**Files:**
- Modify: `core/database/ingestors/db_tick_aggregator.py:57-69`
- Test: `tests/database/ingestors/test_aggregator_synthetic.py` (create)

**Interfaces:**
- Consumes: `core.market.session_schedule.{CAS_EFFECTIVE, session_window}` (Task 1).
- Produces: module-level `is_carry_forward(symbol, bar_ts, op, hi, lo, cl, vol) -> bool`. Consumed by nothing else; the insert uses it inline.

> **`NSE_EQ`-scoped by rule.** The predicate leans on `volume == 0`, which discriminates only for equities. **`NSE_INDEX` symbols carry `volume = 0` on every bar of every session** (existing CLAUDE.md pitfall), so an unscoped predicate marks the index's own flat closing bar as synthetic — on 2026-08-04 the Nifty 50 auction value 24614.90 sits at 15:29 as `O=H=L=C` with `volume=0` and would be destroyed. The `symbol.startswith("NSE_EQ|")` guard is load-bearing, not defensive padding, and the same rule governs Task 5.

- [ ] **Step 1: Write the failing test**

Create `tests/database/ingestors/test_aggregator_synthetic.py`:

```python
from datetime import datetime

from core.database.ingestors.db_tick_aggregator import is_carry_forward

EQ = "NSE_EQ|INE002A01018"
IDX = "NSE_INDEX|Nifty 50"


def test_zero_volume_flat_bar_in_post_cas_auction_window_is_carry_forward():
    assert is_carry_forward(
        EQ, datetime(2026, 8, 24, 15, 20), 1304.1, 1304.1, 1304.1, 1304.1, 0
    )


def test_auction_print_is_not_carry_forward():
    assert not is_carry_forward(
        EQ, datetime(2026, 8, 24, 15, 29), 1309.8, 1309.8, 1309.8, 1309.8, 377584
    )


def test_continuous_bar_before_1515_is_not_carry_forward():
    assert not is_carry_forward(
        EQ, datetime(2026, 8, 24, 15, 14), 1305.0, 1305.1, 1302.9, 1304.1, 68944
    )


def test_pre_cas_zero_volume_bar_is_not_carry_forward():
    assert not is_carry_forward(
        EQ, datetime(2026, 7, 29, 15, 20), 1040.9, 1040.9, 1040.9, 1040.9, 0
    )


def test_index_bars_are_never_marked_because_index_volume_is_always_zero():
    # Nifty 50's real closing value on 2026-08-04 sits at 15:29 as a flat,
    # zero-volume bar. An unscoped predicate would destroy it.
    assert not is_carry_forward(
        IDX, datetime(2026, 8, 4, 15, 29), 24614.9, 24614.9, 24614.9, 24614.9, 0
    )
    assert not is_carry_forward(
        IDX, datetime(2026, 8, 4, 15, 20), 24463.45, 24463.45, 24463.45, 24463.45, 0
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/database/ingestors/test_aggregator_synthetic.py -v`
Expected: FAIL — `ImportError: cannot import name 'is_carry_forward'`

- [ ] **Step 3: Write minimal implementation**

In `core/database/ingestors/db_tick_aggregator.py`, add after line 6 (`from core.messaging.zmq_handler import ZmqPublisher`):

```python
from core.market.session_schedule import CAS_EFFECTIVE, session_window

CAS_MARKABLE_PREFIX = "NSE_EQ|"


def is_carry_forward(symbol, bar_ts, op, hi, lo, cl, vol) -> bool:
    """True if this bar is a stale-LTP artifact of the CAS cash halt.

    During 15:15-15:35 the Upstox feed keeps broadcasting the last traded price
    with quantity 0, so a bar materialises with no trades behind it.

    EQUITIES ONLY. The predicate discriminates on volume == 0, and NSE_INDEX
    symbols carry volume 0 on every bar of every session — applying it to an
    index would mark that index's real closing value as fabricated.
    """
    if not symbol.startswith(CAS_MARKABLE_PREFIX):
        return False
    if bar_ts.date() < CAS_EFFECTIVE or int(vol) != 0:
        return False
    auction = session_window("cash_auction", bar_ts.date())
    if auction is None:
        return False
    return auction[0] <= bar_ts.time() < auction[1] and op == hi == lo == cl
```

Replace the insert block (lines 57-69) with:

```python
        with db_manager.live_candles_writer() as candles_conn:
            for bar_ts, op, hi, lo, cl, vol in completed:
                synthetic = is_carry_forward(symbol, bar_ts, op, hi, lo, cl, vol)
                candles_conn.execute(
                    """
                    INSERT INTO candles
                    (symbol, timeframe, timestamp, open, high, low, close, volume, is_synthetic)
                    VALUES (?, '1m', ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (symbol, timeframe, timestamp) DO UPDATE SET
                        open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                        close=EXCLUDED.close, volume=EXCLUDED.volume,
                        is_synthetic=EXCLUDED.is_synthetic
                    """,
                    [symbol, bar_ts, op, hi, lo, cl, int(vol), synthetic],
                )
```

Note the resume query at line 35 selects `MAX(timestamp) ... WHERE is_synthetic=FALSE`. That remains correct: a synthetic tail must not advance the resume watermark, so a later real bar is still picked up.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/database/ingestors/ -v`
Expected: PASS — the 4 new tests plus the existing `test_market_ingestor_wiring.py`.

- [ ] **Step 5: Commit**

```bash
git add core/database/ingestors/db_tick_aggregator.py tests/database/ingestors/test_aggregator_synthetic.py
git commit -m "fix: aggregator labels CAS carry-forward bars as synthetic"
```

---

## Phase 3 — Live capture

### Task 7: Ingestor and pollers cover the derivatives tail

Register: B4 (capture half), B5, B6, B10. Every session not captured between 15:30 and 15:40 is gone permanently — the chain cache is rolling, not an archive.

**Files:**
- Modify: `scripts/market_ingestor.py:285`
- Modify: `scripts/nifty_shield_paper/chain_poller.py:375`
- Modify: `core/options_wall/poller.py:182`
- Test: `tests/ops/test_cas_capture_windows.py` (create)

**Interfaces:**
- Consumes: `MarketHours.is_any_open` / `MarketHours.is_derivatives_open` from Task 2.
- Produces: no new API.

- [ ] **Step 1: Write the failing test**

Create `tests/ops/test_cas_capture_windows.py`:

```python
import inspect
from datetime import datetime

from core.database.utils.market_hours import MarketHours


def test_derivatives_tail_is_inside_the_capture_window():
    # 15:35 on a post-CAS trading day: cash shut, F&O live.
    dt = datetime(2026, 8, 3, 15, 35)
    assert not MarketHours.is_market_open(dt)
    assert MarketHours.is_derivatives_open(dt)
    assert MarketHours.is_any_open(dt)


def test_chain_poller_gates_on_derivatives_not_cash():
    from scripts.nifty_shield_paper import chain_poller

    source = inspect.getsource(chain_poller)
    assert "is_derivatives_open" in source
    assert "if not MarketHours.is_market_open()" not in source


def test_wall_poller_gates_on_derivatives_not_cash():
    from core.options_wall import poller

    source = inspect.getsource(poller)
    assert "is_derivatives_open" in source
    assert "if not MarketHours.is_market_open()" not in source


def test_market_ingestor_gates_on_any_open():
    import scripts.market_ingestor as ingestor

    source = inspect.getsource(ingestor)
    assert "is_any_open" in source
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ops/test_cas_capture_windows.py -v`
Expected: FAIL — the three source-inspection tests fail; `is_derivatives_open`/`is_any_open` appear nowhere.

- [ ] **Step 3: Write minimal implementation**

In `scripts/nifty_shield_paper/chain_poller.py`, replace line 375:

```python
            if not MarketHours.is_derivatives_open():
```

In `core/options_wall/poller.py`, replace line 182:

```python
            if not MarketHours.is_derivatives_open():
```

In `scripts/market_ingestor.py`, replace line 285:

```python
            if MarketHours.is_any_open(now):
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/ops/test_cas_capture_windows.py tests/nifty_shield_paper/test_chain_poller.py -v`
Expected: PASS — the 4 new tests plus the existing chain-poller suite.

- [ ] **Step 5: Commit**

```bash
git add scripts/market_ingestor.py scripts/nifty_shield_paper/chain_poller.py core/options_wall/poller.py tests/ops/test_cas_capture_windows.py
git commit -m "feat: capture the 15:30-15:40 derivatives session"
```

---

### Task 8: Segment-aware telemetry and UI status

Register: B7, C3.

**Files:**
- Modify: `core/runtime/driver.py:872-883`
- Modify: `flask_app/blueprints/ops/routes.py:69-76`
- Test: `tests/runtime/test_driver_segment_telemetry.py` (create)

**Interfaces:**
- Consumes: `MarketHours.{is_market_open, is_derivatives_open}` (Task 2).
- Produces: telemetry payload gains `derivatives_open: bool` alongside the existing `market_open`.

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/test_driver_segment_telemetry.py`:

```python
import inspect

from core.database.utils.market_hours import MarketHours


def test_driver_publishes_a_derivatives_open_flag():
    from core.runtime import driver

    assert "derivatives_open" in inspect.getsource(driver)


def test_ops_route_reports_derivatives_session():
    from flask_app.blueprints.ops import routes

    assert "is_derivatives_open" in inspect.getsource(routes)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/runtime/test_driver_segment_telemetry.py -v`
Expected: FAIL — both assertions fail; neither string is present.

- [ ] **Step 3: Write minimal implementation**

In `core/runtime/driver.py`, in the telemetry dict at line 883, add a sibling key:

```python
            "market_open": MarketHours.is_market_open(now),
            "derivatives_open": MarketHours.is_derivatives_open(now),
```

and extend the docstring at line 872:

```
        - `market_open` — `MarketHours.is_market_open(clock.now())` (cash
          Category I; ends 15:15 since CAS), keyed to the
        - `derivatives_open` — the F&O segment, which runs to 15:40 since CAS.
```

In `flask_app/blueprints/ops/routes.py`, insert a branch before the `is_post_market` branch at line 76:

```python
    elif MarketHours.is_derivatives_open():
        status = "DERIVATIVES_ONLY"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/runtime/ tests/flask/ -v`
Expected: PASS — the 2 new tests plus the existing runtime and flask suites.

- [ ] **Step 5: Commit**

```bash
git add core/runtime/driver.py flask_app/blueprints/ops/routes.py tests/runtime/test_driver_segment_telemetry.py
git commit -m "feat: segment-aware telemetry and ops status for CAS"
```

---

## Phase 4 — Research remediation

### Task 9: Contiguity gate gains a tradeability arm

Register: A4. The gate counted bars correctly; it simply cannot certify that a bar is a tradeable observation. This is the mirror of the CLAUDE.md pitfall "a gate that tests file existence cannot certify row existence", one level down.

**Files:**
- Modify: `scripts/isd/gate_contiguity.py:56-88` (`audit_session`), `:117-145` (`run`)
- Test: `tests/isd/test_gate_tradeability.py` (create)

**Interfaces:**
- Consumes: the `is_synthetic` column populated by Tasks 5 and 6.
- Produces: `audit_session` result dict gains `synthetic_bars: int` and `tradeable_slots: int`; `run` result gains `aggregate["synthetic_bars"]`.

- [ ] **Step 1: Write the failing test**

Create `tests/isd/test_gate_tradeability.py`:

```python
from datetime import datetime

import duckdb

from scripts.isd.gate_contiguity import audit_session

SYM = "NSE_EQ|INE002A01018"


def test_audit_counts_synthetic_bars_separately(tmp_path):
    path = tmp_path / "2026-08-24.duckdb"
    con = duckdb.connect(str(path))
    con.execute(
        "CREATE TABLE candles (symbol VARCHAR, instrument_key VARCHAR, "
        "timeframe VARCHAR, timestamp TIMESTAMP, open DOUBLE, high DOUBLE, "
        "low DOUBLE, close DOUBLE, volume BIGINT, is_synthetic BOOLEAN)"
    )
    con.executemany(
        "INSERT INTO candles VALUES (?, '', '1m', ?, 1.0, 1.0, 1.0, 1.0, ?, ?)",
        [(SYM, datetime(2026, 8, 24, 15, 14), 100, False),
         (SYM, datetime(2026, 8, 24, 15, 20), 0, True),
         (SYM, datetime(2026, 8, 24, 15, 21), 0, True)],
    )
    con.close()

    result = audit_session(path, "2026-08-24")

    assert result["synthetic_bars"] == 2
    assert result["tradeable_slots"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/isd/test_gate_tradeability.py -v`
Expected: FAIL — `KeyError: 'synthetic_bars'`

- [ ] **Step 3: Write minimal implementation**

In `scripts/isd/gate_contiguity.py`, inside `audit_session`'s `try` block, add after the duplicate-slot query (line 76):

```python
        n_synthetic = con.execute(
            "select count(*) from candles where symbol like 'NSE_EQ%' "
            "and is_synthetic").fetchone()[0]
```

and extend the returned dict (line 80-88) with:

```python
        "synthetic_bars": int(n_synthetic),
        "tradeable_slots": int(distinct_slots - n_synthetic),
```

In `run`, extend the aggregate initialiser (line 118-119):

```python
    agg = {"symbols": 0, "missing_slots": 0, "duplicate_slots": 0,
           "bars_outside_grid": 0, "synthetic_bars": 0}
```

and widen the ledger trigger (line 124) so synthetic-bearing sessions are always published:

```python
        if (r["missing_slots"] or r["duplicate_slots"]
                or r["bars_outside_grid"] or r["synthetic_bars"]):
```

Note `agg` is summed by iterating its own keys, so `tradeable_slots` is deliberately not aggregated — it is a per-session figure.

Update the module docstring's L2 clause (lines 9-11) to:

```
  L2 intraday completeness: for each present (symbol, minute-of-day) slot in
     09:15..15:29 the file carries exactly one bar; shortfalls are counted into
     an explicit ledger (parquet under data/isd/) rather than silently ignored.
     Bar presence is not tradeability — since CAS (2026-08-03) a Category I
     symbol's 15:15..15:27 slots are carry-forward artifacts, counted here as
     `synthetic_bars` and excluded from `tradeable_slots`.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/isd/ -v`
Expected: PASS — the new test plus the existing `test_gates.py` and `test_battery.py`.

- [ ] **Step 5: Commit**

```bash
git add scripts/isd/gate_contiguity.py tests/isd/test_gate_tradeability.py
git commit -m "feat: ISD contiguity gate distinguishes tradeable from synthetic bars"
```

---

### Task 10: Day features exclude synthetic bars

Register: A8. `PM_START_BAR = 255` means the PM window is 13:30–15:29, of which 13–14 bars are now fabricated for Category I names — deflating realized vol, range, and CLV. These features feed the DayType facts store, which feeds NiftyShield regime classification.

**Files:**
- Modify: `core/analytics/day_features.py:30-40`, and the PM slice at `:273`
- Test: `tests/analytics/test_day_features_synthetic.py` (create)

**Interfaces:**
- Consumes: `is_synthetic` column (Tasks 5, 6).
- Produces: `drop_synthetic(df1m: pd.DataFrame) -> pd.DataFrame`, applied at the top of the feature pipeline.

- [ ] **Step 1: Write the failing test**

Create `tests/analytics/test_day_features_synthetic.py`:

```python
import pandas as pd

from core.analytics.day_features import drop_synthetic


def test_synthetic_bars_are_removed():
    df = pd.DataFrame({
        "close": [100.0, 101.0, 101.0],
        "is_synthetic": [False, False, True],
    })
    assert len(drop_synthetic(df)) == 2


def test_frames_without_the_column_pass_through_unchanged():
    df = pd.DataFrame({"close": [100.0, 101.0]})
    assert len(drop_synthetic(df)) == 2


def test_index_is_reset_so_positional_bar_slices_stay_valid():
    df = pd.DataFrame({
        "close": [100.0, 101.0, 102.0],
        "is_synthetic": [False, True, False],
    })
    result = drop_synthetic(df)
    assert list(result.index) == [0, 1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/analytics/test_day_features_synthetic.py -v`
Expected: FAIL — `ImportError: cannot import name 'drop_synthetic'`

- [ ] **Step 3: Write minimal implementation**

In `core/analytics/day_features.py`, replace the confused comment block at lines 32-40 with:

```python
AM_END_BAR = 105        # 11:00 AM cutoff (exclusive) — 09:15 + 105 min
PM_START_BAR = 255      # 13:30 cutoff (inclusive)   — 09:15 + 255 min
FIRST_HOUR_END_BAR = 60 # 10:15 AM cutoff (exclusive)
EXPECTED_BARS = 375     # 09:15..15:29. Post-CAS (2026-08-03) a Category I
                        # symbol has only 361 TRADEABLE minutes; the balance are
                        # auction carry-forward bars, dropped by drop_synthetic.
```

and add after `_range_epsilon` (line 45):

```python
def drop_synthetic(df1m):
    """Remove CAS auction carry-forward bars before any feature computation.

    Positional bar slices (AM_END_BAR, PM_START_BAR) index into this frame, so
    the index is reset after filtering.
    """
    if "is_synthetic" not in df1m.columns:
        return df1m
    return df1m[~df1m["is_synthetic"].fillna(False)].reset_index(drop=True)
```

Then apply it at the single per-session entry point, `compute_session_features` (line 521), so every block (B–G) and the derived 5m/15m/TWAP frames all see the filtered data. Add as the first statement of that function's body:

```python
    session_1m = drop_synthetic(session_1m)
```

This is the only call site. The positional slices at `AM_END_BAR`, `PM_START_BAR`, and the PM slice (line 273) then index into an already-filtered, index-reset frame.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/analytics/ tests/daytype/ -v`
Expected: PASS — the 3 new tests plus the existing analytics and daytype suites.

- [ ] **Step 5: Commit**

```bash
git add core/analytics/day_features.py tests/analytics/test_day_features_synthetic.py
git commit -m "fix: exclude CAS synthetic bars from day features"
```

---

### Task 11: Index-slice certifier gains a third era

Register: A7. The existing check hardcodes vendor era (`09:16`/`15:30`) vs native era (`09:15`/`15:29`) split at 2023-03-01; a third era begins 2026-08-03. The check currently keeps passing while the semantics underneath it changed.

> **Scope: the `era_for()` boundary only.** Do **not** touch any exit rule here. D2/D6 already pinned the A exit at the 15:14 bar close (commit `d33e762`) and the A construct was retired at HOLDOUT (`c72fa63`). The era logic is still needed — the certifier must not describe a CAS-era session in native-era terms — but it is now a correctness fix to the certifier, not an input to a live construct decision.
>
> **Branch:** this file exists only on `isd-program-reassessment`. Run this task there.

**Files:**
- Modify: `scripts/a_index_intraday/certify_index_slice.py:175-185`, `:355-365`
- Test: `tests/a_index_intraday/test_era_boundaries.py` (create)

**Interfaces:**
- Consumes: `core.market.session_schedule.CAS_EFFECTIVE` (Task 1).
- Produces: `era_for(session: date) -> str` returning `"vendor" | "native" | "cas"`.

- [ ] **Step 1: Write the failing test**

Create `tests/a_index_intraday/test_era_boundaries.py`:

```python
from datetime import date

from scripts.a_index_intraday.certify_index_slice import era_for


def test_vendor_era():
    assert era_for(date(2022, 6, 1)) == "vendor"


def test_native_era():
    assert era_for(date(2024, 6, 1)) == "native"


def test_cas_era_starts_2026_08_03():
    assert era_for(date(2026, 7, 31)) == "native"
    assert era_for(date(2026, 8, 3)) == "cas"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/a_index_intraday/test_era_boundaries.py -v`
Expected: FAIL — `ImportError: cannot import name 'era_for'`

- [ ] **Step 3: Write minimal implementation**

In `scripts/a_index_intraday/certify_index_slice.py`, add near the top imports:

```python
from datetime import date as _date

from core.market.session_schedule import CAS_EFFECTIVE

NATIVE_ERA_START = _date(2023, 3, 1)


def era_for(session):
    """Which structural era a session belongs to."""
    if session >= CAS_EFFECTIVE:
        return "cas"
    if session >= NATIVE_ERA_START:
        return "native"
    return "vendor"
```

Replace the hardcoded first/last-bar check at lines 179-181 with:

```python
            era = era_for(session)
            if era == "vendor":
                bad = bad or ft != "09:16" or lt != "15:30"
            else:
                # native and cas both label 09:15..15:29; in the cas era the
                # last bar is the auction print, not a continuous trade.
                bad = bad or ft != "09:15" or lt != "15:29"
```

Extend the interpretation string at lines 359-364 with a third sentence:

```python
        "From 2026-08-03 (CAS) the 15:29 bar is the closing-auction print rather "
        "than a continuous trade: it equals the official close, but it is not "
        "reachable by a continuous-market order, and the 15:15-15:27 bars are "
        "carry-forward artifacts.",
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/a_index_intraday/ -v`
Expected: PASS, 3 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/a_index_intraday/certify_index_slice.py tests/a_index_intraday/test_era_boundaries.py
git commit -m "feat: third structural era (CAS) in index-slice certification"
```

---

### Task 12: ISD battery exit re-pin — **WITHDRAWN 2026-08-27, do not implement**

Register: A5. This task existed to protect ISD's one-shot sealed window from being spent on a majority-post-CAS sample with an unfillable 15:29 exit.

**The ISD battery closed at TRAIN** (commit `05f5ed2`: both families FAIL — F1 sign negative, F4 net-spread gate). No sealed read will be taken, so there is nothing to protect and no exit to re-pin. Editing `battery_features.py` or re-freezing `isd_opening_drive.py` now would move a declaration SHA on a closed program — the same "don't touch a terminal artifact" discipline recorded for PSB-2's selection report.

**Replacement action (documentation only, folded into Task 14):** mark register item A5 as moot with the closing commit cited. Do not write code for this task.

---

## Phase 5 — Execution rules

### Task 13: CAS order-type and square-off guards

Register: B8, B9. No cash LIVE path exists today, but ISD targets intraday cash equity, so these must be encoded before any equity LIVE promotion. B9 is the sharper one: broker MIS auto-square-off (~15:12) now precedes ISD's own exit, which is an execution-feasibility break rather than a cost error.

**Files:**
- Create: `core/execution/equity/cas_rules.py`
- Modify: `core/execution/equity/intraday_fees.py` (add square-off constant near `CANONICAL_CAPITAL`)
- Test: `tests/execution/test_cas_rules.py`

**Interfaces:**
- Consumes: `core.market.session_schedule.{CAS_EFFECTIVE, session_window}` (Task 1).
- Produces: `MIS_SQUAREOFF = time(15, 12)`; `is_order_type_permitted(order_type: str, dt: datetime) -> bool`; `latest_intraday_exit(on: date) -> time`.

- [ ] **Step 1: Write the failing test**

Create `tests/execution/test_cas_rules.py`:

```python
from datetime import date, datetime, time

from core.execution.equity.cas_rules import (
    MIS_SQUAREOFF, is_order_type_permitted, latest_intraday_exit,
)


def test_stop_loss_rejected_during_the_auction():
    assert not is_order_type_permitted("SL", datetime(2026, 8, 24, 15, 20))


def test_stop_loss_permitted_during_continuous_trading():
    assert is_order_type_permitted("SL", datetime(2026, 8, 24, 14, 0))


def test_market_orders_rejected_after_1525():
    assert is_order_type_permitted("MARKET", datetime(2026, 8, 24, 15, 22))
    assert not is_order_type_permitted("MARKET", datetime(2026, 8, 24, 15, 26))


def test_limit_orders_permitted_throughout_the_auction():
    assert is_order_type_permitted("LIMIT", datetime(2026, 8, 24, 15, 26))


def test_pre_cas_imposes_no_restriction():
    assert is_order_type_permitted("SL", datetime(2026, 7, 29, 15, 20))


def test_latest_intraday_exit_is_the_broker_squareoff_post_cas():
    assert latest_intraday_exit(date(2026, 8, 24)) == MIS_SQUAREOFF
    assert latest_intraday_exit(date(2026, 7, 29)) == time(15, 30)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/execution/test_cas_rules.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.execution.equity.cas_rules'`

- [ ] **Step 3: Write minimal implementation**

Create `core/execution/equity/cas_rules.py`:

```python
"""Order-placement rules imposed by the Closing Auction Session.

Stop-loss, IOC, iceberg, and disclosed-quantity orders are rejected during CAS;
market orders are barred once Order Entry II opens at 15:25. Separately, broker
MIS auto-square-off for Category I cash moved to ~15:12, which is EARLIER than
the 15:29 close a naive intraday backtest would exit at — an execution
feasibility limit, not a cost adjustment.
"""
from __future__ import annotations

from datetime import date, datetime, time

from core.market.session_schedule import CAS_EFFECTIVE, session_window

MIS_SQUAREOFF = time(15, 12)
MARKET_ORDER_CUTOFF = time(15, 25)

_AUCTION_BANNED = frozenset({"SL", "SL-M", "IOC", "ICEBERG", "DISCLOSED"})


def is_order_type_permitted(order_type: str, dt: datetime) -> bool:
    """Whether `order_type` may be sent to the cash segment at `dt`."""
    if dt.date() < CAS_EFFECTIVE:
        return True
    auction = session_window("cash_auction", dt.date())
    if auction is None or not (auction[0] <= dt.time() < auction[1]):
        return True
    normalized = order_type.upper()
    if normalized in _AUCTION_BANNED:
        return False
    if normalized == "MARKET":
        return dt.time() < MARKET_ORDER_CUTOFF
    return True


def latest_intraday_exit(on: date) -> time:
    """The last moment an MIS intraday cash position can be exited by choice."""
    if on < CAS_EFFECTIVE:
        return session_window("cash_cat1", on)[1]
    return MIS_SQUAREOFF
```

In `core/execution/equity/intraday_fees.py`, add below `CANONICAL_CAPITAL` (line ~43):

```python
# Broker MIS auto-square-off for CAS Category I cash (register B9). Re-exported
# from cas_rules so the cost model and the feasibility limit ship together.
from core.execution.equity.cas_rules import MIS_SQUAREOFF  # noqa: E402,F401
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/execution/test_cas_rules.py tests/isd/ -v`
Expected: PASS — 6 new tests plus the ISD suite (which imports `intraday_fees` via `scripts/isd/__init__.py`, so a circular-import regression would surface here).

- [ ] **Step 5: Commit**

```bash
git add core/execution/equity/cas_rules.py core/execution/equity/intraday_fees.py tests/execution/test_cas_rules.py
git commit -m "feat: CAS order-type and MIS square-off rules"
```

---

## Phase 6 — Documentation

### Task 14: CLAUDE.md, pitfall, and register closure

Register: C4, C5, C6, C7, plus B11 (verify the ingest hole is closed).

**Files:**
- Modify: `CLAUDE.md` (Data Layout + Known Pitfalls)
- Modify: `core/database/providers/daily_bhavcopy.py:105,235`
- Modify: `docs/reports/CAS_ADAPTATION_REGISTER.md` (status column)
- Modify: `docs/CHANGELOG_PLATFORM.md`

**Interfaces:** none (documentation).

- [ ] **Step 1: Verify the 1m ingest hole is closed (register B11)**

Run: `ls data/market_data/nse/candles/1m/ | tail -5`
Expected: files through the last completed trading session. If 2026-08-25/26 are still absent, run the EOD chain for those dates before proceeding — a documentation pass must not paper over a live data hole.

- [ ] **Step 2: Add the Data Layout note to CLAUDE.md**

Under **Data Layout**, after the 1-min candles bullet, add:

```markdown
- **CAS (Closing Auction Session), live 2026-08-03** — for F&O ("Category I")
  stocks, continuous cash trading ends **15:15**; the official close is the
  auction equilibrium struck 15:30–15:35; derivatives trade to **15:40**.
  In the 1m store this means Category I symbols carry **carry-forward bars**
  from 15:15 to ~15:27 (`O=H=L=C`, `volume=0`) with the whole auction landing in
  one print at 15:28/15:29. Those bars are flagged `is_synthetic = TRUE` — always
  filter on it. Session windows come from `core/market/session_schedule.py`, never
  from a bare constant. The auction print **equals** the official bhavcopy close
  (verified 92–95%; misses are Category II VWAP closes), so daily-close constructs
  are unaffected. Full detail: `docs/reports/CAS_ADAPTATION_REGISTER.md`.
```

- [ ] **Step 3: Add the Known Pitfall**

Under **Known Pitfalls**, add:

```markdown
- **A bar is not a trade.** Since CAS (2026-08-03) roughly 13 minutes per session
  per F&O symbol are aggregator carry-forward from a stale LTP the feed keeps
  broadcasting through the halt — real-looking rows with no trades behind them.
  A contiguity gate that counts one bar per slot passes on fabricated data;
  ISD's did, over 16 certified sessions. **Bar-count completeness is not
  tradeability** — assert `is_synthetic = FALSE`, and for indices (where
  `volume` is always 0 and there is no tell) resolve the era by rule, never by
  detection.
```

- [ ] **Step 4: Fix the daily timestamp label and mark the register**

In `core/database/providers/daily_bhavcopy.py`, at both line 105 and line 235, extend the existing comment beside `time(15, 30)`:

```python
                # Nominal session-close stamp. Post-CAS the Category I official
                # close is struck 15:30-15:35; the VALUE here is correct, only
                # the label is nominal (register C4).
```

In `docs/reports/CAS_ADAPTATION_REGISTER.md`, append a status line to each item resolved by this plan, and record the two Phase 0 outcomes:

```markdown
### Status — A5 and A6 closed 2026-08-27 without code

**A5 (ISD SEALED straddle) — MOOT.** The ISD battery closed at TRAIN (`05f5ed2`:
both families FAIL, F1 sign negative and F4 net-spread gate). No sealed read will
be taken, so the 55%-post-CAS straddle is history rather than a live risk. The
declaration is left frozen as-is; moving a SHA on a closed program is the error
this repo already recorded against PSB-2's selection report.

**A6 (A-construct exit) — RESOLVED at 15:14.** Operator decision D6 (`d33e762`)
pinned the exit at the 15:14 bar close: last continuous print in all eras, auction
window untraded. The construct was then retired at HOLDOUT (`c72fa63`: TRAIN net
+1.27 bp p 0.003; HOLDOUT net −0.22 bp p 0.15), SEALED untouched at 873 sessions.
D6 stands as the settled convention for any index intraday exit.
```

Also record the B11 lag fill outcome from Step 1.

Append to `docs/CHANGELOG_PLATFORM.md`:

```markdown
## 2026-08-27 — CAS adaptation implemented

Segment-aware session schedule (`core/market/session_schedule.py`) replaces the
15:30 constants; PIT CAS category from futures bhavcopy; `is_synthetic`
populated truthfully (backfill + aggregator); live capture extended to the 15:40
derivatives close; ISD contiguity gate distinguishes tradeable from synthetic
slots; day features drop synthetic bars; CAS order-type and MIS square-off rules
encoded. *(docs/superpowers/plans/2026-08-27-cas-adaptation.md)*
```

- [ ] **Step 5: Run the full suite and commit**

Run: `python -m pytest tests/ -q`
Expected: PASS — no regressions across the suite.

```bash
git add CLAUDE.md core/database/providers/daily_bhavcopy.py docs/reports/CAS_ADAPTATION_REGISTER.md docs/CHANGELOG_PLATFORM.md
git commit -m "docs: record CAS adaptation in CLAUDE.md, pitfalls, and changelog"
```

---

## Coverage check against the register

| Register item | Task |
|---|---|
| A1 synthetic bars indistinguishable | 5, 6 |
| A2 auction bar not reliably last; no index tell | 5 (predicate), 11 (era rule) |
| A3 heterogeneous store / PIT category | 4 |
| A4 ISD cert covers post-CAS sessions | 9 |
| A5 ISD SEALED straddle | **MOOT** — battery closed at TRAIN (`05f5ed2`); Task 12 withdrawn, recorded in 14 |
| A6 A-construct exit | **RESOLVED** — D6 pinned 15:14 (`d33e762`); construct retired at HOLDOUT (`c72fa63`), recorded in 14 |
| A7 two-era certifier | 11 (`era_for()` only) |
| A8 PM window synthetic bars | 10 |
| B1 MARKET_CLOSE | 1, 2 |
| B2 SESSION_END | 1, 3 |
| B3 ingest_reference_1m | 3 |
| B4 ingestor (both halves) | 6 (marking), 7 (capture) |
| B5 chain poller | 7 |
| B6 wall poller | 7 |
| B7 driver telemetry | 8 |
| B8 order types | 13 |
| B9 MIS square-off | 13 |
| B10 rolling chain cache | 7 (mitigation: capture forward) |
| B11 1m ingest lag | 14 step 1 |
| C1 docstring | 2 |
| C2 POST_MARKET_CLOSE | 2 |
| C3 UI status | 8 |
| C4 daily timestamp label | 14 |
| C5 day_features comment | 10 |
| C6 CLAUDE.md | 14 |
| C7 known pitfall | 14 |

All 22 register items are covered. **A5 and A6 are closed without code** (see Phase 0); every remaining item has a code task.

**13 code tasks, one withdrawn (12).** Tasks 1–10 and 13–14 are branch-independent; **Task 11 must run on `isd-program-reassessment`**, where `scripts/a_index_intraday/` exists.

## Revision log

- **2026-08-27 (rev 2)** — revised against the `isd-program-reassessment` handoff (head `c3bb6bd`):
  - **Bug fix, Tasks 5 & 6:** the synthetic-bar predicate is now `NSE_EQ`-scoped. `NSE_INDEX` carries `volume = 0` on every bar, so the unscoped predicate would have marked the index's real closing value as fabricated — Nifty 50's 24614.90 on 2026-08-04 sits at 15:29 as a flat zero-volume bar. Guard added in both `is_carry_forward` (now takes `symbol`) and `mark_file`, with a regression test in each.
  - **Phase 0 closed:** D1 moot (ISD battery closed at TRAIN), D2 resolved (D6 pinned 15:14).
  - **Task 12 withdrawn**; its register outcome folded into Task 14.
  - **Task 11 narrowed** to the `era_for()` boundary, with a branch note.
  - Task 13's `intraday_fees.py` re-export confirmed benign for `futures_fees.py` (operator).
  - Task 14's B11 lag fill (2026-08-25/26) confirmed in scope (operator).
