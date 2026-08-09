# Ops Orchestrator + Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A single foreground command that brings up the NiftyShield PAPER trading-window stack (Flask → token → ingestor → poller → session) in dependency order and keeps it alive, plus a standalone read-only preflight go/no-go checker.

**Architecture:** Two units under a new `scripts/ops/` package sharing Windows-safe PID/lock helpers. `preflight.py` resolves system state into a frozen context and runs pure tiered checks (BLOCK/WARN). `orchestrator.py` is a foreground supervisor: a start state machine (token gate → warm-up park → background catch-up → final preflight gate) then a supervise loop that restarts crashed children and stops them cleanly. A small change to `session.py` makes the PAPER session stop cleanly on an external signal.

**Tech Stack:** Python 3.10+, DuckDB, `subprocess`, `ctypes` (Windows process APIs), pytest. Design spec: `docs/superpowers/specs/2026-08-09-ops-orchestrator-preflight-design.md`.

## Global Constraints

- **Python 3.10+**; Windows 11 is the primary target — every process-control path must be Windows-correct and POSIX-safe. **Never `os.kill(pid, 0)` on Windows** (use `OpenProcess`).
- **DuckDB read contention:** the chain cache is written by the poller via `os.replace`. All reads of `data/options/chain_cache.duckdb` are read-only with a bounded retry — never a naive long-held `duckdb.connect`.
- **Frozen strategy package untouched.** Only `scripts/ops/*` (new) and `scripts/nifty_shield_paper/session.py` (ops composition-root code) may change. Do **not** edit anything under `strategies/nifty_shield_v1/` or the frozen handler package.
- **Recording stays ON.** The session is always spawned without `--no-record` (F-B1: a non-recorded session is excluded from the ≥20/≥30 count).
- **No over-engineering** (per repo `CLAUDE.md`): no abstractions for single callers; a crash with a clear traceback beats a swallowed exception in deterministic ops code.
- **TDD, frequent commits.** Commit after each task. Branch first (we are on `main`): `git checkout -b feat/ops-orchestrator`.
- Supervised session process: `scripts/nifty_shield_paper/session.py` (**not** `nifty_shield_paper_runner.py`). Spawn: `python scripts/nifty_shield_paper/session.py --date <today> --data-root data/nifty_shield`.

---

### Task 1: Windows-safe PID/lock helpers

**Files:**
- Create: `scripts/ops/__init__.py`
- Create: `scripts/ops/pidfile.py`
- Create: `tests/ops/__init__.py`
- Test: `tests/ops/test_pidfile.py`

**Interfaces:**
- Produces:
  - `pid_alive(pid: int) -> bool`
  - `read_pid(path: Path) -> Optional[int]`
  - `write_pid(path: Path, pid: Optional[int] = None) -> None`
  - `lock_alive(path: Path) -> bool`
  - `acquire_lock(path: Path) -> bool`
  - `release_lock(path: Path) -> None`

- [ ] **Step 1: Write the failing test**

`tests/ops/test_pidfile.py`:
```python
import os
from pathlib import Path

from scripts.ops import pidfile


def test_pid_alive_true_for_current_process():
    assert pidfile.pid_alive(os.getpid()) is True


def test_pid_alive_false_for_absent_pid():
    assert pidfile.pid_alive(2_000_000_000) is False
    assert pidfile.pid_alive(0) is False


def test_acquire_write_read_release_cycle(tmp_path):
    lock = tmp_path / "x.pid"
    assert pidfile.acquire_lock(lock) is True
    assert pidfile.read_pid(lock) == os.getpid()
    assert pidfile.lock_alive(lock) is True
    pidfile.release_lock(lock)
    assert lock.exists() is False


def test_acquire_refuses_when_live_pid_present(tmp_path):
    lock = tmp_path / "x.pid"
    pidfile.write_pid(lock, os.getpid())          # a "live" holder
    assert pidfile.acquire_lock(lock) is False


def test_acquire_overwrites_stale_pid(tmp_path):
    lock = tmp_path / "x.pid"
    pidfile.write_pid(lock, 2_000_000_000)        # dead pid
    assert pidfile.acquire_lock(lock) is True
    assert pidfile.read_pid(lock) == os.getpid()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ops/test_pidfile.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.ops.pidfile`.

- [ ] **Step 3: Write minimal implementation**

`scripts/ops/__init__.py`: empty file.
`tests/ops/__init__.py`: empty file.
`scripts/ops/pidfile.py`:
```python
"""Windows-safe PID/lock helpers for the ops supervisor.

Consolidates the `_pid_alive` pattern already used in `schedule_worker.py` and
`chain_poller.py`: NEVER `os.kill(pid, 0)` on Windows (CPython maps signals to
TerminateProcess). Uses OpenProcess on Windows.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        if hasattr(ctypes, "windll"):
            SYNCHRONIZE = 0x00100000
            handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def read_pid(path: Path) -> Optional[int]:
    try:
        return int(Path(path).read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def write_pid(path: Path, pid: Optional[int] = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid if pid is not None else os.getpid()), encoding="utf-8")


def lock_alive(path: Path) -> bool:
    pid = read_pid(path)
    return pid is not None and pid_alive(pid)


def acquire_lock(path: Path) -> bool:
    """Single-instance guard: refuse if a live PID holds the lock, else claim it."""
    if lock_alive(path):
        return False
    write_pid(path)
    return True


def release_lock(path: Path) -> None:
    path = Path(path)
    if read_pid(path) == os.getpid():
        try:
            path.unlink()
        except OSError:
            pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/ops/test_pidfile.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/ops/__init__.py scripts/ops/pidfile.py tests/ops/__init__.py tests/ops/test_pidfile.py
git commit -m "feat(ops): Windows-safe PID/lock helpers for the supervisor"
```

---

### Task 2: Cooperative clean stop for `session.py`

The orchestrator must stop the PAPER session so its `finally` finalizes the evidence
package. `driver.run()` returns on `driver.stop()`; `session.py:203-212` already
finalizes in `finally`. Add a signal handler that calls `driver.stop()`, so an
external `SIGTERM` (POSIX) / `SIGBREAK` (Windows `CTRL_BREAK_EVENT`) drains the loop
cleanly instead of killing it mid-finalize.

**Files:**
- Modify: `scripts/nifty_shield_paper/session.py` (`run_session`, around `session.py:172-212`)
- Test: `tests/nifty_shield_paper/test_session_stop.py`

**Interfaces:**
- Produces: `scripts.nifty_shield_paper.session._make_stop_handler(driver) -> Callable[[int, object], None]`

- [ ] **Step 1: Write the failing test**

`tests/nifty_shield_paper/test_session_stop.py`:
```python
from scripts.nifty_shield_paper import session


class _FakeDriver:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


def test_stop_handler_calls_driver_stop():
    drv = _FakeDriver()
    handler = session._make_stop_handler(drv)
    handler(15, None)          # signum, frame
    assert drv.stopped is True


def test_stop_handler_swallows_driver_stop_error():
    class _Boom:
        def stop(self):
            raise RuntimeError("already stopping")

    handler = session._make_stop_handler(_Boom())
    handler(15, None)          # must not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/nifty_shield_paper/test_session_stop.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute '_make_stop_handler'`.

- [ ] **Step 3: Write minimal implementation**

In `scripts/nifty_shield_paper/session.py`, add `import signal` to the imports, and add this helper above `run_session`:
```python
def _make_stop_handler(driver):
    """Return a signal handler that requests a clean driver stop (loop drains to
    STOPPED, the run_session `finally` finalizes the session package). Errors are
    swallowed so a second signal can never abort finalization."""
    def _handler(signum, frame):
        _logger.info("stop signal %s received; requesting clean driver stop", signum)
        try:
            driver.stop()
        except Exception as exc:  # noqa: BLE001 — shutdown must not raise
            _logger.warning("driver.stop() during shutdown raised: %s", exc)
    return _handler
```
Then, inside `run_session`, immediately after the `driver = build_nifty_shield_paper_driver(...)` call and before `driver.run()`, register it:
```python
    handler = _make_stop_handler(driver)
    signal.signal(signal.SIGTERM, handler)
    if hasattr(signal, "SIGBREAK"):           # Windows CTRL_BREAK_EVENT
        signal.signal(signal.SIGBREAK, handler)
```
Leave the existing `try/except KeyboardInterrupt/finally` intact — Ctrl+C in a foreground console still works; the new handlers add the external-supervisor path.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/nifty_shield_paper/test_session_stop.py -v`
Expected: PASS (2 tests).

Also confirm no regression in the existing session tests:
Run: `python -m pytest tests/nifty_shield_paper/ -q`
Expected: PASS (no new failures).

- [ ] **Step 5: Commit**

```bash
git add scripts/nifty_shield_paper/session.py tests/nifty_shield_paper/test_session_stop.py
git commit -m "feat(nifty-shield): cooperative clean stop for the PAPER session runner"
```

---

### Task 3: Preflight context + BLOCK checks

**Files:**
- Create: `scripts/ops/preflight.py`
- Test: `tests/ops/test_preflight.py`

**Interfaces:**
- Produces:
  - `CheckResult(name: str, tier: str, ok: bool, detail: str)` — frozen dataclass; `tier ∈ {"block","warn"}`
  - `PreflightContext` — frozen dataclass of resolved system state (fields below)
  - `check_token(ctx) -> CheckResult`
  - `check_stop_file(ctx) -> CheckResult`
  - `check_marks(ctx) -> CheckResult`
  - `check_vix(ctx) -> CheckResult`
  - Constants `MARKS_HEARTBEAT_MAX_S = 60`, `VIX_BAR_MAX_S = 300`
- Consumes (Task 1): `scripts.ops.pidfile`

`PreflightContext` fields (all resolved values, no IO in the checks):
```
now: datetime            market_open: bool        stop_file_present: bool
has_token: bool          token_expired: bool
marks_rows: int          marks_priceable: int     marks_heartbeat_age_s: Optional[float]
poller_alive: bool       ingestor_alive: bool     vix_last_bar_age_s: Optional[float]
span_present: bool       master_age_days: Optional[float]
feed_fresh: dict[str, bool]                        eod_worker_alive: bool
```

- [ ] **Step 1: Write the failing test**

`tests/ops/test_preflight.py`:
```python
from datetime import datetime

from scripts.ops import preflight as pf


def _ctx(**over):
    base = dict(
        now=datetime(2026, 8, 11, 9, 30), market_open=True, stop_file_present=False,
        has_token=True, token_expired=False,
        marks_rows=120, marks_priceable=118, marks_heartbeat_age_s=5.0,
        poller_alive=True, ingestor_alive=True, vix_last_bar_age_s=30.0,
        span_present=True, master_age_days=0.2,
        feed_fresh={"equity": True, "futures": True, "stock_options": True, "index": True},
        eod_worker_alive=True,
    )
    base.update(over)
    return pf.PreflightContext(**base)


def test_token_blocks_when_expired():
    assert pf.check_token(_ctx(token_expired=True)).ok is False


def test_token_blocks_when_absent():
    assert pf.check_token(_ctx(has_token=False)).ok is False


def test_stop_file_blocks():
    assert pf.check_stop_file(_ctx(stop_file_present=True)).ok is False


def test_marks_block_when_no_priceable_rows_during_market_hours():
    # rows>0 but every ltp==0 → reader yields {} → BLOCK
    assert pf.check_marks(_ctx(marks_rows=120, marks_priceable=0)).ok is False


def test_marks_block_when_heartbeat_stale_during_market_hours():
    assert pf.check_marks(_ctx(marks_heartbeat_age_s=600.0)).ok is False


def test_marks_preopen_only_requires_poller_alive():
    ctx = _ctx(market_open=False, marks_rows=0, marks_priceable=0,
               marks_heartbeat_age_s=None, poller_alive=True)
    assert pf.check_marks(ctx).ok is True


def test_vix_blocks_when_bar_stale_during_market_hours():
    assert pf.check_vix(_ctx(vix_last_bar_age_s=900.0)).ok is False


def test_vix_preopen_only_requires_ingestor_alive():
    ctx = _ctx(market_open=False, vix_last_bar_age_s=None, ingestor_alive=True)
    assert pf.check_vix(ctx).ok is True


def test_all_block_checks_pass_on_healthy_context():
    ctx = _ctx()
    for fn in (pf.check_token, pf.check_stop_file, pf.check_marks, pf.check_vix):
        assert fn(ctx).ok is True
        assert fn(ctx).tier == "block"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ops/test_preflight.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.ops.preflight`.

- [ ] **Step 3: Write minimal implementation**

`scripts/ops/preflight.py` (BLOCK checks + dataclasses only — WARN checks and `build_context`/`main` land in Task 4):
```python
"""NiftyShield ops preflight — read-only go/no-go over the trading-window stack.

Pure tiered checks over a resolved PreflightContext (all IO happens in
build_context, Task 4), so every check is unit-testable without processes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

MARKS_HEARTBEAT_MAX_S = 60.0
VIX_BAR_MAX_S = 300.0
MASTER_MAX_AGE_DAYS = 1.0


@dataclass(frozen=True)
class CheckResult:
    name: str
    tier: str      # "block" | "warn"
    ok: bool
    detail: str


@dataclass(frozen=True)
class PreflightContext:
    now: datetime
    market_open: bool
    stop_file_present: bool
    has_token: bool
    token_expired: bool
    marks_rows: int
    marks_priceable: int
    marks_heartbeat_age_s: Optional[float]
    poller_alive: bool
    ingestor_alive: bool
    vix_last_bar_age_s: Optional[float]
    span_present: bool
    master_age_days: Optional[float]
    feed_fresh: dict
    eod_worker_alive: bool


def check_token(ctx: PreflightContext) -> CheckResult:
    ok = ctx.has_token and not ctx.token_expired
    detail = ("token present and fresh" if ok
              else "Upstox token absent" if not ctx.has_token
              else "Upstox token expired — re-login via /ops/login/upstox")
    return CheckResult("upstox_token", "block", ok, detail)


def check_stop_file(ctx: PreflightContext) -> CheckResult:
    ok = not ctx.stop_file_present
    return CheckResult("stop_file", "block", ok,
                       "no STOP file" if ok else "STOP kill-switch file present")


def check_marks(ctx: PreflightContext) -> CheckResult:
    if not ctx.market_open:
        return CheckResult("marks_warm", "block", ctx.poller_alive,
                           "pre-open: poller alive" if ctx.poller_alive
                           else "pre-open: chain poller not running")
    fresh = (ctx.marks_heartbeat_age_s is not None
             and ctx.marks_heartbeat_age_s <= MARKS_HEARTBEAT_MAX_S)
    ok = ctx.marks_rows > 0 and ctx.marks_priceable > 0 and fresh
    detail = (f"{ctx.marks_priceable} priceable rows, "
              f"heartbeat {ctx.marks_heartbeat_age_s}s"
              if ok else
              f"marks not warm (rows={ctx.marks_rows} priceable="
              f"{ctx.marks_priceable} hb_age={ctx.marks_heartbeat_age_s}s)")
    return CheckResult("marks_warm", "block", ok, detail)


def check_vix(ctx: PreflightContext) -> CheckResult:
    if not ctx.market_open:
        return CheckResult("live_vix", "block", ctx.ingestor_alive,
                           "pre-open: ingestor alive" if ctx.ingestor_alive
                           else "pre-open: market ingestor not running")
    fresh = (ctx.vix_last_bar_age_s is not None
             and ctx.vix_last_bar_age_s <= VIX_BAR_MAX_S)
    ok = ctx.ingestor_alive and fresh
    detail = (f"VIX bar {ctx.vix_last_bar_age_s}s old" if ok
              else f"VIX not flowing (ingestor_alive={ctx.ingestor_alive} "
                   f"bar_age={ctx.vix_last_bar_age_s}s) — 13:00 fact would be skipped")
    return CheckResult("live_vix", "block", ok, detail)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/ops/test_preflight.py -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/ops/preflight.py tests/ops/test_preflight.py
git commit -m "feat(ops): preflight context + BLOCK checks (token, STOP, marks, VIX)"
```

---

### Task 4: Preflight WARN checks + `run_preflight` / `verdict` / `build_context` / `main`

**Files:**
- Modify: `scripts/ops/preflight.py`
- Test: `tests/ops/test_preflight.py` (append)

**Interfaces:**
- Produces:
  - `check_span(ctx) -> CheckResult`, `check_master(ctx) -> CheckResult`,
    `check_feeds(ctx) -> CheckResult`, `check_eod_worker(ctx) -> CheckResult` (all `tier="warn"`)
  - `run_preflight(ctx) -> list[CheckResult]` — the 8 checks in order
  - `verdict(results) -> str` — `"NO-GO"` iff any `tier=="block"` result is not ok, else `"GO"`
  - `build_context(now=None, root=None) -> PreflightContext` — resolves real system state
  - `main() -> int` — prints the table + verdict; returns 0 (GO) / 1 (NO-GO)
- Consumes: `core.database.utils.market_hours.MarketHours`, `core.auth.credentials.credentials`, `core.scheduler.eod_decision.probe_feeds`, `core.risk.span.span_freshness.expected_span_date`, `scripts.ops.pidfile`

- [ ] **Step 1: Write the failing test (append)**

Append to `tests/ops/test_preflight.py`:
```python
def test_warn_checks_flag_but_do_not_block():
    ctx = _ctx(span_present=False, master_age_days=5.0,
               feed_fresh={"equity": False, "futures": True,
                           "stock_options": True, "index": True},
               eod_worker_alive=False)
    results = pf.run_preflight(ctx)
    # Every WARN failure is present but the verdict is still GO (blocks all pass).
    warn_fail = [r for r in results if r.tier == "warn" and not r.ok]
    assert {r.name for r in warn_fail} == {"span", "instrument_master",
                                           "eod_feeds", "eod_worker"}
    assert pf.verdict(results) == "GO"


def test_verdict_no_go_on_any_block_failure():
    results = pf.run_preflight(_ctx(token_expired=True))
    assert pf.verdict(results) == "NO-GO"


def test_run_preflight_returns_all_eight_checks():
    assert len(pf.run_preflight(_ctx())) == 8
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ops/test_preflight.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'run_preflight'`.

- [ ] **Step 3: Write minimal implementation (append to `preflight.py`)**

Add the WARN checks, the runner/verdict, and the real resolver. Append:
```python
def check_span(ctx: PreflightContext) -> CheckResult:
    return CheckResult("span", "warn", ctx.span_present,
                       "SPAN snapshot present" if ctx.span_present
                       else "SPAN snapshot absent (PAPER tolerates — flat-rate margin)")


def check_master(ctx: PreflightContext) -> CheckResult:
    ok = ctx.master_age_days is not None and ctx.master_age_days <= MASTER_MAX_AGE_DAYS
    return CheckResult("instrument_master", "warn", ok,
                       f"master age {ctx.master_age_days}d" if ok
                       else f"instrument master stale/absent (age={ctx.master_age_days}d)")


def check_feeds(ctx: PreflightContext) -> CheckResult:
    stale = sorted(n for n, fresh in ctx.feed_fresh.items() if not fresh)
    ok = not stale
    return CheckResult("eod_feeds", "warn", ok,
                       "all EOD feeds fresh" if ok
                       else f"EOD feeds behind expected session: {', '.join(stale)}")


def check_eod_worker(ctx: PreflightContext) -> CheckResult:
    return CheckResult("eod_worker", "warn", ctx.eod_worker_alive,
                       "EOD worker alive" if ctx.eod_worker_alive
                       else "EOD worker not running (schedule_worker.py)")


def run_preflight(ctx: PreflightContext) -> list:
    return [
        check_token(ctx), check_stop_file(ctx), check_marks(ctx), check_vix(ctx),
        check_span(ctx), check_master(ctx), check_feeds(ctx), check_eod_worker(ctx),
    ]


def verdict(results) -> str:
    return "NO-GO" if any(r.tier == "block" and not r.ok for r in results) else "GO"
```

Then the real resolver + CLI (also appended). Import at top of file:
```python
import json
from pathlib import Path

from core.database.utils.market_hours import MarketHours
from scripts.ops import pidfile
```
And append:
```python
ROOT = Path(__file__).resolve().parents[2]
CHAIN_CACHE = ROOT / "data" / "options" / "chain_cache.duckdb"
POLLER_PID = ROOT / "data" / "options" / "chain_poller.pid"
POLLER_HB = ROOT / "data" / "options" / "chain_poller_heartbeat.json"
INGESTOR_STATUS = ROOT / "logs" / "market_ingestor_status.json"
LIVE_BUFFER = ROOT / "data" / "live_buffer" / "candles_today.duckdb"
MASTER_DB = ROOT / "data" / "instruments" / "nse_fo_instruments.duckdb"
SPAN_DIR = ROOT / "data" / "span"
EOD_LOCK = ROOT / "data" / "_eod_worker.lock"
VIX_SYMBOL = "NSE_INDEX|India VIX"


def _read_marks(path: Path, retries: int = 5, delay_s: float = 0.1):
    """Bounded-retry read of the latest snapshot's row + priceable-row counts.
    Read-only; retries transient sharing violations from the poller's os.replace."""
    import time
    import duckdb
    if not path.exists():
        return 0, 0
    for attempt in range(retries):
        try:
            con = duckdb.connect(str(path), read_only=True)
            try:
                names = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
                if "option_chain_snapshot" not in names:
                    return 0, 0
                row = con.execute(
                    "SELECT COUNT(*), COUNT(*) FILTER (WHERE ltp > 0) "
                    "FROM option_chain_snapshot WHERE snapshot_timestamp = "
                    "(SELECT MAX(snapshot_timestamp) FROM option_chain_snapshot)"
                ).fetchone()
                return int(row[0] or 0), int(row[1] or 0)
            finally:
                con.close()
        except Exception:
            if attempt == retries - 1:
                return 0, 0
            time.sleep(delay_s)
    return 0, 0


def _heartbeat_age_s(now: datetime) -> Optional[float]:
    try:
        payload = json.loads(POLLER_HB.read_text(encoding="utf-8"))
        ts = datetime.fromisoformat(payload["last_snapshot"])
        return (now - ts).total_seconds()
    except (OSError, ValueError, KeyError):
        return None


def _ingestor_alive(now: datetime) -> bool:
    try:
        payload = json.loads(INGESTOR_STATUS.read_text(encoding="utf-8"))
        pid = int(payload.get("pid", 0))
        if not pidfile.pid_alive(pid):
            return False
        hb = datetime.fromisoformat(payload["last_heartbeat"])
        return (now - hb).total_seconds() <= 120.0
    except (OSError, ValueError, KeyError):
        return False


def _vix_bar_age_s(now: datetime) -> Optional[float]:
    if not LIVE_BUFFER.exists():
        return None
    try:
        import duckdb
        con = duckdb.connect(str(LIVE_BUFFER), read_only=True)
        try:
            row = con.execute(
                "SELECT MAX(timestamp) FROM candles WHERE symbol = ?", [VIX_SYMBOL]
            ).fetchone()
        finally:
            con.close()
        if not row or row[0] is None:
            return None
        ts = row[0] if isinstance(row[0], datetime) else datetime.fromisoformat(str(row[0]))
        return (now - ts).total_seconds()
    except Exception:
        return None


def _span_present() -> bool:
    try:
        from core.risk.span.span_freshness import expected_span_date
        d = expected_span_date()
        return (SPAN_DIR / f"nse_fo_span_{d.isoformat()}.parquet").exists()
    except Exception:
        return False


def _master_age_days(now: datetime) -> Optional[float]:
    if not MASTER_DB.exists():
        return None
    return (now.timestamp() - MASTER_DB.stat().st_mtime) / 86400.0


def _prev_trading_session(today) -> "date":
    from datetime import timedelta
    d = today - timedelta(days=1)
    while not MarketHours.is_trading_day(datetime.combine(d, datetime.min.time())):
        d -= timedelta(days=1)
    return d


def _feed_fresh(expected) -> dict:
    from core.scheduler.eod_decision import probe_feeds
    feeds = probe_feeds()
    return {name: (d is not None and d >= expected) for name, d in feeds.items()}


def build_context(now: Optional[datetime] = None, root: Optional[Path] = None) -> PreflightContext:
    now = now or MarketHours.get_ist_now().replace(tzinfo=None)
    root = root or ROOT
    market_open = MarketHours.is_market_open()
    from core.auth.credentials import credentials
    credentials._load()
    rows, priceable = _read_marks(CHAIN_CACHE)
    expected_eod = _prev_trading_session(now.date())
    return PreflightContext(
        now=now,
        market_open=market_open,
        stop_file_present=(root / "STOP").exists(),
        has_token=credentials.has_upstox_token,
        token_expired=credentials.is_token_expired,
        marks_rows=rows,
        marks_priceable=priceable,
        marks_heartbeat_age_s=_heartbeat_age_s(now),
        poller_alive=pidfile.lock_alive(POLLER_PID),
        ingestor_alive=_ingestor_alive(now),
        vix_last_bar_age_s=_vix_bar_age_s(now),
        span_present=_span_present(),
        master_age_days=_master_age_days(now),
        feed_fresh=_feed_fresh(expected_eod),
        eod_worker_alive=pidfile.lock_alive(EOD_LOCK),
    )


def main() -> int:
    ctx = build_context()
    results = run_preflight(ctx)
    v = verdict(results)
    print(f"NiftyShield preflight @ {ctx.now:%Y-%m-%d %H:%M}  "
          f"(market_open={ctx.market_open})\n" + "-" * 60)
    for r in results:
        mark = "OK " if r.ok else ("!! " if r.tier == "block" else " ~ ")
        print(f"  [{mark}] {r.tier.upper():5} {r.name:18} {r.detail}")
    print("-" * 60 + f"\n  VERDICT: {v}")
    return 0 if v == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/ops/test_preflight.py -v`
Expected: PASS (12 tests total).

Then a live smoke (no assertions — just confirms `build_context` resolves without raising):
Run: `python scripts/ops/preflight.py`
Expected: prints the table + a `VERDICT:` line, exit code reflects it. (Today it will be NO-GO — poller/ingestor absent.)

- [ ] **Step 5: Commit**

```bash
git add scripts/ops/preflight.py tests/ops/test_preflight.py
git commit -m "feat(ops): preflight WARN checks, verdict, real resolver + CLI"
```

---

### Task 5: Orchestrator child registry — spawn / adopt / liveness

**Files:**
- Create: `scripts/ops/orchestrator.py`
- Test: `tests/ops/test_orchestrator.py`

**Interfaces:**
- Produces:
  - `ChildSpec(name, argv, pid_path=None, native_lock=None, new_group=False)` — frozen dataclass. Exactly one of `pid_path` (orchestrator-owned) / `native_lock` (child owns its own lock) is set.
  - `child_alive(spec) -> bool`
  - `spawn(spec, *, popen=subprocess.Popen) -> object` — starts the process (new group if `new_group`), writes `pid_path` for owned children, returns the process handle
  - `CHILDREN: dict[str, ChildSpec]` — the canonical registry (flask, ingestor, poller, session, eod)
- Consumes (Task 1): `scripts.ops.pidfile`

- [ ] **Step 1: Write the failing test**

`tests/ops/test_orchestrator.py`:
```python
import os
from pathlib import Path

from scripts.ops import orchestrator as orch
from scripts.ops import pidfile


class _FakePopen:
    def __init__(self, argv, **kw):
        self.argv = argv
        self.kw = kw
        self.pid = 4321
        self._alive = True

    def poll(self):
        return None if self._alive else 0


def test_spawn_owned_writes_pid_file(tmp_path):
    pidp = tmp_path / "flask.pid"
    spec = orch.ChildSpec(name="flask", argv=["python", "x"], pid_path=pidp)
    captured = {}

    def fake_popen(argv, **kw):
        captured["argv"], captured["kw"] = argv, kw
        return _FakePopen(argv, **kw)

    proc = orch.spawn(spec, popen=fake_popen)
    assert captured["argv"] == ["python", "x"]
    assert pidfile.read_pid(pidp) == proc.pid


def test_child_alive_owned_reads_pid_file(tmp_path):
    pidp = tmp_path / "flask.pid"
    spec = orch.ChildSpec(name="flask", argv=[], pid_path=pidp)
    assert orch.child_alive(spec) is False
    pidfile.write_pid(pidp, os.getpid())
    assert orch.child_alive(spec) is True


def test_child_alive_native_lock_reads_lock_file(tmp_path):
    lock = tmp_path / "chain_poller.pid"
    spec = orch.ChildSpec(name="poller", argv=[], native_lock=lock)
    pidfile.write_pid(lock, os.getpid())
    assert orch.child_alive(spec) is True


def test_session_child_spawns_in_new_group():
    spec = orch.CHILDREN["session"]
    assert spec.new_group is True
    assert "session.py" in " ".join(spec.argv)
    assert "--no-record" not in spec.argv        # recording must stay ON (F-B1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ops/test_orchestrator.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.ops.orchestrator`.

- [ ] **Step 3: Write minimal implementation**

`scripts/ops/orchestrator.py`:
```python
"""NiftyShield ops orchestrator — foreground supervisor for the PAPER window.

Manages Flask, market_ingestor, chain_poller, the PAPER session, and the EOD
worker; starts them in dependency order behind a preflight gate; restarts crashed
children; stops them cleanly. See the design spec for the full contract.
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from scripts.ops import pidfile

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
OPS_DIR = ROOT / "data" / "ops"

_CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows creationflag


@dataclass(frozen=True)
class ChildSpec:
    name: str
    argv: List[str]
    pid_path: Optional[Path] = None      # orchestrator-owned liveness
    native_lock: Optional[Path] = None   # child writes its own lock
    new_group: bool = False              # spawn in a new process group (session)


def child_alive(spec: ChildSpec) -> bool:
    lock = spec.native_lock or spec.pid_path
    return bool(lock) and pidfile.lock_alive(lock)


def spawn(spec: ChildSpec, *, popen: Callable = subprocess.Popen):
    creationflags = _CREATE_NEW_PROCESS_GROUP if (spec.new_group and os.name == "nt") else 0
    kwargs = {"cwd": str(ROOT), "creationflags": creationflags} if os.name == "nt" \
        else {"cwd": str(ROOT), "start_new_session": spec.new_group}
    proc = popen(spec.argv, **kwargs)
    if spec.pid_path is not None:
        pidfile.write_pid(spec.pid_path, proc.pid)
    return proc


CHILDREN = {
    "flask": ChildSpec(
        "flask", [PY, str(ROOT / "scripts" / "run_flask.py")],
        pid_path=OPS_DIR / "flask.pid"),
    "ingestor": ChildSpec(
        "ingestor", [PY, str(ROOT / "scripts" / "market_ingestor.py")],
        pid_path=OPS_DIR / "market_ingestor.pid"),
    "poller": ChildSpec(
        "poller", [PY, str(ROOT / "scripts" / "nifty_shield_paper" / "chain_poller.py")],
        native_lock=ROOT / "data" / "options" / "chain_poller.pid"),
    "session": ChildSpec(
        "session",
        [PY, str(ROOT / "scripts" / "nifty_shield_paper" / "session.py"),
         "--data-root", str(ROOT / "data" / "nifty_shield")],
        pid_path=OPS_DIR / "session.pid", new_group=True),
    "eod": ChildSpec(
        "eod", [PY, str(ROOT / "scripts" / "schedule_worker.py")],
        native_lock=ROOT / "data" / "_eod_worker.lock"),
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/ops/test_orchestrator.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/ops/orchestrator.py tests/ops/test_orchestrator.py
git commit -m "feat(ops): orchestrator child registry (spawn/adopt/liveness)"
```

---

### Task 6: Orchestrator start state machine

The ordered bring-up: orchestrator lock → STOP guard → Flask → token gate (block-poll)
→ ingestor+poller → warm-up park → background catch-up → preflight final gate → session
→ ensure EOD. Injected seams (`Deps`) make it testable with no processes/network/clock.

**Files:**
- Modify: `scripts/ops/orchestrator.py`
- Test: `tests/ops/test_orchestrator.py` (append)

**Interfaces:**
- Produces:
  - `Deps` dataclass: `spawn`, `child_alive`, `token_fresh: Callable[[], bool]`, `open_login: Callable[[], None]`, `preflight: Callable[[], str]` (returns "GO"/"NO-GO"), `marks_warm: Callable[[], bool]`, `dispatch_catchup: Callable[[], None]`, `sleep: Callable[[float], None]`, `now: Callable[[], datetime]`
  - `start_sequence(deps, *, token_timeout_s=600.0, warmup_timeout_s=120.0) -> str` — returns `"started"` / `"blocked:<reason>"` / `"timeout:<stage>"`; spawns children in order via `deps.spawn`
- Consumes: `CHILDREN`, `child_alive`, `spawn` (Task 5)

- [ ] **Step 1: Write the failing test (append)**

Append to `tests/ops/test_orchestrator.py`:
```python
from datetime import datetime

from scripts.ops import orchestrator as orch


def _deps(**over):
    calls = {"spawned": [], "catchup": 0, "login": 0}

    def spawn(spec, **kw):
        calls["spawned"].append(spec.name)
        return _FakePopen(spec.argv)

    base = dict(
        spawn=spawn,
        child_alive=lambda spec: spec.name == "eod",   # eod already up (adopt)
        token_fresh=lambda: True,
        open_login=lambda: calls.__setitem__("login", calls["login"] + 1),
        preflight=lambda: "GO",
        marks_warm=lambda: True,
        dispatch_catchup=lambda: calls.__setitem__("catchup", calls["catchup"] + 1),
        sleep=lambda s: None,
        now=lambda: datetime(2026, 8, 11, 9, 30),
    )
    base.update(over)
    d = orch.Deps(**base)
    return d, calls


def test_happy_path_starts_in_dependency_order():
    deps, calls = _deps()
    assert orch.start_sequence(deps) == "started"
    # flask before ingestor/poller before session; eod adopted, not re-spawned.
    order = calls["spawned"]
    assert order.index("flask") < order.index("ingestor") < order.index("session")
    assert "poller" in order and order.index("poller") < order.index("session")
    assert "eod" not in order                     # already alive → adopted
    assert calls["catchup"] == 1                  # background catch-up dispatched


def test_blocks_when_preflight_no_go():
    deps, calls = _deps(preflight=lambda: "NO-GO")
    assert orch.start_sequence(deps).startswith("blocked:")
    assert "session" not in calls["spawned"]      # never start the session on NO-GO


def test_token_gate_opens_login_then_waits():
    seq = iter([False, False, True])              # fresh on 3rd poll
    deps, calls = _deps(token_fresh=lambda: next(seq))
    assert orch.start_sequence(deps) == "started"
    assert calls["login"] == 1                    # login opened exactly once


def test_warmup_timeout_when_marks_never_warm():
    deps, calls = _deps(marks_warm=lambda: False)
    assert orch.start_sequence(deps, warmup_timeout_s=0.0).startswith("timeout:")
    assert "session" not in calls["spawned"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ops/test_orchestrator.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'Deps'`.

- [ ] **Step 3: Write minimal implementation (append to `orchestrator.py`)**

Add imports at top: `import webbrowser`, `from datetime import datetime`, and:
```python
@dataclass
class Deps:
    spawn: Callable
    child_alive: Callable
    token_fresh: Callable[[], bool]
    open_login: Callable[[], None]
    preflight: Callable[[], str]
    marks_warm: Callable[[], bool]
    dispatch_catchup: Callable[[], None]
    sleep: Callable[[float], None]
    now: Callable[[], datetime]


def _ensure(deps: Deps, name: str) -> None:
    """Adopt a living child; else spawn it."""
    spec = CHILDREN[name]
    if not deps.child_alive(spec):
        deps.spawn(spec)


def start_sequence(deps: Deps, *, token_timeout_s: float = 600.0,
                   warmup_timeout_s: float = 120.0, poll_s: float = 2.0) -> str:
    # 2. Flask (needed for the OAuth handshake).
    _ensure(deps, "flask")

    # 3. Token gate — open the login page once, then block-poll until fresh.
    if not deps.token_fresh():
        deps.open_login()
        waited = 0.0
        while not deps.token_fresh():
            if waited >= token_timeout_s:
                return "timeout:token"
            deps.sleep(poll_s)
            waited += poll_s

    # 4. Live feed + marks.
    _ensure(deps, "ingestor")
    _ensure(deps, "poller")

    # 5. Warm-up park — wait for marks to flow before the runner constructs.
    waited = 0.0
    while not deps.marks_warm():
        if waited >= warmup_timeout_s:
            return "timeout:warmup"
        deps.sleep(poll_s)
        waited += poll_s

    # 6. Background catch-up (non-blocking; never gates the session).
    deps.dispatch_catchup()

    # 7. Final preflight gate.
    if deps.preflight() != "GO":
        return "blocked:preflight"

    # 8. Start the session (recording ON via CHILDREN["session"]).
    _ensure(deps, "session")

    # 9. Ensure the EOD worker.
    _ensure(deps, "eod")
    return "started"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/ops/test_orchestrator.py -v`
Expected: PASS (8 tests total).

- [ ] **Step 5: Commit**

```bash
git add scripts/ops/orchestrator.py tests/ops/test_orchestrator.py
git commit -m "feat(ops): orchestrator start state machine (token gate, warmup park, gated session start)"
```

---

### Task 7: Supervise loop, cooperative stop, and CLI (`start`/`status`/`stop`/`--dry-run`)

**Files:**
- Modify: `scripts/ops/orchestrator.py`
- Test: `tests/ops/test_orchestrator.py` (append)

**Interfaces:**
- Produces:
  - `stop_child(spec, proc, *, killer=os.kill, term=None) -> None` — session gets `CTRL_BREAK_EVENT` (Windows) / `SIGTERM` (POSIX) to its group + bounded wait; others get `terminate()`
  - `Supervisor` class: holds started `{name: proc}`, `.tick()` restarts crashed owned children (backoff), `.shutdown()` stops all it started (session first, cleanly), leaving adopted children
  - `main(argv=None) -> int` — subcommands `start` (default), `status`, `stop`, plus `--dry-run`
- Consumes: `CHILDREN`, `spawn`, `child_alive`, `start_sequence`, `scripts.ops.preflight`

- [ ] **Step 1: Write the failing test (append)**

Append to `tests/ops/test_orchestrator.py`:
```python
import signal

from scripts.ops import orchestrator as orch


def test_stop_child_session_signals_group_and_waits():
    spec = orch.CHILDREN["session"]
    proc = _FakePopen(spec.argv)
    proc.pid = 777
    sent = {}

    def killer(pid, sig):
        sent["pid"], sent["sig"] = pid, sig
        proc._alive = False

    waited = {"n": 0}
    proc.wait = lambda timeout=None: waited.__setitem__("n", waited["n"] + 1)
    orch.stop_child(spec, proc, killer=killer)
    assert sent["pid"] == 777
    # Windows → CTRL_BREAK, POSIX → SIGTERM; both are cooperative, never kill.
    expected = signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGTERM
    assert sent["sig"] == expected
    assert waited["n"] >= 1


def test_supervisor_restarts_crashed_owned_child():
    started = {"ingestor": _FakePopen([])}
    started["ingestor"]._alive = False            # crashed
    respawns = []
    sup = orch.Supervisor(
        started=started,
        spawn=lambda spec: respawns.append(spec.name) or _FakePopen([]),
        child_alive=lambda spec: False,           # pid file also dead
    )
    sup.tick()
    assert "ingestor" in respawns


def test_supervisor_shutdown_leaves_adopted_children():
    # only started children are torn down; eod (adopted, not in `started`) is left.
    stops = []
    sup = orch.Supervisor(
        started={"session": _FakePopen([])},
        spawn=lambda spec: _FakePopen([]),
        child_alive=lambda spec: True,
        stopper=lambda spec, proc: stops.append(spec.name),
    )
    sup.shutdown()
    assert stops == ["session"]                   # session only; eod untouched
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ops/test_orchestrator.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'stop_child'`.

- [ ] **Step 3: Write minimal implementation (append to `orchestrator.py`)**

Add imports: `import argparse`, `import signal`, `import time`, `import logging`. Append:
```python
_logger = logging.getLogger("ops_orchestrator")
ORCH_LOCK = OPS_DIR / "orchestrator.pid"
SESSION_FINALIZE_BUDGET_S = 90.0


def stop_child(spec: ChildSpec, proc, *, killer=os.kill, term_wait_s: float = SESSION_FINALIZE_BUDGET_S) -> None:
    """Stop one child. The session gets a cooperative group signal + bounded wait
    (its SIGBREAK/SIGTERM handler calls driver.stop() → clean finalize); other
    children get a normal terminate()."""
    if spec.new_group:
        sig = signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGTERM
        try:
            killer(proc.pid, sig)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("signalling %s failed: %s", spec.name, exc)
        try:
            proc.wait(timeout=term_wait_s)
        except Exception:
            _logger.error("%s did not exit within %ss — escalating to kill",
                          spec.name, term_wait_s)
            try:
                proc.kill()
            except Exception:
                pass
    else:
        try:
            proc.terminate()
        except Exception as exc:  # noqa: BLE001
            _logger.warning("terminating %s failed: %s", spec.name, exc)
    if spec.pid_path is not None:
        pidfile.release_lock(spec.pid_path)


class Supervisor:
    def __init__(self, *, started: dict, spawn=spawn, child_alive=child_alive,
                 stopper=stop_child, backoff_cap_s: float = 30.0):
        self._started = started
        self._spawn = spawn
        self._child_alive = child_alive
        self._stopper = stopper
        self._backoff_cap = backoff_cap_s
        self._fails: dict = {}

    def tick(self) -> None:
        for name, proc in list(self._started.items()):
            spec = CHILDREN[name]
            proc_dead = proc is not None and proc.poll() is not None
            if proc_dead and not self._child_alive(spec):
                self._fails[name] = self._fails.get(name, 0) + 1
                _logger.error("child %s died — restart #%d", name, self._fails[name])
                self._started[name] = self._spawn(spec)

    def shutdown(self) -> None:
        # Session first (longest finalize), then the rest — only what we started.
        for name in sorted(self._started, key=lambda n: 0 if n == "session" else 1):
            self._stopper(CHILDREN[name], self._started[name])


def _dispatch_catchup() -> None:
    """Fire download_all_data as a detached background one-shot; never blocks."""
    argv = [PY, str(ROOT / "scripts" / "download_all_data.py")]
    flags = _CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    kw = {"cwd": str(ROOT)}
    if os.name == "nt":
        kw["creationflags"] = flags
    else:
        kw["start_new_session"] = True
    try:
        subprocess.Popen(argv, **kw)
        _logger.info("background catch-up download dispatched")
    except Exception as exc:  # noqa: BLE001
        _logger.warning("catch-up dispatch failed (non-blocking): %s", exc)


def _live_deps(started: dict) -> Deps:
    from scripts.ops import preflight
    from core.auth.credentials import credentials

    def _spawn(spec):
        proc = spawn(spec)
        started[spec.name] = proc
        return proc

    def _token_fresh() -> bool:
        credentials._load()
        return credentials.has_upstox_token and not credentials.is_token_expired

    def _open_login():
        url = "http://127.0.0.1:5000/ops/login/upstox"
        print(f"\n>>> Upstox token required. Opening {url}\n"
              f">>> Complete the browser login; the orchestrator will continue "
              f"automatically.\n")
        try:
            webbrowser.open(url)
        except Exception:
            pass

    def _marks_warm() -> bool:
        ctx = preflight.build_context()
        return preflight.check_marks(ctx).ok

    return Deps(
        spawn=_spawn, child_alive=child_alive, token_fresh=_token_fresh,
        open_login=_open_login,
        preflight=lambda: preflight.verdict(preflight.run_preflight(preflight.build_context())),
        marks_warm=_marks_warm, dispatch_catchup=_dispatch_catchup,
        sleep=time.sleep, now=datetime.now,
    )


def _cmd_start(dry_run: bool) -> int:
    if dry_run:
        print("DRY-RUN start plan (dependency order):")
        for name in ["flask", "ingestor", "poller", "session", "eod"]:
            spec = CHILDREN[name]
            print(f"  {name:9} -> {' '.join(spec.argv)}"
                  + (" [new group]" if spec.new_group else ""))
        return 0
    if not pidfile.acquire_lock(ORCH_LOCK):
        print(f"another orchestrator is running (see {ORCH_LOCK})")
        return 1
    started: dict = {}
    sup = Supervisor(started=started)
    try:
        outcome = start_sequence(_live_deps(started))
        print(f"start sequence: {outcome}")
        if outcome != "started":
            sup.shutdown()
            return 1
        _logger.info("supervising — Ctrl+C to stop")
        while True:
            sup.tick()
            time.sleep(5.0)
    except KeyboardInterrupt:
        print("\nshutting down...")
        sup.shutdown()
        return 0
    finally:
        pidfile.release_lock(ORCH_LOCK)


def _cmd_status() -> int:
    from scripts.ops import preflight
    print("children:")
    for name, spec in CHILDREN.items():
        print(f"  {name:9} alive={child_alive(spec)}")
    ctx = preflight.build_context()
    results = preflight.run_preflight(ctx)
    print(f"preflight verdict: {preflight.verdict(results)}")
    return 0


def _cmd_stop() -> int:
    stopped = 0
    for name in sorted(CHILDREN, key=lambda n: 0 if n == "session" else 1):
        spec = CHILDREN[name]
        if spec.pid_path is None:          # never stop natively-locked adopted daemons
            continue
        pid = pidfile.read_pid(spec.pid_path)
        if pid and pidfile.pid_alive(pid):
            stop_child(spec, _RemoteProc(pid))
            stopped += 1
    print(f"stopped {stopped} orchestrator-owned child(ren)")
    return 0


class _RemoteProc:
    """Minimal proc handle for `stop` from a second console (pid only)."""
    def __init__(self, pid: int):
        self.pid = pid

    def poll(self):
        return None if pidfile.pid_alive(self.pid) else 0

    def wait(self, timeout=None):
        end = time.time() + (timeout or 0)
        while pidfile.pid_alive(self.pid) and time.time() < end:
            time.sleep(0.2)

    def kill(self):
        if os.name == "nt":
            os.system(f"taskkill /F /PID {self.pid} >nul 2>&1")
        else:
            try:
                os.kill(self.pid, signal.SIGKILL)
            except OSError:
                pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="NiftyShield ops orchestrator")
    parser.add_argument("command", nargs="?", default="start",
                        choices=["start", "status", "stop"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    if args.command == "start":
        return _cmd_start(args.dry_run)
    if args.command == "status":
        return _cmd_status()
    return _cmd_stop()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/ops/test_orchestrator.py -v`
Expected: PASS (11 tests total).

Then a dry-run smoke (spawns nothing):
Run: `python scripts/ops/orchestrator.py start --dry-run`
Expected: prints the 5-line dependency-ordered start plan; exit 0.

Run: `python scripts/ops/orchestrator.py status`
Expected: per-child `alive=` lines + a preflight verdict; exit 0.

- [ ] **Step 5: Commit**

```bash
git add scripts/ops/orchestrator.py tests/ops/test_orchestrator.py
git commit -m "feat(ops): supervise loop, cooperative stop, and start/status/stop CLI"
```

---

### Task 8: Runbook + CLAUDE.md ops section

**Files:**
- Create: `docs/reports/OPS_ORCHESTRATOR_RUNBOOK.md`
- Modify: `CLAUDE.md` (add a short "Ops — trading-window orchestrator" section near "Key Directories")

**Interfaces:** none (documentation).

- [ ] **Step 1: Write the runbook**

`docs/reports/OPS_ORCHESTRATOR_RUNBOOK.md`:
```markdown
# Ops Orchestrator — Runbook

## One-command morning start
    python scripts/ops/orchestrator.py

Brings up (in order) Flask → [browser: Upstox login] → market_ingestor →
chain_poller → PAPER session, ensures the EOD worker, then supervises. Ctrl+C
stops everything it started (the session stops cleanly and finalizes its evidence
package); an already-running EOD worker is left alone.

## Check health without starting anything
    python scripts/ops/preflight.py           # go/no-go, exit 0=GO 1=NO-GO
    python scripts/ops/orchestrator.py status  # per-child liveness + verdict
    python scripts/ops/orchestrator.py start --dry-run   # print the start plan

## Stop from another console
    python scripts/ops/orchestrator.py stop

## Preflight tiers
- BLOCK: Upstox token, STOP file, marks warm (rows>0 + ≥1 ltp>0 + fresh heartbeat),
  live VIX flowing. Pre-open, marks/VIX degrade to "poller/ingestor alive".
- WARN:  SPAN snapshot, instrument-master age, EOD feed freshness, EOD worker alive.

## Notes
- OAuth is interactive; the orchestrator opens the login page and blocks until a
  fresh token lands. It cannot be automated.
- The session is always recorded (never `--no-record`) — F-B1 counts recorded sessions.
- Stale EOD feeds trigger a background `download_all_data` catch-up that never delays
  the live session (the session reads only the live surface).
```

- [ ] **Step 2: Add the CLAUDE.md section**

Insert after the "Key Directories" table in `CLAUDE.md`:
```markdown
## Ops — Trading-Window Orchestrator

One-command foreground supervisor for the NiftyShield PAPER window:
`python scripts/ops/orchestrator.py` (Flask → Upstox login → ingestor → poller →
session → EOD; Ctrl+C stops cleanly). Read-only health: `python scripts/ops/preflight.py`
(BLOCK: token/STOP/marks/VIX; WARN: SPAN/master/feeds/EOD-worker). Full contract:
`docs/superpowers/specs/2026-08-09-ops-orchestrator-preflight-design.md`;
runbook: `docs/reports/OPS_ORCHESTRATOR_RUNBOOK.md`.
```

- [ ] **Step 3: Run the full ops test suite**

Run: `python -m pytest tests/ops/ tests/nifty_shield_paper/test_session_stop.py -q`
Expected: PASS (all green).

- [ ] **Step 4: Commit**

```bash
git add docs/reports/OPS_ORCHESTRATOR_RUNBOOK.md CLAUDE.md
git commit -m "docs(ops): orchestrator runbook + CLAUDE.md ops section"
```

---

## Self-Review

**Spec coverage:**
- §3.1 managed children + session identity → Tasks 5, 8; recording-ON asserted in Task 5 test.
- §4 preflight tiers (BLOCK/WARN, market-hours gating, ltp>0, heartbeat-vs-PID pre-open) → Tasks 3–4.
- §5.1 start state machine (token block-poll, warm-up park, background catch-up, final gate) → Task 6.
- §5.2 supervise loop + cooperative SIGBREAK/SIGTERM stop + new process group → Tasks 2, 7.
- §5.3 status/stop via PID files → Task 7.
- §6 edge cases (adopt-not-respawn, no-double-spawn, session-not-hard-killed) → Tasks 5–7.
- §7 testing (process-free) → every task's tests use fakes/injected seams.

**Placeholder scan:** none — every step carries runnable code and exact commands.

**Type consistency:** `ChildSpec`/`Deps`/`Supervisor`/`stop_child`/`start_sequence`/
`build_context`/`run_preflight`/`verdict`/`CheckResult` names are identical across the
tasks that define and consume them; `spawn(spec, popen=...)` and `stop_child(spec, proc, killer=...)`
signatures match their test call sites.

**Known integration caveat for the executor:** Tasks' unit tests are process-free.
The live paths (`build_context` IO, real `subprocess.Popen` spawning, actual
`CTRL_BREAK_EVENT` delivery to `session.py`) are exercised by the Task 4/7 smoke
commands, not by asserted tests — verify them manually on a real trading morning
before trusting the one-command start.
