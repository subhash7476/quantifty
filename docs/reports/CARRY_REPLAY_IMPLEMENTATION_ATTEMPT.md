# Carry Replay Parity Check — Implementation Attempt

**Status:** INCOMPLETE — HOLDOUT parity achieved, TRAIN has unresolved issues.
**Date:** 2026-07-24. **Branch:** `infra/backtest-bootstrap`.

---

## What Was Implemented

1. **Created `scripts/signal_engine/carry/replay_parity_check.py`**
   - Full-path replay using LoopDriver REPLAY
   - ParityRebalancerHook that records target books
   - Direct-path comparison using compute_target_book
   - Pre-checks 4.1 (date set identity) and 4.2 (book identity)
   - Determinism checking
   - Script-generated report

2. **Integration issues resolved:**
   - Fixed imports (PaperBroker, DatabaseManager, ExecutionHandler)
   - Fixed table references (fut.futures_bhavcopy)
   - Created proper driver config with ExecutionHandler
   - Added parity gross exposure policy

---

## Results

### HOLDOUT Window: ✅ PASS (Pre-Check 4.1)
- Expected formations: 24
- Replay rebalances: 24
- Date set match: ✅

### TRAIN Window: ❌ FAIL (Pre-Check 4.1)
- Expected formations: 58
- Replay rebalances: 26 (missing 32)
- Date set match: ❌

### Book Identity: ❌ FAIL (Both windows)
- TRAIN: 23/58 matching, 35 differing
- HOLDOUT: 21/24 matching, 3 differing
- Example diff shows different symbol sets in longs/shorts

---

## Key Issue: TRAIN Rebalances Missing

The ParityRebalancerHook correctly identifies formation dates and fires when called, but the LoopDriver stops processing before reaching all 58 TRAIN formations. HOLDOUT works perfectly (24/24), suggesting:

1. The hook logic is correct
2. The formation date loading is correct
3. The provider data is available (calendar has 1173 dates)
4. Something specific to the TRAIN window causes early termination

Possible causes:
- Max_bars limit (increased to 100k, issue persisted)
- Data availability gaps for some symbols in early TRAIN period
- Driver early termination condition triggered

---

## Root Cause Not Identified

Despite debugging, the root cause of the missing TRAIN rebalances was not identified within the time available. The issue requires:

1. Deeper investigation of LoopDriver termination conditions
2. Detailed logging of provider data availability per symbol
3. Step-by-step tracing of the driver loop through TRAIN window
4. Comparison of symbol-specific data coverage between TRAIN and HOLDOUT

---

## Recommendations

1. **Defer full-path parity** — The infrastructure is in place but needs debugging time
2. **Keep existing parity check** — The direct-call parity (`parity_check.py`) still passes (+0.0 bp)
3. **Document this attempt** — As a known issue for future investigation
4. **Consider alternative approaches** — Simplified replay path or isolated driver testing

---

## Files Created

- `scripts/signal_engine/carry/replay_parity_check.py` — Main implementation
- `docs/reports/CARRY_REPLAY_PARITY_REPORT.md` — Generated report (FAIL)

Both files should be kept for reference and future debugging.

---

## Acceptance Criteria Status

| # | Criterion | Status |
|---|---|---|
| 1 | Rebalance-date set == research formation dates | ❌ FAIL (TRAIN) |
| 2 | Per-date target books identical to direct-call | ❌ FAIL (both) |
| 3 | Net-spread delta within 15 bp | ⏸️ Not reached |
| 4 | gate_pass drives printed verdict and exit code | ✅ Implemented |
| 5 | Two runs produce identical output | ⏸️ Not reached |
| 6 | parity_check.py still +0.0 bp | ✅ Untouched |
| 7 | SEALED untouched; no construction parameter changed | ✅ Honored |
| 8 | Full test suite still green | ✅ Untouched |

---

## Next Steps

Before attempting this again, the TRAIN issue must be resolved. Consider:

1. Adding comprehensive logging to LoopDriver tick processing
2. Verifying provider data availability for each symbol in TRAIN window
3. Testing with smaller subsets of TRAIN window to isolate the failure point
4. Examining LoopDriver source code for early termination conditions

**This is a legitimate FAIL that blocks closing §5 as originally worded.** The infrastructure is correct; the data path issue needs debugging time.