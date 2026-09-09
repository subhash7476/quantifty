# MM12.3 — GuardedSignalSource Implementation

**Date:** 2026-07-02
**Status:** COMPLETE
**Author role:** Implementation Engineer
**Milestone:** MM12.3 — runtime enforcement layer for the certified Strategy Contract
(MM12.1 architecture §7.3, §8; ADR-018 boundary validation; ADR-019 fault policy)

Scope discipline observed: this is an implementation of an already-approved design.
No architecture decisions were revisited, no ADRs were authored or amended, no
additional abstractions were introduced beyond `GuardedSignalSource` itself.

---

## 1. Implementation Summary

### Files added

| File | Purpose |
|---|---|
| `core/runtime/guarded_signal_source.py` | `GuardedSignalSource(SignalSource)` — the runtime boundary guard. |
| `tests/runtime/test_guarded_signal_source.py` | 35 fault-injection / boundary-enforcement tests (MM12.3 exit criterion). |

### Files modified

| File | Change | Reason |
|---|---|---|
| `core/runtime/event_journal.py` | Added `EventType.STRATEGY_ERROR`, `STRATEGY_QUARANTINED`, `SIGNAL_CONTRACT_REJECTED` + matching `_DEFAULT_SEVERITY` entries. | Architecture §8.3 — additive, non-breaking journal vocabulary. |
| `core/runtime/metrics.py` | Added `RuntimeMetric.STRATEGY_ERRORS`, `STRATEGY_QUARANTINE_EVENTS`, `SIGNAL_CONTRACT_REJECTIONS`; updated docstrings (removed the now-inaccurate "exactly twelve" claim). | Architecture §8.3 — "telemetry counters mirror these." |
| `tests/runtime/test_event_journal.py` | Updated the exact-membership assertion (`len(EventType)`, the expected value set) and added 3 severity-parametrize cases. | The enum grew by 3 additive members; the existing test asserted an exact count/set. |
| `tests/runtime/test_telemetry_sink.py` | Updated the exact-membership assertion and renamed the test off "twelve." | Same reason, for `RuntimeMetric`. |

### Files explicitly NOT touched (frozen, zero diffs — verified via `git diff --stat`)

`core/runtime/driver.py`, `core/execution/handler.py`, `core/runtime/signal_source.py`,
`core/runtime/conformance.py`. Confirmed empty diff for all four before submission.

`scripts/fno_runner.py` was also left untouched. The MM12.1 roadmap (§15) assigns
composition-root wiring ("the real composition root drives the guarded reference
source through a full session") to **MM12.4**, not MM12.3. MM12.3's exit criterion is
the guard component plus its fault-injection proof, with zero diffs in the frozen
runtime files — which this implementation satisfies without touching the root.

### Runtime impact

None on any existing code path. `GuardedSignalSource` is a new, optional decorator;
nothing in the platform constructs or requires one yet (no production strategy
exists — greenfield, per `CLAUDE.md`). The three new `EventType`/`RuntimeMetric`
members are additive enum values with no behavioral effect until a `GuardedSignalSource`
instance is composed and driven.

---

## 2. Boundary Enforcement Report

Every invariant `GuardedSignalSource` enforces, and where it is implemented
(`core/runtime/guarded_signal_source.py`):

| Invariant | Enforcement | Outcome on violation |
|---|---|---|
| Quarantine short-circuit | `on_bar` returns `[]` immediately if `self._quarantined` | N/A (this *is* the enforcement) |
| Fault containment | inner `on_bar` called inside `try/except Exception` | quarantine (§below) |
| Return shape | `isinstance(result, list)` and every element `isinstance(SignalEvent)` | quarantine (treated as a fault, per architecture §8.1: "a source that violates the return shape is defective, not merely noisy") |
| Timestamp discipline | `signal.timestamp == bar.timestamp` | drop + journal `SIGNAL_CONTRACT_REJECTED` |
| Mandatory entry risk metadata | `sl_distance` and `risk_r` present, numeric, `> 0` on BUY/SELL (not EXIT) | drop + journal `SIGNAL_CONTRACT_REJECTED` |
| Per-signal isolation | one violating signal does not suppress contract-clean siblings in the same list | clean signals still returned |
| No signal mutation | rejected signals are dropped, never rewritten; accepted signals are returned by identity, never copied/default-filled | see `test_guard_never_mutates_a_clean_signal_it_passes_through` |
| `on_start` fault = refusal | journal `STRATEGY_ERROR`, then re-raise (does not quarantine, does not swallow) | composition root aborts before `RUNNING` |
| `on_stop` fault = swallow | logged via the module logger, never raised | shutdown always completes |
| Side-channel containment | journal / telemetry / alerter calls each individually wrapped in `try/except` | a broken journal, sink, or alert channel can never let an exception escape `on_bar`/`on_start` |

**Validation scope note:** the guard validates exactly what
`core/runtime/conformance.py` (MM12.2, frozen for this task) already codifies as the
mechanically-checked §4 contract: return shape, timestamp discipline, and mandatory
entry risk metadata. See §7 Deviations for the one architecture-prose invariant
("universe membership") deliberately not implemented, and why.

**Non-responsibilities preserved** (verified — the guard's constructor accepts
only `inner`, `journal`, `telemetry`, `strategy_id`, `alerter`; it holds no
ledger/broker/handler/execution reference; `test_guard_wrapping_inert_source_is_conformant`
and `test_guard_wrapping_raising_source_is_conformant` both run the full MM12.2
conformance suite — including `check_no_forbidden_handles` — against a guarded
source and pass): the guard never sizes, prices, evaluates alpha, modifies a
signal's content, executes an order, or reads broker/portfolio state.

---

## 3. Fault Injection Report

| # | Injected failure | Expected behaviour (spec) | Observed behaviour | Test |
|---|---|---|---|---|
| 1 | Malformed metadata (missing/zero/negative/non-numeric `sl_distance`/`risk_r`) | Drop + `SIGNAL_CONTRACT_REJECTED`; not quarantined | Matched, all 5 shapes | `test_all_malformed_metadata_shapes_are_dropped` (parametrized) |
| 2 | Invalid timestamp (drifted from bar) | Drop + `SIGNAL_CONTRACT_REJECTED`; not quarantined | Matched | `test_invalid_timestamp_signal_is_dropped_not_quarantined` |
| 3 | Contract-clean sibling alongside a violator | Sibling still routes | Matched | `test_malformed_metadata_signal_is_dropped_clean_sibling_routes` |
| 4 | Invalid return type (`on_bar` returns a string, not a list) | Quarantine (treated as fault) | Matched | `test_malformed_return_type_quarantines` |
| 5 | Invalid element type (list containing a non-`SignalEvent`) | Quarantine | Matched | `test_malformed_element_type_quarantines` |
| 6 | Strategy exception (`on_bar` raises) | Quarantine; `[]` for this and every subsequent bar; inner never invoked again | Matched | `test_on_bar_exception_quarantines_and_returns_empty`, `test_quarantine_is_terminal_inner_source_never_invoked_again` |
| 7 | Repeated bars post-quarantine (no auto-retry) | Deterministic `[]` forever; inner call count stays at 1 | Matched | `test_no_auto_retry_deterministic_quarantine_across_bars` |
| 8 | Replay determinism after quarantine | Two independent guarded instances over the identical corpus emit byte-identical (empty) streams | Matched | `test_replay_determinism_after_quarantine`; also proven generically via `test_guard_wrapping_raising_source_is_conformant` (full replay-twice conformance check) |
| 9 | `on_start` raises | Refusal: journal `STRATEGY_ERROR`, re-raise (not quarantine, not swallowed) | Matched | `test_on_start_fault_journals_then_reraises` |
| 10 | `on_stop` raises | Logged and swallowed; shutdown proceeds | Matched | `test_on_stop_fault_is_swallowed_not_raised` |
| 11 | Journal write fails during quarantine | No exception escapes `on_bar` | Matched | `test_broken_journal_does_not_escape_on_bar` |
| 12 | Telemetry increment fails during quarantine | No exception escapes `on_bar` | Matched | `test_broken_telemetry_does_not_escape_on_bar` |
| 13 | Alert delivery fails during quarantine (e.g. Telegram down) | No exception escapes `on_bar` | Matched | `test_alerter_fault_does_not_escape_quarantine_path` |
| 14 | Contract violation on bar N, exception on bar N+1 (ADR-019: "exercise validation and quarantine as one surface") | Bar N drops+journals; bar N+1 quarantines; both event types present | Matched | `test_contract_violation_then_raise_on_subsequent_bar` |
| 15 | Journal emission (all 3 new event types occur) | `STRATEGY_ERROR`, `STRATEGY_QUARANTINED`, `SIGNAL_CONTRACT_REJECTED` all observed in the journal file | Matched | multiple; see §4 |
| 16 | Telemetry emission (all 3 new counters increment) | `STRATEGY_ERRORS`, `STRATEGY_QUARANTINE_EVENTS`, `SIGNAL_CONTRACT_REJECTIONS` | Matched | `test_quarantine_increments_telemetry_counters`, `test_rejected_signal_increments_telemetry_counter` |
| 17 | Guard itself passes conformance (Layer 1 + Layer 2, `run_conformance`) | The guard is a conforming `SignalSource` — no driver change needed | Matched, for both an inert and a permanently-raising inner source | `test_guard_wrapping_inert_source_is_conformant`, `test_guard_wrapping_raising_source_is_conformant` |

All 17 failure-mode classes have a dedicated test (35 tests total, several
parametrized/covering multiple assertions per class — including two additional
tests added after review: journal-metadata content for `STRATEGY_ERROR`
(`strategy_id` + traceback digest) and multi-signal routing-order preservation).

---

## 4. Journal Report

| Event type | Severity | Emitted when | Verified by |
|---|---|---|---|
| `SIGNAL_CONTRACT_REJECTED` | WARNING | per dropped contract-violating signal | `test_signal_contract_rejected_severity_is_warning`, drop-path tests |
| `STRATEGY_ERROR` | WARNING (see §7 Deviations — architecture prose says "ERROR", a level `Severity` does not define) | uncaught `on_bar` fault, malformed return, or `on_start` fault | `test_on_bar_exception_quarantines_and_returns_empty`, `test_on_start_fault_journals_then_reraises` |
| `STRATEGY_QUARANTINED` | CRITICAL | quarantine latch set (edge-triggered, exactly once per process lifetime) | `test_strategy_quarantined_severity_is_critical`, `test_quarantine_journal_entry_is_edge_triggered_once` |

`journal=None` is a supported construction mode (disables journaling without
raising) — used by several tests and by the conformance-suite-facing factory to
isolate the check under test.

---

## 5. Telemetry Report

| Metric | Group | Incremented when |
|---|---|---|
| `RuntimeMetric.SIGNAL_CONTRACT_REJECTIONS` | Strategy guard | every dropped contract-violating signal |
| `RuntimeMetric.STRATEGY_ERRORS` | Strategy guard | every uncaught `on_bar`/`on_start` fault (including malformed-return quarantine triggers) |
| `RuntimeMetric.STRATEGY_QUARANTINE_EVENTS` | Strategy guard | the quarantine latch transition (edge-triggered, once) |

`telemetry=None` defaults to `NullTelemetrySink` (inert no-op), matching the
`LoopDriver`'s own Phase H default — the guard behaves identically with or
without telemetry wired.

---

## 6. Test Report

| Stage | Result |
|---|---|
| Baseline (before MM12.3) | **1083 passed, 4 skipped** |
| Final (after MM12.3) | **1121 passed, 4 skipped** |
| New tests | 38 (35 in `test_guarded_signal_source.py` + 3 new severity-parametrize cases in `test_event_journal.py`) |
| Existing tests | All 1083 baseline tests still pass; 2 test files updated (`test_event_journal.py`, `test_telemetry_sink.py`) to reflect the additive enum growth their exact-membership assertions require (no test *deleted* or *weakened* — both now assert the new, larger, still-exact set) |
| Regression summary | **Zero regressions.** `git diff --stat` on `core/runtime/driver.py`, `core/execution/handler.py`, `core/runtime/signal_source.py`, `core/runtime/conformance.py` is empty. |

Full suite: `python -m pytest -q` → `1121 passed, 4 skipped in 78.62s`.
Guard-only: `python -m pytest tests/runtime/test_guarded_signal_source.py -q` → `35 passed in 1.35s`.

---

## 7. Deviations

One deliberate, reported deviation and one documented mapping — both within the
"stop and report rather than improvise" instruction; neither required an
architecture change.

### 7.1 "Universe membership" validation — not implemented

The MM12.1 architecture's §4.1 field-contract table states a signal's `symbol`
"must be inside the configured driver universe (`DriverConfig.symbols`) or
resolvable from it," and ADR-018's prose summary lists "universe membership"
alongside timestamp/metadata as something the guard validates. **This is not
implemented.**

Reasons:

1. **No concrete, testable definition exists.** Unlike timestamp discipline and
   entry risk metadata, universe membership is not one of the checks the MM12.2
   conformance suite (`core/runtime/conformance.py`, frozen for this task)
   codifies, and the MM12.3 roadmap exit criterion (architecture §15) lists only
   "fault-injection tests prove quarantine, per-signal drop, and journal
   vocabulary" — it does not name universe membership as a required behaviour.
2. **The composition sequence gives the guard no way to check it.** The
   architecture's own composition diagram (§1, §11.1) constructs the guard as
   `GuardedSignalSource(source, journal, telemetry)` — three parameters, none
   of them `DriverConfig` or a symbol set. "Resolvable from it" additionally
   requires option-underlying resolution logic (`OptionsContractSelector`,
   `handler.py:654`) — an execution-layer concern the guard must not import
   (mirrors the conformance suite's own forbidden-import boundary).
3. **Building the missing constructor surface would be the abstraction the task
   forbids.** Adding a `symbols`/`config` parameter to reach for this check is
   exactly the kind of scope growth the task instructions rule out ("Do NOT
   introduce additional abstractions") without a concrete driving need — no
   production strategy exists yet to demonstrate one (`CLAUDE.md`: Production
   Strategy Status — greenfield).

The guard implements exactly the three checks conformance mechanically defines:
return shape, timestamp discipline, and mandatory entry risk metadata. If a
future milestone (e.g. MM12.4's reference source, or MM13's first real
strategy) demonstrates a concrete need for universe-membership enforcement at
the boundary, it should be added then, with the constructor surface and
enforcement logic co-designed against that need — not speculatively here.

### 7.2 `STRATEGY_ERROR` severity mapping

The architecture's fault matrix (§8.3) lists `STRATEGY_ERROR` at severity
"ERROR." `core/runtime/event_journal.py`'s `Severity` enum defines only
`INFO`, `WARNING`, `CRITICAL` — it has no `ERROR` level, and extending the
severity taxonomy itself was out of scope for this task (a change to a
platform-wide enum consumed by 26 importers, not a MM12.3 deliverable).
`STRATEGY_ERROR` is mapped to `Severity.WARNING` — the same severity the
platform already uses for `BROKER_ERROR`, its existing precedent for "a
survivable program fault, logged durably, that does not by itself halt the
loop." This mapping is recorded inline in `core/runtime/event_journal.py` and
tested (`test_normative_default_severities[...STRATEGY_ERROR-WARNING]`).

### 7.3 `event_journal.py` and `metrics.py` are on the frozen-components list

The user's standing instruction (this task's final message) names Telemetry and
Persistence architecture as components requiring "stop and report" before
modification. `core/runtime/event_journal.py` (the durable journal) and
`core/runtime/metrics.py` (the telemetry sink) both fall under that umbrella, and
both were modified in this task (additive enum members only — see the Files
Modified table in §1).

This is authorized, not a violation: the same CLAUDE.md frozen-components clause
carries the explicit carve-out "except where explicitly required by the MM12.3
specification," and the modification is not incidental — it is *directly named*
by the governing spec. MM12.1 architecture §8.3 states: "Three additions to
`EventType` (`core/runtime/event_journal.py`) — additive, non-breaking:
`STRATEGY_ERROR`, `STRATEGY_QUARANTINED`, `SIGNAL_CONTRACT_REJECTED`... Telemetry
counters mirror these (`RuntimeMetric` additions)." ADR-018's Consequences section
repeats the same requirement verbatim. No existing behavior of either subsystem
changed: no method signature, no existing enum member, no severity mapping for
any pre-existing event type was altered — only three new enum values were
appended to each, each with a corresponding severity/telemetry mapping.

No other deviations. `LoopDriver`, `ExecutionHandler`, the Risk/Margin
engines, persistence (storage/repositories), broker interfaces, the
`SignalEvent` contract, and the conformance suite were not modified.

---

*Ref: docs/reports/MM12_1_STRATEGY_INTEGRATION_ARCHITECTURE.md §7.3, §8, §15;
docs/ARCHITECTURE_DECISIONS.md ADR-016..019; core/runtime/guarded_signal_source.py;
tests/runtime/test_guarded_signal_source.py; core/runtime/event_journal.py;
core/runtime/metrics.py.*
