# MM9.1-S1 Implementation Specification
## `ExecutionConfig.max_capital_utilisation` Field Addition

**Slice:** MM9.1-S1
**Date:** 2026-06-26
**Plan authority:** `docs/reports/MM9_IMPLEMENTATION_PLAN.md §4 MM9.1-S1`
**Scope:** Single field addition to `ExecutionConfig` dataclass. No behavioural change. No other files touched.

---

## 1. Repository Impact Review

### File modified

`core/execution/handler.py` — one line added inside the `ExecutionConfig` dataclass at lines 68–84.

### Change surface

The `ExecutionConfig` dataclass is a `@dataclass(frozen=False)` — a plain Python dataclass with keyword-argument construction. Adding a new field with a default value is a backwards-compatible operation under the following condition: **no caller passes `ExecutionConfig` arguments positionally**. All callers verified below (§2). The condition is met.

### What does not change

- `ExecutionConfig.__init__` signature for all existing parameters — unchanged
- All existing field names, types, and defaults — unchanged
- `ExecutionHandler` behaviour — unchanged (the new field is not read anywhere until MM9.1-S2)
- `ExecutionMetrics` — unchanged
- `RiskManager` — unchanged
- `MarginTracker` — unchanged
- All tests — pass unchanged (verified in §5)

### Dataclass field ordering constraint

Python dataclasses require that fields with defaults come after fields without defaults. All existing `ExecutionConfig` fields already carry defaults. The new field carries a default (`0.80`). Appending it at the end of the dataclass is safe and is the conventional position for milestone-tagged additions.

---

## 2. Existing Call-Site Audit

Every `ExecutionConfig(...)` instantiation in the repository. Verified by grep (`ExecutionConfig\(`).

| Location | Instantiation form | Safe after addition? |
|---|---|---|
| `core/execution/handler.py:145` | `config or ExecutionConfig()` | Yes — no-arg |
| `scripts/fno_runner.py:175` | `ExecutionConfig(mode=execution_mode)` | Yes — keyword-only |
| `tests/g1/test_g1_closure_guard.py:119` | `ExecutionConfig()` | Yes — no-arg |
| `tests/execution/test_g1_characterization.py:91` | `ExecutionConfig()` | Yes — no-arg |
| `tests/execution/test_g1_restore_canonicalization.py:64` | `ExecutionConfig()` | Yes — no-arg |
| `tests/execution/test_g1_restore_characterization.py:90` | `ExecutionConfig()` | Yes — no-arg |
| `tests/execution/test_signalsource_exit_boundary.py:38` | `ExecutionConfig()` | Yes — no-arg |
| `tests/execution/test_signalsource_consumer_contract.py:50` | `config or ExecutionConfig()` | Yes — no-arg |
| `tests/execution/test_signalsource_consumer_contract.py:107` | `ExecutionConfig(max_position_size=1000.0)` | Yes — keyword-only |
| `tests/execution/test_signalsource_consumer_contract.py:118` | `ExecutionConfig(default_quantity=100.0)` | Yes — keyword-only |
| `tests/execution/test_mm8_acceptance.py:40` | `ExecutionConfig(mode=ExecutionMode.PAPER, ...)` | Yes — keyword-only |
| `tests/execution/test_handler_journal_injection.py:36` | `ExecutionConfig()` | Yes — no-arg |
| `tests/execution/test_handler_broker_unavailable_error.py:48` | `ExecutionConfig(mode=ExecutionMode.PAPER, ...)` | Yes — keyword-only |
| `tests/execution/test_handler_broker_unavailable_error.py:79` | `ExecutionConfig()` | Yes — no-arg |
| `tests/execution/test_handler_broker_unavailable_error.py:83` | `ExecutionConfig(broker_error_threshold=5)` | Yes — keyword-only |
| `tests/execution/test_handler_broker_auth_error.py:45` | `ExecutionConfig(mode=ExecutionMode.PAPER)` | Yes — keyword-only |
| `tests/execution/test_g1_wave4b_position_characterization.py:65` | `ExecutionConfig()` | Yes — no-arg |
| `tests/execution/test_g1_wave4a1_option_characterization.py:89` | `ExecutionConfig()` | Yes — no-arg |
| `tests/execution/test_g1_restore_order_canonicalization.py:67` | `ExecutionConfig()` | Yes — no-arg |
| `tests/runtime/test_synthetic_wiring_proof.py:136` | `ExecutionConfig(mode=ExecutionMode.PAPER, default_quantity=100.0, max_position_size=1000.0)` | Yes — keyword-only |

**Conclusion:** No positional argument instantiation exists anywhere in the codebase. All call sites are safe. Zero call sites require modification.

---

## 3. TDD Plan

### Test file

`tests/execution/test_handler_broker_unavailable_error.py` is the established precedent — it contains two `ExecutionConfig` field tests at lines 78–84 following the pattern:

```
def test_execution_config_<field>_defaults_to_<value>():
    assert ExecutionConfig().<field> == <value>

def test_execution_config_<field>_is_configurable():
    cfg = ExecutionConfig(<field>=<custom>)
    assert cfg.<field> == <custom>
```

### Target test file

New tests belong in `tests/execution/test_mm9_1_margin_gate.py` (the MM9.1 test file specified in MM9.1-S4). If that file does not yet exist, create it as part of S1. It will receive additional tests in S2, S3, and S4 without modification to the S1 tests.

### Tests required for MM9.1-S1

**Test 1 — Default value**

```
test_execution_config_max_capital_utilisation_defaults_to_0_80
```

- Arrange: `ExecutionConfig()` with no arguments
- Assert: `config.max_capital_utilisation == 0.80`
- Why: the default is the operative gate threshold for all deployments that do not configure it; a wrong default silently changes gate behaviour in MM9.1-S3

**Test 2 — Custom value accepted**

```
test_execution_config_max_capital_utilisation_is_configurable
```

- Arrange: `ExecutionConfig(max_capital_utilisation=0.5)`
- Assert: `config.max_capital_utilisation == 0.5`
- Why: confirms the field participates in normal dataclass construction and is not frozen or overridden

**Test 3 — Existing fields unaffected**

```
test_execution_config_existing_fields_unaffected_by_s1
```

- Arrange: `ExecutionConfig()`
- Assert: `config.broker_error_threshold == 3` and `config.max_drawdown_limit == 0.05`
- Why: regression guard confirming the field addition did not displace or shadow an existing field

**Test 4 — Type is float**

```
test_execution_config_max_capital_utilisation_type_is_float
```

- Arrange: `ExecutionConfig()`
- Assert: `isinstance(config.max_capital_utilisation, float)` is `True`
- Why: the gate formula in S2 uses this value in arithmetic; the type annotation is a contract for static analysis

### TDD sequence

Write all four tests first. Run against unmodified codebase — all four fail with `AttributeError: 'ExecutionConfig' object has no attribute 'max_capital_utilisation'`. Add the field. All four pass. No other tests change state.

---

## 4. Exact Implementation Diff

**File:** `core/execution/handler.py`
**Location:** End of `ExecutionConfig` dataclass body, after line 83 (`broker_error_threshold: int = 3`)

```diff
     # MM8.2A: consecutive BrokerUnavailableError threshold before kill switch
     broker_error_threshold: int = 3
+    # MM9.1: capital-utilisation limit for margin gate (single-symbol estimate — see MM9.1-S3)
+    max_capital_utilisation: float = 0.80
```

**Total lines changed:** 2 (one comment line, one field line)
**Total files changed:** 1

No other changes. The comment records the milestone tag and the MM9.1 scope limitation so a future reader understands why the default is what it is and that a more accurate gate (MM9.2) supersedes the single-symbol approximation.

---

## 5. Risk Review

| Risk | Severity | Assessment |
|---|---|---|
| Positional argument breakage | None | All 20 call sites use no-arg or keyword-arg construction. No positional callers exist. |
| Default value is wrong | Low | 0.80 is specified in MM9.0 (D2), MM9_IMPLEMENTATION_PLAN.md §4 MM9.1-S1, and MM9.1 pre-implementation validation §J.6. It is deliberately conservative. |
| Field shadows an existing field | None | All existing field names are distinct from `max_capital_utilisation`. Zero occurrences of this name exist in the codebase prior to this change. |
| Field is read before S2 is merged | None | The field has a valid default. If S2 never ships, the field is inert — no code reads it yet. |
| Dataclass field ordering violation | None | All existing fields carry defaults. Appending a defaulted field is valid. |
| Float precision | None | 0.80 is representable exactly in IEEE-754 double precision. No rounding artefact. |
| `frozen=True` conflict | None | `ExecutionConfig` is not frozen. Field addition is valid. |
| Static analysis / mypy breakage | None | `max_capital_utilisation: float = 0.80` is a well-typed field. Existing type-check passes are unaffected. |

---

## 6. Acceptance Checklist

```
MM9.1-S1 acceptance — field addition

[ ] Field `max_capital_utilisation: float = 0.80` present in `ExecutionConfig` dataclass
[ ] Field is the last entry in the dataclass body
[ ] Inline comment present: records MM9.1 milestone tag and single-symbol scope limitation
[ ] `ExecutionConfig().max_capital_utilisation == 0.80` — confirmed by test
[ ] `ExecutionConfig(max_capital_utilisation=0.5).max_capital_utilisation == 0.5` — confirmed by test
[ ] `isinstance(ExecutionConfig().max_capital_utilisation, float)` is True — confirmed by test
[ ] Existing fields unaffected: `broker_error_threshold == 3`, `max_drawdown_limit == 0.05` — confirmed by test
[ ] All 569 pre-existing tests pass unchanged
[ ] No other file modified
[ ] `tests/execution/test_mm9_1_margin_gate.py` exists with S1 tests (4 tests, all green)
[ ] MM9.1-S2 dependency met: field readable via `self.config.max_capital_utilisation`
```

**Definition of Done:** All checklist items ticked.
**Commit message:** `MM9.1-S1 — ExecutionConfig.max_capital_utilisation field (default 0.80)`
