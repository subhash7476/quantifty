# Options-Wall Step Health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every swallowed failure in the options-wall poller visible within one cycle — in the log, on the dashboard, and (for real faults) on Telegram.

**Architecture:** A pure classification/accumulation module (`health.py`) decides transient vs structural and tracks consecutive failures per `(underlying, step)`. The poller replaces six identical `logger.warning` blocks with one `_record_step` call that logs at the right level, alerts edge-triggered, and folds the state into the heartbeat file it already writes atomically each cycle. Flask reads that file — never the results DB — and the page renders a health strip plus a banner over the farm gate.

**Tech Stack:** Python 3.10+, DuckDB 1.4.3, Flask, pytest. No new dependencies.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-07-options-wall-step-health-design.md` (APPROVED).
- The per-step `try/except` structure in `poller.py` **stays**. One underlying or step failing must never stop the others.
- No retries are added anywhere. No change to executor logic.
- Health state must **never** be stored in `wall_scan_results.duckdb` — that store is the thing whose failure is being reported.
- Health reporting must never raise out of the poller. A failure inside `_record_step` or the notifier is logged and swallowed.
- Structural is the **default** classification. Only the explicitly listed exceptions are transient.
- Alerting is **edge-triggered**: a fault that persists for 101 cycles produces exactly one alert, re-armed only by a success.
- `ALERT_AT["close_request"] = 1` — operator decision, alerts on first failure of either kind. Default for all other steps is 10.
- Repo conventions: no docstrings/comments on code you did not change; no back-compat shims; delete rather than deprecate.
- Actual heartbeat file: `data/options/wall_poller_heartbeat.json` (written by `WallPoller._write_heartbeat`, `poller.py:122`). Its existing keys are `last_snapshot` and `rows` — **extend, do not rename**.
- **Task 0 is a prerequisite, not optional.** `core/logging/logger.py:80` hardcodes `Path("logs")`, and `poller.py:42` calls `setup_logger("options_wall_poller")` at import time — so any test importing the poller writes into the live operational log. Verified on 2026-09-07: a test-suite run injected 57 `<lambda>() takes 5 positional arguments` warnings into `logs/options_wall_poller.log`, which were then mistaken for production faults during the outage diagnosis. Once Task 3 emits `ERROR` and sends Telegram, an un-isolated test run would inject fake ERRORs **and fire real alerts**.
- No test may reach the real `TelegramNotifier`. Every test touching `_record_step` monkeypatches it.
- Blueprint prefix is `/options/wall` (the spec's `/options-wall/api/health` was shorthand). The real route is **`/options/wall/api/health`**.

---

### Task 0: Isolate test logging from the operational log

**Files:**
- Modify: `core/logging/logger.py:80`
- Create: `tests/conftest.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `setup_logger` honours `NIFTY_LOG_DIR`; every pytest run writes logs to a temp directory instead of `logs/`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_log_isolation.py`:

```python
"""A test run must never write into the operational log directory."""
import os
from pathlib import Path


def test_tests_do_not_log_into_the_repo_logs_dir():
    assert os.environ.get("NIFTY_LOG_DIR"), "conftest must redirect logs during tests"
    assert Path(os.environ["NIFTY_LOG_DIR"]).resolve() != (Path.cwd() / "logs").resolve()


def test_setup_logger_writes_under_the_override(tmp_path, monkeypatch):
    monkeypatch.setenv("NIFTY_LOG_DIR", str(tmp_path))
    from core.logging.logger import setup_logger
    logger = setup_logger("isolation_probe")
    logger.warning("probe")
    for handler in logger.handlers:
        handler.flush()
    assert (tmp_path / "isolation_probe.log").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_log_isolation.py -q`
Expected: FAIL — first test fails on the missing `NIFTY_LOG_DIR`; second fails because the file lands in `logs/`

- [ ] **Step 3: Write minimal implementation**

In `core/logging/logger.py`, change line 80 from `logs_dir = Path("logs")` to:

```python
    logs_dir = Path(os.environ.get("NIFTY_LOG_DIR", "logs"))
```

Add `import os` to that module's imports if it is not already present.

Create `tests/conftest.py`:

```python
"""Redirect logging away from `logs/` for the whole test session.

`setup_logger` runs at module import time, so this must take effect before any
test module imports a production module. conftest.py top-level code runs during
collection, which is early enough; an autouse fixture is not.
"""

import os
import tempfile
from pathlib import Path

_TEST_LOGS = Path(tempfile.gettempdir()) / "nifty-test-logs"
_TEST_LOGS.mkdir(parents=True, exist_ok=True)
os.environ["NIFTY_LOG_DIR"] = str(_TEST_LOGS)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_log_isolation.py -q`
Expected: PASS, 2 passed

Then confirm the whole suite no longer touches the operational log:

```bash
cp logs/options_wall_poller.log /tmp/before.log
python -m pytest tests/options_wall/ tests/data/test_options_wall_poller.py -q
diff -q /tmp/before.log logs/options_wall_poller.log
```

Expected: `diff` reports no difference.

- [ ] **Step 5: Commit**

```bash
git add core/logging/logger.py tests/conftest.py tests/test_log_isolation.py
git commit -m "fix(logging): keep test runs out of the operational log directory"
```

---

### Task 1: Classification module

**Files:**
- Create: `core/options_wall/health.py`
- Test: `tests/options_wall/test_health.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `classify(exc: BaseException) -> str` returning `"transient"` or `"structural"`; constants `TRANSIENT`, `STRUCTURAL`, `DEFAULT_ALERT_AT = 10`, `ALERT_AT = {"close_request": 1}`, `WALL_HEARTBEAT_PATH: Path`.

- [ ] **Step 1: Write the failing test**

Create `tests/options_wall/test_health.py`:

```python
"""Transient vs structural: only a known-recoverable fault may be transient."""
import duckdb
import pytest
import requests

from core.options_wall.health import STRUCTURAL, TRANSIENT, classify


def _lock_error():
    return duckdb.IOException(
        'IO Error: Cannot open file "wall_scan_results.duckdb": '
        "The process cannot access the file because it is being used by another process."
    )


@pytest.mark.parametrize("exc, expected", [
    (_lock_error(), TRANSIENT),
    (duckdb.ConnectionException("different configuration than existing connections"), TRANSIENT),
    (requests.ConnectionError("upstox unreachable"), TRANSIENT),
    (duckdb.ConstraintException('Duplicate key "trade_id: 1" violates primary key constraint'), STRUCTURAL),
    (duckdb.CatalogException("Table with name trades does not exist!"), STRUCTURAL),
    (ZeroDivisionError("float division by zero"), STRUCTURAL),
    (TypeError("<lambda>() takes 5 positional arguments but 6 were given"), STRUCTURAL),
    (KeyError("max_loss"), STRUCTURAL),
])
def test_classify(exc, expected):
    assert classify(exc) == expected


def test_unknown_exception_is_structural():
    class Weird(Exception):
        pass
    assert classify(Weird("never seen before")) == STRUCTURAL


def test_io_error_that_is_not_the_lock_is_structural():
    assert classify(duckdb.IOException("IO Error: disk full")) == STRUCTURAL
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/options_wall/test_health.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.options_wall.health'`

- [ ] **Step 3: Write minimal implementation**

Create `core/options_wall/health.py`:

```python
"""Step-level health for the options-wall poller.

The poller runs six independent steps per cycle and swallows each one's
exceptions so a single failure cannot stop the others. This module decides
whether a swallowed exception is routine — a lock the next cycle clears — or a
defect that will never clear on its own, and tracks consecutive failures so
alerting is edge-triggered rather than fired every cycle.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import requests

ROOT = Path(__file__).resolve().parents[2]
WALL_HEARTBEAT_PATH = ROOT / "data" / "options" / "wall_poller_heartbeat.json"

TRANSIENT = "transient"
STRUCTURAL = "structural"

DEFAULT_ALERT_AT = 10
ALERT_AT = {"close_request": 1}

_LOCK_MARKER = "used by another process"


def classify(exc: BaseException) -> str:
    if isinstance(exc, duckdb.ConnectionException):
        return TRANSIENT
    if isinstance(exc, duckdb.IOException) and _LOCK_MARKER in str(exc):
        return TRANSIENT
    if isinstance(exc, requests.RequestException):
        return TRANSIENT
    return STRUCTURAL
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/options_wall/test_health.py -q`
Expected: PASS, 10 passed

- [ ] **Step 5: Commit**

```bash
git add core/options_wall/health.py tests/options_wall/test_health.py
git commit -m "feat(options-wall): classify poller step failures as transient or structural"
```

---

### Task 2: Failure accumulator and alert verdict

**Files:**
- Modify: `core/options_wall/health.py`
- Test: `tests/options_wall/test_health.py`

**Interfaces:**
- Consumes: `classify`, `ALERT_AT`, `DEFAULT_ALERT_AT`, `TRANSIENT`, `STRUCTURAL` from Task 1.
- Produces: `Verdict(ok: bool, kind: str | None, level: str, alert: bool, record: dict)` and `StepHealth` with `record(step, underlying, exc=None, now=None) -> Verdict`, `snapshot() -> dict[str, dict[str, dict]]`, `any_failing() -> bool`.

- [ ] **Step 1: Write the failing test**

Append to `tests/options_wall/test_health.py`:

```python
from datetime import datetime

from core.options_wall.health import StepHealth


def _at(minute):
    return datetime(2026, 9, 7, 10, minute, 0)


def test_structural_alerts_once_and_only_once():
    h = StepHealth()
    exc = duckdb.ConstraintException("Duplicate key")
    verdicts = [h.record("executor", "NIFTY", exc, now=_at(i % 60)) for i in range(101)]
    assert sum(1 for v in verdicts if v.alert) == 1
    assert verdicts[0].alert is True
    assert verdicts[0].level == "error"
    assert verdicts[-1].record["consecutive"] == 101


def test_success_clears_and_rearms():
    h = StepHealth()
    exc = duckdb.ConstraintException("Duplicate key")
    assert h.record("executor", "NIFTY", exc, now=_at(0)).alert is True
    assert h.record("executor", "NIFTY", exc, now=_at(1)).alert is False
    assert h.record("executor", "NIFTY", None, now=_at(2)).ok is True
    assert h.record("executor", "NIFTY", exc, now=_at(3)).alert is True


def test_since_pins_to_the_first_failure():
    h = StepHealth()
    exc = duckdb.ConstraintException("Duplicate key")
    h.record("executor", "NIFTY", exc, now=_at(10))
    v = h.record("executor", "NIFTY", exc, now=_at(30))
    assert v.record["since"] == "2026-09-07T10:10:00"


def test_transient_waits_for_the_tenth_cycle():
    h = StepHealth()
    exc = duckdb.ConnectionException("lock")
    verdicts = [h.record("scan_persist", "NIFTY", exc, now=_at(i)) for i in range(12)]
    assert [i for i, v in enumerate(verdicts) if v.alert] == [9]
    assert verdicts[0].level == "warning"


def test_close_request_alerts_on_the_first_transient_failure():
    h = StepHealth()
    v = h.record("close_request", "NIFTY", duckdb.ConnectionException("lock"), now=_at(0))
    assert v.alert is True
    assert v.kind == "transient"


def test_steps_and_underlyings_are_tracked_independently():
    h = StepHealth()
    h.record("executor", "NIFTY", duckdb.ConstraintException("x"), now=_at(0))
    h.record("executor", "SENSEX", None, now=_at(0))
    snap = h.snapshot()
    assert snap["NIFTY"]["executor"]["ok"] is False
    assert snap["SENSEX"]["executor"]["ok"] is True
    assert h.any_failing() is True


def test_any_failing_false_when_everything_succeeded():
    h = StepHealth()
    h.record("executor", "NIFTY", None, now=_at(0))
    assert h.any_failing() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/options_wall/test_health.py -q`
Expected: FAIL — `ImportError: cannot import name 'StepHealth'`

- [ ] **Step 3: Write minimal implementation**

Append to `core/options_wall/health.py` (and add `from dataclasses import dataclass`, `from datetime import datetime`, `from typing import Dict, Optional, Tuple` to the imports):

```python
@dataclass(frozen=True)
class Verdict:
    ok: bool
    kind: Optional[str]
    level: str
    alert: bool
    record: dict


class StepHealth:
    """Per-(underlying, step) failure state, edge-triggered alert decisions."""

    def __init__(self, alert_at: Optional[Dict[str, int]] = None):
        self._alert_at = dict(ALERT_AT if alert_at is None else alert_at)
        self._state: Dict[Tuple[str, str], dict] = {}

    def record(self, step: str, underlying: str,
               exc: Optional[BaseException] = None,
               now: Optional[datetime] = None) -> Verdict:
        key = (underlying, step)
        if exc is None:
            record = {"ok": True}
            self._state[key] = record
            return Verdict(True, None, "info", False, record)

        now = now or datetime.now()
        kind = classify(exc)
        prev = self._state.get(key)
        failing = prev is not None and not prev["ok"]
        consecutive = prev["consecutive"] + 1 if failing else 1
        since = prev["since"] if failing else now.isoformat(timespec="seconds")
        record = {
            "ok": False,
            "kind": kind,
            "error_type": type(exc).__name__,
            "error_msg": str(exc)[:200],
            "consecutive": consecutive,
            "since": since,
        }
        self._state[key] = record
        threshold = 1 if kind == STRUCTURAL else self._alert_at.get(step, DEFAULT_ALERT_AT)
        return Verdict(False, kind, "error" if kind == STRUCTURAL else "warning",
                       consecutive == threshold, record)

    def snapshot(self) -> Dict[str, Dict[str, dict]]:
        out: Dict[str, Dict[str, dict]] = {}
        for (underlying, step), record in self._state.items():
            out.setdefault(underlying, {})[step] = record
        return out

    def any_failing(self) -> bool:
        return any(not record["ok"] for record in self._state.values())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/options_wall/test_health.py -q`
Expected: PASS, 17 passed

- [ ] **Step 5: Commit**

```bash
git add core/options_wall/health.py tests/options_wall/test_health.py
git commit -m "feat(options-wall): edge-triggered failure accumulator for poller steps"
```

---

### Task 3: Poller wiring and heartbeat

**Files:**
- Modify: `core/options_wall/poller.py` — `__init__` (~line 85), `_write_heartbeat` (line 122), and the six `except Exception` sites at lines 229, 245, 250, 255, 259, 265
- Test: `tests/options_wall/test_poller_health.py` (create)

**Interfaces:**
- Consumes: `StepHealth`, `Verdict` from Task 2; the log isolation from Task 0 (without it this task's ERROR logging and alerting pollute the operational log and can fire real alerts).
- Produces: `WallPoller._record_step(step: str, underlying: str, exc: BaseException | None = None) -> None`; `WallPoller._health: StepHealth`; heartbeat JSON gains `status` (`"OK"` / `"DEGRADED"`) and `steps`.

- [ ] **Step 1: Write the failing test**

Create `tests/options_wall/test_poller_health.py`:

```python
"""A failing step must be visible in the heartbeat within one cycle."""
import json

import duckdb
import pytest

from core.options_wall.poller import WallPoller


def _poller(tmp_path):
    return WallPoller(heartbeat_path=tmp_path / "hb.json", pid_path=tmp_path / "p.pid",
                      snapshot_db_path=tmp_path / "s.duckdb",
                      results_db_path=tmp_path / "r.duckdb")


@pytest.fixture(autouse=True)
def _no_telegram(monkeypatch):
    """No test may reach the real notifier — a structural failure alerts by design."""
    class Silent:
        def send_message(self, text):
            pass
    monkeypatch.setattr("core.alerts.telegram_notifier.TelegramNotifier", lambda: Silent())


def test_structural_failure_lands_in_the_heartbeat(tmp_path):
    p = _poller(tmp_path)
    p._record_step("executor", "NIFTY", duckdb.ConstraintException("Duplicate key"))
    p._write_heartbeat({"NIFTY": 74})
    hb = json.loads((tmp_path / "hb.json").read_text(encoding="utf-8"))
    assert hb["status"] == "DEGRADED"
    assert hb["steps"]["NIFTY"]["executor"]["ok"] is False
    assert hb["steps"]["NIFTY"]["executor"]["error_type"] == "ConstraintException"
    assert hb["rows"] == {"NIFTY": 74}
    assert "last_snapshot" in hb


def test_healthy_cycle_reports_ok(tmp_path):
    p = _poller(tmp_path)
    p._record_step("executor", "NIFTY")
    p._write_heartbeat({"NIFTY": 74})
    hb = json.loads((tmp_path / "hb.json").read_text(encoding="utf-8"))
    assert hb["status"] == "OK"
    assert hb["steps"]["NIFTY"]["executor"]["ok"] is True


def test_alert_delivery_failure_does_not_propagate(tmp_path, monkeypatch):
    p = _poller(tmp_path)

    class Boom:
        def send_message(self, text):
            raise RuntimeError("telegram down")

    monkeypatch.setattr("core.alerts.telegram_notifier.TelegramNotifier", lambda: Boom())
    p._record_step("executor", "NIFTY", duckdb.ConstraintException("Duplicate key"))


def test_alert_is_sent_once_for_a_persistent_fault(tmp_path, monkeypatch):
    p = _poller(tmp_path)
    sent = []

    class Spy:
        def send_message(self, text):
            sent.append(text)

    monkeypatch.setattr("core.alerts.telegram_notifier.TelegramNotifier", lambda: Spy())
    for _ in range(50):
        p._record_step("executor", "NIFTY", duckdb.ConstraintException("Duplicate key"))
    assert len(sent) == 1
    assert "NIFTY" in sent[0] and "executor" in sent[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/options_wall/test_poller_health.py -q`
Expected: FAIL — `AttributeError: 'WallPoller' object has no attribute '_record_step'`

- [ ] **Step 3: Write minimal implementation**

In `core/options_wall/poller.py`, add to the imports:

```python
from core.options_wall.health import StepHealth
```

Add to `__init__`, immediately after `self._stop = False`:

```python
        self._health = StepHealth()
```

Add these two methods immediately after `_write_heartbeat`:

```python
    def _record_step(self, step: str, underlying: str, exc=None) -> None:
        verdict = self._health.record(step, underlying, exc)
        if exc is not None:
            log = logger.error if verdict.level == "error" else logger.warning
            log("%s %s step failed (%s): %s", underlying, step, verdict.kind, exc)
        if verdict.alert:
            self._alert(step, underlying, verdict)

    def _alert(self, step: str, underlying: str, verdict) -> None:
        record = verdict.record
        text = (f"[options-wall] {underlying} {step} failing\n"
                f"{record['error_type']}: {record['error_msg'].splitlines()[0]}\n"
                f"since {record['since']} ({record['consecutive']} cycles)")
        try:
            from core.alerts.telegram_notifier import TelegramNotifier
            TelegramNotifier().send_message(text)
        except Exception as exc:
            logger.error("health alert delivery failed: %s", exc)
```

Replace the body of `_write_heartbeat`'s `payload` with:

```python
        payload = {
            "last_snapshot": datetime.now().isoformat(),
            "rows": rows_by_name,
            "status": "DEGRADED" if self._health.any_failing() else "OK",
            "steps": self._health.snapshot(),
        }
```

Now replace all six swallow sites. Each currently reads `logger.warning(...)`; each becomes a `_record_step` call, and each success path gains a matching record.

Line 229 — quotes:

```python
                        if qresp.get("error"):
                            self._record_step("quotes", name, RuntimeError(qresp["error"]))
                        else:
                            self._record_step("quotes", name)
```

Lines 244-245 — analytics:

```python
                    try:
                        structural, rv = self._analytics_for(sym, rows, expiry)
                    except Exception as exc:
                        self._record_step("analytics", name, exc)
                    else:
                        self._record_step("analytics", name)
```

Lines 248-250 — executor:

```python
                        try:
                            self._executor_step(name, sym, rows, structural, rv)
                        except Exception as exc:
                            self._record_step("executor", name, exc)
                        else:
                            self._record_step("executor", name)
```

Lines 252-255 — scan-persist:

```python
                        try:
                            self._scan_persist_step(name, sym, rows,
                                                    structural, rv, quotes)
                        except Exception as exc:
                            self._record_step("scan_persist", name, exc)
                        else:
                            self._record_step("scan_persist", name)
```

Lines 256-259 — close-request:

```python
                    try:
                        self._process_close_requests(name, sym, rows, datetime.now())
                    except Exception as exc:
                        self._record_step("close_request", name, exc)
                    else:
                        self._record_step("close_request", name)
```

Lines 263-265 — fetch (this one wraps the whole per-underlying block, so it keeps its existing structure and only swaps the log call):

```python
            except Exception as exc:
                rows_by_name[name] = 0
                self._record_step("fetch", name, exc)
```

Add `self._record_step("fetch", name)` immediately after `rows_by_name[name] = len(rows)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/options_wall/ tests/data/test_options_wall_poller.py -q`
Expected: PASS — the four new tests plus every existing poller test still green

- [ ] **Step 5: Commit**

```bash
git add core/options_wall/poller.py tests/options_wall/test_poller_health.py
git commit -m "feat(options-wall): record and alert on poller step failures"
```

---

### Task 4: Health endpoint

**Files:**
- Modify: `flask_app/blueprints/options_wall.py` (add route; extend the module docstring's Endpoints block)
- Test: `tests/options_wall/test_health_api.py` (create)

**Interfaces:**
- Consumes: `WALL_HEARTBEAT_PATH` from Task 1; the heartbeat shape from Task 3.
- Produces: `GET /options/wall/api/health` returning `{"status", "steps", "heartbeat_age_s", "stale"}`.

- [ ] **Step 1: Write the failing test**

Create `tests/options_wall/test_health_api.py`:

```python
"""The health endpoint reads the heartbeat file, never the results DB."""
import json
from datetime import datetime, timedelta

import pytest

from flask_app.blueprints import options_wall as bp


def _write_hb(path, *, status, age_s):
    ts = (datetime.now() - timedelta(seconds=age_s)).isoformat()
    path.write_text(json.dumps({
        "last_snapshot": ts, "rows": {"NIFTY": 74}, "status": status,
        "steps": {"NIFTY": {"executor": {"ok": status == "OK"}}},
    }), encoding="utf-8")


def test_reports_degraded(tmp_path, monkeypatch):
    hb = tmp_path / "hb.json"
    _write_hb(hb, status="DEGRADED", age_s=2)
    monkeypatch.setattr(bp, "WALL_HEARTBEAT_PATH", hb)
    payload = bp._health_payload()
    assert payload["status"] == "DEGRADED"
    assert payload["stale"] is False
    assert payload["steps"]["NIFTY"]["executor"]["ok"] is False


def test_stale_heartbeat_is_unknown(tmp_path, monkeypatch):
    hb = tmp_path / "hb.json"
    _write_hb(hb, status="OK", age_s=120)
    monkeypatch.setattr(bp, "WALL_HEARTBEAT_PATH", hb)
    payload = bp._health_payload()
    assert payload["stale"] is True
    assert payload["status"] == "UNKNOWN"


def test_missing_heartbeat_is_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr(bp, "WALL_HEARTBEAT_PATH", tmp_path / "absent.json")
    payload = bp._health_payload()
    assert payload["status"] == "UNKNOWN"
    assert payload["steps"] == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/options_wall/test_health_api.py -q`
Expected: FAIL — `AttributeError: module ... has no attribute 'WALL_HEARTBEAT_PATH'`

- [ ] **Step 3: Write minimal implementation**

In `flask_app/blueprints/options_wall.py`, add to the imports:

```python
import json
from datetime import datetime

from core.options_wall.health import WALL_HEARTBEAT_PATH
```

Add the endpoint and its helper:

```python
HEARTBEAT_STALE_S = 60


def _health_payload() -> dict:
    try:
        hb = json.loads(WALL_HEARTBEAT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "UNKNOWN", "steps": {}, "heartbeat_age_s": None, "stale": True}
    age = (datetime.now() - datetime.fromisoformat(hb["last_snapshot"])).total_seconds()
    stale = age > HEARTBEAT_STALE_S
    return {
        "status": "UNKNOWN" if stale else hb.get("status", "UNKNOWN"),
        "steps": hb.get("steps", {}),
        "heartbeat_age_s": round(age, 1),
        "stale": stale,
    }


@options_wall_bp.route("/api/health")
@login_required
def api_health():
    return jsonify(_health_payload())
```

Add to the module docstring's Endpoints block:

```
GET  /options/wall/api/health     poller step health from the heartbeat file
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/options_wall/test_health_api.py -q`
Expected: PASS, 3 passed

- [ ] **Step 5: Commit**

```bash
git add flask_app/blueprints/options_wall.py tests/options_wall/test_health_api.py
git commit -m "feat(options-wall): health endpoint backed by the poller heartbeat"
```

---

### Task 5: Dashboard health strip and gate banner

**Files:**
- Modify: `flask_app/templates/options_wall/index.html`

**Interfaces:**
- Consumes: `GET /options/wall/api/health` from Task 4.
- Produces: no code interface — UI only.

- [ ] **Step 1: Locate the insertion anchor**

Run: `grep -n "Premium farm gate" flask_app/templates/options_wall/index.html`

The health strip goes **immediately before** the element containing that heading, so a red strip can never sit below a green gate.

- [ ] **Step 2: Add the markup**

Insert directly above the farm-gate card:

```html
<section id="wall-health" class="wall-health" hidden>
  <div id="wall-health-banner" class="wall-health-banner" hidden></div>
  <div id="wall-health-chips" class="wall-health-chips"></div>
</section>
```

Add to the page's stylesheet block:

```css
.wall-health { margin: 0 0 12px; }
.wall-health-banner { padding: 8px 12px; border-radius: 6px; font-weight: 600;
  background: #fdecea; color: #8a1c12; border: 1px solid #f3b8b0; margin-bottom: 8px; }
.wall-health-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.wall-health-chip { font: 12px ui-monospace, monospace; padding: 3px 8px; border-radius: 999px;
  background: #eef3ee; color: #24603a; border: 1px solid #cfe0d4; }
.wall-health-chip.bad { background: #fdecea; color: #8a1c12; border-color: #f3b8b0; }
.wall-health-chip.unknown { background: #f2f2f0; color: #6b6b66; border-color: #ddd; }
```

- [ ] **Step 3: Add the poll**

Add to the page's script block:

```javascript
async function refreshWallHealth() {
  const root = document.getElementById('wall-health');
  const chips = document.getElementById('wall-health-chips');
  const banner = document.getElementById('wall-health-banner');
  let h;
  try {
    h = await (await fetch('/options/wall/api/health')).json();
  } catch (e) { return; }

  const entries = [];
  for (const [underlying, steps] of Object.entries(h.steps || {})) {
    for (const [step, rec] of Object.entries(steps)) entries.push([underlying, step, rec]);
  }
  const failing = entries.filter(([, , r]) => r.ok === false);

  if (h.stale) {
    root.hidden = false;
    banner.hidden = false;
    banner.textContent = 'Poller heartbeat is stale — step health unknown.';
    chips.innerHTML = '';
    return;
  }
  if (!failing.length) { root.hidden = true; return; }

  root.hidden = false;
  chips.innerHTML = failing.map(([u, s, r]) =>
    `<span class="wall-health-chip bad">${u} · ${s} · ${r.error_type} · since ${r.since}</span>`
  ).join('');

  const exec = failing.find(([, s]) => s === 'executor');
  banner.hidden = !exec;
  if (exec) {
    banner.textContent =
      `Gate passing, executor failing since ${exec[2].since} — no trades will open.`;
  }
}
setInterval(refreshWallHealth, 5000);
refreshWallHealth();
```

- [ ] **Step 4: Verify by hand**

Run the Flask app, then with the poller stopped confirm the strip shows the stale banner. With the poller running and healthy, confirm the strip is hidden.

Expected: healthy → nothing rendered; stale → grey banner; executor failing → red banner reading "no trades will open".

- [ ] **Step 5: Commit**

```bash
git add flask_app/templates/options_wall/index.html
git commit -m "feat(options-wall): surface step health and a gate banner on the wall page"
```

---

## Self-review

**Spec coverage.** §1 classify → Task 1. §1 `StepHealth`/`Verdict` → Task 2. §2 edge-triggered alerting incl. `ALERT_AT["close_request"] = 1` → Task 2 (thresholds) and Task 3 (delivery). §3 poller integration, WARNING/ERROR split, success recording → Task 3. §4 heartbeat `status` + `steps` → Task 3. §5 endpoint, strip, gate banner, 60 s staleness → Tasks 4 and 5. Every spec test row maps to a test above.

**Two spec corrections carried into the plan.** The route is `/options/wall/api/health`, not `/options-wall/...` — the blueprint's `url_prefix` is `/options/wall`. And the heartbeat's existing keys are `last_snapshot`/`rows`, not `last_heartbeat`/`rows_by_name` as the spec's illustrative JSON showed; the plan extends the real keys.

**Amendment 2026-09-07 (post-restart verification).** Two problems found by checking the plan against the running system rather than against the spec. First, `core/logging/logger.py:80` hardcodes `Path("logs")` and `poller.py:42` builds its logger at import time, so the test suite writes into the live operational log — confirmed when a suite run injected 57 warnings that were then misread as production faults during the outage diagnosis. That is now Task 0, and it is a prerequisite: once Task 3 emits ERROR and calls Telegram, an un-isolated run would inject fake ERRORs and fire real alerts. Second, two Task 3 tests drove `_record_step` with a structural exception — which alerts by design — without patching the notifier, so on any machine with `TELEGRAM_TOKEN` set they would have sent live messages. Task 3 now carries an autouse `_no_telegram` fixture.

**Deferred deliberately.** The spec's "poller wiring: a raising executor step records structural **and** `scan_persist` still runs" is covered structurally — Task 3 keeps the independent `try/except` blocks, and the existing `tests/options_wall/test_poller_executor_wiring.py` already asserts the isolation. No new test duplicates it.
