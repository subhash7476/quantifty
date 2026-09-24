# NiftyShield PAPER — Expiry Mismatch Triage (no entries on Mon/Tue sessions)

**Date:** 2026-08-17 (session window, ~13:30 IST)
**Platform commit:** `8f2d046`
**Status:** ROOT CAUSE CONFIRMED — fix recommended, not yet applied (live window running)
**Severity:** HIGH — NiftyShield cannot enter any structure on ~2 of every 5 trading days.

---

## Symptom

The 13:00 checkpoint fired correctly and today's fact landed
(`session_date=2026-08-17, checkpoint=13pm, regime=BullTrend, conf=0.602,
vix_at_checkpoint=11.41, produced_by=live@8f2d046`), the strategy emitted a
`bull_put_spread`, but **no paper trade executed**. The session journal shows:

```
13:01:21  FACT_PUBLISH_SKIPPED   live 13:00 fact not ready: no 13pm checkpoint produced   (first hook tick, pre-225-bar)
13:02:14  facts.duckdb written    BullTrend fact (second hook tick, succeeded)
13:02:15  ENTRY_SKIPPED           bull_put_spread — "missing option marks (E7-4, no synthetic fallback)"
                                   missing_legs: NIFTY25AUG2624350PE, NIFTY25AUG2624200PE
```

The entry was skipped at the pricing step: the execution handler could not find
marks for the two put legs and, under the E7-4 real-marks gate, refuses to enter
at synthetic/unknown prices.

## Root cause — expiry mismatch between the poller and the strategy

The marks feed is healthy. The failure is that the **chain poller caches a
different expiry than the strategy trades.**

| Component | Selector | Result on Mon 2026-08-17 |
|---|---|---|
| **chain_poller** (`scripts/nifty_shield_paper/chain_poller.py:496`) | `provider.get_weekly_expiry(index)` — raw nearest weekly, **no min-DTE** | **2026-08-18** (Tue, 1 DTE) |
| **nifty_shield_v1** (`strategies/nifty_shield_v1/structures.py:74`) | `nearest_expiry(today, expiry_days_min=2)` — nearest weekly **≥ 2 days out** | **2026-08-25** (Tue, 8 DTE) |

`nearest_expiry(2026-08-17, min_days=2, Nifty)`:
`target = Aug 17 + 2 = Aug 19` → roll to next Tuesday → **Aug 25**. The 18-Aug
weekly is deliberately excluded (< 2 DTE).

`get_weekly_expiry` (`core/data/options_provider.py:504`) returns the nearest
weekly ≥ today with **no** `expiry_days_min` parameter → **Aug 18**.

### Evidence from the live cache (`data/options/chain_cache.duckdb`, mtime 13:30)
- Distinct expiries cached: **only `2026-08-18`** (210 rows, one expiry).
- The requested legs `NIFTY25AUG26…` (Aug 25): **0 rows** → both legs "missing".
- The same strikes on the cached expiry *are* fully priced —
  `NIFTY18AUG2624350PE`=43.25, `NIFTY18AUG2624200PE`=11.05 — confirming it is
  purely the wrong expiry, not a cold/thin feed.

## Impact

The two selectors **agree only Wed–Fri**, when the front weekly is naturally
≥ 2 DTE. On every **Monday** (1 DTE to the Tue weekly) and every **Tuesday**
(0 DTE, rolls to next week), the poller caches an expiry the strategy will never
trade, and **every** structure entry is E7-4-skipped for missing marks. NiftyShield
is structurally unable to enter on roughly **2 of every 5 sessions**.

The canonical roll rule (`expiry_days_min=2`) is used consistently by the strategy
and the execution selector (`strategies/nifty_shield_v1/config.py:39`,
`strategies/nifty_shield_v1/structures.py:74`,
`core/execution/options/selector.py:85`). The **poller is the sole component that
ignores it** — the bug is in the ops/poller wiring, not in the strategy roll rule.

> Note: today's 13:01:21 `FACT_PUBLISH_SKIPPED` ("no 13pm checkpoint produced")
> is a *separate, benign* first-tick artifact — the hook fired once before the
> 225-bar checkpoint was complete, then fired again at 13:02 and succeeded. It is
> not part of this defect and did not block the entry.

## Recommended fix

Make the poller cache the **same expiry the strategy trades** by driving its
expiry off the shared `expiry_days_min` roll rule instead of the raw front weekly.
Two options, in order of preference:

1. **Single shared selector (preferred).** Have the poller compute its expiry with
   the min-DTE rule — reuse `nearest_expiry(today, expiry_days_min)` (or the
   `core/execution/options/selector.py` `_nearest_expiry`) so the poller and the
   strategy can never diverge. On Wed–Fri this is identical to today's behavior; on
   Mon/Tue it correctly rolls to the ≥2-DTE weekly. No downside — the poller's cache
   (`data/options/chain_cache.duckdb`) is NiftyShield-specific; the general options
   dashboard reads `options_provider` directly and is unaffected.

2. **Poll both expiries.** Cache the front weekly *and* the strategy's ≥2-DTE target
   each cycle. More robust to future strategies that trade multiple expiries, but
   doubles row volume and adds no value while NiftyShield trades exactly one expiry.

**Concrete change (option 1):** in `chain_poller.py`'s `_fetch` closure, replace

```python
expiry = provider.get_weekly_expiry(args.index)
```

with a min-DTE-aware selection using `expiry_days_min` (default 2, sourced from the
strategy config), keeping `get_weekly_expiry` only as the underlying weekly-grid
source. This aligns the cached expiry with `nearest_expiry` for all sessions.

## Verification plan (post-fix)

- **Unit:** poller expiry == `nearest_expiry(today, 2)` for a Mon/Tue/Wed fixture set
  (must return next-week on Mon/Tue, front weekly on Wed–Fri).
- **Live smoke:** on a Monday session, confirm `chain_cache.duckdb` distinct expiry
  equals the strategy's target, and a `bull_put_spread`/other structure reaches
  `ENTRY_*` (filled) rather than `ENTRY_SKIPPED: missing option marks`.
- **Regression:** confirm Wed–Fri behavior is unchanged (same front weekly cached).

## Related

- Memory: `nifty-shield-chain-cache-gap` (chain-cache/poller wiring).
- E7-4 real-marks gate (no synthetic fallback) — working as designed; it correctly
  refused to trade unpriced legs. The defect is upstream, in which expiry is cached.
