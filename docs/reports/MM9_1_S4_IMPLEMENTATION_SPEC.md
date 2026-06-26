# MM9.1-S4 Implementation Specification

## Scope Clarification — Renumbering

`MM9_IMPLEMENTATION_PLAN.md §4` labels this slice **S5** ("fno_runner.py initial_capital propagation") and labels S4 as "test suite." The test suite was delivered inside S3 (20 tests, `test_mm9_1_margin_gate.py`, 578→598 passing). Therefore: **plan's S4 is already done; this spec covers plan's S5, renumbered S4.** This is a flaw in the original plan, not an implementation risk. If S5 labeling is preferred, redirect before implementation begins.

---

## 1. Repository Audit

### 1.1 Files Requiring Change

| File | Line(s) | Change |
|------|---------|--------|
| `scripts/fno_runner.py` | 78 (`build_runner` def), 171–181 (`handler_kwargs`) | Add `initial_capital` to signature; add to `handler_kwargs` |
| `tests/scripts/_runner_harness.py` | 118 (`build` def), 128 (`build_runner(...)` call) | Add `initial_capital` to `build()`; thread into `build_runner` call |

### 1.2 Files Requiring New Tests

| File | Existing Tests | New Tests |
|------|---------------|-----------|
| `tests/scripts/test_fno_runner_composition.py` | 5 (composition wiring, none for `initial_capital`) | 2 (custom capital propagates; default preserved) |

### 1.3 Files Requiring No Change

- `core/execution/handler.py` — `ExecutionHandler.__init__` already accepts `initial_capital: float = 100000.0` (line 132); `ExecutionMetrics` uses it correctly at construction (lines 183–185). No change required.
- `core/execution/config.py` / `ExecutionConfig` — `max_capital_utilisation` field added in S1. No change required.
- `tests/execution/test_mm9_1_margin_gate.py` — All S4 tests from the original plan already present (delivered with S3). No change required.

### 1.4 Callers of `build_runner` — Complete Enumeration

Production callers: **none.** `fno_runner.py` has no `if __name__ == "__main__":` block and exposes `build_runner` as a library function requiring an injected `SignalSource`. No external caller provides one today. Closing I.H.2 is an **API boundary fix** — it makes the plumbing correct without creating a new live code path.

Test callers:
- `tests/scripts/_runner_harness.py:128` — the main seam (must be updated)
- `tests/scripts/test_fno_runner_refusal.py:28,37,46` — direct calls testing rejection; pass only required args, do not need `initial_capital`
- `tests/scripts/test_fno_runner_credential_validation.py:68,90,111` — direct calls testing credential rejection; same pattern

Refusal and credential callers do not exercise the handler construction path (they raise before `handler_kwargs` is assembled) — they do not need `initial_capital` added.

### 1.5 Hidden Couplings

**`ExecutionMetrics.max_equity`**: Set at construction as `max_equity=initial_capital`. The drawdown calculation uses `max_equity` as the denominator. If `initial_capital` is wrong, the drawdown percentage is also wrong. This confirms why the fix matters beyond the gate.

**`_replay_state()`**: Called on `load_db_state=True` at construction. Replays fills into `PositionTracker` and `OrderTracker` but does NOT update `metrics.cash_balance` or `metrics.max_equity`. After restart, `cash_balance` resets to the constructor-supplied `initial_capital` regardless of PnL. This is I.H.1, deferred to MM9.2-S4. S4 does not change this behaviour — it ensures the reset value is operator-configured rather than hardcoded.

### 1.6 ADR / Constitution Impacts

- **ADR-MM7E-1 (Design B)**: `build_runner` accepts `SignalSource` by injection; does not construct one. S4 adds `initial_capital` as an additional optional constructor argument — consistent with Design B, no violation.
- **Platform Constitution §3 (Execution Owns Reality)**: `initial_capital` is an execution configuration input. Passing it through the composition root into `ExecutionHandler` is correct layering.
- **No new ADR required.** This is a parameter threading change, not an architectural decision.

### 1.7 Replay / Recovery Implications

Recovery restart resets `cash_balance` to the constructor `initial_capital` value. After S4, the reset value will be whatever the caller passes — operator-configured rather than hardcoded. This is the correct behaviour for a construction-time denominator. The limitation (I.H.1: no live PnL update) is unchanged and documented.

---

## 2. Behaviour Analysis

### 2.1 Current Behaviour (Before S4)

`build_runner()` does not accept `initial_capital`. The `handler_kwargs` dict does not include `initial_capital`. `ExecutionHandler.__init__` receives no `initial_capital` argument and therefore initialises `ExecutionMetrics` with `cash_balance=100_000.0` (the hardcoded default).

**Consequence**: The capital-utilisation gate (`_check_margin_budget`) computes:

```
utilisation = (used_margin + incremental_est) / 100_000.0
```

regardless of the operator's actual configured capital. An operator running ₹10,00,000 gets a gate 10× more restrictive than intended. An operator running ₹50,000 gets a gate 2× too permissive. **This is I.H.2 (HIGH risk), flagged in `PROJECT_STATE.md`.**

### 2.2 Desired Behaviour (After S4)

`build_runner(initial_capital=500_000.0)` propagates `initial_capital` through `handler_kwargs` to `ExecutionHandler`, which initialises `cash_balance=500_000.0`. The gate computes utilisation against the operator's actual capital.

**No change to gate logic, formula, bypass rules, or rejection behaviour.** The gate arithmetic is unchanged — only the denominator is now correct.

### 2.3 Denominator Semantics

`cash_balance` is a **construction-time scalar**, not a live-updated balance. It represents the operator's declared capital allocation for this runner instance. After S4:
- Correct at session start (operator-configured rather than hardcoded default)
- Stale during session (no PnL update — I.H.1, MM9.2-S4)
- Resets on restart to the configured value (not persisted across restarts — I.H.1)

S4 deliberately preserves this semantics. PnL tracking is not in scope.

### 2.4 Edge Cases

| Case | Behaviour |
|------|-----------|
| `initial_capital` not supplied | Defaults to `100_000.0` — identical to current behaviour; backward-compatible |
| `initial_capital=0.0` | `cash_balance=0.0`; `_check_margin_budget` returns `(True, 0.0)` immediately via early-exit guard (`if self.metrics.cash_balance <= 0`); gate is disabled. No crash. |
| `initial_capital` negative | Same as zero case — guard fires. Misconfiguration; no validation required at this layer. |
| Very large `initial_capital` | Gate becomes very permissive; no overflow risk (Python float). |

### 2.5 Failure Modes

None introduced. `initial_capital` is a scalar float. There are no new code paths, no new I/O, no new network calls, no new state transitions.

### 2.6 Determinism Review

Fully deterministic. `initial_capital` is a construction-time constant. The gate formula has no stochastic components. Backtest runs are unaffected (they use `_build_handler()` directly, not `build_runner`).

---

## 3. Implementation Plan

### 3.1 Slice A — `build_runner` Signature and `handler_kwargs` (1 file, 2 hunks)

**File**: `scripts/fno_runner.py`

**Hunk 1 — `build_runner` signature**: Add `initial_capital: float = 100_000.0` as a keyword-only parameter. Insert after the last existing keyword parameter (before the closing `)` of the `def build_runner(` block at line 78). The current signature uses a `*` separator — all parameters are keyword-only.

**Hunk 2 — `handler_kwargs` dict** (lines 171–181): Add `initial_capital=initial_capital` as a new key alongside `db_manager`, `clock`, `broker`, `config`, `load_db_state`.

After the change, `handler_kwargs` contains:
```python
handler_kwargs: Dict[str, Any] = dict(
    db_manager=db_manager,
    clock=clock,
    broker=order_broker,
    config=ExecutionConfig(mode=execution_mode),
    load_db_state=True,
    initial_capital=initial_capital,     # new
)
```

**Verification**: No import changes required. `ExecutionHandler` already accepts `initial_capital`.

### 3.2 Slice B — `_runner_harness.build()` (1 file, 2 hunks)

**File**: `tests/scripts/_runner_harness.py`

**Hunk 1 — `build()` signature** (line 118): Add `initial_capital: float = 100_000.0` parameter. Default preserves all existing callers without change.

**Hunk 2 — `build_runner(...)` call** (line 128): Thread `initial_capital=initial_capital` into the `fno_runner.build_runner(...)` call.

**Verification**: All 5 existing composition tests continue to pass without modification (they call `build(tmp_path, monkeypatch, ...)` without `initial_capital`; default applies).

### 3.3 Slice C — New Tests (1 file, 2 test functions)

**File**: `tests/scripts/test_fno_runner_composition.py`

**Test 1 — Custom capital propagates**:
- Name: `test_initial_capital_propagates_to_execution_metrics`
- Call: `d = build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,), initial_capital=500_000.0)`
- Assert: `d._execution.metrics.cash_balance == 500_000.0`
- Assert: `d._execution.metrics.max_equity == 500_000.0`
- Rationale: Directly verifies I.H.2 is resolved — gate denominator is operator-configured.

**Test 2 — Default capital preserved**:
- Name: `test_initial_capital_default_is_100k`
- Call: `d = build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,))`
- Assert: `d._execution.metrics.cash_balance == 100_000.0`
- Rationale: Guards against the default being silently changed; confirms backward compatibility.

**Import note**: `EQUITY` and `build` are already imported at the top of the file. No new imports required.

### 3.4 Acceptance Criteria

| ID | Criterion |
|----|-----------|
| AC1 | `build_runner(initial_capital=500_000.0)` sets `handler.metrics.cash_balance == 500_000.0` |
| AC2 | `build_runner()` (no arg) sets `handler.metrics.cash_balance == 100_000.0` — default unchanged |
| AC3 | All 5 existing `test_fno_runner_composition.py` tests pass without modification |
| AC4 | All existing `test_fno_runner_refusal.py` and `test_fno_runner_credential_validation.py` tests pass |
| AC5 | All 20 S3 margin gate tests in `test_mm9_1_margin_gate.py` continue to pass |
| AC6 | Full test suite passes: 600/600 (598 + 2 new tests) |
| AC7 | `PROJECT_STATE.md` updated: S3 and S4 entries correct |
| AC8 | `CHANGELOG_PLATFORM.md` has S3 and S4 entries under correct dates |
| AC9 | `DRIVER_SPECIFICATION.md` has a "Margin Gate" section |
| AC10 | `MM9_IMPLEMENTATION_PLAN.md §9` has S3 and S4 ticked |

### 3.5 Definition of Done

- All AC1–AC10 satisfied
- `git push` to `origin/main` with commit message documenting S4
- No TODO, FIXME, or placeholder left in changed files
- No `initial_capital` wiring added to refusal/credential test files (they don't reach handler construction)

---

## 4. Testing Plan

### 4.1 Characterization Baseline (Before Any Changes)

Confirm these pass before touching code:
- `test_fno_runner_composition.py` — 5 tests pass
- `test_fno_runner_refusal.py` — all tests pass
- `test_fno_runner_credential_validation.py` — all tests pass
- `test_mm9_1_margin_gate.py` — 24 tests pass (4 S1 + 20 S3)
- Full suite: 598/598

If any test in this baseline fails before changes begin, stop and investigate.

### 4.2 New Tests (Slice C)

Both tests call through `build()` → `build_runner()` → `ExecutionHandler(initial_capital=...)` → `ExecutionMetrics`. They test the full parameter threading path as a composition integration test.

- `test_initial_capital_propagates_to_execution_metrics`: Positive case — custom value propagates.
- `test_initial_capital_default_is_100k`: Negative case — default preserved when arg omitted.

These two tests are the complete test requirement for S4. No unit-level mocking of `initial_capital` is required — the value is a plain scalar, not a collaborator.

### 4.3 Regression Risks

| ID | Risk | Likelihood | Mitigation |
|----|------|-----------|------------|
| R1 | Refusal tests broken by signature change | Low | Refusal paths raise before `handler_kwargs` is assembled; optional param with default has no effect |
| R2 | Harness tests broken by `build()` signature change | None | All callers omit `initial_capital`; default is backward-compatible |
| R3 | `max_equity` discrepancy | Low | Test 1 asserts both `cash_balance` and `max_equity`; both set from same argument in handler.py lines 183–185 |
| R4 | S3 gate tests broken | None | `test_mm9_1_margin_gate.py` uses `_build_handler()` directly, never calls `build_runner` |

### 4.4 Acceptance Gate

Run full test suite after Slices A–C. Expected: 600/600. If count is not 598+2, investigate before proceeding to Slice D (documentation).

---

## 5. Documentation Impact

### 5.1 `docs/PROJECT_STATE.md` — S3 Correction + S4 Entry

**S3 correction** (overdue — KB sync from S3): The MM9 "In Progress" section currently reads "S2 complete, Margin Check status remains MISSING." Update to show:

```
  - [✓] MM9.1-S1 — ExecutionConfig.max_capital_utilisation field — COMPLETE
  - [✓] MM9.1-S2 — _estimate_required_margin helper — COMPLETE
  - [✓] MM9.1-S3 — _check_margin_budget gate implementation + full test suite (578→598) — COMPLETE
  - [ ] MM9.1-S4 — fno_runner.py initial_capital propagation — IN PROGRESS
```

Remove or promote the "I.H.2 (HIGH risk)" entry: resolved at API boundary in S4.

**S4 entry** (add after S4 ships):
```
  - [✓] MM9.1-S4 — fno_runner.build_runner initial_capital propagation (598→600) — COMPLETE
       Closes I.H.2. Gate denominator is now operator-configured. Live effect awaits F&O entry script.
```

Update risk note: "I.H.2 resolved at API boundary. I.H.1 (static denominator, no PnL update) remains, deferred to MM9.2."

### 5.2 `docs/CHANGELOG_PLATFORM.md` — Two New Entries

**S3 entry** (overdue — insert under S3 commit date, commit 7f5dd5f):

```
## 2026-06-[date] — MM9.1-S3 — Capital-utilisation gate implementation (578→598 passing)
`_check_margin_budget(order, current_price) → tuple[bool, float]` wired into `ExecutionHandler.process_signal`
before `order_tracker.add_order()`. Gate fires on ENTRY signals only (EXIT bypass — D8). Rejection increments
`rejected_trades`, returns `None` (recoverable, no kill switch — D4). C1 fix: uses `canonical_instrument.multiplier`.
C2 fix: gate fires before order registration. C3 limitation: single-symbol denominator only (documented in L1 test).
+20 tests (test_mm9_1_margin_gate.py).
*Ref: core/execution/handler.py; tests/execution/test_mm9_1_margin_gate.py; docs/reports/MM9_1_S3_IMPLEMENTATION_SPEC.md.*
```

**S4 entry** (add when S4 ships):

```
## 2026-06-[date] — MM9.1-S4 — fno_runner initial_capital propagation (598→600 passing)
`build_runner()` now accepts `initial_capital: float = 100_000.0`. Closes I.H.2: gate denominator is
operator-configured rather than hardcoded ₹1,00,000. No production caller exists yet — effect is at the API
boundary (BUILT, not WIRED). `_runner_harness.build()` updated in parallel. +2 tests (test_fno_runner_composition.py).
*Ref: scripts/fno_runner.py; tests/scripts/_runner_harness.py; tests/scripts/test_fno_runner_composition.py;
docs/reports/MM9_1_S4_IMPLEMENTATION_SPEC.md.*
```

### 5.3 `docs/DRIVER_SPECIFICATION.md` — Margin Gate Section

Current doc has no "Margin Gate" section (confirmed by grep — `cash_balance` appears only in heartbeat context at line 364 and metrics context at line 393). Add a new section after the ExecutionMetrics section, before Recovery:

```markdown
## Margin Gate (MM9.1)

The execution handler applies a pre-trade capital-utilisation check before registering any ENTRY order.

**Method**: `ExecutionHandler._check_margin_budget(order, current_price) → tuple[bool, float]`

**Formula**:
  utilisation = (used_margin + incremental_est) / cash_balance
  approved = utilisation ≤ config.max_capital_utilisation

**Gate placement**: Fires AFTER order normalisation and current-price fetch, BEFORE `order_tracker.add_order()`.
Rejection returns `None` and increments `metrics.rejected_trades`. EXIT signals bypass the gate unconditionally.

**Denominator** (`cash_balance`): Construction-time scalar set from `ExecutionHandler(initial_capital=...)`.
Propagated through `build_runner(initial_capital=...)`. Does not update with PnL during the session (I.H.1,
deferred to MM9.2). Resets to configured value on restart.

**Limitation (C3)**: `get_used_margin()` is called with a single-symbol price dict. Open positions in other
symbols contribute zero to the used-margin estimate. Known limitation, documented in test
`test_multi_symbol_blindness_documented`.

**Configuration**: `ExecutionConfig.max_capital_utilisation` (default 0.80).
```

### 5.4 `docs/reports/MM9_IMPLEMENTATION_PLAN.md` — §9 Checklist

Update the completion checklist in §9:

```
[✓] S1 — ExecutionConfig.max_capital_utilisation
[✓] S2 — _estimate_required_margin helper
[✓] S3 — _check_margin_budget gate + full test suite (plan's S4 test suite delivered inside S3)
[✓] S4 — fno_runner.build_runner initial_capital propagation (plan's S5, renumbered)
[ ] MM9.2 — Live PnL tracking (I.H.1 resolution)
```

Add inline note: "Plan's S4 (test suite) was delivered bundled with S3 on commit 7f5dd5f. Remaining S5 renumbered S4."

---

## 6. Implementation Order for GLM

Execute in this order. Each slice must pass its verification gate before the next begins.

1. **Slice A** — Edit `scripts/fno_runner.py`: add `initial_capital` parameter; add to `handler_kwargs`.
2. **Slice B** — Edit `tests/scripts/_runner_harness.py`: add `initial_capital` to `build()`; thread to `build_runner()`.
3. **Slice C** — Add 2 tests to `tests/scripts/test_fno_runner_composition.py`.
4. **Run test suite** — Expect 600/600. If not, investigate before documentation.
5. **Slice D** — Update 4 documentation files: `PROJECT_STATE.md`, `CHANGELOG_PLATFORM.md`, `DRIVER_SPECIFICATION.md`, `MM9_IMPLEMENTATION_PLAN.md §9`.
6. **Commit** — Message: `MM9.1-S4 — fno_runner initial_capital propagation; close I.H.2 at API boundary (598→600)`
7. **Push** to `origin/main`.

---

## 7. Readiness Verdict

**READY FOR IMPLEMENTATION.**

All required information is present. No architectural decisions remain for GLM to make. The change is ~4 lines of production code, ~6 lines of test harness, and 2 test functions. No new imports, no new collaborators, no new failure paths. The only risk is mechanical (forgetting one of the two hunks in fno_runner.py or the harness) — mitigated by the 600/600 gate after Slice C.
