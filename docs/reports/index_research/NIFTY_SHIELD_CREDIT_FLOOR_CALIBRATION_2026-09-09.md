# NiftyShield — is the 90% credit floor calibrated?

**Date:** 2026-09-09, after the close (18:30 IST). Market shut, nothing live touched.
**Question:** today's only entry was refused at `credit 57.50 is 79% of the 72.86 reference
(floor 90%)`. Is `credit_fair_frac = 0.90` too tight?

**Answer: the floor cannot be judged from this evidence, because the reference it compares
against is priced at the wrong volatility.** Fix the reference first; only then is there a
calibration question worth asking. **This report proposes no new floor value.**

---

## 1. The sample is n=2, and both come from one structure

Across the whole PAPER window the journal holds **7** `ENTRY_SKIPPED` events, of which only
**2** are credit-gate refusals — both today, both the same `group_id`
(`4ff280ac…`), both `bull_put_spread`, 13:01:27 and 13:04:06, at 79% each.

The gate is new (added in the 2026-09-08 remediation), so the window's 9 completed
structures pre-date it and say nothing about its pass rate. **No floor value can be
defended from two observations of one structure in one session.**

## 2. The reference is priced at India VIX, flat across every leg

`strategies/nifty_shield_v1/source.py:122`:

```python
iv = (float(vix) / 100.0) if vix else float(...)
```

That single number is carried on the signal and handed to
`fair_structure_credit(legs, spot, dte, iv, rate)`
(`core/execution/options/nifty_shield_handler.py:336`), which prices **every leg** at it.
Today: VIX 11.59 → `iv = 0.1159`, applied to 6-DTE Nifty puts.

Three separate errors follow, all pushing the reference **up**:

1. **India VIX is a variance-swap-style strip, not an ATM vol.** It integrates the whole OTM
   wing, so by construction it sits above ATM implied vol. Today's ATM PE IV on the traded
   expiry was **9.83** against VIX **11.59**.
2. **It is a 30-day constant-maturity measure applied to a 6-DTE option.** With an upward
   term structure the 30-day number overstates the weekly.
3. **A flat vol misprices a vertical in one direction.** For a bull put spread the short leg
   is nearer the money (lower IV than VIX) and the long leg further OTM (higher IV than
   VIX). A flat vol therefore **overprices the short leg and underprices the long leg**, and
   credit = short − long, so both errors inflate the reference. Skew does not offset the
   bias here — it compounds it.

Measured PE surface, expiry 2026-09-15, spot 23431.5:

| Strike | −pts from spot | PE IV |
|---|--:|--:|
| 23450 (ATM) | +18 | 9.83 |
| 23350 | −82 | 10.19 |
| 23150 | −282 | 11.26 |
| 22950 | −482 | 12.54 |
| 22750 | −682 | 14.19 |

## 3. The decisive test

Five candidate bull put spreads, all from the **same** chain snapshot, priced two ways with
the repo's own `nifty_shield_pricing` module — once at VIX-as-a-flat-vol (what the gate
does), once at each leg's own market IV (what it should do):

| short/long | market credit | BS @ VIX | ratio | BS @ per-leg IV | ratio |
|---|--:|--:|--:|--:|--:|
| 23350/23050 | 52.90 | 71.51 | **0.740** | 54.20 | **0.976** |
| 23300/23000 | 43.10 | 59.12 | **0.729** | 43.48 | **0.991** |
| 23250/22950 | 34.15 | 48.10 | **0.710** | 35.28 | **0.968** |
| 23150/22850 | 21.65 | 30.31 | **0.714** | 22.39 | **0.967** |
| 23400/23100 | 65.70 | 85.18 | **0.771** | 66.67 | **0.985** |

Priced at the legs' own vols, the market pays **96.7–99.1%** of reference — comfortably
clear of the 0.90 floor. Priced at India VIX, the same spreads pay **71.0–77.1%** — nowhere
near it.

Today's live refusal at 79% sits squarely in that second band.

**The gate is not measuring whether the credit on offer is good. It is measuring the gap
between India VIX and the weekly put surface.** The floor never gets a chance to do its job,
and no value of `credit_fair_frac` above ~0.70 would ever pass a bull put spread.

The residual 2–3% shortfall under correct pricing is bid/ask plus the no-smile and
discrete-strike approximations — plausibly the thing a fair-value floor is *for*.

## 4. The docstring that let this through

`core/execution/options/nifty_shield_pricing.py:9-11`:

> Deliberately a reference price, not a valuation engine: European Black-Scholes on the
> index level, no dividend term, no smile. It is used only for a ratio against the same
> legs' marks, where a shared bias cancels.

The last clause is **wrong as applied**. A shared bias cancels only when it enters both
sides of the ratio. The marks come from the market and carry the market's vol; the
reference carries India VIX. A wrong vol *level* enters the Black-Scholes side **only**, and
scales the reference directly. "No smile" is exactly the simplification that does not cancel
for a vertical spread, because the two legs sit at different points on the surface.

## 5. Recommendation

1. **Price each leg at its own implied vol.** The chain store already carries it —
   `option_chain_snapshot.iv`, per strike and per option type, alongside the marks the gate
   already reads. This is a substitution of an input the pipeline already has, not new
   machinery.
2. **Then measure.** Collect the market/reference ratio per attempted structure over a real
   run of sessions and look at its distribution.
3. **Then set the floor**, from that distribution.
4. **Correct the docstring's cancellation claim** in the same change.
5. **Do not move `credit_fair_frac` now.** Loosening it to let today's trade through would
   fit a certified strategy parameter to a pricing defect, and would hard-code the VIX bias
   into the threshold — the classic in-session tuning the platform's guardrails exist to
   prevent.

Until (1) lands, expect the gate to refuse essentially every bull put spread. It is
currently a near-unconditional no-trade filter on that structure, not a quality gate.

## 6. Provenance

Chain snapshot `2026-09-09 15:40:00`, `data/options/chain_cache.duckdb` (read-only). Credit
figures computed with the shipped `fair_structure_credit` / `bs_price`, dte 6, rate 0.065,
spot 23431.5. Journal figures from `data/nifty_shield/journal.jsonl`. Nothing was written to
any production store and no strategy parameter was changed.

Caveat on §3: the snapshot is 15:40, whereas the two live refusals were at 13:01/13:04 with
a different spot and vol level. The table is a same-instant comparison of two pricing
methods, which is what the argument needs; it is not a reconstruction of today's specific
legs, whose strikes are not recorded in the journal metadata.

---

## 7. Fix applied — 2026-09-09, after the close

Recommendation (1) is implemented. `credit_fair_frac` was **not** touched.

| File | Change |
|---|---|
| `core/execution/options/nifty_shield_marks.py` | New **abstract** `implied_vols(symbols) -> Dict[str, float]` on `OptionMarksSource`. `ChainSnapshotMarksSource` reads `iv` from the same `MAX(snapshot_timestamp)` row as the marks and converts the feed's percent to a decimal at the one place that knows the unit. `StaticMarksSource` takes an optional `implied_vols` map. |
| `core/execution/options/nifty_shield_pricing.py` | `fair_structure_credit(legs, spot, dte_days, rate)` — **the flat `iv` parameter is gone**. Each leg carries its own `iv`; a leg with none returns `None` (gate unavailable). Docstring's "shared bias cancels" claim corrected. |
| `core/execution/options/nifty_shield_handler.py` | Reads per-leg IV from the marks source and attaches it to each leg. The ENTRY_DIAGNOSTIC now reports IV coverage (`n/m legs`). |
| `strategies/nifty_shield_v1/source.py` | Comment corrected: the signal's `iv` (India VIX) sizes sigma strike offsets **only** and is not a leg price input. |
| `scripts/nifty_shield_paper/recorder.py` | `RecordingMarksSource` forwards; `ReplayMarksSource` returns `{}` with the limitation stated. |

**No flat-vol fallback was added, deliberately.** Removing the parameter makes the
defect unrepresentable; a fallback would have reintroduced it silently on any leg the
snapshot could not price. A missing IV now routes to the existing "gate unavailable"
path — journaled as `ENTRY_DIAGNOSTIC`, never as a skip, so it cannot block an entry.

### End-to-end verification against the live chain cache

Through the production `ChainSnapshotMarksSource` and the shipped pricer:

| short/long | market credit | reference | ratio | vs 0.90 floor |
|---|--:|--:|--:|---|
| 23350/23050 | 52.90 | 54.20 | 0.976 | PASS |
| 23300/23000 | 43.10 | 43.48 | 0.991 | PASS |
| 23250/22950 | 34.15 | 35.28 | 0.968 | PASS |
| 23400/23100 | 65.70 | 66.67 | 0.985 | PASS |

Was 0.710–0.771, all refused. The floor is now reachable and the 2–3% residual is
bid/ask plus the no-smile approximation — which is what a fair-value floor should be
measuring.

### Tests

`tests/execution/test_nifty_shield_credit_gate_vol.py` — 10 tests: per-leg pricing, the
flat-vol overstatement, the floor passing only under per-leg pricing, unusable-IV →
`None` (parametrised over `None`/`0`/negative), percent→decimal conversion, NULL/zero IV
omission, and that a non-forwarding `OptionMarksSource` fails at construction.

Suites re-run green: `tests/execution/test_nifty_shield_execution.py` +
`test_nifty_shield_paper_execution.py` + `tests/nifty_shield_paper` (107 passed), and
`tests/strategies` + `tests/flask` + `test_greek_limits.py` + the new file (81 passed).

### Two things left open

1. **REPLAY no longer exercises the credit gate.** The session marks log records marks
   only, so `ReplayMarksSource.implied_vols` returns `{}` and the gate reads unavailable
   — a REPLAY can enter a structure LIVE would refuse. Stated in the code rather than
   papered over. Closing it means recording IVs alongside marks, which the strict
   call-order divergence check makes a change in its own right.
2. **A flaky test-isolation hazard, pre-existing.** On one combined run
   `test_broker_margin_entry_through_the_recording_wrapper` failed with *"Kill switch
   activated: Manual STOP file detected"*. It passes in isolation, passes on a clean tree
   at the same selection and order, and passed on re-run of the identical selection with
   these changes (107/107). `tests/nifty_shield_paper/test_phase_b_tools.py:349` writes a
   real `Path.cwd() / "STOP"` while other tests run handlers with kill-switch watchdogs —
   a genuine race, unrelated to this fix, worth its own ticket.
