# Skew Sleeve — Phase 0 Pre-Registration (DRAFT)

**Status:** DRAFT. To be **FROZEN** on operator approval (SHA-256).
**Parent:** `SIGNAL_ENGINE_DESIGN.md` — sleeve #3 (Skew), validated standalone before it enters
the combined engine. Shares construction and discipline with `CARRY_PHASE0_PRE_REGISTRATION.md`.
**Consumes:** no sealed data. Options substrate is ingested (98,320,092 rows, OPTSTK verified,
2016-02-11 → 2026-07-20).

---

## 1. Hypothesis (TWO-SIDED — the deliberate correction to the v1-Carry sign error)

Per-name option-implied **skew** predicts forward cross-sectional returns. The documented
direction (Xing–Zhang–Zhao 2010, *What does individual option volatility smirk tell us about
future equity returns?*) is that a **steep put skew → lower** forward returns (informed
pessimism priced into downside protection). But a crowding / hedging-unwind reading gives the
**opposite** sign, so this signal is **genuinely sign-ambiguous.**

**The metric is therefore registered `two_sided`.** The sign is **not** pre-committed. TRAIN
establishes existence *and reveals* the sign in a single read; HOLDOUT confirms the sign
persists. This is the explicit lesson from v1-Carry, where a one-sided bet on an ambiguous sign
burned a whole registration when the data came in the other way. Two-sided costs a little power
(§5) and buys immunity to that failure.

---

## 2. Universe

The **liquid options subset only** — names with option OI/turnover sufficient for a stable
skew estimate (target **top ~50–100** by 20-day option turnover; exact floor pinned at freeze).
This is a **narrower cross-section than Carry/Trend**, so Skew's composite contribution is
smaller — but it is **decorrelated** from a basis signal and a price-trend signal, which is
exactly what the breadth thesis rewards (`IR ≈ √(Σ IR_i²)` rewards independence, not size).

---

## 3. Signal construction

Per name, per monthly formation, from the nearest monthly expiry with **≥ 10 trading days to
expiry** (avoid expiry-microstructure noise):

1. Interpolate implied vol at fixed delta from the option chain.
2. **Skew = IV(25Δ put) − IV(25Δ call)** (risk-reversal; the cleaner, more standard construct —
   pinned as the single choice at freeze, no post-hoc switch to the Xing ATM-smirk variant).
3. Winsorize ±3σ; cross-sectional z-score → `z_skew`.
4. **Neutralize beta + sector** (identical procedure to `CARRY_PHASE0_PRE_REGISTRATION.md` §4).

Portfolio construction, monthly cadence, ADV/liquidity caps, no-trade band, and the futures fee
model are inherited from the Carry pre-reg (§6, §8): the book trades **futures**, the skew is
only the ranking signal.

---

## 4. Metric

Cross-sectional **rank-IC, `two_sided`**. Existence tested on TRAIN; sign read from TRAIN and
**confirmed on HOLDOUT** before Skew counts toward the composite.

---

## 5. RFA power pre-check (declared bands — frozen at approval)

`metric = rank_ic`, **`test = two_sided`**, power hurdle 0.80.

| Quantity | Band | Provenance |
|---|---|---|
| **delta** (|mean IC|) | **[0.020, 0.045]** | Option-skew return predictability: Xing–Zhang–Zhao (2010); An–Ang–Bali–Cakici (2014); Bali–Hovakimian — cross-sectional IC ~0.02–0.05 for skew/IV-spread signals. |
| **SD** (IC dispersion) | **[0.10, 0.18]** | As Carry; large-cross-section monthly IC dispersion. |
| **n*** | **= 42** (monthly, sealed 2023-01 → 2026-07) | Options span matches futures. |

Two-sided raises the critical value (~1.96 vs 1.645 one-sided), costing power. Optimistic
corner `(0.045 / 0.10, n=42)` → ncp ≈ 2.92 → two-sided power ≈ **0.83** → **PROCEED** (a floor,
not clearance; central sits below the hurdle, as expected). If the honest band cannot clear the
optimistic corner two-sided, **ABANDON is dispositive.**

---

## 6. Acceptance (ordered; standalone before combination)

1. **RFA gate:** PROCEED at the two-sided optimistic corner. ABANDON dispositive.
2. **TRAIN (2016-07 → 2020-12):** rank-IC two-sided significant (AC₁-corrected); read the sign;
   net quintile spread > 0 under fees; IC SD inside [0.10, 0.18].
3. **HOLDOUT (2021–22):** the TRAIN-read sign **persists** and net spread > 0; no parameter
   touched between TRAIN and HOLDOUT.
4. **Composite:** Skew feeds the realized composite; **0.80 binds on the composite**
   (`CARRY_PHASE0_PRE_REGISTRATION.md` §13 rule 3).
5. **SEALED (2023–26):** one final read, reported as-is.

---

## 7. Falsifiable predictions (before the run)

1. Skew rank-IC is two-sided significant on TRAIN.
2. Its sign **persists** from TRAIN to HOLDOUT (a sign flip between the two = the effect is
   noise, and Skew is dead).
3. IC survives beta/sector neutralization (neutralized magnitude ≥ 60% of raw).
4. Net quintile spread > 0 under futures fees on the liquid subset.

---

## 8. Key files (to be created)

| File | Purpose |
|---|---|
| `governance/rfa/declarations/skew.py` | Frozen RFA declaration (bands, n*, `two_sided`) |
| `scripts/signal_engine/skew/build_skew.py` | §3 skew construction from the option chain |
| `scripts/signal_engine/skew/run_train.py` | §6 TRAIN read → `SKEW_TRAIN_REPORT.md` |
| `tests/signal_engine/skew/` | skew-construction + neutralization unit tests |
| `docs/reports/SKEW_TRAIN_REPORT.md` | script-generated TRAIN report (no hand-edited numbers) |

---

## 9. Freeze

On approval: SHA-256 over this file; record in `skew.py`. §1 (two-sided, no pre-committed sign),
§3 (construction, risk-reversal pinned), §5 (bands), §6 (acceptance) immutable. Any change
starts a new pre-registration.
