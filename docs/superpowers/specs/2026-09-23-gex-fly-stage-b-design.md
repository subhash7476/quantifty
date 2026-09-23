# GEX Fly — Stage B: an N-gated NIFTY iron fly, from development read to pre-registration

**Date:** 2026-09-23 · **Branch:** `research/options-hedging-scenarios`
**Parent:** Stage A PASS — `docs/superpowers/specs/2026-09-23-gex-regime-stage-a-design.md`,
`docs/reports/GEX_REGIME_STAGE_A_{TRAIN,HOLDOUT}.md`, `GEX_REGIME_STAGE_A_TRAIN_REVIEW.md` (§3, §5).
**Status:** DESIGN — every parameter below is pinned before any fly P&L is read.

## 1. Purpose

Stage A showed that EOD NIFTY normalized net GEX (N) predicts next-day realized variance *below* VIX-implied
(≈ −20 % from N p10 → p90, TRAIN t −3.20, HOLDOUT t −2.65). It did not show a tradeable edge: no P&L, no fees,
R² ≈ 0.06–0.07, and no evidence for the dealer mechanism. Stage B asks whether a short-gamma structure gated on N
carries that information into **net P&L**, through a staged gate (B1 → B2 → B3) where each stage can stop it.

## 2. Interpretation rule (operator, 2026-09-23 — binding on every report)

History and the current market differ. Verdicts are stated as **"demonstrated / not demonstrated on window W"** —
never "the construct is good" or "the construct is bad". A weak 2019–22 read does not condemn the idea for today's
market; a strong one does not vouch for it. Structural breaks are named in advance (§8), and **forward paper is the
only direct evidence about the current market**.

## 3. Construct

- **Signal:** N_t exactly as Stage A (`core/analytics/gex_history.py` at `c1ccd45`, unchanged). Zone thresholds are
  causal: the trailing 250-session 67th percentile (**p67**) and median (**p50**) of N over sessions t−249..t.
- **Entry (at close t):** if flat and N_t ≥ p67_t, open **one** ATM iron fly:
  - **Expiry:** the nearest NIFTY expiry with ≥ 3 trading sessions remaining after t (sessions = dates present in the
    1d index store).
  - **Body:** short CE + short PE at the listed strike nearest the expiry's parity forward F (Stage A §4.3).
  - **Wings:** long CE at the nearest listed strike ≥ K + w, long PE at the nearest listed strike ≤ K − w, where
    w = σ_ATM · √(DTE/365) · F; σ_ATM = the Stage A IV of the body strike's OTM leg (CE if K ≥ F, else PE);
    DTE = calendar days to expiry.
  - All four legs must have traded at t (`contracts > 0`) and the forward must exist, else no entry that day
    (counted by reason).
- **Daily check at each close s > entry, first rule that fires closes the fly at that close:**
  1. **Stop:** mark-to-market loss ≥ 1.0 × entry credit.
  2. **Profit lock:** mark-to-market gain ≥ 0.5 × entry credit.
  3. **Regime:** N_s < p50_s.
  4. **Time:** s is the last trading session before the expiry date (T−1).
  If N_s is missing on a day, rule 3 does not fire that day; rules 1, 2, 4 still apply.
- **Re-entry:** not at the close where a fly exits; the earliest re-entry is the next close. Never more than one
  fly open.
- **Primary structure:** the iron fly. **Descriptive only**, same entry/exit rules:
  - iron condor — shorts at the nearest strikes to F ± 0.5w, wings at the nearest strikes to F ± 1.5w;
  - unhedged short straddle — body only; its "max loss" for return-on-risk uses the fly's wing width.
- **Out of scope:** the intraday HedgeWall-style overlay (C) — a later, paper-only spec.

## 4. Pricing (from `options_bhavcopy`, at each close)

- **Traded leg** (`contracts > 0` that day): mark = `close`.
- **Untraded leg:** conservative of `close` (stale) and `settle` (theoretical): **max** for a short leg, **min** for
  a long leg.
- **Entry credit** C₀ = (short CE + short PE − long CE − long PE) at entry marks (all traded by rule).
- **Exit liquidity is never a filter** — a fly closes at conservative marks whether or not its legs traded.
- **Fills at the close only**; a gap can overshoot the stop, bounded by the wings.
- **Max loss per unit** L = max(wing width CE side, wing width PE side) − C₀. Entries with L ≤ 0 are skipped
  (counted) — a data error, since a fly's credit cannot exceed its narrower wing.

## 5. Costs

- **Statutory + brokerage:** `core/execution/options/fees.py`, unchanged (effective-dated STT, NSE txn, SEBI, stamp,
  GST, ₹20/order). A round trip is **8 orders**.
- **Spread:** half of a **2 %** relative spread paid per leg on entry and on exit (the seller-edge study's
  convention). Descriptive: 1 % and 4 %, and the break-even spread at which net mean P&L reaches zero.
- **Lot size:** a pinned NIFTY table (per unit, brokerage = ₹20 ÷ lot). Values must be verified against NSE circulars
  **before** any P&L is computed (plan task 1); the table below is the starting hypothesis:

  | from | lot |
  |---|--:|
  | 2015-11-01 | 75 |
  | 2021-07-30 | 50 |
  | 2024-04-26 | 25 |
  | 2024-11-20 | 75 |
  | 2025-12-30 | 65 |

## 6. P&L unit

- **Per trade:** return on risk R = (net P&L per unit, after spread and fees) ÷ L.
- **Daily series:** mark-to-market change in return on risk of the open fly (0 on flat days), summing to R over a
  trade's life; annualized Sharpe = mean / sd × √250. This is the quantity an RFA `per_trade_pnl` declaration takes
  (annualized Sharpe + `cadence_per_year = 250`).

## 7. Evaluation

### B1 — development read, 2019-02-11 → 2022-12-30 (weeklies era only)
- N history from 2016 provides the 250-session warmup, so thresholds are causal from the first weekly.
- A fly still open at 2022-12-30's close is force-closed there. **No price at or after 2023-01-01 is read**; the
  runner refuses such dates.
- Reported: annualized net Sharpe (headline); trades, hit rate, mean R, max drawdown of the cumulative daily series,
  exits by reason, entries skipped by reason, fee drag, break-even spread; the **ungated fly** (enter whenever flat,
  exits 1, 2, 4 only); condor and short straddle (descriptive); per-year table (descriptive).
- **Stop rules (pinned now).** Stage B ends at B1 — no RFA — if either:
  1. the gated fly's net Sharpe ≤ 0, or
  2. the gated fly's net Sharpe ≤ the ungated fly's net Sharpe (N adds nothing).
  Per §2 this reads "not demonstrated on 2019–22 history".

### B2 — Sharpe band and RFA (only if B1 does not stop)
- S₁ = B1 gated-fly net Sharpe. Band: **optimistic S₁, central 0.5·S₁, pessimistic 0.25·S₁**, cadence 250.
  The 0.5 central is the CB-N50 out-of-sample halving; it is fixed now, not chosen after B1.
- Declaration `governance/rfa/declarations/gex_fly.py`, SHA-frozen before `scripts/rfa/run_rfa.py` runs.
- MSRP Phase 7's unconditional NIFTY daily-straddle Sharpe 0.74 read **2023–25** — the confirmation window — so it
  is **disclosed as prior exposure and not used** to set the band.
- Expected arithmetic: the confirmation window 2023-01-02 → 2026-09-11 is ≈ 3.7 years, so power 0.80 at one-sided
  α 0.05 needs S ≈ 2.49 / √3.7 ≈ **1.3** at the optimistic corner. ABANDON blocks the B3 read, not forward paper,
  and is recorded as "not provable on the available window".

### B3 — pre-registration and one-shot confirmation (only if RFA PROCEED)
- A frozen pre-registration pins §3–§6 and the test: mean daily return on risk > 0, Newey–West (lag 5) one-sided
  p < 0.05, over 2023-01-02 → the last bhavcopy date **as fixed at freeze**.
- **Pre-declared descriptive splits:** before / after 2024-11-20 (SEBI F&O reform), 2025-09 (NIFTY expiry to
  Tuesday), 2026-08-03 (CAS). The pass rule stays one test on the whole window.
- The B3 runner refuses to start unless the pre-registration file matches its frozen SHA (the `run_sealed.py`
  pattern). It is written only after PROCEED.

## 8. Prior exposure (disclosed)

- Stage A read N vs next-day RV/IV over 2016–2022 (TRAIN + HOLDOUT, both spent for that question).
- MSRP Phase 7: unconditional NIFTY daily ATM short straddle, 2023–25 (S 0.74).
- Seller-edge study: NIFTY monthly straddles 2016 onward incl. its confirmation window; weekly / DTE-0 / overnight
  index selling reads.
- Options-Wall counterfactual battery: intraday iron fly worst-of-battery on 2026-09-04 → 09-17 snapshots.
- HedgeWall claim-1 arm: expiry-day OI concentration 2024-01 → 2026-09.

## 9. Files

| File | Purpose |
|---|---|
| `core/analytics/iron_fly.py` | Pure: zone thresholds, leg selection, conservative marks, credit / max loss, exit evaluation |
| `tests/analytics/test_iron_fly.py` | Unit tests (§10) |
| `scripts/gex_regime/fly_dev.py` | B1 runner (reuses Stage A panel build for N); refuses dates ≥ 2023-01-01 |
| `docs/reports/GEX_FLY_B1_DEV.md` | Script-generated B1 report |
| `governance/rfa/declarations/gex_fly.py` | B2 only |

`core/analytics/gex_history.py`, `scripts/gex_regime/run_stage_a.py` and `core/execution/options/fees.py` are
imported, not modified.

## 10. Tests

- Zone thresholds use only sessions ≤ t (a spike at t+1 does not change p67_t).
- Leg selection: body at strike nearest F; wings at the nearest listed strikes beyond ±w; condor shorts/wings at
  ±0.5w / ±1.5w.
- Conservative marks: untraded short leg takes max(close, settle); long takes min.
- Exit precedence: a day where both stop and regime fire exits as **stop**; T−1 fires on the last session before
  expiry.
- One fly at a time; no same-close re-entry.
- Return on risk: a hand-built fly with known credit, wings and fees gives the expected R.
- Runner guard: any date ≥ 2023-01-01 raises.
