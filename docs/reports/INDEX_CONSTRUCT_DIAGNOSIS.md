# Index Construct Diagnosis — why Nifty/BankNifty constructs keep dying, and the one surface that escapes

**Date:** 2026-08-02
**Status:** Findings record. No construct is authorized. No pre-registration exists. No gate has been run.
**Scope:** Why every index-level construct in this repo has failed the RFA, and what is actually available for a successor.

---

## 1. The diagnosis — it is a measurement problem, not an edge problem

Every index construct attempted here died at the same place, for the same reason:

| Construct | Metric | Verdict | Max power |
|---|---|---|---|
| O1 (Nifty VRP) | per_trade_pnl | WITHDRAWN | Sharpe 0.59 vs 0.92 needed |
| RS-MOM (Nifty-BankNifty RS) | per_trade_pnl | ABANDON | 0.337 |
| N50-LS (Nifty 50 L/S book) | per_trade_pnl | ABANDON | 0.7466 |

The common cause is arithmetic, not signal quality. For a single P&L series,
`ncp = (delta/sd)·√n = S·√T`. Cadence cancels. Computed from this repo's own
`scripts/rfa/power.py`:

| Unread window T | Annualized Sharpe needed for power 0.80 |
|---|--:|
| 3.50 yr (2023–2026) | **1.499** |
| 5.50 yr | 1.195 |
| 7.00 yr | **1.059** |
| 10.50 yr | 0.865 |

Cadence invariance re-verified: at T=3.5 yr, daily (n=882) needs Sharpe 1.499 and
weekly (n=182) needs 1.506 — identical within rounding. **Trading more often buys
no statistical power.**

**The consequence, stated plainly:** an index is one number per period, so one
period yields one observation. Nifty could carry a genuine Sharpe-0.9 timing edge
and the gate would still — correctly — return ABANDON, because 887 noisy
observations of a single series cannot separate 0.9 from 0. The wall is about
*evidence*, not about whether the edge exists.

Stocks escape via `rank_ic`: 50 names per day converts one observation into a rank
IC whose dispersion is 0.15–0.25 rather than a P&L series' unit sd, so `√n = 29.8`
does the work (CB-N50: n=887, ncp=6.95, power 1.00). **The escape was never a
better index signal. It is a genuine cross-section that lives on the index.**

## 2. Finding A — the index does have a cross-section: its option surface

`data/market_data/options_bhavcopy.duckdb`, table `option_bhavcopy`, NIFTY only,
5,490,319 rows, 2016-02-11 → 2026-07-17, 2,572 trade dates.

Median *liquid* cells per day (`contracts > 0 AND open_int > 0`):

| Year | 2016 | 2018 | 2020 | 2022 | 2024 | 2026 |
|---|--:|--:|--:|--:|--:|--:|
| Median liquid strike-expiry cells | 213 | 246 | 477 | 843 | 862 | 1108 |

18 expiries are live on a typical recent day. One price series; hundreds of
simultaneous cross-sectional units.

## 3. Finding B — a 6.9-year unread window exists and was never noticed

`OPTIONS_STRATEGY_RESEARCH.md` §5.1 (2026-07-17) recorded the store as
2023-01-02 → 2026-07-06 and listed backward extension as a prerequisite.
Commit `35b3469` ("feat: PSB-O0 — extend option bhavcopy ingestion start to
2016-02-11") did it. That commit is **a 2-line change to
`scripts/msrp/ingest_option_bhavcopy.py`** — no report, no analysis, no gate.

The only research read that has ever touched this store is
`scripts/msrp/triage_fee_impact.py`, hard-pinned at `DEV_START = "2023-01-02"`,
`DEV_END = "2025-12-31"`.

**Therefore: 2016-02-11 → 2022-12-31 — 1,701 trade dates, ~4.12M rows, ~6.89
years — is ingested and has never been read by any script or report in this
repository.** It is the largest unread confirmatory window remaining, and roughly
twice the length of the 2023–2026 window the equity tracks have been contesting.

Rows per year, confirming the span is genuinely populated and not a stub:

| Year | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 |
|---|--:|--:|--:|--:|--:|--:|--:|
| Rows | 456,062 | 527,414 | 566,450 | 770,090 | 731,639 | 510,565 | 562,041 |
| Trade dates | 218 | 248 | 246 | 244 | 250 | 247 | 248 |

## 4. Finding C — the fee wall that killed PSB-1/PSB-2 does not exist here

Per `core/execution/options/fees.py`, index-option STT is levied on **premium**,
sell side only, versus delivery equity's 0.1% of **full notional on both legs**.
Effective cost per unit of market exposure is roughly **0.2–0.5 bp versus ~20 bp** —
two orders of magnitude. The 13pp/yr STT hurdle that consumed PSB-1's C1–C4 gross
spreads is not present in this venue.

This does not make any construct viable. It removes the constraint that made
sub-monthly cash-equity constructs *structurally* non-viable.

## 5. Finding D — BankNifty options are absent by ingest filter, not by source

`scripts/msrp/ingest_option_bhavcopy.py` rejects `symbol != "NIFTY"` at lines 144
and 241, and purges non-NIFTY rows at line 504 (originally an anti-NIFTYNXT50
contamination fix). NSE F&O bhavcopy carries BANKNIFTY options across the same
span. **The second index is one filter change plus a re-ingest away.** This is
recorded as a gap, not a task — re-ingest changes the breadth arithmetic and
should be decided before, not during, any measurement.

Note the contrast: `futures_bhavcopy` *does* carry BANKNIFTY (FUTIDX, 7,746 rows,
2016-02-11 → 2026-07-31, same as NIFTY).

## 6. Finding E — the delta-hedge NO-GO was stricter than the literature requires

`MSRP_PHASE7_RESEARCH_RESET.md` §A1 killed the delta-hedged straddle: *"delta-hedging
needs intraday options prices or at minimum intraday spot… NO-GO — data does not
exist at retail scale for 2023–2026."*

Bakshi & Kapadia (RFS 2003, *Delta-Hedged Gains and the Negative Market Volatility
Risk Premium*) computes delta-hedged gains with **daily** rebalancing on end-of-day
data; Goyal & Saretto (JFE 2009) builds the cross-sectional version on the same
EOD basis. Daily-rebalanced delta-hedged option returns are a standard, published
EOD methodology.

The same RESET recorded the finding that matters most: unhedged ATM straddle
open→close return has Spearman **0.093** with actual realized vol, and −0.027
against the gated forecast. Its own conclusion was that *the instrument* was
wrong — *"an unhedged ATM straddle pays off on |Δspot|, not on Σ(r²)"* — and
delta-hedging is precisely the correction it identified and then discarded on an
over-strict data objection.

## 7. Corrections to CLAUDE.md warranted by this pass

1. **The 1d index store is far larger than documented.** CLAUDE.md describes
   `candles/1d/` as "Nifty 50, Bank Nifty, India VIX", 3,548 files from 2012-02-21.
   Actual: **4,105 files from 2010-01-04**, carrying ~50 NSE indices by 2015 and
   **~150 by 2026** (all sector, thematic, strategy and G-Sec indices). India VIX is
   present by 2015-07-09 but absent from the 2010-01-04 file; its true start date is
   unestablished.
2. **Index options span is understated.** CLAUDE.md records
   "5,490,319 rows, 2016-02-11 → 2026-07-17" correctly, but nothing anywhere records
   that 2016–2022 is *unread*. That fact is load-bearing and was nearly lost.

## 8. What is NOT claimed here

- No construct is proposed as validated. Nothing has been measured.
- The sector-index cross-section (~150 daily index series) is **not** a viable
  route: FUTIDX shows sector index futures (NIFTYIT, NIFTYINFRA, NIFTYPSE,
  NIFTYCPSE, NIFTYMID50) all ceased 2018–2020. Only NIFTY, BANKNIFTY, FINNIFTY
  (2021+), MIDCPNIFTY (2022+) and NIFTYNXT50 (2024+) are live. Trading a sector
  index means constituent baskets, which re-enters the delivery-STT wall.
- **Confirming on 2016–2022 is backward confirmation.** The 2023–2025 window is
  prior-exposed (MSRP triage found the unconditional short ATM straddle net
  +Rs 110K with fee drag ≈6%). Any feature designed now is designed with that
  knowledge. This is defensible and standard in the literature, but it is weaker
  than forward confirmation and must be stated in those words in any
  pre-registration. TS Basis Daily was lost to exactly this class of quiet
  contamination.

## 9. The open question that decides everything

A surface-cross-section construct clears the power wall **only if** the daily
cross-sectional rank IC has small enough dispersion. Option cells are far more
correlated than 50 stocks — a single vol-level move drives every cell at once, so
effective breadth may collapse toward 1.

Feasibility ladder against the 1,701 unread formations (computed from
`scripts/rfa/power.py`, two-sided, power 0.80):

| Assumed δ (mean IC) | Largest feasible sd |
|---|--:|
| 0.015 | **0.2207** |
| 0.020 | **0.2943** |
| 0.029 | **0.4267** |

**This SD must be measured on the already-burned 2023-01-02 → 2025-12-31 window
before any RFA declaration is drafted.** It costs no window purity and it is the
single number that decides whether the construct is worth designing. See
`OSC_SD_PROBE_PROMPT.md`.

**Methodological note:** only the *dispersion* may be carried forward from the
burned window. The measured IC *mean* must NOT become the δ anchor — inheriting
an effect size from a short prior-exposed read is the error that retired C2.

**Outcome (2026-08-02):** OSC was probed, diagnosed, and abandoned at the RFA
gate. The honest effect size (+0.0167 within-moneyness) was too small relative
to its own dispersion (sd_IC = 0.2502) to clear power 0.80 at n = 1,701.
The 2016-2022 window was never read. Full verdict: `OSC_RFA_ABANDON.md`.
