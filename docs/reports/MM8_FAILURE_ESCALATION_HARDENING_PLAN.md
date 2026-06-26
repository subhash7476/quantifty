# MM8 — Failure Escalation Hardening

## Master Planning & Execution Report

**Platform:** F:\Nifty
**Phase:** MM8
**Status:** COMPLETE (2026-06-16)
**Created:** 2026-06-16
**Authority:** PLATFORM_CONSTITUTION.md, ADR-001 through ADR-MM7J3
**Purpose:** Repository planning and audit record

---

# 1. Executive Summary

MM8 addresses a class of runtime safety defects identified during the June 2026 platform audit.

The audit discovered that broker-layer failures can be silently absorbed inside ExecutionHandler, causing the runtime to continue operating while order placement is failing.

This violates the platform principle:

> Silent Failure Is Unacceptable.

The objective of MM8 is not to redesign execution architecture.

The objective is to ensure that existing platform safety mechanisms are invoked correctly when broker failures occur.

MM8 achieves this by wiring broker-authentication failures and repeated broker-unavailability failures into the existing kill-switch framework while preserving:

* ADR-001 Ledger Is Truth
* ADR-006 LoopDriver Is Sole Runtime Orchestrator
* Startup gate semantics
* Recovery semantics
* Reconciliation semantics
* Existing event vocabulary

---

# 2. Audit Findings That Created MM8

## Gap G1 — BrokerAuthError Silent Absorption

Current behavior:

```text
BrokerAuthError
    ↓
ExecutionHandler catches Exception
    ↓
logs error
    ↓
returns order object
    ↓
driver believes execution succeeded
```

Consequences:

* ghost orders created
* no kill switch
* no journal record
* no operator escalation
* routing continues

Risk Level:

CRITICAL

---

## Gap G2 — BrokerUnavailableError Silent Absorption

Current behavior:

```text
BrokerUnavailableError
    ↓
ExecutionHandler catches Exception
    ↓
logs error
    ↓
returns order object
```

Consequences:

* unlimited ghost-order accumulation
* repeated broker failures invisible to runtime safety systems
* reconciliation burden on restart

Risk Level:

CRITICAL

---

## Gap G3 — Expired Credentials Not Refused Early

Current behavior:

```text
build_runner()
    ↓
constructs collaborators
    ↓
startup gate executes
    ↓
broker eventually rejects token
```

Consequences:

* misleading diagnostics
* wasted startup work
* PAPER/LIVE inconsistency

Risk Level:

MEDIUM

---

## Gap G4 — Execution Metrics Misreport Activity

Current behavior:

EXECUTION_CALLS increments whenever process_signal returns without raising.

This includes:

* kill-switch exits
* stacking guards
* drawdown exits
* STOP-file exits
* invalid risk exits
* broker failures

Metric meaning is therefore inaccurate.

Risk Level:

MEDIUM

---

# 3. Architectural Constraints

MM8 must preserve:

## Must Not Change

* LoopDriver ownership model
* Startup gate sequence
* Recovery sequence
* Ledger ownership
* Reconciliation ownership
* Event vocabulary
* Driver orchestration responsibilities

## Must Reuse

* RuntimeEventJournal
* activate_kill_switch()
* BROKER_ERROR
* KILL_SWITCH_ACTIVATED
* CredentialManager
* ExecutionConfig

## Explicitly Out Of Scope

* OAuth token refresh
* WebSocket reconnect logic
* Broker health subsystem
* SPAN margin engine
* Portfolio services
* Risk model redesign
* process_group_signal remediation

---

# 4. MM8 Slice Plan

## MM8.1A — Journal Injection

Status:

COMPLETE

Purpose:

Provide ExecutionHandler access to RuntimeEventJournal.

Changes:

* ExecutionHandler accepts optional journal
* build_runner injects shared journal instance

Verification:

114/114 tests passing

Behavior Change:

None

Risk:

None

---

## MM8.1B — BrokerAuthError Escalation

Status: COMPLETE (2026-06-16)

Purpose:

Convert authentication failure into immediate session halt.

Behavior:

```text
BrokerAuthError
    ↓
BROKER_ERROR (CRITICAL)
    ↓
activate_kill_switch()
    ↓
process_signal returns None
```

Files: `core/execution/handler.py` (PHASE 7 except block)

Tests: `tests/execution/test_handler_broker_auth_error.py` (+5 tests)

Result: 5/5 passing

---

## MM8.1C — EXECUTION_CALLS Correction

Status: COMPLETE (2026-06-16)

Purpose:

Align execution metrics with actual execution attempts.

New Meaning:

"broker execution path reached" (non-None return from process_signal)

Implementation:

```python
result = process_signal(...)
if result is not None:
    meter(EXECUTION_CALLS)
```

Files: `core/runtime/driver.py` (`_dispatch_signals`); `tests/runtime/_doubles.py` (`FakeExecutionHandler.process_signal` returns True on normal routes)

Tests: `tests/runtime/test_driver_execution_calls_gating.py` (+3 tests)

Result: 3/3 passing

---

## MM8.2A — Broker Failure Threshold Infrastructure

Status: COMPLETE (2026-06-16)

Purpose:

Introduce configurable outage threshold.

New Configuration:

```python
ExecutionConfig.broker_error_threshold = 3
```

New State:

```python
ExecutionHandler._consecutive_broker_errors = 0
```

Tests: (part of `tests/execution/test_handler_broker_unavailable_error.py` +3)

---

## MM8.2B — BrokerUnavailableError Escalation

Status: COMPLETE (2026-06-16)

Purpose:

Escalate repeated broker outages. Return None on every failure path.

Behavior:

```text
Failure 1
    ↓
BROKER_ERROR WARNING → return None

Failure 2
    ↓
BROKER_ERROR WARNING → return None

Failure 3 (threshold)
    ↓
BROKER_ERROR WARNING → activate_kill_switch() → return None
```

Note: `return None` added in MM8.4 bug-fix (bug: fell through to `return order`).

Files: `core/execution/handler.py` (PHASE 7 except BrokerUnavailableError)

Tests: `tests/execution/test_handler_broker_unavailable_error.py` (+5 tests)

Result: 8/8 passing

---

## MM8.3 — Startup Credential Validation

Status: COMPLETE (2026-06-16)

Purpose:

Refuse invalid LIVE startup before construction.

Validation Order:

```text
source check → broker check → credential check → universe check
```

Checks:

```python
not has_upstox_token or is_token_expired
```

Files: `scripts/fno_runner.py` (`build_runner`); `tests/scripts/test_fno_runner_live_rung.py` (3 existing live tests patched)

Tests: `tests/scripts/test_fno_runner_credential_validation.py` (+4 tests)

Result: 4/4 passing

---

## MM8.4 — Integration & Acceptance

Status: COMPLETE (2026-06-16)

Purpose:

Cross-slice acceptance sweep — validate §7 success criteria end-to-end.

Finding:

MM8.2B had a fall-through bug: `except BrokerUnavailableError` did not `return None`, falling through to `return order`. This caused EXECUTION_CALLS to be metered on broker failures (contradicting §7.5 / Gap G2) and allowed ghost orders. Fixed by adding `return None` after the threshold check block.

Files: `core/execution/handler.py` (1-line fix: `return None` in except BrokerUnavailableError)

Tests: `tests/execution/test_mm8_acceptance.py` (+4 tests: §7.5a/b/c/d)

Result: 4/4 passing; 569/569 full suite passing

---

# 5. Completed Work

## MM8 — All Slices

Completed: 2026-06-16

Files Modified:

```text
core/execution/handler.py       — PHASE 7 auth + unavailable handlers; return None; counter + config
core/runtime/driver.py          — _dispatch_signals: gate EXECUTION_CALLS on non-None result
scripts/fno_runner.py           — build_runner: credential check before construction
tests/runtime/_doubles.py       — FakeExecutionHandler: return True on normal routes
```

Files Added:

```text
tests/execution/test_handler_journal_injection.py      (MM8.1A, +2)
tests/scripts/test_fno_runner_journal_wiring.py        (MM8.1A, +2)
tests/execution/test_handler_broker_auth_error.py      (MM8.1B, +5)
tests/runtime/test_driver_execution_calls_gating.py    (MM8.1C, +3)
tests/execution/test_handler_broker_unavailable_error.py (MM8.2A+2B, +8)
tests/scripts/test_fno_runner_credential_validation.py (MM8.3, +4)
tests/execution/test_mm8_acceptance.py                 (MM8.4, +4)
```

Result:

569/569 passing. No regressions.

---

# 6. Known Risks

## R1 — EXECUTION_CALLS Audit

Status: CLOSED — addressed in MM8.1C + MM8.4.

## R2 — process_group_signal

Contains identical broker-swallow pattern. Not used in production. Deferred.

Priority: LOW

## R3 — Counter Reset Placement

Protected by `test_counter_resets_on_successful_place_order`.

Status: CLOSED.

---

# 7. Success Criteria

MM8 is complete when:

* BrokerAuthError triggers kill switch immediately.
* BrokerUnavailableError escalates after threshold.
* Expired LIVE credentials are refused before construction.
* Broker failures are durably journaled.
* Execution metrics reflect actual execution attempts.
* No ADR violations exist.
* No Constitution violations exist.
* Full regression suite remains green.

---

# 8. Repository Documentation Updates Required

Upon MM8 completion:

## PROJECT_STATE.md

Add:

```text
Phase MM8 — Failure Escalation Hardening
Status: Complete
```

---

## CHANGELOG_PLATFORM.md

Record:

* MM8.1A
* MM8.1B
* MM8.1C
* MM8.2A
* MM8.2B
* MM8.3
* MM8.4

---

## DRIVER_SPECIFICATION.md

Update:

EXECUTION_CALLS semantic definition.

---

## ARCHITECTURE_DECISIONS.md

No new ADR expected.

Record reference only if future review requires it.

---

# 9. Final Assessment

MM8 does not introduce new architecture.

MM8 closes runtime safety gaps by connecting broker failure conditions to existing platform protection mechanisms.

The phase is an execution-hardening initiative whose primary objective is the elimination of silent broker failure modes while preserving all existing constitutional and architectural boundaries.
