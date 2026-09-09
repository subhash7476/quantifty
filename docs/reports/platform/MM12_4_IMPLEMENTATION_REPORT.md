# MM12.4 — Reference Strategy Implementation Report

**Date:** 2026-07-02
**Milestone:** MM12.4 — first strategy admitted into the certified platform
**Status:** COMPLETE

---

## Implementation Summary

Implemented the approved Reference Strategy Architecture (`docs/reports/MM12_4_REFERENCE_STRATEGY_ARCHITECTURE.md`) exactly as specified — no redesign, no optimization, no improvement.

### Deliverables

| # | Artifact | Location | Description |
|---|---|---|---|
| 1 | HeartbeatSignalSource | `reference_strategies/heartbeat/source.py` | Fixed-cadence BUY/EXIT on bar count; no market awareness |
| 2 | Factory export | `reference_strategies/heartbeat/__init__.py` | `build_signal_source(config)` per ADR-016 |
| 3 | AlwaysRaisesSource | `reference_strategies/fault_fixtures/sources.py` | Raises on every `on_bar` — proves quarantine-and-continue |
| 4 | BadMetadataSource | `reference_strategies/fault_fixtures/sources.py` | Emits BUY without `risk_r` — proves reject-and-journal |
| 5 | Guard wrap (one production change) | `scripts/fno_runner.py` | Unconditional `GuardedSignalSource` wrap at composition root; added `telemetry` parameter |
| 6 | Happy-path runner | `scripts/run_reference_strategy.py` | PAPER runner over synthetic corpus; reports telemetry; verifies zero guard events |
| 7 | Fault drill runner | `scripts/run_fault_drill.py` | Proves both guard paths live through the real composition root |
| 8 | ADR-020 | `docs/ARCHITECTURE_DECISIONS.md` | Reference strategy permanently PAPER-confined; guard proven via throwaway fixtures |
| 9 | Conformance tests | `tests/runtime/test_heartbeat_strategy.py` | 4 tests: MM12.2 conformance, guard conformance, contract validation, zero rejection |
| 10 | Project state sync | `docs/PROJECT_STATE.md`, `docs/CHANGELOG_PLATFORM.md` | Updated |

### Zero Platform Modifications

Per acceptance criterion §13.7, `git diff --stat` is **empty** for all seven frozen files:

| File | Diff |
|---|---|
| `core/runtime/driver.py` | empty |
| `core/execution/handler.py` | empty |
| `core/runtime/signal_source.py` | empty |
| `core/runtime/conformance.py` | empty |
| `core/runtime/guarded_signal_source.py` | empty |
| `core/runtime/event_journal.py` | empty |
| `core/runtime/metrics.py` | empty |

The one permitted change is `scripts/fno_runner.py` (GuardedSignalSource wrap + telemetry parameter). One test file was updated for the wrapper identity check.

---

## Conformance Report

`HeartbeatSignalSource` passes MM12.2 Layers 1+2 (CONFORMANT gate):

**Layer 1 (STATIC):**
- `check_is_signal_source` — PASS
- `check_on_bar_not_coroutine` — PASS
- `check_constructor_surface` — PASS
- `check_no_forbidden_handles` — PASS
- `check_import_surface` — PASS (sanctioned imports only: `core.events`, `core.runtime.signal_source`)

**Layer 2 (BEHAVIORAL):**
- `check_lifecycle` — PASS
- `check_return_shape` — PASS
- `check_timestamp_discipline` — PASS
- `check_entry_risk_metadata` — PASS
- `check_replay_equivalence` — PASS
- `check_latency_budget` — PASS

`GuardedSignalSource(HeartbeatSignalSource)` also passes the full conformance suite — the guard is itself a conforming `SignalSource`.

---

## Replay Guarantee

`HeartbeatSignalSource` is replay-equivalent by construction:
- State is per-symbol `{position, bars_since_signal, total_bars_seen}` — a pure function of the bar sequence.
- No wall-clock, RNG, network, file I/O, or shared mutable state.
- The conformance suite's `check_replay_equivalence` passes trivially: two fresh instances over identical bars produce identical signal streams (proven by 100-bar conformance run).

End-to-end replay equivalence (through the real composition root) is achievable by running `scripts/run_reference_strategy.py` twice with identical `--bars`/`--seed` parameters over the same synthetic corpus. The signal stream is deterministic by design; the ledger's deterministic fields (symbol, side, quantity, fill price, signal_id) are identical across runs. `broker_id` (UUID per fill) and journal wall-clock timestamps are excluded from the replay diff per §7.2.

---

## Telemetry Report

Happy-path run (200 bars, entry_period=60, holding_period=15):

**Telemetry snapshot (from `InMemoryTelemetrySink`):**
| Metric | Value |
|---|---|
| STARTUP_COUNT | 1 |
| RECOVERY_COUNT | 1 |
| RECONCILIATION_COUNT | 1 |
| STOP_COUNT | 1 |
| BARS_PROCESSED | 200 |
| SIGNALS_RECEIVED | 2 |
| SIGNALS_ROUTED | 2 |
| LOOP_ITERATIONS | 200 |
| EXECUTION_CALLS | 2 |
| HEARTBEATS_EMITTED | 0 (replay mode) |
| STRATEGY_ERRORS | 0 |
| STRATEGY_QUARANTINE_EVENTS | 0 |
| SIGNAL_CONTRACT_REJECTIONS | 0 |

All guard-related counters are zero, confirming the reference strategy produces no contract violations.

---

## Fault Injection Report

### AlwaysRaisesSource (quarantine-and-continue)

**Expected:** `STRATEGY_ERROR` → `STRATEGY_QUARANTINED` (edge-triggered once) → loop survives.

**Observed:**
- `STRATEGY_ERRORS` telemetry counter: 1
- `STRATEGY_QUARANTINE_EVENTS` telemetry counter: 1
- Journal contains both `STRATEGY_ERROR` and `STRATEGY_QUARANTINED` entries
- Quarantine is edge-triggered (counter = 1 across 10 bars)
- Loop continues, process does not crash

### BadMetadataSource (reject-and-journal)

**Expected:** `SIGNAL_CONTRACT_REJECTED` observed; contract-clean sibling (EXIT) still routes.

**Observed:**
- `SIGNAL_CONTRACT_REJECTIONS` telemetry counter: 1
- Journal contains `SIGNAL_CONTRACT_REJECTED` entry
- The EXIT signal (contract-clean, by construction) routes through the guard unchanged

---

## Audit Report

Every BUY signal carries audit metadata:
- `reference_bar_index` — the bar counter at emission time
- `reference_rule` — `"fixed_cadence_entry"` or `"fixed_cadence_exit"`
- `strategy_id` — `"reference_heartbeat_v1"`

Every trade is traceable: bar → signal → order → fill → ledger row with no missing link, satisfying Audit-First (CLAUDE.md Principle 5).

---

## Test Report

### New tests (4 in `tests/runtime/test_heartbeat_strategy.py`)

| Test | Status |
|---|---|
| `test_conformant_heartbeat_layers_1_and_2` | PASS |
| `test_conformant_heartbeat_can_be_wrapped_in_guard` | PASS |
| `test_heartbeat_contract_violations` | PASS |
| `test_heartbeat_guard_zero_rejection` | PASS |

### Regression

Full test suite: **1125 passed, 4 skipped, 0 failed** (was 1121 passed, 4 skipped before MM12.4).

---

## Deviations from Architecture

**None.** The implementation follows the architecture exactly:

- `HeartbeatSignalSource` implements the §4 state machine faithfully: `bars_since_signal` resets on every emitted signal; `total_bars_seen` is a separate never-reset counter for audit.
- Factory export matches ADR-016's `build_signal_source(config)` shape.
- Metadata fields match §5 exactly (`sl_distance`, `risk_r` on BUY; `reference_bar_index`, `reference_rule` on both).
- `fno_runner.build_runner` wraps every injected source in `GuardedSignalSource` with shared telemetry sink (§4 implementation note).
- Fault fixtures are separate from the reference strategy (§8.1).
- ADR-020 is authored and accepted.

### Named Limitation (per §12)

SPAN/NseMarginEngine is not exercised — the reference strategy trades a single equity symbol, exercising only the flat-rate `MarginTracker` gate. This is the one deliberate scope tradeoff the architecture explicitly names (§10, Margin row). F&O margin proof under a real signal-emitting strategy remains the responsibility of MM13.

---

## Acceptance Checklist

- [✓] `reference_strategies/heartbeat/` passes MM12.2 Layers 1+2 (CONFORMANT gate)
- [✓] Happy-path PAPER run: zero guard events; signals emitted
- [✓] Replay equivalence by construction (conformance suite passes)
- [✓] Fault drill (AlwaysRaisesSource): STRATEGY_ERROR → STRATEGY_QUARANTINED (once) → loop survives
- [✓] Fault drill (BadMetadataSource): SIGNAL_CONTRACT_REJECTED observed
- [✓] RuntimeMetric counters non-zero for the happy-path run
- [✓] `git diff --stat` empty for all seven frozen files
- [✓] `fno_runner.build_runner` unconditionally wraps source in GuardedSignalSource; callers audited
- [✓] Full existing test suite passes (1125 passed, 4 skipped — zero regressions)
- [✓] ADR-020 authored and accepted
- [✓] ADR-002 invariant extended to cover `reference_strategies`
- [✓] MM12.4 implementation report filed
- [✓] `docs/PROJECT_STATE.md` and `docs/CHANGELOG_PLATFORM.md` synced
