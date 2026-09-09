# MM8 — Failure Escalation Hardening: Full Implementation Report

**Platform:** F:\Nifty
**Date:** 2026-06-16
**Status:** COMPLETE
**Suite:** 565 → 569 passing (28 new tests across 7 new/modified files)

---

## 1. Problem Statement

A June 2026 audit identified four silent-failure gaps in `ExecutionHandler.process_signal`:

| Gap | Description | Risk |
|-----|-------------|------|
| **G1** | `BrokerAuthError` caught by bare `except Exception`, logged, then `return order` — ghost order created, no kill switch, no journal | CRITICAL |
| **G2** | `BrokerUnavailableError` same bare swallow — unlimited ghost-order accumulation, no escalation | CRITICAL |
| **G3** | `build_runner()` with `ExecutionMode.LIVE` constructed all collaborators before detecting an expired/missing token — wasted startup work, misleading errors | MEDIUM |
| **G4** | `EXECUTION_CALLS` incremented on every non-raising `process_signal` return — kill-switch exits, stacking guards, drawdown blocks, and broker failures all counted as "executions" | MEDIUM |

Objective: wire broker failures into the existing `activate_kill_switch()` and `RuntimeEventJournal` framework without redesigning execution architecture.

---

## 2. Slice-by-Slice Implementation

---

### MM8.1A — Journal Injection

**Purpose:** Give `ExecutionHandler` access to `RuntimeEventJournal` before any usage sites are added.

**Changes:**

`core/execution/handler.py`
- `ExecutionHandler.__init__` gains `journal: Optional[RuntimeEventJournal] = None` parameter
- Stored as `self._journal`
- All existing call sites unaffected (default is `None`)

`scripts/fno_runner.py`
- `build_runner()` adds `handler_kwargs["journal"] = journal` so the shared journal instance flows into the handler

**Behavior change:** None — `self._journal` is stored but not called yet.

**Tests added (+4):**
- `tests/execution/test_handler_journal_injection.py` — journal stored when injected; `None` when omitted
- `tests/scripts/test_fno_runner_journal_wiring.py` — `build_runner` threads journal into handler

**Suite:** 114/114 passing

---

### MM8.1B — BrokerAuthError Escalation

**Purpose:** Convert authentication failure into immediate, durable session halt.

**Changes:**

`core/execution/handler.py`
- Import block: `BrokerAuthError`, `BrokerUnavailableError` added from `core.brokers.upstox_adapter`; `EventType`, `Severity` added to event journal import
- PHASE 7 of `process_signal`: new `except BrokerAuthError` clause before the bare `except Exception`:

```python
except BrokerAuthError as e:
    if self._journal:
        self._journal.record(
            EventType.BROKER_ERROR,
            f"Broker authentication failure: {e}",
            severity=Severity.CRITICAL,
            source_component="ExecutionHandler",
            metadata={"error": str(e), "signal_id": str(signal_id)},
        )
    self.activate_kill_switch(f"BrokerAuthError: {e}")
    return None
```

**Behavior:** `BrokerAuthError` → journal `BROKER_ERROR` (CRITICAL) → kill switch → `return None`. No re-raise. No order returned. No ghost order.

**Tests added (+5):** `tests/execution/test_handler_broker_auth_error.py`
- Kill switch fires on `BrokerAuthError`
- `process_signal` returns `None`
- Journal receives `BROKER_ERROR` with `severity=CRITICAL`
- Exception is not re-raised (loop survives)
- Behaviour is correct when `journal=None` (no crash)

**Suite:** 119/119 passing (delta from 1A)

---

### MM8.1C — EXECUTION_CALLS Metric Correction

**Purpose:** Make `EXECUTION_CALLS` mean "broker execution path reached" rather than "process_signal did not raise."

**Changes:**

`core/runtime/driver.py` — `_dispatch_signals`:
```python
# Before:
self._execution.process_signal(signal, bar.close)
self._meter(RuntimeMetric.EXECUTION_CALLS)

# After:
result = self._execution.process_signal(signal, bar.close)
if result is not None:
    self._meter(RuntimeMetric.EXECUTION_CALLS)
```

`tests/runtime/_doubles.py` — `FakeExecutionHandler.process_signal`:
- Changed `return None` on the normal path to `return True` (non-None sentinel meaning "broker execution path reached")
- Explicit `return None` retained only for the `kill_switch_on` branch
- Preserves the `test_controlled_replay_run_produces_exact_metric_snapshot` expectation of `EXECUTION_CALLS: 2`

**Behavior:** Kill-switch exits, stacking guards, drawdown blocks, risk refusals, and broker failures all return `None` → not metered. Successful broker placements return the `NormalizedOrder` → metered.

**Tests added (+3):** `tests/runtime/test_driver_execution_calls_gating.py`
- `None`-returning handler → `EXECUTION_CALLS` stays 0
- non-`None`-returning handler → `EXECUTION_CALLS` incremented
- Selective handler → only successful signals counted

**Suite:** 122/122 passing (delta from 1B)

---

### MM8.2A — Broker Error Threshold Infrastructure

**Purpose:** Introduce the configurable consecutive-failure threshold and its counter.

**Changes:**

`core/execution/handler.py`
- `ExecutionConfig` dataclass: `broker_error_threshold: int = 3`
- `ExecutionHandler.__init__`: `self._consecutive_broker_errors = 0`

**Behavior change:** None on its own — infrastructure only.

**Tests added (+3):** first three tests in `tests/execution/test_handler_broker_unavailable_error.py`
- `ExecutionConfig.broker_error_threshold` defaults to 3
- `broker_error_threshold` is configurable
- Handler initialises `_consecutive_broker_errors` to 0

---

### MM8.2B — BrokerUnavailableError Escalation

**Purpose:** Escalate repeated broker outages: journal every failure as WARNING, activate kill switch at threshold.

**Changes:**

`core/execution/handler.py` — PHASE 7 of `process_signal`: new `except BrokerUnavailableError` clause:

```python
except BrokerUnavailableError as e:
    self._consecutive_broker_errors += 1
    if self._journal:
        self._journal.record(
            EventType.BROKER_ERROR,
            f"Broker unavailable: {e}",
            severity=Severity.WARNING,
            source_component="ExecutionHandler",
            metadata={"error": str(e), "signal_id": str(signal_id),
                      "consecutive_errors": self._consecutive_broker_errors},
        )
    if self._consecutive_broker_errors >= self.config.broker_error_threshold:
        self.activate_kill_switch(
            f"BrokerUnavailableError x{self._consecutive_broker_errors}: {e}")
    return None   # added in MM8.4 bug-fix; see section 3
```

Success-path reset (in the try block, immediately after `place_order` succeeds):
```python
self._consecutive_broker_errors = 0
```

**Tests added (+5):** remaining tests in `tests/execution/test_handler_broker_unavailable_error.py`
- Counter increments on each failure
- `BROKER_ERROR` WARNING journaled on each failure (with `consecutive_errors` in metadata)
- Kill switch fires exactly at threshold (not before)
- Counter resets to 0 after successful placement
- `process_signal` returns `None` after kill switch trips (4th call hits top-of-function guard)

**Suite:** 130/130 passing (delta from 1C)

---

### MM8.3 — Startup Credential Validation

**Purpose:** Refuse `ExecutionMode.LIVE` before any collaborator is constructed when the Upstox token is absent or expired.

**Changes:**

`scripts/fno_runner.py`
- Module-level import: `from core.auth.credentials import credentials as _live_credentials`
- Inside `build_runner()`, after the `broker is None` check:

```python
if execution_mode is ExecutionMode.LIVE:
    if not _live_credentials.has_upstox_token or _live_credentials.is_token_expired:
        raise ValueError(
            "fno_runner: ExecutionMode.LIVE requires a valid, unexpired Upstox "
            "token; refresh the token before starting "
            "(CredentialManager.needs_daily_refresh is True)"
        )
```

Validation order: `source → broker → credential → universe`

`tests/scripts/test_fno_runner_live_rung.py` (regression fix)
- Added `_patch_live_creds(monkeypatch)` helper (MagicMock with `has_upstox_token=True`, `is_token_expired=False`)
- Applied to tests L1, L2, L5 (those that construct the driver with `ExecutionMode.LIVE`)

**Tests added (+4):** `tests/scripts/test_fno_runner_credential_validation.py`
- LIVE + missing token → `ValueError` before construction
- LIVE + expired token → `ValueError` before construction
- LIVE + valid token → no error
- PAPER mode → credential check skipped entirely

**Suite:** 134/134 passing (delta from 2B)

---

### MM8.4 — Integration & Acceptance (+ bug fix)

**Purpose:** Cross-slice acceptance sweep validating MM8 §7 success criteria end-to-end.

**Bug found:** The `except BrokerUnavailableError` clause from MM8.2B had no `return None` — execution fell through to `return order` (non-None). This meant:

- Every `BrokerUnavailableError`, even below threshold, returned the `NormalizedOrder`
- `EXECUTION_CALLS` was metered on broker failures (violates §7.5 / Gap G4)
- The order built in PHASE 5 became a ghost order in `order_tracker` (Gap G2)
- The existing `test_process_signal_returns_none_after_kill_switch` only passed because the *next* call (after kill switch) hit the top-of-function guard — not because the failing call itself returned `None`

**Fix (1 line):** `return None` added inside `except BrokerUnavailableError`, after the threshold check.

**Tests added (+4):** `tests/execution/test_mm8_acceptance.py`
- §7.5a: first `BrokerUnavailableError` (below threshold) returns `None`
- §7.5b: all below-threshold failures return `None`
- §7.5c: successful placement returns non-`None` (metrics correctly metered)
- §7.5d: success after prior failures returns non-`None` and resets counter

**Suite:** 569/569 passing

---

## 3. Files Modified / Added

**Modified:**

| File | Change |
|------|--------|
| `core/execution/handler.py` | `ExecutionConfig.broker_error_threshold`; `__init__` counter; PHASE 7 two new except clauses + success-path reset + `return None` fix |
| `core/runtime/driver.py` | `_dispatch_signals`: gate `EXECUTION_CALLS` on non-`None` result |
| `scripts/fno_runner.py` | `_live_credentials` import; credential check in `build_runner()` |
| `tests/runtime/_doubles.py` | `FakeExecutionHandler.process_signal`: `return True` on normal routes |
| `tests/scripts/test_fno_runner_live_rung.py` | `_patch_live_creds` helper; applied to L1, L2, L5 |

**Added:**

| File | Slice | Tests |
|------|-------|-------|
| `tests/execution/test_handler_journal_injection.py` | MM8.1A | 2 |
| `tests/scripts/test_fno_runner_journal_wiring.py` | MM8.1A | 2 |
| `tests/execution/test_handler_broker_auth_error.py` | MM8.1B | 5 |
| `tests/runtime/test_driver_execution_calls_gating.py` | MM8.1C | 3 |
| `tests/execution/test_handler_broker_unavailable_error.py` | MM8.2A+2B | 8 |
| `tests/scripts/test_fno_runner_credential_validation.py` | MM8.3 | 4 |
| `tests/execution/test_mm8_acceptance.py` | MM8.4 | 4 |

**Total new tests: 28** (24 in new files + 4 in modified files)

---

## 4. §7 Success Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `BrokerAuthError` triggers kill switch immediately | PASS | `test_kill_switch_activated_on_broker_auth_error` |
| `BrokerUnavailableError` escalates after threshold | PASS | `test_kill_switch_fires_at_threshold` |
| Expired LIVE credentials refused before construction | PASS | `test_live_refuses_when_token_expired` |
| Broker failures are durably journaled | PASS | `test_broker_auth_error_journals_critical_event`, `test_broker_unavailable_journals_warning_each_failure` |
| Execution metrics reflect actual execution attempts | PASS | `test_execution_calls_not_incremented_on_none_return` + MM8.4 bug-fix |
| No ADR violations | PASS | All architectural boundaries preserved; no new imports across forbidden seams |
| No Constitution violations | PASS | Existing kill switch, journal, and reconcile seams reused unchanged |
| Full regression suite green | PASS | **569/569 passing** |

---

## 5. Notable Design Decisions

**BrokerAuthError → immediate kill switch (no threshold):** Auth failure is not transient. A single `401` means the session token is invalid for the rest of the trading day. No threshold makes sense — one auth failure is sufficient to halt all order routing.

**BrokerUnavailableError → threshold before kill switch:** Network outages are transient. Three consecutive failures (default `broker_error_threshold=3`) distinguishes a brief glitch from a sustained outage. Each failure is journaled individually so the operator can track degradation in `logs/runtime_events.jsonl` before the kill switch trips.

**`return None` on every BrokerUnavailableError path (MM8.4 fix):** Below-threshold failures must also return `None` — not just threshold-hitting ones. Returning the order on a failed placement creates a ghost order in `order_tracker` and a false `EXECUTION_CALLS` count. The MM8.4 acceptance sweep caught this fall-through.

**`EXECUTION_CALLS` gates on non-`None` return (not on non-raise):** The metric answers "did the broker receive an order?" not "did the handler complete without error?" A kill-switch return, a stacking guard, a drawdown block, and a broker failure all return `None` — none should count. This required updating `FakeExecutionHandler` to return `True` (not `None`) on the normal path so existing telemetry snapshot tests remained correct.

**Credential check at composition root, before construction:** Failing at `build_runner()` before any collaborator is constructed gives operators an immediate, unambiguous diagnostic. Failing inside the handler mid-run after one signal is processed is confusing and wasteful. Validation order (`source → broker → credential → universe`) places the cheapest checks first.

---

*Ref: docs/reports/MM8_FAILURE_ESCALATION_HARDENING_PLAN.md; docs/PROJECT_STATE.md; docs/CHANGELOG_PLATFORM.md*
