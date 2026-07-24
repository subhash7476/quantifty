# Carry — Replay Fix, Independent Review

**Verdict: ACCEPT the core fix — the defect is genuinely closed, verified on the real
`LoopDriver`. Four follow-ups, one of which should land before the parity run.**

**Date:** 2026-07-24. Reviews the calendar-driven fix to `DailyBhavcopyProvider` +
`LoopDriver`, against the defect measured in `CARRY_REPLAY_INFRA_TEST_REPORT.md`.
Re-measured independently, not read off `CARRY_REPLAY_FIX_SUMMARY.md`.

---

## 1. The fix works — measured on the real driver

Re-ran a real `LoopDriver(Mode.REPLAY)` — `ReplayClock`, real `ExecutionHandler` + `PaperBroker`,
real provider, observing hook. Tick boundaries delimited by the provider's own `advance_tick()`
(the true delimiter), 229 TRAIN-eligible symbols.

| Metric | Before fix | After fix |
|---|--:|--:|
| Ticks with non-zero within-tick spread | **1,049 / 1,173 (89.4%)** | **0 / 53 (0%)** |
| Max within-tick date spread | **1,676 days** | **0 days** |
| Tick-1 symbols >1yr ahead of hook date | **34 of 229** | **0** |
| `advance_tick()` calls by driver | n/a | **53 for 53 ticks** |
| Bars per tick | constant 229 (wrong) | **173 → 164, varying** |

The varying bar count is the positive confirmation: unlisted names are now correctly **absent**
rather than delivering their first future-dated bar early. Hook dates strictly increasing.

**Test suite: 742 passed** across `tests/runtime`, `tests/database`, `tests/msi` — broader than the
224 claimed, no regressions. The new `test_daily_bhavcopy_calendar.py` passes standalone (6.1 s).

### 1.1 A false alarm I nearly filed

My first re-measurement showed 52/53 ticks with a 5-day spread and looked like a regression. It was
**my probe's off-by-one**: I delimited ticks by the rebalance hook, which fires *after* the tick's
first bar is already recorded, so every chunk straddled a tick boundary and picked up a weekend.
Re-delimiting by `advance_tick()` gave 0/53. Recorded because the failure mode — a measurement
artifact presenting as a code defect — is the mirror image of this track's usual problem, and the
5-day (weekend-sized) magnitude was the tell.

---

## 2. Follow-ups

### 2.1 The `isinstance` guard breaks the provider abstraction — fix before the parity run

`driver.py` now does:

```python
from core.database.providers.daily_bhavcopy import DailyBhavcopyProvider
if isinstance(self._provider, DailyBhavcopyProvider):
    self._provider.advance_tick()
```

Three problems, in order of weight:

1. **It is fragile by construction, and this repo already contains the thing that breaks it.**
   `ResamplingMarketDataProvider` (`resampling_wrapper.py:14`) wraps a base provider and is a
   `MarketDataProvider`, **not** a `DailyBhavcopyProvider`. Measured: `isinstance(Wrapper(provider),
   DailyBhavcopyProvider)` → **False**. Any wrapping or decoration silently skips `advance_tick()`.
2. **The failure mode is a hang, not a crash.** If `advance_tick()` is never called, `_calendar_idx`
   stays 0, `get_next_bar` returns the same date's bars forever, and `is_data_available` stays
   `True` forever. An unbounded replay would not terminate; a `max_bars`-bounded one would silently
   replay one day repeatedly. **This is inference from the code, not observed** — I did not run an
   unbounded replay to confirm the hang.
3. **It violates "Runner is Neutral."** The driver now imports a concrete Carry-specific provider
   and branches on its type. `LoopDriver` is meant to hold no strategy- or source-specific
   knowledge (`driver.py:64`).

**Fix:** put `advance_tick()` on the `MarketDataProvider` base class as a no-op default, and have
the driver call it unconditionally. That removes the import, the branch, and the wrapper hazard in
one change, and gives every provider a defined tick boundary.

*No current call site wraps `DailyBhavcopyProvider`, so this is a latent hazard, not a live bug —
but it is cheap to close and the abstraction violation is real today.*

### 2.2 The regression test does not guard the driver change

`test_daily_bhavcopy_calendar.py` drives the provider directly (lines 50-57) and **never constructs
a `LoopDriver`**. It therefore tests the provider contract — valuable, and it does enforce the
0-spread acceptance criterion — but **delete the `isinstance` block from `driver.py` and this test
still passes.** The driver-side half of the fix is unguarded.

This is the same shape as §5.3 of the bridge doc: a test verifying a replica of the production loop
rather than the loop. Add a driver-level test that constructs a real `LoopDriver(Mode.REPLAY)` and
asserts within-tick spread 0 — roughly what my probe does.

### 2.3 `DuckDBMarketDataProvider` still has the original defect

Untouched by this fix. It retains `_indices: Dict[str, int]` with positional `get_next_bar`
(`market_data.py:58,110-121`) — the exact architecture that produced the Carry defect. Any
**multi-symbol** replay through it carries the same misalignment. Not urgent for Carry (which uses
the bhavcopy provider) and MSI is single-symbol so unaffected, but it should not be left
undocumented. Fixing 2.1 via the base class makes this provider's fix a natural follow-on.

### 2.4 Minor

- **Hardcoded `expected_trading_days = 1173`** (test line 74). Brittle — a bhavcopy re-ingest
  breaks it for a reason unrelated to alignment. Derive it: `SELECT COUNT(DISTINCT trade_date)`
  over the same window and filters.
- **Wrong cross-references** in the provider docstring: it cites
  `CARRY_REPLAY_INFRA_TEST_REPORT.md` "§4.1 for measurement and §5.1 for the regression test".
  Those sections do not exist — the measurement is **§3**, the fix and acceptance test are **§5**.
  Worth correcting since the file is governance-linked.
- The test selects symbols from `futures_bhavcopy` (all FUTSTK underlyings), whereas the parity
  path uses `carry_facts` eligible names. Both reach 1,173 trading dates so the assertion holds;
  noting it only so the difference isn't mistaken for equivalence later.

---

## 2.5 Follow-up round — verified 2026-07-24 (commit `ff2338e`, branch `infra/backtest-bootstrap`)

All four follow-ups landed and were re-verified independently, not read off
`CARRY_REPLAY_FIX_SUMMARY.md`:

| Follow-up | State | Evidence |
|---|---|---|
| 2.1 base-class `advance_tick()` | **Done** | `base.py:112` no-op default; `driver.py:698` calls it unconditionally; `grep -rn "isinstance.*DailyBhavcopy" core/` → **no matches** |
| 2.2 driver-level test | **Done** | `tests/runtime/test_driver_calendar_alignment.py` constructs a real `LoopDriver(Mode.REPLAY)` |
| 2.3 `DuckDBMarketDataProvider` | **STILL OPEN** | not in the change set; retains positional `_indices` cursors |
| 2.4 hardcoded tick count | **Done** | derived via `COUNT(DISTINCT trade_date)` (test lines 82-90) |
| 2.4 docstring cross-refs | **Done** | corrected to §3/§5 |

**Test suite: 780 passed** across `tests/runtime`, `tests/database`, `tests/msi`, `tests/portfolio`,
`tests/strategies`. No regressions.

### 2.5.1 Mutation check — the guard guards, but fails as a HANG

The new driver-level test asserts the *fixed* behavior; nothing verified it actually fails when the
fix is absent. Checked by neutering `advance_tick()` on a provider subclass — the mutation, without
editing `driver.py` — and running a real bounded `LoopDriver`:

```
bars served: 1500      distinct dates seen: 1  -> ['2016-03-31']
clock after run: 2016-03-31 15:30:00
```

**The driver replays a single date forever.** This confirms §2.1 point 2, which was previously
labelled inference — it is now observed. `is_data_available` stays `True`, so the loop never
terminates.

**Consequence for the test:** `test_driver_calendar_alignment.py` sets `max_bars=None` (line 110).
If the fix regresses, that test **hangs rather than fails** — in CI a hang blocks the pipeline until
timeout, which is worse than a red assertion. **Recommended one-line change: give the test a
`max_bars` bound.** With a bound, the regression surfaces cleanly as a tick-count assertion failure
(all bars share one date → 1 tick ≠ expected trading days). The guard is real either way; this is
about how it reports.

---

## 3. On "ready for a full TRAIN/HOLDOUT parity check"

**Alignment is necessary, not sufficient** — restating `CARRY_REPLAY_INFRA_TEST_REPORT.md` §5 so it
isn't lost. The §5 gate is that the LoopDriver replay **reproduces the research net spread**
(`parity_check.py`'s +0.0 bp). What today's fix establishes is that the replay is now *eligible* to
attempt that comparison — it feeds a coherent daily cross-section. Whether it reproduces the
research book is a separate, unrun measurement.

Sequence from here: fix 2.1 (base-class `advance_tick`) → add 2.2 (driver-level test) → run the
full TRAIN + HOLDOUT replay → compare net spread → only then is §5 closed as originally worded.
**SEALED stays sealed**; per bridge §5.2 its parity follows by construction.
