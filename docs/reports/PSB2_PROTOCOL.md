# PSB-2 Screening Protocol

**Document type:** Pre-registered screening protocol (Phase 0 deliverable)

**Status:** DRAFT Rev 1 (2026-07-14) — authored by DeepSeek V4. Because the author is the implementer, the two-party discipline requires an **independent review by Claude (Lead Reviewer)** before the operator ratifies. On ratification this document is stamped **FROZEN** and §9 immutability applies.

**Governing record:** `docs/reports/PSB2_PHASE0_RESEARCH_RECORD.md` (operator decisions D8–D10, RATIFIED 2026-07-14). Roles: DeepSeek V4 implements; Claude writes prompts and reviews; the operator decides.

**Predecessor protocol:** `docs/reports/PSB1_PROTOCOL.md` Rev 2 (FROZEN). PSB-2 reuses its structure — §4 common scoring rules, §6 metrics, §7 power projection, §8 selection rule, §9 immutability, §10 determinism — with only the §3 cadence rule and §5 candidate definitions changing. The substrate, harness, and fee model are inherited without modification.

---

## §1 Scope and prohibitions

PSB-2 is an **explicitly exploratory** screening battery over five declared candidate constructs, run entirely on development data. Its sole output is a ranked selection report that either recommends **at most one** candidate for promotion to a full CSMP-grade pre-registration (a new program), or recommends none.

**Prohibited under this protocol:**

- **Any load of price, delivery, volume, or universe data with `trade_date` or `rebalance_date` ≥ 2023-01-01.** Every loader asserts and prints its observed `MAX(trade_date)` (the dev fence, CSMP-style). Sole exception: §7's sealed-grid count reads **dates only** from `trading_calendar` (no prices, no symbols' data).
- Any formula, parameter, window, or metric change after any candidate result exists (§9).
- Any sealed read, consumer, or strategy code. Nothing lands in `core/strategies/`.
- Any new data ingestion (operator decision D4, carried from PSB-1).
- **Any weekly or higher-frequency construct** (D10 — monthly cadence only).
- Momentum-family constructs on a CSMP-sealed read: the one prior CSMP momentum read (42 monthly observations, December 2022 cutoff) is disclosed as prior exposure per PSB-1 operator decision D2. The successor pre-registration may apply an explicit α penalty. **No momentum candidate in this battery may read the sealed window for its own selection.**

## §2 Data substrate (pinned)

| Item | Pin |
|---|---|
| Store | `data/market_data/equity_bhavcopy.duckdb`, opened `read_only=True` |
| Adjusted view | `equity_bhavcopy_adjusted` — **certified** by the four-arm contract suite (`scripts/psb1/contract_arms.py`): 0 view-induced fabrications, 7,030,920 rows |
| Prices | `equity_bhavcopy_adjusted` (entity-grain, time-aware via `symbol_entity_intervals`): `trade_date`, `symbol`, `close`, `open`, `deliv_pct` |
| Delivery | `deliv_pct` from `equity_bhavcopy_adjusted` — a **ratio**, invariant to split/bonus share-count changes. Non-NULL span: 2020-01-01 onward (SECFULL era). NULLs inside the span handled by §5 completeness rules. |
| Universe | `universe_membership` (`rebalance_date`, `symbol`, `rank`) — the gate-(c) point-in-time NIFTY-200. Membership at formation date *t* = the row set of the **most recent `rebalance_date` ≤ t**. |
| Entity resolution | `symbol_entity_intervals` — time-aware, half-open `[valid_from, valid_to)`, covers every `(symbol, trade_date)` exactly once. |
| Calendar | `trading_calendar`, full-session days defined as `n_symbols >= 200` (the CSMP convention). |
| Fees | `core.execution.equity.delivery_fees.delivery_equity_fees(side, trade_value, trade_date).total` (gate-d, era-accurate, 6 rate schedules). |
| Slippage | κ = **5 bp per side** on traded notional (the CSMP B3 convention). |
| Harness lineage | PSB-1 Phase 1 `screening_harness.py` — loader, grids, scoring, metrics, power, AC₁/NW. Adapted for the five new §5 formulas. |
| Contract arms | `scripts/psb1/contract_arms.py` — four-arm suite: intra-symbol CA-shape (Arm A), cross-symbol handoff (Arm B), prev_close identity (Arm C), factor evidence (Arm D). Run before any candidate score touches real data; must return 0 undocumented violations. |

## §3 Time conventions

- **Grid:** **monthly only** — last full-session trading day of each calendar month per `trading_calendar` (D10). Formations at monthly grid dates, rebalanced on that grid.
- **Dev window:** all candidates on **2012-01-01 → 2022-12-31**. Candidates using `deliv_pct` (C2, C3) additionally report on their respective delivery-data subset (post-2020-04).
- Formation *inputs* (trailing windows) may reach back before the dev window start (the store begins 2010-01-04); nothing may reach past 2022-12-31.
- **Common robustness sub-window:** all five candidates are additionally reported on **2020-04-01 → 2022-12-31**.

## §4 Common scoring rules

Same as PSB-1 Protocol §4 — carried forward without change.

## §5 Candidate definitions (exact; no free parameters remain)

All five constructs operate at **monthly cadence** (D10). Each is fee-survivable by construction: turnover ≤ 0.17 (i.e., ≥6-month effective holding period, staggered 1/6th rebalancing, or banded exit at ≤ 0.30 band).

### C1 — Low-volatility, tighter band

```
σ_i(t) = std of daily close-to-close returns over the 252 trading days ending t   (≥ 200 obs)
s_i(t) = − σ_i(t)
```

Rebalancing: same as C5 in PSB-1 — banded exit. A name enters the top-quintile portfolio when in the top quintile by score and exits only when it falls out of the **top 35%** (0.35 exit band, tighter than PSB-1 C5's 0.40). IC uses no banding.

### C2 — Delivery-percentage anomaly, monthly

```
dp_i(t) = mean of deliv_pct over month's whole trading days ending t     (≥ 15 non-NULL)
μ_i, σ_i = mean, std of deliv_pct over 252 trading days ending t−21     (≥ 150 non-NULL, σ_i > 0)
s_i(t) = ( dp_i(t) − μ_i ) / σ_i
```

Hypothesis (pre-registered direction): abnormally high delivery predicts positive relative returns. The monthly window gives the signal time to express; PSB-1's weekly C3 showed +0.025 mean IC with +17.5% gross spread — a real signal killed by weekly rebalance fees. Banded exit (0.40). Delivery-data window: 2020-04-01 → 2022-12-31 (~34 monthly formations).

### C3 — Delivery-conditioned reversal, monthly

Let `p_i(t)` = cross-sectional percentile rank of the C2 score `s^{C2}_i(t)` among names scored at *t* (0 = most abnormally low delivery, 1 = most abnormally high). Let `r_i(t)` = the trailing 1-month return (close at grid day *t* divided by close at previous grid day, minus 1).

```
s_i(t) = − r_i(t) × ( 1 − 2·p_i(t) )
```

Formation-complete requires both the C2 score (delivery z) and the 1-month return present. Hypothesis: low-delivery monthly moves are noise and revert; high-delivery moves are informed and persist. The monthly cadence tests whether the interaction (null at weekly in PSB-1 C4, mean IC −0.003) resolves at a slower frequency. Banded exit (0.40). Delivery-data window: 2020-04-01 → 2022-12-31.

### C4 — Momentum, long-only, staggered 6-month holding

```
r_{12,i}(t) = trailing 12-month return (close at grid day *t* divided by close at grid day *t-12*, minus 1)
r_{1,i}(t)   = trailing 1-month return (skip most recent month)
s_i(t)     = r_{12,i}(t) − r_{1,i}(t)
```

Hypothesis (pre-registered direction): past 12-month winners (excluding the most recent month, to strip the short-term reversal effect) continue to outperform. Long-only (top-quintile portfolio). **Staggered holding:** the portfolio is split into 6 equal tranches; each month, 1/6th is rebalanced to the current top quintile. A name held in any tranche remains held until its tranche's next rebalance date, regardless of rank drift. Turnover ~0.17 (1/6th of the portfolio per month) → fee drag ~2.5pp/yr. Requires 12 grid dates of history.

**Momentum-fence disclosure (D2/D8):** CSMP's sealed read of a monthly momentum construct (42 observations, mean IC +0.0279) is disclosed as prior exposure. The successor pre-registration may apply an α penalty. No sealed data is read here.

### C5 — Quality-at-reasonable-price (QARP)

```
roe_i(t)  = trailing 4-quarter net income / average equity (or, if unavailable, trailing annual ROE)
s_i(t) = rank of ( roe_i(t) / σ_i(t) ) among the NIFTY-200 at t
```

where `σ_i(t)` is the 252-day trailing return volatility per C1. Hypothesis: high-quality names (high ROE per unit of risk) earn higher risk-adjusted relative returns. Turnover should be ~0.10 or lower (the quality composition is sticky); banded exit at 0.35. Requires both `roe_i(t)` and `σ_i(t)` present.

## §6 Metrics

Same as PSB-1 Protocol §6 — carried forward without change.

## §7 Power projection

Same as PSB-1 Protocol §7 — carried forward without change. `n*` = number of monthly grid dates in 2023-01-01 → 2026-06-30 (≈ 42). Hurdle: ≥ 0.80.

## §8 Selection rule

Same as PSB-1 Protocol §8 — carried forward without change. Eligible candidates ranked by projected sealed power; evidence floor at Bonferroni-deflated p < 0.05 (m = 5). At most one winner. "No winner recommended" is a valid outcome.

## §9 Multiplicity ledger and immutability

- Exactly **five** candidates: C1–C5 as defined in §5. No additions, variants, or parameter sweeps.
- After any candidate result exists, its definition is immutable.
- Pinned parameters (exhaustive): monthly grid only (§3); 252-day vol window with ≥ 200 obs; 252-day delivery baseline ending t−21 with ≥ 150 non-NULL; 1-month delivery mean with ≥ 15 non-NULL; C1 exit band 0.35; C2/C3 exit band 0.40; C4 staggered 6 tranches, 1/6th per month; C5 exit band 0.35; quintile portfolios, EW; κ = 5 bp/side; fee model as in §2; percentile ranks with average ties; Bonferroni m = 5; power hurdle 0.80 at α = 0.05 one-sided; delisting imputation = date's worst realized forward return among scored names (§4.2); AC₁ robustness trigger 0.1 with Newey–West lag 4; power tie band 0.02.

## §10 Determinism, audit, and reporting

Same as PSB-1 Protocol §10 — carried forward without change.

## §11 Sequencing and stop rules

1. **Phase 0 gate:** the substrate must pass the four-arm contract suite (`certify_substrate.py` Arm A–D) with **0 undocumented violations** before any candidate score touches real data. This is a structural gate — no Phase 1 without a certified substrate.
2. **Phase 1 gate:** the adapted screening harness must pass a synthetic-data dev-proof and Lead Review **before** any real candidate runs.
3. **Run order:** C1 → C2 → C3 → C4 → C5, one report per candidate, committed as produced.
4. **Stop rules:** all PSB-1 §11 stop rules carry forward.

## §12 What this protocol does not authorize

Same as PSB-1 Protocol §12 — carried forward. Additionally: no momentum-family sealed read; the one prior CSMP momentum read is disclosed as prior exposure per D2/D8.

## §13 Next steps after this document

1. Independent review of this protocol by **Claude (Lead Reviewer)**.
2. Operator ratification → status stamped **FROZEN**.
3. Prompt 1 (Phase 1 harness adaptation + synthetic dev-proof) issued to DeepSeek V4.
