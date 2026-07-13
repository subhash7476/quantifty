# PSB-1 Screening Protocol

**Document type:** Pre-registered screening protocol (Phase 0 deliverable)

**Status:** DRAFT Rev 1 (2026-07-13) — authored by Claude (Lead Reviewer). Because the
author is the reviewer, the two-party discipline requires an **independent review by
DeepSeek V4** (the CSMP Phase 2 pattern) before the operator ratifies. On ratification
this document is stamped **FROZEN** and §9 immutability applies.

**Governing record:** `docs/reports/PSB1_PHASE0_RESEARCH_RECORD.md` (operator decisions
D1–D4, LOCKED 2026-07-13). Roles: DeepSeek V4 implements; Claude writes prompts and
reviews; the operator decides.

---

## §1 Scope and prohibitions

PSB-1 is an **explicitly exploratory** screening battery over five declared candidate
constructs, run entirely on development data. Its sole output is a ranked selection
report that either recommends **at most one** candidate for promotion to a full
CSMP-grade pre-registration (a new program), or recommends none.

Prohibited under this protocol:

- **Any load of price, delivery, volume, or universe data with `trade_date` or
  `rebalance_date` ≥ 2023-01-01.** Every loader asserts and prints its observed
  `MAX(trade_date)` (the dev fence, CSMP-style). Sole exception: §7's sealed-grid
  count reads **dates only** from `trading_calendar` (no prices, no symbols' data).
- Any formula, parameter, window, or metric change after any candidate result exists
  (§9).
- Any sealed read, consumer, or strategy code. Nothing lands in `core/strategies/`.
- Any new data ingestion (operator decision D4).
- Momentum-family constructs (CSMP closure fence).

## §2 Data substrate (pinned)

| Item | Pin |
|---|---|
| Store | `data/market_data/equity_bhavcopy.duckdb`, opened `read_only=True` |
| Prices | `equity_bhavcopy_adjusted` (gate-b corporate-action-adjusted): `trade_date`, `symbol`, `close`, `deliv_pct` |
| Delivery | `deliv_pct` from `equity_bhavcopy_adjusted` — a **ratio**, invariant to split/bonus share-count changes. `deliv_qty` is **not used** (share-count adjusted nowhere; using it would be a known corruption). Non-NULL span: 2020-01-01 onward (SECFULL era); NULLs inside the span (e.g., BE rows) handled by §5 completeness rules. |
| Universe | `universe_membership` (`rebalance_date`, `symbol`, `rank`) joined to `universe_eligibility` for `entity` — the gate-(c) point-in-time NIFTY-200. Membership at formation date *t* = the row set of the **most recent `rebalance_date` ≤ t**. |
| Calendar | `trading_calendar`, full-session days defined as `n_symbols >= 200` (the CSMP convention). |
| Fees | `core.execution.equity.delivery_fees.delivery_equity_fees(side, trade_value, trade_date).total` (gate-d, era-accurate). |
| Slippage | κ = **5 bp per side** on traded notional (the CSMP B3 convention). |
| Loader lineage | Phase 1 harness derives from `run_a2_validation.load_window()` at commit `0ae1dc4` (price load restricted to ever-member entities — the Prompt-13 memory fix), re-fenced to the dev cutoff. |

## §3 Time conventions

- **Weekly grid** (C1–C4): for each ISO week, the **last full-session trading day** of
  that week per `trading_calendar`. Formation at the close of grid day *t*; forward
  return = `adj_close(t → t')` where *t'* is the next grid day. Portfolios are formed
  at the close of *t* (the CSMP §5.2 convention — kept for comparability; the successor
  pre-registration may pin an execution lag).
- **Monthly grid** (C5): last full-session trading day of each calendar month (the
  CSMP grid).
- **Dev windows (formation dates):**
  - C1, C2, C5: **2012-01-01 → 2022-12-31** (~572 weekly / 132 monthly formations).
  - C3, C4: **2020-04-01 → 2022-12-31** (~143 weekly formations; delivery data begins
    2020-01-01 and the §5 baselines need ~3 months of run-up).
  - Formation *inputs* (trailing windows) may reach back before the dev window start
    (the store begins 2010-01-04); nothing may reach past 2022-12-31.
- **Common robustness sub-window:** all five candidates are additionally reported on
  **2020-04-01 → 2022-12-31** (§8).

## §4 Common scoring rules

1. **Formation-complete rule (CSMP-inherited):** a name is scored at *t* only if every
   input its candidate requires (§5) is present. Unscored names cannot enter portfolios;
   the excluded count is reported per formation date.
2. **Forward-return availability:** a scored name with no price at *t'* (delisting,
   suspension) is excluded from that date's IC and portfolios; the count is reported.
   Exit returns are not synthesized — this is a recorded limitation, mitigated by the
   point-in-time universe keeping delisted names in the panel until exit.
3. **Direction convention:** every score in §5 is oriented so that the candidate's
   hypothesis predicts **positive** rank IC.
4. **Notation:** `P_i(t)` = adjusted close of name *i* at trading day *t*;
   `r_i(a,b) = P_i(b)/P_i(a) − 1`; `t−k` counts **trading days**; `w` indexes weekly
   grid dates; ranks are fractional percentile ranks in `[0,1]` with average-tie
   handling, computed over that date's scored names only.

## §5 Candidate definitions (exact; no free parameters remain)

### C1 — Short-term reversal (weekly, dev 2012–2022)

```
s_i(t) = − r_i(t−5, t)
```

Requires `P_i(t−5)` and `P_i(t)`. Hypothesis: last week's cross-sectional losers
outperform winners over the next week.

### C2 — Residual reversal (weekly, dev 2012–2022)

Market return: `r_mkt(w)` = equal-weighted mean of `r_i(w−5, w)` over names that are
universe members at *w* with both prices present.

Per name at formation date *t*: OLS regression `r_i = α_i + β_i·r_mkt + ε` fitted on
the **52 weekly grid returns ending at the grid date immediately preceding t**
(formation week excluded; require ≥ 40 of 52 weeks with both name and market
returns). Then:

```
resid_i(t) = r_i(t−5, t) − α_i − β_i · r_mkt(t−5, t)
s_i(t)     = − resid_i(t) / σ_i(ε)
```

where `σ_i(ε)` is the regression's residual standard deviation (require `σ_i(ε) > 0`).
Hypothesis: the market-stripped component of last week's move reverts, with lower
turnover than C1.

### C3 — Delivery-percentage anomaly (weekly, dev 2020-04→2022)

```
dp_i(t)  = mean of deliv_pct over the 5 trading days ending t        (≥ 3 non-NULL)
μ_i, σ_i = mean, std of deliv_pct over the 60 trading days ending t−5 (≥ 40 non-NULL, σ_i > 0)
s_i(t)   = ( dp_i(t) − μ_i ) / σ_i
```

Hypothesis (pre-registered direction): **abnormally high** delivery — real
position-taking vs the name's own recent norm — predicts positive relative returns
(informed accumulation). Spearman rank IC makes winsorization unnecessary.

### C4 — Delivery-conditioned reversal (weekly, dev 2020-04→2022)

Let `p_i(t)` = cross-sectional percentile rank of the C3 score `s^{C3}_i(t)` among
names scored at *t* (0 = most abnormally low delivery, 1 = most abnormally high).

```
s_i(t) = − r_i(t−5, t) × ( 1 − 2·p_i(t) )
```

Formation-complete requires both C1 and C3 completeness. Hypothesis: low-delivery
moves are noise and revert (weight → +1 · reversal); high-delivery moves are informed
and persist (weight → −1, i.e., continuation). This is the interaction bet — it is
**not** a momentum construct: its persistence leg conditions on the delivery field,
not on trailing return alone, and its formation window is one week.

### C5 — Low-volatility (monthly, dev 2012–2022)

```
σ_i(t) = std of daily close-to-close returns over the 252 trading days ending t   (≥ 200 obs)
s_i(t) = − σ_i(t)
```

Hypothesis: low-volatility names earn higher risk-adjusted (and, per the anomaly,
raw) relative returns. Net-spread portfolio uses **banded rebalancing**: a name enters
the top-quintile portfolio when in the top quintile and exits only when it falls out
of the **top two** quintiles; IC uses no banding.

## §6 Metrics

**Primary (the selection statistic's input):** per formation date,
`IC_t` = Spearman rank correlation between `s_i(t)` and forward return `r_i(t, t')`
over scored names with forward returns. Report the series mean, SD, n, one-sided
t-statistic and p-value (H₁: mean IC > 0).

**Secondary (eligibility qualifier):** annualized **net top-quintile spread** — the
equal-weighted top-quintile portfolio (by score, rebalanced on the candidate's grid,
C5 banded), minus the formation-complete equal-weighted universe baseline, **net of
gate-(d) fees on turnover-derived traded notional + κ = 5 bp/side slippage** (the
CSMP Δ_net construction, quintile instead of top-40).

**Reported, non-gating:** gross spread; fee + slippage drag (bp/yr); one-way turnover
per rebalance; long-short (Q1−Q5) spread; first-half / second-half sub-period ICs;
per-date exclusion counts (§4).

## §7 Power projection (the hurdle — operator decision D3 made structural)

For each candidate:

1. `n*` = number of grid dates in **2023-01-01 → 2026-06-30** at the candidate's
   cadence, computed **exactly** from `trading_calendar` (dates only — the §1
   exception; ≈ 182 weekly, 42 monthly).
2. Projected power = `P( T ≥ t_{0.95, n*−1} )` where `T` is noncentral-t with
   noncentrality `δ / (SD_dev / √n*)`, `δ` = the candidate's **dev mean IC** and
   `SD_dev` = its dev IC standard deviation. This is the same calculation that,
   applied to CSMP after the fact, yielded the ~41% that killed it — now run **before**
   promotion, per candidate.
3. **Hurdle: projected power ≥ 0.80.** A candidate below the hurdle is **dropped by
   rule**, whatever its dev IC. Power at `δ/2` is also reported (information only,
   never gating).

The `δ = dev point estimate` assumption is the pre-registered one; CSMP's sealed read
landing on top of its dev estimate is the recorded precedent for its reasonableness.

## §8 Selection rule (at most one winner)

**Eligibility** — a candidate is eligible iff, on its declared dev window:
(i) mean IC > 0; (ii) annualized net top-quintile spread > 0; (iii) §7 power ≥ 0.80.

**Selection statistic:** the one-sided t-statistic of mean IC, with **Bonferroni
deflation at m = 5** (deflated p = min(1, 5·p)). The winner is the eligible candidate
with the smallest deflated p. A recommendation for promotion additionally requires
**deflated p < 0.05**; otherwise the battery reports **"no winner recommended."**

**Tie-break** (|Δt| < 0.1 between the top two): higher net spread wins.

**Unequal dev windows (recorded honestly):** C3/C4 are scored on 2020-04→2022; the
others on 2012→2022. The selection statistic runs on each candidate's declared window.
All five are *also* reported on the common sub-window 2020-04→2022 (§3). **If the
winner by deflated p differs between the declared-window and common-sub-window
rankings, both rankings are presented and the operator decides** — the discrepancy is
flagged, never silently resolved.

**Bonferroni is pinned now, not after results.** With m = 5 it is conservative but
computable by hand, immune to correlation-structure assumptions the candidates would
violate (C1/C2/C4 are correlated by construction), and it cannot be argued with after
the fact.

## §9 Multiplicity ledger and immutability

- Exactly **five** candidates: C1–C5 as defined in §5. The ledger admits no additions,
  variants, or parameter sweeps under this protocol.
- After any candidate result exists, its definition is immutable. A candidate whose
  formula "needs fixing" after results is **dead for this increment**; the fix may
  re-enter only as a new candidate in a future battery (PSB-2) with a fresh ledger.
- Pinned parameters (exhaustive): 5-day formation return; 52-week beta window with
  ≥ 40-week completeness, formation week excluded; 5-day delivery mean with ≥ 3
  non-NULL; 60-day delivery baseline ending t−5 with ≥ 40 non-NULL; 252-day vol window
  with ≥ 200 obs; quintile portfolios, EW; C5 two-quintile exit band; κ = 5 bp/side;
  weekly/monthly grids per §3; percentile ranks with average ties; Bonferroni m = 5;
  power hurdle 0.80 at α = 0.05 one-sided.

## §10 Determinism, audit, and reporting

- Every script is deterministic and re-runnable to **byte-identical** output. No RNG
  is required by this protocol; if any resampling is ever added by amendment, its seed
  is pinned to **20260713**.
- Every data load asserts and prints the dev fence (`MAX(trade_date) ≤ 2022-12-31`).
- All reports are **script-generated** (the CSMP discipline — no hand-edited numbers):
  one `docs/reports/PSB1_C{1..5}_REPORT.md` per candidate and one
  `docs/reports/PSB1_SELECTION_REPORT.md`, each stamped with the code commit and the
  store's row count + max trade_date at run time.
- Failures are reported as failures (the 43%-coverage lesson stands).

## §11 Sequencing and stop rules

1. **Phase 1 gate:** the screening harness must pass a synthetic-data dev-proof
   (planted signal recovered; null signal yields |mean IC| consistent with 0; fee
   model invoked with era-correct dates) and Lead Review **before** any real candidate
   runs.
2. **Run order:** C1 → C2 → C3 → C4 → C5, one report per candidate, committed as
   produced. Results of earlier candidates cannot alter later definitions (§9 makes
   this structural, the ordering makes any attempt visible in git history).
3. **Stop rule — data integrity:** any formation window surfacing an unexplained
   > |20%| single-day move (outside the gate-b documented set) halts the battery for a
   gate-(b)-style triage before any further candidate runs.
4. **Stop rule — protocol breach:** any fence assertion failure or detected formula
   deviation voids the affected candidate's report; the candidate is re-run only if
   the deviation was mechanical (wrong constant vs pinned) and the fix restores the
   pinned definition.

## §12 What this protocol does not authorize

No sealed read — the 2023-01→2026-06 window stays untouched (PSB-1 only earns the
right to propose spending it). No consumer, no strategy code, no new ingestion, no
tuning. The winner, if any, is a **recommendation** — promotion happens only through a
new, full pre-registration program ratified by the operator, which will pin its own
execution conventions, α, and sealed-read mechanics, disclosing the one prior CSMP
momentum read as prior exposure per operator decision D2.

## §13 Next steps after this document

1. Independent review of this protocol by **DeepSeek V4** (CSMP Phase 2 pattern —
   the author cannot be the only reviewer). Claude drafts the review prompt.
2. Operator ratification → status stamped **FROZEN**.
3. Claude writes Prompt 1 (Phase 1 screening harness + synthetic dev-proof) for
   DeepSeek V4.
