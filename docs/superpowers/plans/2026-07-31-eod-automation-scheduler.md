# EOD Automation Scheduler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A UI-toggleable nightly job that runs `download_all_data.py` at 20:00 Mon–Fri, retries every 30 minutes until market data arrives, then runs the strategy chain and reports results to Telegram.

**Architecture:** A standalone worker daemon (`scripts/schedule_worker.py`) owns all execution; Flask only reads/writes a SQLite control store. Business logic lives in small, pure, unit-testable modules under `core/scheduler/`. Trading-day status is inferred from whether any of four independent NSE feeds published data for today.

**Tech Stack:** Python 3.10+, SQLite (stdlib `sqlite3`, WAL mode) for the control plane, DuckDB (read-only) for feed probes, Flask + Tailwind for UI, `requests` for Telegram.

**Design spec:** `docs/superpowers/specs/2026-07-31-eod-automation-scheduler-design.md`

## Global Constraints

- **Control store is SQLite, never DuckDB.** DuckDB does not support concurrent multi-process read-write; Flask and the worker both write. Market data reads stay DuckDB (read-only).
- **All subprocess capture uses `encoding="utf-8", errors="replace"`.** Repo console output contains `—`, `→`, `₹`; the Windows default code page raises `UnicodeDecodeError`.
- **Every subprocess call passes an explicit `timeout`.**
- **Telegram messages send as plain text** — no `parse_mode`. Tickers containing `_` or `*` cause HTTP 400 under Markdown and the message is lost silently.
- **Telegram messages truncate to 4096 chars** with an explicit `… truncated` marker.
- **Terminal outcomes** (a date is done, do not retry): `success`, `holiday`, `exhausted`, `chain_failed`.
- **Fire window:** 20:00–23:30 local, Mon–Fri, 30-minute interval, max 8 attempts.
- **Holiday grace:** all-feeds-stale before 21:00 → retry; at/after 21:00 → holiday.
- Do **not** modify `download_all_data.py`, `refresh_all_strategies.py`, `ts_basis_daily_signals.py`, or `ts_basis_daily_options.py`. This feature only orchestrates them.
- Do **not** reuse or modify the existing `_schedule.duckdb` / `scheduled_jobs` table.
- Run tests with `python -m pytest` from repo root `F:\Nifty`.

---

## File Structure

| File | Responsibility |
|---|---|
| `core/scheduler/__init__.py` | Package marker (empty) |
| `core/scheduler/eod_store.py` | SQLite control store: enabled flag, heartbeat, run log, run-now trigger |
| `core/scheduler/eod_decision.py` | Feed probing + the pure decision function (retry / chain / holiday) |
| `core/scheduler/eod_telegram.py` | Synchronous Telegram send + message formatters |
| `core/scheduler/eod_chain.py` | Sequential script runner, aborts on first failure |
| `core/scheduler/eod_job.py` | Orchestrator: one attempt = probe → decide → act → record |
| `scripts/schedule_worker.py` | Daemon: tick loop, single-instance lock, fire-time logic |
| `app_facade/data_facade.py` | (modify) EOD status/toggle/run-now facade methods |
| `flask_app/blueprints/data/routes.py` | (modify) three new endpoints |
| `flask_app/templates/data/index.html` | (modify) new Automation tab |
| `tests/scheduler/test_*.py` | Unit + integration tests |

---

## Task 1: Control store

**Files:**
- Create: `core/scheduler/__init__.py`
- Create: `core/scheduler/eod_store.py`
- Test: `tests/scheduler/__init__.py`, `tests/scheduler/test_eod_store.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `EodStore(db_path: Path)` — all methods below are instance methods
  - `.is_enabled() -> bool`
  - `.set_enabled(value: bool) -> None`
  - `.heartbeat(pid: int) -> None`
  - `.get_heartbeat() -> tuple[str | None, int | None]` → `(iso_timestamp, pid)`
  - `.request_run_now() -> None`
  - `.consume_run_now() -> bool` — returns True once, then clears the flag
  - `.record(run_date: date, attempt: int, phase: str, outcome: str, detail: str) -> None`
  - `.attempts_today(run_date: date) -> list[dict]` — scheduled attempts only (`attempt >= 1`), ordered by attempt
  - `.last_attempt_started(run_date: date) -> datetime | None` — scheduled attempts only
  - `.is_date_terminal(run_date: date) -> bool`
  - `.latest_run() -> dict | None` — most recent row by `started_at`, for the UI
  - Module constant `TERMINAL_OUTCOMES: frozenset[str]`

- [ ] **Step 1: Write the failing test**

Create `tests/scheduler/__init__.py` as an empty file, then `tests/scheduler/test_eod_store.py`:

```python
from datetime import date, datetime

import pytest

from core.scheduler.eod_store import EodStore, TERMINAL_OUTCOMES


@pytest.fixture
def store(tmp_path):
    return EodStore(tmp_path / "eod.sqlite")


def test_enabled_defaults_false_and_round_trips(store):
    assert store.is_enabled() is False
    store.set_enabled(True)
    assert store.is_enabled() is True
    store.set_enabled(False)
    assert store.is_enabled() is False


def test_heartbeat_records_timestamp_and_pid(store):
    assert store.get_heartbeat() == (None, None)
    store.heartbeat(4321)
    ts, pid = store.get_heartbeat()
    assert pid == 4321
    assert datetime.fromisoformat(ts)


def test_run_now_is_consumed_exactly_once(store):
    assert store.consume_run_now() is False
    store.request_run_now()
    assert store.consume_run_now() is True
    assert store.consume_run_now() is False


def test_attempts_today_excludes_manual_runs(store):
    d = date(2026, 7, 31)
    store.record(d, 0, "download", "success", "manual")
    store.record(d, 1, "download", "retry", "futures stale")
    attempts = store.attempts_today(d)
    assert [a["attempt"] for a in attempts] == [1]


def test_manual_run_does_not_make_date_terminal(store):
    d = date(2026, 7, 31)
    store.record(d, 0, "done", "success", "manual")
    assert store.is_date_terminal(d) is False


def test_scheduled_success_makes_date_terminal(store):
    d = date(2026, 7, 31)
    store.record(d, 1, "done", "success", "")
    assert store.is_date_terminal(d) is True


@pytest.mark.parametrize("outcome", sorted(TERMINAL_OUTCOMES))
def test_all_terminal_outcomes_stop_the_day(store, outcome):
    d = date(2026, 7, 31)
    store.record(d, 1, "download", outcome, "")
    assert store.is_date_terminal(d) is True


def test_retry_outcome_is_not_terminal(store):
    d = date(2026, 7, 31)
    store.record(d, 1, "download", "retry", "")
    assert store.is_date_terminal(d) is False


def test_last_attempt_started_returns_latest_scheduled(store):
    d = date(2026, 7, 31)
    store.record(d, 1, "download", "retry", "")
    store.record(d, 2, "download", "retry", "")
    assert store.last_attempt_started(d).date() == d
    assert len(store.attempts_today(d)) == 2


def test_record_is_idempotent_on_same_attempt(store):
    d = date(2026, 7, 31)
    store.record(d, 1, "download", "retry", "first")
    store.record(d, 1, "download", "success", "second")
    attempts = store.attempts_today(d)
    assert len(attempts) == 1
    assert attempts[0]["outcome"] == "success"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/scheduler/test_eod_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.scheduler'`

- [ ] **Step 3: Write minimal implementation**

Create `core/scheduler/__init__.py` as an empty file. Create `core/scheduler/eod_store.py`:

```python
"""SQLite control store for the EOD automation worker.

SQLite (not DuckDB) because Flask and the worker are separate processes that
both write: DuckDB takes an exclusive file lock and would raise intermittent
lock errors. WAL mode makes concurrent reader/writer access safe.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

TERMINAL_OUTCOMES = frozenset({"success", "holiday", "exhausted", "chain_failed"})


class EodStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("""
                CREATE TABLE IF NOT EXISTS eod_automation (
                    id               INTEGER PRIMARY KEY CHECK (id = 1),
                    enabled          INTEGER NOT NULL DEFAULT 0,
                    run_now          INTEGER NOT NULL DEFAULT 0,
                    updated_at       TEXT,
                    worker_heartbeat TEXT,
                    worker_pid       INTEGER
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS eod_run_log (
                    run_date    TEXT NOT NULL,
                    attempt     INTEGER NOT NULL,
                    started_at  TEXT,
                    finished_at TEXT,
                    phase       TEXT,
                    outcome     TEXT,
                    detail      TEXT,
                    PRIMARY KEY (run_date, attempt)
                )
            """)
            con.execute("INSERT OR IGNORE INTO eod_automation (id) VALUES (1)")

    def _conn(self):
        con = sqlite3.connect(str(self.db_path), timeout=30)
        con.row_factory = sqlite3.Row
        return con

    def is_enabled(self) -> bool:
        with self._conn() as con:
            return bool(con.execute("SELECT enabled FROM eod_automation WHERE id=1").fetchone()[0])

    def set_enabled(self, value: bool) -> None:
        with self._conn() as con:
            con.execute("UPDATE eod_automation SET enabled=?, updated_at=? WHERE id=1",
                        [int(value), datetime.now().isoformat()])

    def heartbeat(self, pid: int) -> None:
        with self._conn() as con:
            con.execute("UPDATE eod_automation SET worker_heartbeat=?, worker_pid=? WHERE id=1",
                        [datetime.now().isoformat(), pid])

    def get_heartbeat(self) -> tuple[str | None, int | None]:
        with self._conn() as con:
            row = con.execute(
                "SELECT worker_heartbeat, worker_pid FROM eod_automation WHERE id=1").fetchone()
            return row[0], row[1]

    def request_run_now(self) -> None:
        with self._conn() as con:
            con.execute("UPDATE eod_automation SET run_now=1 WHERE id=1")

    def consume_run_now(self) -> bool:
        with self._conn() as con:
            row = con.execute("SELECT run_now FROM eod_automation WHERE id=1").fetchone()
            if not row[0]:
                return False
            con.execute("UPDATE eod_automation SET run_now=0 WHERE id=1")
            return True

    def record(self, run_date: date, attempt: int, phase: str, outcome: str, detail: str) -> None:
        now = datetime.now().isoformat()
        with self._conn() as con:
            existing = con.execute(
                "SELECT started_at FROM eod_run_log WHERE run_date=? AND attempt=?",
                [run_date.isoformat(), attempt]).fetchone()
            started = existing[0] if existing else now
            con.execute("""
                INSERT OR REPLACE INTO eod_run_log
                    (run_date, attempt, started_at, finished_at, phase, outcome, detail)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [run_date.isoformat(), attempt, started, now, phase, outcome, detail])

    def attempts_today(self, run_date: date) -> list[dict]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM eod_run_log WHERE run_date=? AND attempt >= 1 ORDER BY attempt",
                [run_date.isoformat()]).fetchall()
            return [dict(r) for r in rows]

    def last_attempt_started(self, run_date: date) -> datetime | None:
        attempts = self.attempts_today(run_date)
        if not attempts:
            return None
        return datetime.fromisoformat(attempts[-1]["started_at"])

    def is_date_terminal(self, run_date: date) -> bool:
        return any(a["outcome"] in TERMINAL_OUTCOMES for a in self.attempts_today(run_date))

    def latest_run(self) -> dict | None:
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM eod_run_log ORDER BY started_at DESC LIMIT 1").fetchone()
            return dict(row) if row else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/scheduler/test_eod_store.py -v`
Expected: PASS — 11 passed

- [ ] **Step 5: Commit**

```bash
git add core/scheduler/__init__.py core/scheduler/eod_store.py tests/scheduler/
git commit -m "feat: add SQLite control store for EOD automation"
```

---

## Task 2: Feed probe and decision logic

**Files:**
- Create: `core/scheduler/eod_decision.py`
- Test: `tests/scheduler/test_eod_decision.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces:
  - `FEED_STORES: dict[str, tuple[Path, str]]` — feed name → (duckdb path, table); index feed handled separately
  - `probe_feeds() -> dict[str, date | None]` — keys: `equity`, `futures`, `stock_options`, `index`
  - `decide(feeds: dict[str, date | None], today: date, now: datetime, attempt: int) -> Decision`
  - `Decision` — dataclass with fields `action: str` (`"chain"` | `"retry"` | `"holiday"` | `"exhausted"`), `reason: str`
  - `GRACE_HOUR = 21`, `MAX_ATTEMPTS = 8`

- [ ] **Step 1: Write the failing test**

Create `tests/scheduler/test_eod_decision.py`:

```python
from datetime import date, datetime

from core.scheduler.eod_decision import MAX_ATTEMPTS, decide

TODAY = date(2026, 7, 31)
YESTERDAY = date(2026, 7, 30)


def feeds(equity=YESTERDAY, futures=YESTERDAY, stock_options=YESTERDAY, index=YESTERDAY):
    return {"equity": equity, "futures": futures, "stock_options": stock_options, "index": index}


def at(hour, minute=0):
    return datetime(2026, 7, 31, hour, minute)


def test_futures_today_runs_the_chain():
    d = decide(feeds(futures=TODAY), TODAY, at(20), attempt=1)
    assert d.action == "chain"


def test_partial_feeds_without_futures_retries():
    d = decide(feeds(equity=TODAY), TODAY, at(20), attempt=1)
    assert d.action == "retry"


def test_partial_feeds_retries_even_after_grace_hour():
    # A trading day is proven: some feed published. Grace must not apply.
    d = decide(feeds(index=TODAY), TODAY, at(22), attempt=3)
    assert d.action == "retry"


def test_all_feeds_stale_before_grace_hour_retries():
    d = decide(feeds(), TODAY, at(20, 30), attempt=2)
    assert d.action == "retry"


def test_all_feeds_stale_at_grace_hour_declares_holiday():
    d = decide(feeds(), TODAY, at(21), attempt=3)
    assert d.action == "holiday"


def test_all_feeds_stale_after_grace_hour_declares_holiday():
    d = decide(feeds(), TODAY, at(22, 30), attempt=6)
    assert d.action == "holiday"


def test_attempt_cap_exhausts_before_holiday_check():
    d = decide(feeds(equity=TODAY), TODAY, at(23, 30), attempt=MAX_ATTEMPTS)
    assert d.action == "exhausted"


def test_chain_wins_even_on_final_attempt():
    d = decide(feeds(futures=TODAY), TODAY, at(23, 30), attempt=MAX_ATTEMPTS)
    assert d.action == "chain"


def test_missing_store_is_treated_as_stale():
    d = decide(feeds(equity=None, futures=None, stock_options=None, index=None),
               TODAY, at(21), attempt=3)
    assert d.action == "holiday"


def test_decision_carries_a_reason():
    assert decide(feeds(futures=TODAY), TODAY, at(20), attempt=1).reason
    assert decide(feeds(), TODAY, at(21), attempt=3).reason
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/scheduler/test_eod_decision.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.scheduler.eod_decision'`

- [ ] **Step 3: Write minimal implementation**

Create `core/scheduler/eod_decision.py`:

```python
"""Trading-day inference and the EOD retry decision.

No holiday list exists in this repo and `trading_calendar` is derived from the
downloads themselves, so trading-day status is inferred from whether any of the
four independent NSE feeds published data for today.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "market_data"

GRACE_HOUR = 21
MAX_ATTEMPTS = 8

FEED_STORES = {
    "equity": (DATA / "equity_bhavcopy.duckdb", "equity_bhavcopy"),
    "futures": (DATA / "futures_bhavcopy.duckdb", "futures_bhavcopy"),
    "stock_options": (DATA / "stock_options_bhavcopy.duckdb", "stock_options_bhavcopy"),
}
INDEX_1D_DIR = DATA / "nse" / "candles" / "1d"


@dataclass(frozen=True)
class Decision:
    action: str  # "chain" | "retry" | "holiday" | "exhausted"
    reason: str


def _max_trade_date(db_path: Path, table: str) -> date | None:
    if not db_path.exists():
        return None
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        names = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        if table not in names:
            return None
        return con.execute(f"SELECT MAX(trade_date) FROM {table}").fetchone()[0]
    finally:
        con.close()


def _max_index_date() -> date | None:
    if not INDEX_1D_DIR.exists():
        return None
    stems = [f.stem for f in INDEX_1D_DIR.glob("*.duckdb")]
    return max((date.fromisoformat(s) for s in stems), default=None)


def probe_feeds() -> dict[str, date | None]:
    feeds = {name: _max_trade_date(path, table) for name, (path, table) in FEED_STORES.items()}
    feeds["index"] = _max_index_date()
    return feeds


def decide(feeds: dict[str, date | None], today: date, now: datetime, attempt: int) -> Decision:
    fresh = [name for name, d in feeds.items() if d == today]

    if feeds.get("futures") == today:
        return Decision("chain", f"futures published {today}")

    if attempt >= MAX_ATTEMPTS:
        return Decision("exhausted", f"no futures data after {attempt} attempts (fresh: {fresh or 'none'})")

    if fresh:
        return Decision("retry", f"trading day confirmed by {', '.join(sorted(fresh))}; futures not yet published")

    if now.hour >= GRACE_HOUR:
        return Decision("holiday", f"no feed published {today} by {now:%H:%M} — treating as non-trading day")

    return Decision("retry", f"no feed published {today} yet; before {GRACE_HOUR}:00 grace cutoff")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/scheduler/test_eod_decision.py -v`
Expected: PASS — 10 passed

- [ ] **Step 5: Commit**

```bash
git add core/scheduler/eod_decision.py tests/scheduler/test_eod_decision.py
git commit -m "feat: add peer-feed trading-day inference and EOD decision logic"
```

---

## Task 3: Telegram sync send and formatters

**Files:**
- Create: `core/scheduler/eod_telegram.py`
- Test: `tests/scheduler/test_eod_telegram.py`

**Interfaces:**
- Consumes: `Decision` from Task 2 (only its `.reason`, passed as a string).
- Produces:
  - `TELEGRAM_LIMIT = 4096`
  - `truncate(text: str) -> str`
  - `send_sync(text: str) -> bool` — plain text, no `parse_mode`; returns delivery success
  - `format_download_success(feeds: dict[str, date | None], today: date, attempt: int) -> str`
  - `format_options_book(target: date, contracts: list[dict]) -> str`
  - `format_chain_failure(step: str, tail: str) -> str`
  - `format_stopped(outcome: str, reason: str, attempt: int) -> str`

- [ ] **Step 1: Write the failing test**

Create `tests/scheduler/test_eod_telegram.py`:

```python
from datetime import date

from core.scheduler.eod_telegram import (
    TELEGRAM_LIMIT,
    format_chain_failure,
    format_download_success,
    format_options_book,
    format_stopped,
    truncate,
)

TODAY = date(2026, 7, 31)


def test_truncate_leaves_short_text_untouched():
    assert truncate("hello") == "hello"


def test_truncate_caps_at_telegram_limit_with_marker():
    out = truncate("x" * 5000)
    assert len(out) <= TELEGRAM_LIMIT
    assert out.endswith("… truncated")


def test_download_success_names_fresh_feeds():
    msg = format_download_success(
        {"equity": TODAY, "futures": TODAY, "stock_options": date(2026, 7, 30), "index": TODAY},
        TODAY, attempt=2)
    assert "2026-07-31" in msg
    assert "futures" in msg
    assert "stock_options" in msg  # stale feeds are reported too


def test_options_book_renders_one_line_per_contract():
    contracts = [
        {"ticker": "RELIANCE", "direction": "LONG", "opt_type": "CE", "expiry": date(2026, 8, 27),
         "strike": 1500.0, "settle": 42.5, "premium_cost": 21250.0, "lot_size": 500,
         "screen": "ok", "screen_reason": "", "instrument_key": "NSE_FO|1234"},
        {"ticker": "TCS", "direction": "SHORT", "opt_type": "PE", "expiry": date(2026, 8, 27),
         "strike": 3200.0, "settle": 55.0, "premium_cost": 9350.0, "lot_size": 170,
         "screen": "ok", "screen_reason": "", "instrument_key": "NSE_FO|5678"},
    ]
    msg = format_options_book(TODAY, contracts)
    assert "RELIANCE" in msg and "TCS" in msg
    assert "CE" in msg and "PE" in msg
    assert len(msg) <= TELEGRAM_LIMIT


def test_options_book_marks_untradeable_contracts():
    contracts = [{"ticker": "IDEA", "direction": "LONG", "opt_type": "CE", "expiry": None,
                  "strike": None, "settle": None, "premium_cost": None, "lot_size": None,
                  "screen": "no_tradeable_strike", "screen_reason": "spread 12%",
                  "instrument_key": None}]
    msg = format_options_book(TODAY, contracts)
    assert "IDEA" in msg
    assert "spread 12%" in msg


def test_options_book_handles_empty_book():
    msg = format_options_book(TODAY, [])
    assert "no contracts" in msg.lower()


def test_formatters_never_emit_markdown_control_chars_unescaped():
    # Plain-text mode: underscores in tickers must survive verbatim.
    contracts = [{"ticker": "M_M", "direction": "LONG", "opt_type": "CE", "expiry": date(2026, 8, 27),
                  "strike": 100.0, "settle": 1.0, "premium_cost": 100.0, "lot_size": 100,
                  "screen": "ok", "screen_reason": "", "instrument_key": "k"}]
    assert "M_M" in format_options_book(TODAY, contracts)


def test_chain_failure_includes_step_and_tail():
    msg = format_chain_failure("refresh_all_strategies.py", "Traceback\nBoomError")
    assert "refresh_all_strategies.py" in msg
    assert "BoomError" in msg


def test_stopped_message_includes_outcome_and_reason():
    msg = format_stopped("holiday", "no feed published 2026-07-31", attempt=3)
    assert "holiday" in msg.lower()
    assert "no feed published" in msg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/scheduler/test_eod_telegram.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.scheduler.eod_telegram'`

- [ ] **Step 3: Write minimal implementation**

Create `core/scheduler/eod_telegram.py`:

```python
"""Telegram delivery for the EOD job.

Deliberately does NOT use TelegramNotifier.send_message: that dispatches on a
daemon thread and returns, so a message sent just before process exit can be
killed mid-flight. It also hardcodes Markdown parse mode, which returns HTTP
400 for tickers containing `_` or `*` — losing the message silently.
"""
from __future__ import annotations

import logging
import os
from datetime import date

import requests

logger = logging.getLogger(__name__)

TELEGRAM_LIMIT = 4096
_MARKER = "… truncated"


def truncate(text: str) -> str:
    if len(text) <= TELEGRAM_LIMIT:
        return text
    return text[: TELEGRAM_LIMIT - len(_MARKER)] + _MARKER


def send_sync(text: str) -> bool:
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.warning("TELEGRAM_TOKEN/TELEGRAM_CHAT_ID not set — message not sent")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": truncate(text)},  # plain text, no parse_mode
            timeout=20,
        )
    except requests.RequestException as e:
        logger.error(f"Telegram send failed: {e}")
        return False
    if resp.status_code != 200:
        logger.error(f"Telegram send failed: HTTP {resp.status_code} {resp.text[:200]}")
        return False
    return True


def format_download_success(feeds: dict[str, date | None], today: date, attempt: int) -> str:
    lines = [f"DATA DOWNLOADED — {today}", f"attempt {attempt}", ""]
    for name in sorted(feeds):
        d = feeds[name]
        mark = "OK  " if d == today else "old "
        lines.append(f"  {mark}{name}: {d if d else 'no data'}")
    return truncate("\n".join(lines))


def format_options_book(target: date, contracts: list[dict]) -> str:
    lines = [f"TS BASIS DAILY — ATM OPTIONS {target}", ""]
    if not contracts:
        lines.append("  (no contracts selected)")
        return truncate("\n".join(lines))
    for c in contracts:
        if c.get("strike") is None:
            reason = c.get("screen_reason") or c.get("screen") or "no chain"
            lines.append(f"{c['ticker']} {c['direction']} {c['opt_type']} — SKIP ({reason})")
            continue
        cost = c.get("premium_cost") or 0
        lines.append(
            f"{c['ticker']} {c['direction']} {c['opt_type']} {c['strike']:.0f} "
            f"exp {c['expiry']}"
        )
        lines.append(
            f"   prem {c['settle']:.2f} x {c.get('lot_size') or 0} = {cost:,.0f}"
        )
    lines.append("")
    lines.append("Live prices: /ts-basis-daily/")
    return truncate("\n".join(lines))


def format_chain_failure(step: str, tail: str) -> str:
    return truncate(f"CHAIN FAILED — {step}\n\n{tail}")


def format_stopped(outcome: str, reason: str, attempt: int) -> str:
    return truncate(f"EOD STOPPED — {outcome}\nattempts: {attempt}\n{reason}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/scheduler/test_eod_telegram.py -v`
Expected: PASS — 9 passed

- [ ] **Step 5: Commit**

```bash
git add core/scheduler/eod_telegram.py tests/scheduler/test_eod_telegram.py
git commit -m "feat: add synchronous Telegram sender and EOD message formatters"
```

---

## Task 4: Chain runner

**Files:**
- Create: `core/scheduler/eod_chain.py`
- Test: `tests/scheduler/test_eod_chain.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `CHAIN_STEPS: list[tuple[str, Path]]` — `(label, script_path)` in execution order
  - `StepResult` — dataclass: `label: str`, `ok: bool`, `stdout: str`, `stderr_tail: str`
  - `run_step(label: str, script: Path, timeout: int = 3600) -> StepResult`
  - `run_chain(steps=None) -> list[StepResult]` — stops after the first failure

- [ ] **Step 1: Write the failing test**

Create `tests/scheduler/test_eod_chain.py`:

```python
from pathlib import Path

from core.scheduler.eod_chain import run_chain, run_step


def _script(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def test_run_step_succeeds_on_zero_exit(tmp_path):
    s = _script(tmp_path, "ok.py", "print('fine')\n")
    r = run_step("ok", s)
    assert r.ok is True
    assert "fine" in r.stdout


def test_run_step_fails_on_nonzero_exit_and_captures_stderr(tmp_path):
    s = _script(tmp_path, "bad.py", "import sys; print('BoomError', file=sys.stderr); sys.exit(1)\n")
    r = run_step("bad", s)
    assert r.ok is False
    assert "BoomError" in r.stderr_tail


def test_run_step_survives_non_ascii_output(tmp_path):
    # Windows default code page raises UnicodeDecodeError on these without utf-8.
    s = _script(tmp_path, "uni.py", "print('carry — basis → ₹100')\n")
    r = run_step("uni", s)
    assert r.ok is True


def test_run_chain_stops_at_first_failure(tmp_path):
    a = _script(tmp_path, "a.py", "print('a')\n")
    b = _script(tmp_path, "b.py", "import sys; sys.exit(2)\n")
    c = _script(tmp_path, "c.py", "raise AssertionError('must not run')\n")
    results = run_chain([("a", a), ("b", b), ("c", c)])
    assert [r.label for r in results] == ["a", "b"]
    assert results[-1].ok is False


def test_run_chain_runs_all_steps_when_all_pass(tmp_path):
    a = _script(tmp_path, "a.py", "print('a')\n")
    b = _script(tmp_path, "b.py", "print('b')\n")
    results = run_chain([("a", a), ("b", b)])
    assert all(r.ok for r in results)
    assert len(results) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/scheduler/test_eod_chain.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.scheduler.eod_chain'`

- [ ] **Step 3: Write minimal implementation**

Create `core/scheduler/eod_chain.py`:

```python
"""Sequential runner for the post-download strategy chain.

Aborts at the first non-zero exit: the chain is a real dependency (options
selection reads what the signal refresh produced), so continuing would emit
authoritative-looking options built on stale signals.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"

CHAIN_STEPS = [
    ("refresh_all_strategies.py", SCRIPTS / "refresh_all_strategies.py"),
    ("ts_basis_daily_signals.py", SCRIPTS / "ts_basis_daily_signals.py"),
    ("ts_basis_daily_options.py", SCRIPTS / "ts_basis_daily_options.py"),
]

STDERR_TAIL_LINES = 20


@dataclass
class StepResult:
    label: str
    ok: bool
    stdout: str
    stderr_tail: str


def run_step(label: str, script: Path, timeout: int = 3600) -> StepResult:
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return StepResult(label, False, "", f"TIMEOUT after {timeout}s")
    tail = "\n".join((proc.stderr or "").strip().splitlines()[-STDERR_TAIL_LINES:])
    return StepResult(label, proc.returncode == 0, proc.stdout or "", tail)


def run_chain(steps=None) -> list[StepResult]:
    results = []
    for label, script in (steps if steps is not None else CHAIN_STEPS):
        result = run_step(label, script)
        results.append(result)
        if not result.ok:
            break
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/scheduler/test_eod_chain.py -v`
Expected: PASS — 5 passed

- [ ] **Step 5: Commit**

```bash
git add core/scheduler/eod_chain.py tests/scheduler/test_eod_chain.py
git commit -m "feat: add abort-on-failure chain runner with utf-8 subprocess capture"
```

---

## Task 5: Job orchestrator

**Files:**
- Create: `core/scheduler/eod_job.py`
- Test: `tests/scheduler/test_eod_job.py`

**Interfaces:**
- Consumes: `EodStore` (Task 1), `probe_feeds`/`decide`/`Decision` (Task 2), `eod_telegram` formatters + `send_sync` (Task 3), `run_chain`/`StepResult` (Task 4).
- Produces:
  - `DOWNLOAD_SCRIPT: Path`
  - `run_download(timeout: int = 3600) -> StepResult`
  - `run_attempt(store: EodStore, run_date: date, attempt: int, now: datetime, deps: Deps | None = None) -> str` — returns the outcome string recorded
  - `Deps` — dataclass injecting `download`, `probe`, `chain`, `send`, `book` callables so tests need no subprocesses or network

- [ ] **Step 1: Write the failing test**

Create `tests/scheduler/test_eod_job.py`:

```python
from datetime import date, datetime

import pytest

from core.scheduler.eod_chain import StepResult
from core.scheduler.eod_job import Deps, run_attempt
from core.scheduler.eod_store import EodStore

TODAY = date(2026, 7, 31)
YESTERDAY = date(2026, 7, 30)


@pytest.fixture
def store(tmp_path):
    return EodStore(tmp_path / "eod.sqlite")


def make_deps(feed_map, chain_results=None, sent=None):
    sent = sent if sent is not None else []
    return Deps(
        download=lambda: StepResult("download", True, "", ""),
        probe=lambda: feed_map,
        chain=lambda: chain_results if chain_results is not None
        else [StepResult(lbl, True, "", "") for lbl in ("a", "b", "c")],
        send=lambda text: (sent.append(text), True)[1],
        book=lambda: (TODAY, []),
    )


def feeds(**kw):
    base = {"equity": YESTERDAY, "futures": YESTERDAY,
            "stock_options": YESTERDAY, "index": YESTERDAY}
    base.update(kw)
    return base


def test_successful_run_records_success_and_sends_two_messages(store):
    sent = []
    outcome = run_attempt(store, TODAY, 1, datetime(2026, 7, 31, 20, 0),
                          make_deps(feeds(futures=TODAY), sent=sent))
    assert outcome == "success"
    assert store.is_date_terminal(TODAY) is True
    assert len(sent) == 2  # download success + options book


def test_retry_records_retry_and_sends_nothing(store):
    sent = []
    outcome = run_attempt(store, TODAY, 1, datetime(2026, 7, 31, 20, 0),
                          make_deps(feeds(equity=TODAY), sent=sent))
    assert outcome == "retry"
    assert store.is_date_terminal(TODAY) is False
    assert sent == []


def test_holiday_records_holiday_and_notifies(store):
    sent = []
    outcome = run_attempt(store, TODAY, 3, datetime(2026, 7, 31, 21, 0),
                          make_deps(feeds(), sent=sent))
    assert outcome == "holiday"
    assert store.is_date_terminal(TODAY) is True
    assert len(sent) == 1


def test_chain_failure_records_chain_failed_and_alerts(store):
    sent = []
    deps = make_deps(
        feeds(futures=TODAY),
        chain_results=[StepResult("refresh_all_strategies.py", False, "", "BoomError")],
        sent=sent,
    )
    outcome = run_attempt(store, TODAY, 1, datetime(2026, 7, 31, 20, 0), deps)
    assert outcome == "chain_failed"
    assert store.is_date_terminal(TODAY) is True
    assert any("BoomError" in m for m in sent)


def test_exhausted_on_final_attempt(store):
    sent = []
    outcome = run_attempt(store, TODAY, 8, datetime(2026, 7, 31, 23, 30),
                          make_deps(feeds(equity=TODAY), sent=sent))
    assert outcome == "exhausted"
    assert store.is_date_terminal(TODAY) is True
    assert len(sent) == 1


def test_options_book_message_is_sent_after_chain(store):
    sent = []
    run_attempt(store, TODAY, 1, datetime(2026, 7, 31, 20, 0),
                make_deps(feeds(futures=TODAY), sent=sent))
    assert "ATM OPTIONS" in sent[-1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/scheduler/test_eod_job.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.scheduler.eod_job'`

- [ ] **Step 3: Write minimal implementation**

Create `core/scheduler/eod_job.py`:

```python
"""One EOD attempt: download -> probe -> decide -> act -> record.

Dependencies are injected via Deps so the whole decision path is testable
without subprocesses, DuckDB stores, or network calls.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from core.scheduler import eod_telegram as tg
from core.scheduler.eod_chain import StepResult, run_chain, run_step
from core.scheduler.eod_decision import decide, probe_feeds
from core.scheduler.eod_store import EodStore

ROOT = Path(__file__).resolve().parents[2]
DOWNLOAD_SCRIPT = ROOT / "scripts" / "download_all_data.py"


def run_download(timeout: int = 3600) -> StepResult:
    return run_step("download_all_data.py", DOWNLOAD_SCRIPT, timeout=timeout)


def _default_book():
    sys.path.insert(0, str(ROOT / "scripts"))
    from ts_basis_daily_options import get_book
    from core.analytics.options_selection import DEFAULT_MIN_DTE, select_book_options
    target, book = get_book(None, 5)
    return target, select_book_options(book, min_dte=DEFAULT_MIN_DTE)


@dataclass
class Deps:
    download: Callable[[], StepResult] = run_download
    probe: Callable[[], dict] = probe_feeds
    chain: Callable[[], list] = run_chain
    send: Callable[[str], bool] = tg.send_sync
    book: Callable[[], tuple] = _default_book


def run_attempt(store: EodStore, run_date: date, attempt: int,
                now: datetime, deps: Deps | None = None) -> str:
    deps = deps or Deps()

    deps.download()  # exit code is not authoritative — the feed probe is
    feeds = deps.probe()
    decision = decide(feeds, run_date, now, attempt)

    if decision.action in ("holiday", "exhausted"):
        deps.send(tg.format_stopped(decision.action, decision.reason, attempt))
        store.record(run_date, attempt, "download", decision.action, decision.reason)
        return decision.action

    if decision.action == "retry":
        store.record(run_date, attempt, "download", "retry", decision.reason)
        return "retry"

    # decision.action == "chain"
    deps.send(tg.format_download_success(feeds, run_date, attempt))

    results = deps.chain()
    failed = next((r for r in results if not r.ok), None)
    if failed:
        deps.send(tg.format_chain_failure(failed.label, failed.stderr_tail))
        store.record(run_date, attempt, "chain", "chain_failed",
                     f"{failed.label}: {failed.stderr_tail[:300]}")
        return "chain_failed"

    target, contracts = deps.book()
    deps.send(tg.format_options_book(target, contracts))
    store.record(run_date, attempt, "done", "success", f"{len(results)} chain steps ok")
    return "success"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/scheduler/test_eod_job.py -v`
Expected: PASS — 6 passed

- [ ] **Step 5: Commit**

```bash
git add core/scheduler/eod_job.py tests/scheduler/test_eod_job.py
git commit -m "feat: add EOD attempt orchestrator with injectable dependencies"
```

---

## Task 6: Worker daemon

**Files:**
- Create: `scripts/schedule_worker.py`
- Create (if absent): `scripts/__init__.py`
- Test: `tests/scheduler/test_worker_timing.py`

**Interfaces:**
- Consumes: `EodStore` (Task 1), `MAX_ATTEMPTS` (Task 2), `run_attempt` (Task 5).
- Produces:
  - `FIRE_HOUR = 20`, `STOP_HOUR = 23`, `STOP_MINUTE = 30`, `RETRY_MINUTES = 30`, `TICK_SECONDS = 60`
  - `is_due(now: datetime, last_started: datetime | None, attempts: int) -> bool` — pure, unit-tested
  - `acquire_lock(lock_path: Path) -> bool`
  - `main() -> int`

- [ ] **Step 1: Write the failing test**

Create `tests/scheduler/test_worker_timing.py`:

```python
from datetime import datetime

from scripts.schedule_worker import is_due

MON_2000 = datetime(2026, 7, 27, 20, 0)     # Monday
MON_1959 = datetime(2026, 7, 27, 19, 59)
MON_2330 = datetime(2026, 7, 27, 23, 30)
MON_2331 = datetime(2026, 7, 27, 23, 31)
SAT_2000 = datetime(2026, 8, 1, 20, 0)      # Saturday


def test_not_due_before_fire_hour():
    assert is_due(MON_1959, None, 0) is False


def test_due_at_fire_hour_with_no_prior_attempt():
    assert is_due(MON_2000, None, 0) is True


def test_not_due_on_weekend():
    assert is_due(SAT_2000, None, 0) is False


def test_not_due_after_stop_time():
    assert is_due(MON_2331, None, 0) is False


def test_due_exactly_at_stop_time():
    assert is_due(MON_2330, datetime(2026, 7, 27, 23, 0), 7) is True


def test_not_due_before_retry_interval_elapses():
    assert is_due(datetime(2026, 7, 27, 20, 20), MON_2000, 1) is False


def test_due_once_retry_interval_elapses():
    assert is_due(datetime(2026, 7, 27, 20, 30), MON_2000, 1) is True


def test_not_due_once_attempt_cap_reached():
    assert is_due(datetime(2026, 7, 27, 23, 0), datetime(2026, 7, 27, 22, 0), 8) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/scheduler/test_worker_timing.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.schedule_worker'`

- [ ] **Step 3: Write minimal implementation**

First ensure `scripts` is importable as a package (the test imports `scripts.schedule_worker`). Create `scripts/__init__.py` **only if it does not already exist**:

```bash
python -c "import pathlib; p=pathlib.Path('scripts/__init__.py'); print('exists') if p.exists() else (p.write_text(''), print('created'))"
```

Create `scripts/schedule_worker.py`:

```python
"""EOD automation worker.

Standalone daemon. Flask must NOT run this in-process: it runs with
debug=True, so the Werkzeug reloader forks two processes and the job would
fire twice.

Usage:
  python scripts/schedule_worker.py
"""
from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.scheduler.eod_decision import MAX_ATTEMPTS  # noqa: E402
from core.scheduler.eod_job import run_attempt  # noqa: E402
from core.scheduler.eod_store import EodStore  # noqa: E402

STORE_PATH = ROOT / "data" / "_eod_automation.sqlite"
LOCK_PATH = ROOT / "data" / "_eod_worker.lock"

FIRE_HOUR = 20
STOP_HOUR = 23
STOP_MINUTE = 30
RETRY_MINUTES = 30
TICK_SECONDS = 60

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
logger = logging.getLogger("eod_worker")


def is_due(now: datetime, last_started: datetime | None, attempts: int) -> bool:
    if now.weekday() > 4:  # Mon=0 .. Fri=4
        return False
    if attempts >= MAX_ATTEMPTS:
        return False
    if now.hour < FIRE_HOUR:
        return False
    if (now.hour, now.minute) > (STOP_HOUR, STOP_MINUTE):
        return False
    if last_started is None:
        return True
    return now >= last_started + timedelta(minutes=RETRY_MINUTES)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    except Exception:
        return True
    return True


def acquire_lock(lock_path: Path) -> bool:
    if lock_path.exists():
        try:
            pid = int(lock_path.read_text().strip())
        except (ValueError, OSError):
            pid = None
        if pid and _pid_alive(pid):
            return False
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(str(os.getpid()))
    return True


def main() -> int:
    if not acquire_lock(LOCK_PATH):
        logger.error(f"Another worker is already running (see {LOCK_PATH}). Exiting.")
        return 1

    store = EodStore(STORE_PATH)
    offset = datetime.now().astimezone().utcoffset()
    logger.info(f"EOD worker started (pid {os.getpid()}), local UTC offset {offset}")
    logger.info(f"Fire window {FIRE_HOUR}:00-{STOP_HOUR}:{STOP_MINUTE:02d} Mon-Fri, "
                f"retry {RETRY_MINUTES}min, max {MAX_ATTEMPTS} attempts")

    while True:
        try:
            store.heartbeat(os.getpid())
            now = datetime.now()
            today = now.date()

            if store.consume_run_now():
                logger.info("Manual run requested — running one attempt (attempt=0)")
                outcome = run_attempt(store, today, 0, now)
                logger.info(f"Manual run outcome: {outcome}")

            elif store.is_enabled() and not store.is_date_terminal(today):
                attempts = store.attempts_today(today)
                if is_due(now, store.last_attempt_started(today), len(attempts)):
                    n = len(attempts) + 1
                    logger.info(f"Attempt {n} for {today}")
                    outcome = run_attempt(store, today, n, now)
                    logger.info(f"Attempt {n} outcome: {outcome}")
        except Exception as e:
            logger.exception(f"Worker tick failed: {e}")

        time.sleep(TICK_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/scheduler/test_worker_timing.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/schedule_worker.py scripts/__init__.py tests/scheduler/test_worker_timing.py
git commit -m "feat: add EOD worker daemon with single-instance lock and fire-window logic"
```

---

## Task 7: Facade and API endpoints

**Files:**
- Modify: `app_facade/data_facade.py` (add import at top; add methods to `DataFacade` after `compute_next_run`, ~line 487)
- Modify: `flask_app/blueprints/data/routes.py` (append endpoints at end of file)
- Test: `tests/scheduler/test_eod_facade.py`

**Interfaces:**
- Consumes: `EodStore`, `TERMINAL_OUTCOMES` (Task 1); `MAX_ATTEMPTS` (Task 2).
- Produces:
  - `DataFacade.get_eod_status() -> dict` — keys: `enabled`, `worker_alive`, `worker_pid`, `heartbeat`, `last_run`, `attempts_today`, `max_attempts`
  - `DataFacade.set_eod_enabled(value: bool) -> dict`
  - `DataFacade.trigger_eod_run_now() -> dict`
  - Endpoints: `GET /data/api/eod/status`, `POST /data/api/eod/toggle`, `POST /data/api/eod/run-now`

- [ ] **Step 1: Write the failing test**

Create `tests/scheduler/test_eod_facade.py`:

```python
import sqlite3
from datetime import date, datetime, timedelta

import pytest

from app_facade.data_facade import DataFacade
from core.scheduler.eod_store import EodStore


@pytest.fixture
def facade(tmp_path):
    f = DataFacade(data_root=tmp_path)
    f._eod_store_path = tmp_path / "eod.sqlite"
    return f


def test_status_reports_disabled_and_no_worker(facade):
    st = facade.get_eod_status()
    assert st["enabled"] is False
    assert st["worker_alive"] is False


def test_toggle_enables_and_persists(facade):
    facade.set_eod_enabled(True)
    assert facade.get_eod_status()["enabled"] is True
    facade.set_eod_enabled(False)
    assert facade.get_eod_status()["enabled"] is False


def test_worker_alive_true_on_fresh_heartbeat(facade):
    EodStore(facade._eod_store_path).heartbeat(999)
    assert facade.get_eod_status()["worker_alive"] is True


def test_worker_alive_false_on_stale_heartbeat(facade):
    EodStore(facade._eod_store_path).heartbeat(999)
    stale = (datetime.now() - timedelta(minutes=10)).isoformat()
    con = sqlite3.connect(str(facade._eod_store_path))
    con.execute("UPDATE eod_automation SET worker_heartbeat=? WHERE id=1", [stale])
    con.commit()
    con.close()
    assert facade.get_eod_status()["worker_alive"] is False


def test_run_now_sets_the_trigger(facade):
    facade.trigger_eod_run_now()
    assert EodStore(facade._eod_store_path).consume_run_now() is True


def test_status_reports_attempts_today(facade):
    EodStore(facade._eod_store_path).record(date.today(), 1, "download", "retry", "")
    assert facade.get_eod_status()["attempts_today"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/scheduler/test_eod_facade.py -v`
Expected: FAIL — `AttributeError: 'DataFacade' object has no attribute 'get_eod_status'`

- [ ] **Step 3: Write minimal implementation**

In `app_facade/data_facade.py`, add near the other imports at the top (after `import duckdb`):

```python
from core.scheduler.eod_store import EodStore
```

Then add these methods to the `DataFacade` class, immediately after `compute_next_run` (~line 487), keeping the existing indentation level (4 spaces, inside the class):

```python
    # ── EOD automation ────────────────────────────────────────────────

    HEARTBEAT_STALE_SECONDS = 180

    @property
    def _eod_store(self) -> EodStore:
        path = getattr(self, "_eod_store_path", None) or (self._root / "_eod_automation.sqlite")
        return EodStore(path)

    def get_eod_status(self) -> dict:
        from datetime import date as _date

        from core.scheduler.eod_decision import MAX_ATTEMPTS

        store = self._eod_store
        heartbeat, pid = store.get_heartbeat()
        alive = False
        if heartbeat:
            age = (datetime.now() - datetime.fromisoformat(heartbeat)).total_seconds()
            alive = age <= self.HEARTBEAT_STALE_SECONDS
        return {
            "enabled": store.is_enabled(),
            "worker_alive": alive,
            "worker_pid": pid,
            "heartbeat": heartbeat,
            "last_run": store.latest_run(),
            "attempts_today": len(store.attempts_today(_date.today())),
            "max_attempts": MAX_ATTEMPTS,
        }

    def set_eod_enabled(self, value: bool) -> dict:
        self._eod_store.set_enabled(value)
        return self.get_eod_status()

    def trigger_eod_run_now(self) -> dict:
        self._eod_store.request_run_now()
        return {"requested": True}
```

In `flask_app/blueprints/data/routes.py`, append at the end of the file:

```python
# ── EOD automation ────────────────────────────────────────────────────

@data_bp.route('/api/eod/status')
@login_required
def eod_status():
    try:
        return jsonify({"success": True, "status": _get_facade().get_eod_status()})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@data_bp.route('/api/eod/toggle', methods=['POST'])
@login_required
def eod_toggle():
    try:
        enabled = bool(request.get_json().get("enabled"))
        return jsonify({"success": True, "status": _get_facade().set_eod_enabled(enabled)})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@data_bp.route('/api/eod/run-now', methods=['POST'])
@login_required
def eod_run_now():
    try:
        return jsonify({"success": True, **_get_facade().trigger_eod_run_now()})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/scheduler/test_eod_facade.py -v`
Expected: PASS — 6 passed

Then confirm the whole suite is green: `python -m pytest tests/scheduler/ -v`
Expected: PASS — 47 passed

- [ ] **Step 5: Commit**

```bash
git add app_facade/data_facade.py flask_app/blueprints/data/routes.py tests/scheduler/test_eod_facade.py
git commit -m "feat: add EOD automation facade methods and API endpoints"
```

---

## Task 8: UI tab

**Files:**
- Modify: `flask_app/templates/data/index.html` (tab bar ~line 56; tab content after the schedule block ending ~line 280; `DataUI` JS object ~line 315 and ~line 730)

**Interfaces:**
- Consumes: `GET /data/api/eod/status`, `POST /data/api/eod/toggle`, `POST /data/api/eod/run-now` (Task 7).
- Produces: no code interface — UI only.

- [ ] **Step 1: Add the tab button**

In `flask_app/templates/data/index.html`, immediately after the Schedule tab button (the `<button>` whose label is `Schedule`, ~lines 56–58), insert:

```html
        <button onclick="DataUI.switchTab('automation')" id="tab-automation" class="tab-btn px-5 py-3 text-sm font-semibold border-b-2 border-transparent text-slate-500 hover:text-slate-300 whitespace-nowrap">
            <i class="fas fa-robot mr-2"></i>Automation
        </button>
```

- [ ] **Step 2: Add the tab content panel**

After the closing `</div>` of `<div id="tab-content-schedule" ...>` (~line 280), insert:

```html
    <div id="tab-content-automation" class="tab-content hidden">
        <div class="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
            <div class="flex items-start justify-between mb-4">
                <div>
                    <h3 class="text-white font-semibold mb-1">EOD Automation</h3>
                    <p class="text-sm text-slate-400">Runs the full download + strategy chain at 20:00 Mon–Fri, retrying every 30 min until data arrives (hard stop 23:30). Reports to Telegram.</p>
                </div>
                <div class="flex items-center gap-3">
                    <button onclick="DataUI._eodRunNow()" class="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg text-sm">Run now</button>
                    <button id="eod-toggle" onclick="DataUI._eodToggle()" class="px-4 py-2 rounded-lg text-sm text-white bg-slate-700">…</button>
                </div>
            </div>
            <div id="eod-status" class="text-sm text-slate-300 space-y-1"></div>
        </div>
    </div>
```

- [ ] **Step 3: Add the JS handlers**

In the `DataUI` object's `switchTab` method, next to the existing `if (name === 'schedule') this._loadSchedule();` line (~line 315), add:

```javascript
        if (name === 'automation') this._loadEod();
```

Then add these methods to the `DataUI` object, after the Schedule section (~line 730). Note the trailing comma — these sit among other object methods:

```javascript
    // ── EOD Automation ───────────────────────────────────────────
    async _loadEod() {
        const r = await fetch('/data/api/eod/status');
        const d = await r.json();
        if (!d.success) return;
        const s = d.status;
        const btn = document.getElementById('eod-toggle');
        btn.textContent = s.enabled ? 'Enabled' : 'Disabled';
        btn.className = 'px-4 py-2 rounded-lg text-sm text-white ' +
            (s.enabled ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-slate-700 hover:bg-slate-600');

        const worker = s.worker_alive
            ? `<span class="text-emerald-400">running</span> (pid ${s.worker_pid})`
            : `<span class="text-red-400">not running</span> — start it with <code>python scripts/schedule_worker.py</code>`;
        const last = s.last_run
            ? `${s.last_run.run_date} attempt ${s.last_run.attempt} → <b>${s.last_run.outcome}</b> <span class="text-slate-500">${s.last_run.detail || ''}</span>`
            : 'no runs recorded';
        document.getElementById('eod-status').innerHTML = `
            <div>Worker: ${worker}</div>
            <div>Last run: ${last}</div>
            <div>Attempts today: ${s.attempts_today} / ${s.max_attempts}</div>`;
    },

    async _eodToggle() {
        const r = await fetch('/data/api/eod/status');
        const cur = (await r.json()).status.enabled;
        await fetch('/data/api/eod/toggle', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({enabled: !cur}),
        });
        this._loadEod();
    },

    async _eodRunNow() {
        await fetch('/data/api/eod/run-now', {method: 'POST'});
        alert('Manual run requested — the worker picks it up within 60 seconds.');
        this._loadEod();
    },
```

- [ ] **Step 4: Verify in the browser**

Start Flask: `python scripts/run_flask.py`
Open `http://127.0.0.1:5000/data/` → **Automation** tab.
Expected: the panel renders; worker shows **not running** (red) since the daemon isn't started; the toggle flips between Enabled/Disabled and the state survives a page reload.

Then start the worker in a second terminal: `python scripts/schedule_worker.py`
Expected: within 60 s, reloading the tab shows worker **running** with a pid.

- [ ] **Step 5: Commit**

```bash
git add flask_app/templates/data/index.html
git commit -m "feat: add EOD automation tab to the data page"
```

---

## Task 9: End-to-end manual verification

**Files:**
- Create: `docs/reports/EOD_AUTOMATION_VERIFICATION.md`

**Interfaces:**
- Consumes: everything above.
- Produces: a verification record.

- [ ] **Step 1: Set Telegram credentials**

PowerShell:
```
$env:TELEGRAM_TOKEN="<token>"
$env:TELEGRAM_CHAT_ID="<chat id>"
```

The worker must be started **in the same shell** so it inherits these.

- [ ] **Step 2: Verify Telegram delivery in isolation**

```bash
python -c "from core.scheduler.eod_telegram import send_sync; print(send_sync('EOD automation test message'))"
```

Expected: prints `True` and the message arrives on the phone. If it prints `False`, read the logged reason and fix it before continuing — do not proceed on a failing send.

- [ ] **Step 3: Run the full path via Run now**

With the worker running and Flask open on the Automation tab, click **Run now**.

Expected within ~60 s, the worker log shows `Manual run requested`, then a `download_all_data.py` run, then one of:
- trading day with data → two Telegram messages (download success, options book), log `Manual run outcome: success`
- non-trading day → one Telegram message, log `Manual run outcome: holiday`

Confirm the manual run recorded `attempt = 0` and did **not** mark the date terminal:

```bash
python -c "import sqlite3;print(sqlite3.connect('data/_eod_automation.sqlite').execute('SELECT run_date,attempt,outcome,detail FROM eod_run_log ORDER BY started_at DESC LIMIT 5').fetchall())"
```

Expected: the newest row has `attempt = 0`.

- [ ] **Step 4: Verify the single-instance lock**

Start a second worker in another terminal: `python scripts/schedule_worker.py`
Expected: it exits immediately with `Another worker is already running`.

- [ ] **Step 5: Write the verification report and commit**

Create `docs/reports/EOD_AUTOMATION_VERIFICATION.md` recording: the date run, which branch of the §4.1 decision table fired, the Telegram messages received (pasted), the `eod_run_log` rows, and the lock-test result.

```bash
git add docs/reports/EOD_AUTOMATION_VERIFICATION.md
git commit -m "docs: EOD automation end-to-end verification record"
```

---

## Self-Review

**Spec coverage:**

| Spec section | Task |
|---|---|
| §3 architecture (3 components) | 1, 2–5, 6 |
| §3.1 SQLite not DuckDB | 1 |
| §3.2 control schema | 1 |
| §4 feed probe, `data_arrived` / `trading_day` | 2 |
| §4.1 decision table (4 branches) | 2 |
| §4.2 21:00 grace | 2 |
| §5 fire window, retry, cap, idempotency, lock, missed-fire, kill switch | 1 (idempotency), 6 (rest) |
| §6 chain, abort-on-failure, utf-8, timeout | 4 |
| §7 sync send, plain text, 4 message types, truncation, `get_book` | 3, 5 |
| §8 UI card, status, worker health, Run now, 3 endpoints, run-now semantics | 7, 8 |
| §9 testing | Tasks 1–7 tests; Task 9 manual |

**Placeholder scan:** clean — every step carries runnable code or an exact command.

**Type consistency:** `StepResult` fields (`label`/`ok`/`stdout`/`stderr_tail`) match across Tasks 4 and 5. `Decision.action` values (`chain`/`retry`/`holiday`/`exhausted`) align with `TERMINAL_OUTCOMES` (which additionally carries `chain_failed`, produced only in Task 5) and the non-terminal `retry`. `EodStore` method names used in Tasks 5–7 match Task 1's definitions. `MAX_ATTEMPTS` is defined once in Task 2 and imported by Tasks 6 and 7.

**External signatures — verified against source, not assumed:**

- `core/analytics/options_selection.py:295` — `select_book_options(book, min_dte: int = DEFAULT_MIN_DTE, today: date | None = None, ...)`. `min_dte` is the correct keyword and is typed **non-optional `int`**, so passing `None` would break it; Task 5 passes `DEFAULT_MIN_DTE` (`= 7`, line 28).
- `scripts/ts_basis_daily_options.py:45` — `get_book(target: date | None, top_n: int)` returns `(target_date, [(underlying, direction), ...])`, which is exactly the `book` argument `select_book_options` expects.
- Contract dict keys used by `format_options_book` (Task 3) — `ticker`, `direction`, `opt_type`, `expiry`, `strike`, `settle`, `lot_size`, `premium_cost`, `screen`, `screen_reason`, `instrument_key` — all confirmed emitted at `scripts/ts_basis_daily_options.py:87-104`.

The Task 5 unit tests inject `book`, so they do not exercise `_default_book()`; Task 9 Step 3 is what proves that path end to end.
