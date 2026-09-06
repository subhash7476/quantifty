# Trend Sleeve — Phase 0 Pre-Registration (DRAFT)

**Status:** DRAFT. To be **FROZEN** on operator approval (SHA-256 over the whole file);
bands cannot be revised in response to results once frozen.
**Parent design:** `SIGNAL_ENGINE_DESIGN.md` — this is sleeve #2 (Trend), validated
standalone before it may enter the combined engine.
**Consumes:** no sealed data. This document authorizes the RFA power pre-check and, if it
returns PROCEED, the TRAIN/HOLDOUT empirical protocol. The 2024→present window stays
**sealed and unread** until §9's acceptance rule is met on TRAIN and HOLDOUT.

---

## 1. Hypothesis (falsifiable)

Cross-sectional dispersion in **vol-scaled multi-horizon time-series momentum** over
single-stock futures predicts forward returns. Names with strong recent trend (high
risk-adjusted trailing return) continue to outperform — names with weak trend (low/negative
risk-adjusted trailing return) continue to underperform.

Sign is declared now and cannot be flipped after seeing results: **long high-trend names,
short low-trend names.** (Economic reading: under-reaction to news/carry trades and
risk-transfer from hedgers to speculators, per Moskowitz-Ooi-Pedersen 2013.) If realized IC
is significant with the *opposite* sign, the hypothesis is falsified, not re-labelled.

**Relation to prior work:** Trend here is distinct from PSB-1 C1 (cross-sectional weekly
reversal) and PSB-2 C4 (long-only staggered-entry momentum). This sleeve uses
**time-series** momentum (vol-scaled, multi-horizon) evaluated **cross-sectionally**:
names are ranked by their individual TSMOM signals, then the book goes long the top
quintile and short the bottom quintile. This is a dollar-neutral cross-sectional book,
not a net-long trend-following strategy.

---

## 2. Universe & point-in-time membership

- **Universe:** NSE F&O-eligible single-stock names, **point-in-time** — a name is eligible
  at formation *t* only if it was F&O-listed and liquid at *t*.
- **Continuous prices:** built from near-month futures with the T-3 roll rule (same as
  Carry §3.4). Roll-adjusted via cumulative roll ratio for a continuous price series per
  name. At least 12 months of price history required before a name enters the universe.
- **Liquidity screen:** trailing 20-day median futures turnover ≥ ₹5 cr (same as Carry).
- **Expected N per formation:** ~120–180 names (same substrate as Carry).

---

## 3. Signal construction (exact, pre-registered)

For each name *i* at formation date *t*, using the continuous (roll-adjusted) futures close:

1. **Horizon returns** (log): for each horizon *h* ∈ {63, 126, 252} trading days:
   `ret_{i,t,h} = ln(adj_close_{i,t}) − ln(adj_close_{i,t−h})`
2. **Volatility scaling:** trailing 60-trading-day annualized volatility:
   `vol_{i,t} = std_dev(daily_log_rets_{i,t-60:t}) × √252`
3. **Vol-scaled signal per horizon:** `z_{i,t,h} = ret_{i,t,h} / vol_{i,t}`
4. **Multi-horizon composite:** `tsmom_{i,t} = mean_h(z_{i,t,h})`
5. **Cross-sectional z-score:** standardize `tsmom_{i,t}` to zero mean / unit SD across the
   eligible universe on each date → `z_trend_{i,t}`. Winsorize at ±3 SD before z-scoring.

### 3.1 Horizon rationale
63/126/252 trading days correspond approximately to 3/6/12 calendar months — the standard
TSMOM horizons from MOP 2013. Equal-weighting across horizons (rather than selecting one)
reduces horizon-specific noise. All three use the same volatility estimate so they share a
common scaling baseline.

### 3.2 Continuous price construction
- Near-month contract selected per Carry §3.4 rules (minimum expiry_dt ≥ trade_date;
  roll to next month when ≤3 trading days remain).
- At each roll date: compute `roll_ratio = close_new_contract / close_old_contract`.
  Back-adjust all prior prices by multiplying by the cumulative roll ratio.
- Raw (unadjusted) close also retained. Only the adjusted close is used for signal
  computation.

---

## 4. Neutralization

Before ranking, residualize `z_trend_i` against:
- **Market beta** (trailing 252-day beta to Nifty 50), and
- **Sector** (NSE sector dummies)

via a single cross-sectional OLS per formation; the **residual** is the tradeable signal
`z_trend_neut_i`. Same methodology as Carry §4.

---

## 5. Metric — and why rank-IC

**Primary metric:** cross-sectional **Spearman rank-IC** of `z_trend_neut` at formation *t*
vs. the forward one-month name return (using spot adjusted returns), measured at monthly
formations.
**Secondary (reported, not the gate):** net top-minus-bottom quintile spread under §8 fees.

**Why rank-IC:** Same rationale as Carry §5. Trend is a cross-sectional ranking signal
(the book is always long the top quintile and short the bottom quintile), so the correct
evaluation metric is rank-IC, not per-trade Sharpe. The RFA contract v2 permits independent
delta/SD bands for rank-IC, avoiding the crossed-corner artifact that withdrew O1.

---

## 6. Portfolio construction

- **Form:** beta-neutral, sector-neutral, dollar-neutral cross-sectional long/short.
- **Weights:** proportional to `z_trend_neut` (z-weighted), renormalized to fixed gross
  exposure; **ADV-capped per name** (position ≤ 10% of 20-day futures ADV).
- **Rebalance cadence:** **monthly**, aligned with Carry. (Signal is computed daily but
  the book rebalances monthly; intra-month signal changes inform stop/take-profit if
  implemented in a later increment.)
- **Turnover penalty:** rebalances smaller than 0.25σ of target weight are suppressed.

---

## 7. RFA power pre-check (declared bands — frozen at approval)

`metric = rank_ic`, one-sided test (sign declared in §1), power hurdle **0.80**.

| Quantity | Band | Provenance |
|---|---|---|
| **delta** (mean cross-sectional IC) | **[0.020, 0.055]** | Cross-sectional TSMOM in equity futures globally has rank-IC ~0.02-0.06 (MOP 2013 Table 2; Baltas-Kosowski 2013).
The vol-scaling and multi-horizon averaging reduce noise, supporting the upper bound.
PSB-1 C1 (plain weekly reversal) showed mean rank-IC |~0.023|; vol-scaled multi-horizon
TSMOM is expected to be higher. |
| **SD** (IC dispersion across formations) | **[0.10, 0.18]** | Same as Carry §7. Monthly cross-sectional IC dispersion for a ~150-name SSF cross-section
is dominated by true time-variation, not sampling noise. No tightening is defensible. |
| **n\*** (formations in the power-projection window) | **= 31** (monthly, sealed 2024-01 → 2026-07) | The futures continuous series is built from the same raw bhavcopy as Carry
(2016-02-11 → 2026-07-20). After a 12-month TSMOM lookback warmup, the first feasible
formation is 2017-02. The sealed window (2024-01 → 2026-07) yields ~31 monthly
formations. **The calendar lever is exhausted** — NSE F&O history before 2016 is not
obtainable (SFB-1/F1 lockdown finding). |

### 7.1 The honest power picture — standalone vs. combined
`ncp = (delta / SD) · √n*`. At n* = 31, clearing power 0.80 (one-sided, α=0.05) needs
per-formation IR `delta/SD ≥ ~0.45`:
- **Optimistic corner** `(delta_hi=0.055, SD_lo=0.10)` → IR 0.55 → **clears** → RFA
  **PROCEED**. (Legitimate here, not a crossed corner — see §5.)
- **Central** `(0.035, 0.14)` → IR 0.25 → standalone power ≈ 0.40 → below hurdle.

Same structural constraint as Carry §7.1. The 0.80 power hurdle binds at the **combined
engine** level, not per-sleeve. Trend's standalone TRAIN/HOLDOUT read is a
**sign + magnitude + fee + persistence** check (§9 gates 2, 4, 5), not a standalone 0.80
gate.

### 7.2 AC₁ / overlap
Monthly non-overlapping formations → no overlap-induced autocorrelation inflation. AC₁
still reported at TRAIN; if materially positive (|AC₁| > 0.10), the effective-n haircut is
applied via Newey-West SE (same as PSB protocol).

---

## 8. Fees & cost model

Same as Carry §8: `core/execution/futures/futures_fees.py` (already implemented).
- Futures STT sell-side only: 0.0125% (TRAIN period) / 0.02% (post-Oct-2024).
- Exchange txn, SEBI fee, stamp duty, GST — all era-accurate.
- Brokerage: default Rs 20/order (discount broker futures).
- Slippage: κ = 5 bp/side, plus ADV position cap as impact control.

---

## 9. Acceptance rule (pre-registered, evaluated before any sealed read)

**Windows (pinned, from the continuous futures series 2016-02-11 → 2026-07-20):**
- **TRAIN:** 2017-02 → 2021-12 (~59 monthly formations). First formation 2017-02 allows
  12-month TSMOM lookback warmup from 2016-02-11. Beta warms up off pre-TRAIN history
  (adjusted spot from 2010, Nifty 50 from 2012).
- **HOLDOUT:** 2022-01 → 2023-12 (24 monthly).
- **SEALED:** 2024-01-01 → 2026-07-20 (~31 monthly) — **untouched** until gates 1–5 pass.

Ordered gates. Each must pass on the stated window before the next window is touched:

1. **RFA gate** (declared bands, §7): single-sleeve bar is **PROCEED** (optimistic corner).
   ABANDON is dispositive.
2. **TRAIN:** mean rank-IC significant with the **declared sign** (t via AC₁-corrected SE);
   net quintile spread > 0 under §8 fees; realized IC SD inside the declared [0.10, 0.18]
   band (if SD > 0.18 — the C2 wide-SD failure — the sleeve stops here, sealed window
   preserved).
3. **HOLDOUT:** sign and net-spread persist; **no parameter touched** between TRAIN and
   HOLDOUT.
4. **Composite power check** (engine level, not standalone): Trend's TRAIN-estimated IR
   feeds the combined-engine power projection with Carry's read (if available); the 0.80
   hurdle binds on the composite, not on Trend alone.
5. **Only then**, one **SEALED** read (2024→present), reported whatever it shows.

Any gate failure → sleeve does not advance; **no successor is auto-authorized**; sealed
window stays sealed if not yet reached.

---

## 10. Prior-exposure disclosure

The operator's prior reads are primarily in:
- **PSB-1/PSB-2**: weekly reversal (C1), delivery-% anomaly (C2/C3), delivery-conditioned
  reversal (C3), momentum long-only staggered (C4). All are **cash-equity delivery**
  constructs — not futures, not vol-scaled, not TSMOM.
- **SFB-1/F1**: cash-synthesized momentum with intraday bracket (12-1 cross-sectional
  momentum on synthetic futures). This is the closest prior read to Trend. The F1 screen
  was inconclusive (TRAIN CI included zero, MaxDD −45.7% on ≤10-name book, grid-picked
  parameters that reduced the signal to plain monthly momentum). The general finding that
  cross-sectional momentum has weak demonstrability at n*=42 on a single sleeve was
  driven by sample-size arithmetic, not by a direct TSMOM read.
- **Carry (completed)**: carry/basis TRAIN read completed 2026-07-23 — IC singed
  **positive** (+0.041), opposite of hypothesis. Carry is not viable. The SSF substrate
  (363 underlyings, spot join 100%) is identical; the Trend TRAIN will read the **same**
  forward returns against a different signal.

**No Trend/TSMOM construct has been screened on this data.** The F1 cash-synthetic screen
is approximate but not equivalent (single-horizon, no vol-scaling, concentrated ≤10-name
book, intraday bracket exit). This is disclosed as prior exposure rather than denied.

---

## 11. Falsifiable predictions (stated before the run)

1. Trend (vol-scaled multi-horizon TSMOM) rank-IC on TRAIN is **positive-signed** (long
   high trend) and its AC₁-corrected t-stat clears the pre-set threshold.
2. The signal is **not** subsumed by beta/sector — IC survives the §4 neutralization
   (raw-trend IC and neutralized IC same sign, neutralized magnitude ≥ 60% of raw).
3. Net quintile spread > 0 under §8 futures fees at monthly turnover.
4. Realized TRAIN IC SD lands inside the declared **[0.10, 0.18]** band (if it exceeds
   0.18, the C2 wide-SD failure repeats and §9 gate 2 stops the sleeve).

If (1) or (3) fails, Trend is not a viable sleeve. The engine composition reverts to
**Skew solo** (or stops, if Skew is not buildable).

---

## 12. Key files (to be created)

| File | Purpose |
|---|---|
| `governance/rfa/declarations/trend.py` | Frozen RFA declaration (bands, n*, sign) |
| `scripts/signal_engine/trend/build_continuous.py` | Build roll-adjusted continuous futures series |
| `scripts/signal_engine/trend/build_trend.py` | §3 signal construction (TSMOM → z → neutralized) |
| `scripts/signal_engine/trend/run_train.py` | §9 TRAIN read → `TREND_TRAIN_REPORT.md` |
| `tests/signal_engine/trend/` | Signal + neutralization + fee unit tests |

---

## 13. Engine viability — empirical, not projected

Same discipline as Carry §13, reproduced here for completeness. The composite engine power
is decided **empirically from realized quantities after TRAIN**, never from a pre-freeze
projection. The binding 0.80 hurdle applies at the combined-engine level after ≥2 sleeves
have TRAIN reads.

After Carry's Gate 2 failure: **Carry is not viable.** The composite is Trend + Skew (2
sleeves) at the time of Trend's TRAIN. If Trend passes, the composite has 1 read; if Skew
also passes, the composite faces 0.80 with 2 realized reads. A 2-sleeve composite at
n*=31 with central-assumption IRs ≈ 0.25 per sleeve → composite IR ≈ √(2 × 0.25²) = 0.35
→ power ≈ 0.50 at n*=31. This does not clear 0.80. If the realized IRs are upper-band
(~0.50 per sleeve), composite IR ≈ 0.71 → power ~0.75, still below 0.80.

**Consequence stated plainly:** a 2-sleeve engine (Trend + Skew) is unlikely to clear
0.80 at n*=31 even with optimistic realized IRs. The engine may need 3 sleeves or a wider
calendar window. This is acknowledged as the track's structural risk (Carry §13 carries
the same finding). Not a reason to stop — but a reason that the composite verdict is
determinative and the sealed window must stay sealed until the hurdle is cleared.

---

## 14. Freeze

On approval: compute SHA-256 over this file (excluding this line), record it here and in
`trend.py`, and treat §1 (sign), §3 (construction), §4 (neutralization), §6
(cadence/caps), §7 (bands), and §9 (acceptance rule) as immutable. Any change after
freeze starts a new pre-registration.
