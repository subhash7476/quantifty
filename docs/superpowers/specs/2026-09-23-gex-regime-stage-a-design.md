# GEX Regime — Stage A: does NIFTY's EOD gamma regime predict next-day realized vs implied vol?

**Date:** 2026-09-23 · **Branch:** `research/options-hedging-scenarios`
**Parent:** `docs/reports/HEDGEWALL_POSITIONING_REVIEW_2026-09-23.md` §2 claim 3
**Status:** DESIGN — frozen at commit; the prediction in §7 is written before any outcome is read.

> **Implementation notes (2026-09-23, before any run):** (1) `implied_vol()` exists only on the ptms branch, not on
> this one — `core/analytics/gex_history.py` carries its own `brentq` solver over the existing `bs_price`, bracket
> [0.01, 3.0] as in §4.5. (2) Reports are written per window — `GEX_REGIME_STAGE_A_TRAIN.md`, then
> `GEX_REGIME_STAGE_A_HOLDOUT.md`; the HOLDOUT run refuses unless the TRAIN report records PASS. (3) An outcome
> day t+1 outside the window drops t, so no fit reads a bar outside its own window.

## 1. Purpose

The operator's end goal is an iron fly whose management (lock profits / reposition on a move) is driven by
HedgeWall-style dealer-positioning reads. Exit and adjustment rules only reshape a P&L distribution; they cannot
create an edge that the base trade lacks (the repo's own evidence: the intraday iron fly was the worst structure in
`OPTIONS_WALL_COUNTERFACTUAL_BATTERY.md`; index weekly selling showed nothing in the seller-edge study). So the
load-bearing question comes first:

> **Does the end-of-day gamma regime carry information about next-day realized volatility beyond what implied
> volatility already prices?**

Stage A is descriptive analytics — no strategy, no `SignalEvent`, outside the RFA gate. A PASS authorizes only a
Stage B brainstorm (fly entry/adjustment design → RFA → pre-registration). A FAIL parks the idea.

## 2. Scope

- **Underlying:** NIFTY only.
- **Windows:** TRAIN 2016-02-11 → 2019-12-31 (fit, prediction written first); HOLDOUT 2020-01-01 → 2022-12-31
  (one confirmatory run). **2023-01-01 onward is not read** — it is the only remaining unread window for this
  table, and futures/options history cannot predate 2016. The runner hard-refuses any date ≥ 2023-01-01.
- **Resolution:** end of day only. HedgeWall's intraday flip is not tested here.
- **Not in scope:** BankNifty; intraday snapshots; dealer-side inference from `chg_in_oi`; any trade simulation.

## 3. Data

| Input | Source |
|---|---|
| Option chain | `data/market_data/options_bhavcopy.duckdb`, table `option_bhavcopy`, `symbol='NIFTY'` |
| Index OHLC | `data/market_data/nse/candles/1d/{date}.duckdb`, `NSE_INDEX|Nifty 50` |
| Implied vol level | same files, `NSE_INDEX|India VIX` (close) |

Known hazards, handled in §4: untraded rows carry the previous close; on an expiry date the expiring series' `settle`
holds the underlying settlement price; `open_int` units are not pinned (minimums of 50/75/25 are not consistently lot
multiples), so **only scale-free GEX measures are used**.

## 4. Per-day construction (for each trading date t)

1. **Expiries used:** every NIFTY expiry with 1 ≤ calendar DTE ≤ 45. The series expiring on t is excluded.
2. **Time:** T = (expiry_dt − t, in calendar days) / 365. Rate r = 0.065, fixed.
3. **Forward per expiry (put–call parity):** among strikes where both CE and PE traded (`contracts > 0`), take the
   strike K* minimizing |C − P| on `close`; F = K* + (C − P)·e^{rT}. An expiry with no such pair is dropped.
   Sanity: |F / Nifty close − 1| ≤ 2 %, else the expiry is dropped and counted.
4. **Strike filter per expiry:** out-of-the-money leg only (PE for K < F, CE for K ≥ F); that leg traded
   (`contracts > 0`); close ≥ 0.5; |ln(K/F)| ≤ 0.10.
5. **IV:** back-solve from the OTM leg's close with the existing spot-Black-Scholes `implied_vol()` in
   `core/execution/options/nifty_shield_pricing.py`, passing the parity-implied spot S* = F·e^{−rT} (equivalent to
   Black-76 on F); keep 0.01 ≤ σ ≤ 3.0, else drop the strike.
6. **Gamma:** Black-Scholes γ(S*, K, T, r, σ) per strike (new function in `gex_history.py`); the same γ applies to
   that strike's CE and PE open interest.
7. **Dealer-sign convention (an assumption, not an observation):** dealers long calls, short puts.
   Signed exposure per strike g = γ · (OI_CE − OI_PE) · F² · 0.01; gross per strike |g| = γ · (OI_CE + OI_PE) · F² · 0.01.
8. **Aggregate over all kept strikes and expiries:**
   - **N_t (primary)** = Σ g / Σ |g| ∈ [−1, 1] — normalized net GEX.
   - **S_t** = sign(Σ g).
   - **D_t** = flip distance: reprice Σ g on a spot grid F·(1+x), x ∈ [−5 %, +5 %] step 0.1 %, with each strike's
     σ and T held fixed (sticky strike); flip = the grid point nearest x = 0 where Σ g changes sign;
     D_t = ln(F_near / flip) / (VIX_t/100/√252). No sign change in the grid → D censored at ±(grid edge), counted.
9. **Day validity:** ≥ 10 kept strikes in total, else t is dropped and counted.

## 5. Outcome and controls

- **Realized variance (Parkinson):** RV_d = (ln(H_d / L_d))² / (4 ln 2) from the Nifty 50 1d bar of day d.
- **Implied daily variance:** IVd_t = (VIX_t / 100)² / 252.
- **Outcome:** y_t = ln(RV_{t+1} / IVd_t), where t+1 is the next trading date in the 1d store.
- **Controls:** ln VIX_t; ln of trailing 5-day and 20-day mean RV (days t−4..t, t−19..t); E_{t+1} = 1 if t+1 is a
  NIFTY expiry date.
- Parkinson excludes the overnight gap. Close-to-close ln(C_{t+1}/C_t)² is reported as a **secondary** outcome only.

## 6. Model

OLS: y_t = a + b·N_t + c₁ ln VIX_t + c₂ ln RV5_t + c₃ ln RV20_t + c₄ E_{t+1} + ε, Newey–West HAC standard errors,
lag 5. The primary coefficient is **b**. S_t and D_t are fitted in the same form and reported **descriptively**
(not part of the pass rule). Reported alongside: effect size of moving N from its TRAIN p10 to p90, expressed as
% change in RV_{t+1}/IVd_t; the correlation of N with ln VIX (to show how much N is a vol-level proxy).

## 7. Prediction and decision rule (written before any outcome is read)

- **Hypothesis (HedgeWall claim 3):** dealers long gamma dampen moves → higher N_t ⇒ lower realized vs implied.
- **TRAIN pass:** b < 0 with NW t ≤ −2.0.
- **HOLDOUT pass (run once, only if TRAIN passes):** b < 0 with one-sided NW p < 0.05.
- **Stage A PASS** = both. → Stage B brainstorm is authorized (nothing more).
- **Stage A FAIL** = either fails → claim 3 not supported at EOD resolution; the fly-adjustment idea is parked. No
  re-specification of §4–§6 after seeing TRAIN; any change is a new, separately recorded design.
- **Regime caveat, disclosed now:** NIFTY weeklies began Feb 2019, so most of TRAIN is monthly-only chains. The
  TRAIN fit is also reported split 2016–2018 / 2019 descriptively; the pass rule uses the full TRAIN.

## 8. Pre-run checks (read no outcome)

Per year: days computed / dropped (by reason), kept strikes per day, expiries per day, forward-vs-close ratio
distribution, share of D censored, distribution of N. These are reported before §6 is fitted.

## 9. Prior exposure (disclosed)

- The HedgeWall claim-1 EOD arm read expiry-day close OI concentration from this table (2024-01 → 2026-09) —
  outside TRAIN/HOLDOUT, but it is the same table.
- The Options-Wall counterfactual battery (2026-09-04 → 09-17 snapshots) and claim-1 intraday arm — post-2023,
  not re-read here.
- The seller-edge study read NIFTY weekly/DTE-0/overnight short-premium returns over 2016 onward — a different
  quantity (P&L of short straddles), but the same underlying vol surface.

## 10. Files

| File | Purpose |
|---|---|
| `core/analytics/gex_history.py` | Pure functions: parity forward, strike filter, gamma, per-day GEX aggregates (N, S, D) |
| `tests/analytics/test_gex_history.py` | Unit tests (§11) |
| `scripts/gex_regime/run_stage_a.py` | Loader + panel build + pre-run checks + fit; `--window train|holdout`; refuses dates ≥ 2023-01-01 |
| `docs/reports/GEX_REGIME_STAGE_A.md` | Script-generated report (no hand-edited numbers) |

`implied_vol` / `bs_price` are reused from `nifty_shield_pricing.py`. `OptionsAnalytics.calculate_gex` (live dashboard)
is not modified.

## 11. Tests

- Black-76 gamma matches a hand-computed value; IV round-trips `bs_price` → `implied_vol`.
- Parity forward recovers F from a synthetic chain priced at known F.
- Strike filter keeps only traded OTM legs inside the band.
- Sign convention: a call-only chain gives N = +1, a put-only chain gives N = −1.
- Flip: a synthetic chain with a known zero crossing returns it within one grid step; no crossing → censored flag.
- Runner guard: any date ≥ 2023-01-01 raises.
