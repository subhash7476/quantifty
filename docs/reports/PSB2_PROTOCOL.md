# PSB-2 Screening Protocol

**Document type:** Pre-registered screening protocol (Phase 0 deliverable)

**Status:** DRAFT Rev 4 (2026-07-16) — incorporating Lead Review findings F1–F11 (`PSB2_PROTOCOL_INDEPENDENT_REVIEW.md`), operator decisions D11/D12 (`PSB2_PHASE0_RESEARCH_RECORD.md`), and Prompt 0R/0R2 fixes R1–R6/S1–S3 (`PSB2_IMPLEMENTATION_PROMPTS.md`). Authored by DeepSeek V4. NOT FROZEN — pending operator ratification.

**Governing record:** `docs/reports/PSB2_PHASE0_RESEARCH_RECORD.md` (operator decisions D8–D12, RATIFIED 2026-07-16). Roles: DeepSeek V4 implements; Claude writes prompts and reviews; the operator decides.

**Predecessor protocol:** `docs/reports/PSB1_PROTOCOL.md` Rev 2 (FROZEN). PSB-2 reuses its structure — §4 common scoring rules, §6 metrics, §7 power projection, §8 selection rule, §9 immutability, §10 determinism — with only the §3 cadence rule and §5 candidate definitions changing. The substrate, harness, and fee model are inherited without modification.

---

## §1 Scope and prohibitions

PSB-2 is an **explicitly exploratory** screening battery over three declared candidate constructs, run entirely on development data. Its sole output is a ranked selection report that either recommends **at most one** candidate for promotion to a full CSMP-grade pre-registration (a new program), or recommends none.

**Prohibited under this protocol:**

- **Any load of price, delivery, volume, or universe data with `trade_date` or `rebalance_date` ≥ 2023-01-01.** Every loader asserts and prints its observed `MAX(trade_date)` (the dev fence, CSMP-style). Sole exception: §7's sealed-grid count reads **dates only** from `trading_calendar` (no prices, no symbols' data).
- Any formula, parameter, window, or metric change after any candidate result exists (§9).
- Any sealed read, consumer, or strategy code. Nothing lands in `core/strategies/`.
- Any new data ingestion (operator decision D4, carried from PSB-1).
- **Any weekly construct** (D10 — fortnightly or slower).
- Momentum-family constructs on a CSMP-sealed read: the one prior CSMP momentum read (42 monthly observations, December 2022 cutoff) is disclosed as prior exposure per PSB-1 operator decision D2. The successor pre-registration may apply an explicit α penalty. **No momentum candidate in this battery may read the sealed window for its own selection.**

## §2 Data substrate (pinned)

| Item | Pin |
|---|---|
| Store | `data/market_data/equity_bhavcopy.duckdb`, opened `read_only=True` |
| Adjusted view | `equity_bhavcopy_adjusted` — **certified** by the four-arm contract suite (`scripts/psb1/contract_arms.py`): 0 view-induced fabrications, 7,030,920 rows |
| Prices | `equity_bhavcopy_adjusted` (entity-grain, time-aware via `symbol_entity_intervals`): `trade_date`, `symbol`, `close`, `deliv_pct` |
| Delivery | `deliv_pct` from `equity_bhavcopy_adjusted` — a **ratio**, invariant to split/bonus share-count changes. Non-NULL span: 2020-01-01 onward (SECFULL era). NULLs inside the span handled by §5 completeness rules. |
| Universe | `universe_membership` (`rebalance_date`, `symbol`, `rank`) joined to `universe_eligibility` for `entity` — the gate-(c) point-in-time NIFTY-200. Membership at formation date *t* = the row set of the **most recent `rebalance_date` ≤ t**. |
| Entity resolution | `symbol_entity_intervals` — time-aware, half-open `[valid_from, valid_to)`, covers every `(symbol, trade_date)` exactly once. |
| Calendar | `trading_calendar`, full-session days defined as `n_symbols >= 200` (the CSMP convention). |
| Fees | `core.execution.equity.delivery_fees.delivery_equity_fees(side, trade_value, trade_date).total` (gate-d, era-accurate, 6 rate schedules). |
| Slippage | κ = **5 bp per side** on traded notional (the CSMP B3 convention). |
| Harness lineage | PSB-1 Phase 1 `screening_harness.py` — loader, grids, scoring, metrics, power, AC₁/NW. Adapted for the three new §5 formulas. |
| Contract arms | `scripts/psb1/contract_arms.py` — four-arm suite: intra-symbol CA-shape (Arm A), cross-symbol handoff (Arm B), prev_close identity (Arm C), factor evidence (Arm D). Run before any candidate score touches real data; must return 0 undocumented violations. |

## §3 Time conventions

- **Fortnightly grid:** for each calendar month, the **last full session on or before the 15th** and the **last full-session trading day** per `trading_calendar`. Formation at the close of grid day *t*; forward return = `adj_close(t → t')` where *t'* is the next grid day (~15 days). Portfolios formed at the close of *t* (the CSMP §5.2 convention).
- **Monthly grid:** last full-session trading day of each calendar month (the CSMP grid, carried from PSB-1).
- **Cadence per candidate:**
  - C2 (delivery z-score): **fortnightly** (delivery signals have sufficient dispersion at higher frequency; banded exit at 0.40 keeps turnover ~0.15 → fee drag ~78 bp/yr — survivable).
  - C3 (delivery-conditioned reversal): **fortnightly** (same rationale as C2; delivery signals benefit from the denser grid for the interaction term's formation count).
  - C4 (momentum staggered): **monthly** rebalance, 6-month hold (the staggered 1/6th-per-month design is monthly by construction).
- **Dev windows (formation dates):**
  - C2, C3: **2020-09-04 → 2022-12-31** (56 fortnightly grid dates — script-derived from `trading_calendar` at the `n_symbols >= 200` full-session convention via `scripts/psb2/count_grid_dates.py`). Delivery data begins 2020-01-01; the 252-day baseline ending *t*−21 with ≥ 150 non-NULL `deliv_pct` pushes the earliest feasible formation to 2020-09-04. Realized per-name n will be lower.
  - C4: **2012-01-01 → 2022-12-31** (132 monthly grid dates).
- Formation *inputs* (trailing windows) may reach back before the dev window start (the store begins 2010-01-04); nothing may reach past 2022-12-31.
- **Common robustness sub-window:** all candidates are additionally reported on **2020-09-04 → 2022-12-31** (§8). For C2/C3 this is their entire declared window; for C4 it supplies a common-horizon robustness column (28 monthly grid dates).

## §4 Common scoring rules

Same as PSB-1 Protocol §4 — carried forward without change.

## §5 Candidate definitions (exact; no free parameters remain)

Three constructs, fee-survivable by construction. Cadence per §3: C2 and C3 run fortnightly (n\* = 84); C4 runs monthly rebalance with 6-month staggered hold (n\* = 42).

### C2 — Delivery-percentage anomaly, fortnightly

```
dp_i(t) = mean of deliv_pct over fortnight's whole trading days ending t     (≥ 8 non-NULL)
μ_i, σ_i = mean, std of deliv_pct over 252 trading days ending t−21          (≥ 150 non-NULL, σ_i > 0)
s_i(t)   = ( dp_i(t) − μ_i ) / σ_i
```

Hypothesis (pre-registered direction): abnormally high delivery predicts positive relative returns. PSB-1's weekly C3 showed +0.025 mean IC with +17.5% gross Q1-Q5 spread — a real signal killed by weekly rebalance fees (12–17pp/yr). At fortnightly cadence with banded exit (0.40), turnover ~0.15 → fee drag ~78 bp/yr, survivable. Banded exit: a name enters the top-quintile portfolio when in the top quintile by score and exits only when it falls out of the top two quintiles (0.40 band). IC uses no banding. Declared window: 2020-09-04 → 2022-12-31.

### C3 — Delivery-conditioned reversal, fortnightly

Let `p_i(t)` = cross-sectional percentile rank of the C2 score `s^{C2}_i(t)` among names scored at *t* (0 = most abnormally low delivery, 1 = most abnormally high). Let `r_i(t)` = the trailing 1-month return (close at grid day *t* divided by close at grid day *t*−21 trading days, minus 1).

```
s_i(t) = − r_i(t) × ( 1 − 2·p_i(t) )
```

Formation-complete requires both the C2 score (delivery z) and the 1-month return present. Hypothesis: low-delivery monthly moves are noise and revert (weight → +1 · reversal); high-delivery moves are informed and persist (weight → −1, i.e., continuation). PSB-1's weekly C4 (mean IC −0.003) was null at weekly cadence before the delivery signal had time to differentiate; the fortnightly cadence gives the interaction term denser formations while keeping turnover survivable. Banded exit (0.40). IC uses no banding. Declared window: 2020-09-04 → 2022-12-31.

### C4 — Momentum, long-only, staggered 6-month holding

Let grid index *g* = 0, 1, ... enumerate monthly grid dates (§3) in ascending order. For a name scored at grid date *g*:

```
r_{12,i}(g) = P_i(t_g) / P_i(t_{g-12}) − 1
r_{1,i}(g)  = P_i(t_g) / P_i(t_{g-1}) − 1
s_i(g)      = (1 + r_{12,i}(g)) / (1 + r_{1,i}(g)) − 1
```

The construct is the standard 12-1 momentum: the 11-month return from *g*−12 to *g*−1 (excluding the most recent month to strip the short-term reversal effect). Requires 12 prior grid dates of price history. Long-only (top-quintile portfolio). **Staggered holding:** the portfolio is split into 6 equal tranches; each month, 1/6th is rebalanced to the current top quintile. A name held in any tranche remains held until its tranche's next rebalance date, regardless of rank drift. No banded exit (the staggered design caps turnover intrinsically). Turnover ~0.17 (1/6th of the portfolio per month) → fee drag ~2.5pp/yr, survivable.

**Momentum-fence disclosure (D2/D8):** CSMP's sealed read of a monthly momentum construct (42 observations, mean IC +0.0279) is disclosed as prior exposure. The successor pre-registration may apply an α penalty. No sealed data is read here.

## §6 Metrics

Same as PSB-1 Protocol §6 — carried forward without change.

## §7 Power projection

Same as PSB-1 Protocol §7 — carried forward, with the following amendments for mixed cadence:

1. **n\* per cadence:**
   - Fortnightly candidates (C2, C3): `n*` = number of fortnightly grid dates in **2023-01-01 → 2026-06-30**, computed exactly from `trading_calendar` (≈ 84).
   - Monthly candidate (C4): `n*` = number of monthly grid dates in the same window (≈ 42).
2. Projected power = `P( T ≥ t_{0.95, n*−1} )` where `T` is noncentral-t with noncentrality `δ / (SD_dev / √n*)`, `δ` = the candidate's **dev mean IC** and `SD_dev` = its dev IC standard deviation.
3. **Hurdle: projected power ≥ 0.80** — applied uniformly regardless of cadence. A candidate below the hurdle is **dropped by rule**, whatever its dev IC.
4. Autocorrelation robustness (AC₁ > 0.1 → Newey–West lag 4) reported alongside — report-only, never gating.

The mixed-cadence design is deliberate (D12): fortnightly candidates gain √2 in noncentrality over a monthly candidate at equal δ/SD. This is legitimate — cadence is a design choice with real consequences for sealed-gate success, unlike dev-window length. The noncentrality advantage is proportional to √(n\*) and is disclosed alongside each candidate's projected power.

**AC₁ exposure (Fortnightly candidates).** Adjacent fortnightly formations overlap in their 252-day delivery baseline, which changes slowly relative to the 15-day grid spacing. This overlap raises the IC series' autocorrelation relative to a monthly construct at equal intrinsic signal strength. Because AC₁/Newey–West columns are report-only and never gating (§6), a fortnightly candidate with inflated AC₁ **can clear the frozen 0.80 hurdle on a simple-t projection that its own reported AC₁ shows is optimistic**. The operator reads every power number with this exposure in view. The gating rule is not changed — this paragraph exists to state the exposure, not to repair it.

## §8 Selection rule (at most one winner)

**Eligibility** — a candidate is eligible iff, on its declared dev window:
(i) mean IC > 0; (ii) annualized net top-quintile spread > 0; (iii) §7 power ≥ 0.80.

**Ranking statistic:** eligible candidates are ranked by **projected sealed power** (§7). Because candidates run at different cadences (C2/C3 fortnightly n\* = 84, C4 monthly n\* = 42), the power ranking is **not invariant to cadence** — the fortnightly noncentrality advantage is structural and disclosed. The **winner is the highest-power eligible candidate.**

**Evidence floor:** a recommendation for promotion additionally requires the winner's declared-window one-sided p, **Bonferroni-deflated at m = 3** (deflated p = min(1, 3·p)), to be **< 0.05**. No cascade: if the highest-power eligible candidate fails the floor, the battery reports **"no winner recommended"**.

**Tie-break** (projected powers within 0.02): smaller deflated p wins, then higher net spread.

**Robustness:** all candidates are additionally reported on the common sub-window 2020-09-04 → 2022-12-31 (§3). The declared-window deflated-p ranking is shown alongside the power ranking. **If the winner differs across these rankings, all are presented and the operator decides** — the discrepancy is flagged, never silently resolved.

**Bonferroni m = 3 — data-independence rationale.** The ledger counts only C2, C3, and C4 because the two excluded candidates were dropped for reasons that are independent of any PSB-2 data: C5 was dropped because its required `roe_i(t)` input does not exist in the pinned store (a schema fact, not a measurement), and C1 was dropped because its IC series is definitionally identical to PSB-1's C5, whose power is already recorded at 0.541 against the 0.80 hurdle (a pre-existing result, not a PSB-2 discovery). Neither candidate was ever scored on PSB-2 data; neither can consume a chance at a PSB-2 false positive; therefore neither may inflate the penalty. Deflating by candidates that cannot produce a result would be an arbitrary tax on the ones that can. Deflation is pinned at m = 3 now, not after results.

## §9 Multiplicity ledger and immutability

- Exactly **three** candidates: C2, C3, C4 as defined in §5. No additions, variants, or parameter sweeps.
- After any candidate result exists, its definition is immutable.
- Pinned parameters (exhaustive — derived from §5 formula blocks and §3 grid rules):
  - **Grids:** fortnightly (last session on or before the 15th + last full session per month); monthly (last full session per month).
  - **C2 delivery z:** 252-day delivery baseline ending t−21 with ≥ 150 non-NULL; fortnightly delivery mean with ≥ 8 non-NULL; banded exit at 0.40.
  - **C3 delivery-conditioned reversal:** 21-trading-day return horizon for r_i(t); inherits C2's delivery parameters; banded exit at 0.40.
  - **C4 momentum, staggered:** 12-month lookback (g−12) for r_{12}; 1-month lookback (g−1) for r_{1}; requires 12 prior grid dates of price history; 6 staggered tranches, 1/6th rebalanced per month.
  - **Common:** quintile portfolios, equal-weighted; κ = 5 bp/side; fee model as in §2; percentile ranks with average ties; Bonferroni m = 3; power hurdle ≥ 0.80 at α = 0.05 one-sided; delisting imputation = date's worst realized forward return among scored names (§4.2); AC₁ robustness trigger > 0.1 with Newey–West lag 4; power tie band 0.02; dev fence MAX(trade_date) ≤ 2022-12-31.
- **Horizon consistency:** §7 projects power from each candidate's own-cadence dev IC series (fortnightly δ/SD → fortnightly n\*, monthly δ/SD → monthly n\*). No cross-horizon carryover is applied. F8's concern — projecting *monthly* δ/SD through *fortnightly* n\* — was specific to D10's rescue arithmetic for the dropped C1/C5 candidates and does not affect the live slate.

## §10 Determinism, audit, and reporting

Same as PSB-1 Protocol §10 — carried forward without change.

## §11 Sequencing and stop rules

1. **Phase 0 gate:** the substrate must pass the four-arm contract suite (`certify_substrate.py` Arm A–D) with **0 undocumented violations** before any candidate score touches real data. This is a structural gate — no Phase 1 without a certified substrate.
2. **Phase 1 gate:** the adapted screening harness must pass a synthetic-data dev-proof and Lead Review **before** any real candidate runs.
3. **Run order:** C2 → C3 → C4, one report per candidate, committed as produced. Results of earlier candidates cannot alter later definitions (§9).
4. **Stop rules:** all PSB-1 §11 stop rules carry forward.

## §12 What this protocol does not authorize

No sealed read — the 2023-01→2026-06 window stays untouched (PSB-2 only earns the right to propose spending it). No consumer, no strategy code, no new ingestion, no tuning. The winner, if any, is a **recommendation** — promotion happens only through a new, full pre-registration program ratified by the operator, which will pin its own execution conventions, α, and sealed-read mechanics, disclosing the one prior CSMP momentum read as prior exposure per operator decision D2.

Momentum-family constructs in this battery (C4) are structurally different from CSMP's (monthly rebalance, long-only, staggered holding, no prior sealed read consumed) and are authorized under D8. The prior CSMP momentum read is disclosed, not consumed.

## §13 Next steps after this document

1. ~~Independent review of Rev 1~~ — **DONE** (findings F1–F11 resolved via D11/D12 + Prompt 0R R1–R6).
2. ~~Rev 2 re-review~~ — **DONE** (BLOCK on circular §8 rationale; closed as R1).
3. ~~Rev 3 re-review~~ — **DONE** (S1–S3 text defects; closed as Rev 4 via Prompt 0R2).
4. Operator ratification of Rev 4 → status stamped **FROZEN**.
5. Prompt 1 (Phase 1 harness adaptation + synthetic dev-proof) issued to DeepSeek V4.
