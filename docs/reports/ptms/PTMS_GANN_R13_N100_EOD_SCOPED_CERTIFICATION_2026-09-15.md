# PTMS — Gann Stage-1: Scoped N100 EOD Substrate Certification (R-13 part 1)

**Date:** 2026-09-15T21:00:57 · **Branch:** `research/ptms-price-time-market-structure` · **Code:** `d0bec75`

**Type:** read-only scoped certification. Meta + validity predicates + corporate-action **enumeration** (event lists, not returns). No return, no cross-date price ratio, no signal, no label, no outcome linkage, no Stage-1 construct run.

**Scope:** `n100_membership` (PIT Nifty 100, 2011-03-25 → open) × `equity_bhavcopy` over 2011-03-25 → 2026-09-11. Price basis: this certificate covers the **store** (as-traded `equity_bhavcopy` and the `equity_bhavcopy_adjusted` view's factor register); the Stage-1 ruled price basis (ratio-adjusted as-of-*t*) is a construction rule of the freeze, not certified here.

**Store stamps (this run):**
- `equity_bhavcopy`: 7,158,443 rows, max trade_date **2026-09-11**
- `n100_membership`: 263 intervals; `adjustment_factors`: 1218 rows; `corporate_actions`: 11,976 rows, max ex_date 2026-09-11
- Store SHA-256 (equity): `57671a28a837c5b0…` · (n100): `0be19812766d5572…`

## Gates

| Gate | Check | Result |
|---|---|---|
| G-0 | Member-day slots in span | 383,997 |
| G-0 | Calendar-artifact slots (2012-11-11, 2016-04-19) | 201 (excluded from all joins) |
| G-JOIN | Priced member slots (EQ+BE, positive close, real sessions) | 383,795 / 383,796 |
| G-JOIN | Unpriced member-days | 1 |
| G-VAL | Null or non-positive OHLC | 0 |
| G-VAL | high < low | 0 |
| G-VAL | close outside [low, high] | 0 |
| G-VAL | open outside [low, high] | 0 |
| G-VAL | volume null or 0 | 0 |
| G-VAL | prev_close null or ≤ 0 | 0 |
| G-VAL | Duplicate EQ+BE rows per member-day | 0 |
| G-ENT | Member slots with >1 entity interval | 0 |
| G-ENT | Member slots with 0 entity intervals | 0 |
| G-CA-BS | Bonus/split events on member entities inside membership | 112 |
| G-CA-BS | …of which without an `adjustment_factors` row | 0 |
| G-CA-NR | Spin-off / scheme / demerger / amalgamation rows in store (member entities, in-membership) | 5 (store-completeness caveat below) |
| G-CA-NR | Rights-issue rows in store (same scope) | 4 |
| G-CA-NR | Factored SPECIAL_DIVIDEND events (same scope) | 0 |
| G-CAL | Rows on 2012-11-11 (Sunday, gold-ETF artifact) | 14 |
| G-CAL | Rows on 2016-04-19 (concurring-absence artifact) | 0 |
| G-AUDIT | Membership-build gates persisted in `n100_audit` | see below |

## Unpriced member-days (source-side, declared)

- **2020-04-13**: the sole case is expected to be DMART 2020-04-13 (NSE's own file carries no BE series that day) — see the feasibility audit D.3.

## Calendar artifacts (declared, not repaired)

- **2012-11-11** (Sunday): 14 gold-ETF rows only — proven a non-session. Member slots excluded.
- **2016-04-19**: 0 rows in the equity store and 0 rows in futures / index-options / stock-options stores on a day whose neighbours are full (feasibility audit D.1). Read as a market holiday **pending confirmation against NSE's official 2016 holiday list** (an operator confirmation item carried from the audit). Excluded either way.

## Corporate-action enumeration — store view (incomplete by construction)

**Caveat (feasibility audit E.4):** `corporate_actions` cannot prove absence before ~2022 (3–13 rows/year for large caps) and omits the 2023 RELIANCE→JIOFIN demerger entirely. **This enumeration is therefore a floor, not the external enumeration R-13 requires.**

### Spin-off / scheme / demerger rows inside membership (store rows only)

| Symbol | Ex-date | Purpose (store) | Source |
|---|---|---|---|
| ITC | 2025-01-06 | Spin Off  | BSE_500875 |
| SIEMENS | 2025-04-07 | Spin Off  | BSE_500550 |
| TVSMOTOR | 2025-08-25 | Scheme of Arrangement  | BSE_532343 |
| HINDUNILVR | 2025-12-05 | Spin Off  | BSE_500696 |
| VEDL | 2026-04-30 | Spin Off  | BSE_500295 |

### Rights-issue rows inside membership (store rows only)

| Symbol | Ex-date | Purpose (store) | Source |
|---|---|---|---|
| BHARTIARTL | 2021-09-27 | Right Issue of Equity Shares  | BSE_532454 |
| GRASIM | 2024-01-10 | Right Issue of Equity Shares  | BSE_500300 |
| TATACONSUM | 2024-07-26 | Right Issue of Equity Shares  | BSE_500800 |
| ADANIENT | 2025-11-17 | Right Issue of Equity Shares  | BSE_512599 |

### Factored special dividends inside membership

None.

**Known non-ratio events absent from these store queries** (carried from feasibility audit E.3): RELIANCE→JIOFIN demerger 2023; the audit's dense-era lists (ITC, SIEMENS, TVSMOTOR, TATAMOTORS/TMPV, HINDUNILVR, VEDL spin-offs; BHARTIARTL/GRASIM/TATACONSUM/ADANIENT rights; LT/COLPAL/HINDUNILVR/BAJFINANCE/CIPLA/HDFCBANK/PIDILITIND/TCS/BAJAJHLDNG/NESTLEIND special dividends) are reproduced in the audit's §E.3 and must be merged with an **authoritative external source** before any outcome read (R-13 part 2).

## Membership-build gate persistence (`n100_audit`)

Persisted: count violations, terminal extras/missings, all 23 overrides, pre-listing screen.
Not persisted (feasibility audit C.7, still open): **G1 breaks, G3 (the load-bearing MCWB gate), G5**. `n100_audit` holds 32 rows; the gate names present are: NIFTY 50_count_violations, NIFTY 50_terminal_extra, NIFTY 50_terminal_missing, NIFTY NEXT 50_count_violations, NIFTY NEXT 50_terminal_extra, NIFTY NEXT 50_terminal_missing, intervals, override, overrides, pre_listing_intervals.

## Verdict

**Scoped store-level certification: PASS on every gate run (G-0, G-JOIN, G-VAL, G-ENT, G-CA-BS).** The figures reproduce the feasibility audit's numbers on the unchanged store (7,158,443 rows, max 2026-09-11). The certificate does **not** close R-13: it covers what is certifiable from in-repo evidence today.

**Still required for R-13 (operator items):**
1. **External CA enumeration** from an authoritative source (spin-offs, schemes, rights, special dividends, for every member entity inside membership) — data work requiring operator authorization (feasibility audit L condition 3).
2. **Exclusion-window rule (freeze checklist G-7)** — length and anchoring around ex-dates, operator-owned.
3. **G1/G3/G5 persistence into `n100_audit`** — engineering change to `scripts/isd/build_n100_membership.py` + a rebuild; a store mutation, so copy-first discipline and operator sign-off apply.
4. **2016-04-19 confirmation** against NSE's official 2016 holiday list.
5. Declared dispositions for the four ±1-month membership boundaries, BE-series member-days (304) and the TATAMTRDVR share class (feasibility audit L condition 4–5), only if the eventual cadence requires them.

No outcome, return or signal was computed by this script.
