# F1 — Phase 0 Pre-Registration Stub

**Candidate code:** **F1** (Futures-1)
**Battery lineage:** **SFB-1** — Stock-Futures Battery, Increment 1 (new lineage; a clean namespace break from the retired cash-equity `PSB` / `C#` sequence)
**Instrument class:** Liquid single-stock futures (NIFTY-50 core, extended to F&O-eligible NIFTY-200 constituents)
**Document type:** Phase 0 pre-registration **stub** — a design blueprint with pinned defaults and explicitly-flagged open decisions. **This is NOT a frozen protocol.** Freeze (§9 immutability, the SFB analogue of `PSB2_PROTOCOL.md` Rev 4) happens only after the open decisions in §11 are ratified by the operator.
**Status:** DRAFT — pre-substrate. No data has been read. No sealed window exists yet.
**Date:** 2026-07-18

---

## §0 Namespace break and closure acknowledgment

The cash-equity candidate sequence is terminally closed. This document does not inherit its namespace, its substrate assumptions, or its results.

| Legacy candidate | Battery | Terminal state |
|---|---|---|
| C1–C4 (weekly cross-sectional, cash equity) | PSB-1 | CLOSED 2026-07-14 — "no winner"; net spread negative under delivery STT |
| C5 (low-vol, monthly banded, cash equity) | PSB-1 | CLOSED — closest candidate; cleared IC + spread, **missed power** (0.54 < 0.80) |
| C2 (delivery-% anomaly, cash equity) | PSB-2 | **RETIRED 2026-07-18** — Phase 0 killed it before any sealed read; no turnover setting rescued a sub-gross-of-fees construct |
| C3 (delivery-conditioned reversal, cash equity) | PSB-2 | CLOSED — not eligible (net<0, power) |
| C4 (momentum staggered, cash equity) | PSB-2 | CLOSED — not eligible (power 0.41) |

**All cash-equity `C#` candidates (C1 through C5) are archived and hand nothing forward.** The recurring result across two batteries — *delivery-equity STT (0.1% per leg, both legs) dominates every sub-monthly cross-sectional construct* — is the structural reason for the instrument-class shift below, not a signal that any specific `C#` construct deserves resurrection.

**F1 is a new pre-registration, not a C2 reopen.** CLAUDE.md's PSB-2 guard note states this path is legitimate *only* as "a **new pre-registered candidate** with train/holdout/sealed structure and an exit rule pinned *before* seeing path data — never a C2 reopen or bolt-on." §5 and §8 below are the concrete discharge of that condition (see §10.3).

---

## §1 Scope

F1 is an **exploratory** single-candidate pre-registration for an intraday-bracketed, concentrated cross-sectional factor in **stock futures**. Its Phase 0 output is this blueprint. It authorizes **no** sealed read, **no** strategy code, and — critically — **no data ingestion** (see §6, the blocking substrate gate).

**Why futures, stated as a structural claim (not a hope):** the cash-equity conclusion was never "the signal is too weak." It was "STT is 0.1%/leg on both legs and no Indian cross-sectional effect clears a ~13pp/yr fee wall at sub-monthly turnover." Single-stock futures dissolve the *specific* wall that killed the `C#` sequence:

- No DP charges (no delivery, no demat movement).
- No 0.1% delivery STT on both legs; futures STT is levied on the **sell side only** at a derivatives rate (~0.0125–0.02%, era-dependent — pinned by the §6 fee-model deliverable, not asserted as a constant here).
- Estimated round-trip *exchange/tax* friction on the order of ~6–8 bps vs. ~22 bps delivery-equity.

**The STT turnover inversion is neutralized, not merely reduced.** In the cash-equity architecture an intraday bracket exit *added* a delivery round-trip and therefore *amplified* STT — the turnover floor was set by formation cadence and brackets could only make fees worse. In futures there is no per-round-trip delivery tax to amplify: triggering a bracket exit does not structurally inflate transaction tax the way holding-then-re-entering a delivery session did.

**But the binding constraint moves — it does not vanish.** In a ~10-name concentrated book the new dominant cost is almost certainly **slippage / market impact**, not tax. §7's Realized Turnover Drag metric foregrounds κ (per-side slippage) and impact, not STT. A futures construct that ignores impact in a concentrated book would repeat the `C#` error one abstraction layer up.

---

## §2 Hypothesis formulation

**Primary hypothesis.** *Intraday path-dependent bracket exits out-compete blind calendar (time-based) exits in liquid stock futures under identifiable structural conditions — specifically, when (a) the underlying return distribution over the holding horizon is fat-tailed / regime-heteroskedastic, so that a volatility-scaled stop truncates the adverse tail faster than a fixed calendar exit, and (b) transaction friction per exit is low enough (the futures fee structure) that the additional round-trips a bracket introduces are not self-defeating.*

**Falsifiable directional prediction (stated before any run, per repo research discipline):** on the training fold, the bracketed variant of F1 must show **higher expectancy AND lower max drawdown** than the identical signal with a pure calendar exit. If brackets improve expectancy but *worsen* max DD (i.e., they cut winners on noise, the documented cash-equity trailing-stop failure mode), the hypothesis is falsified and F1 reverts to a calendar-exit null — it does not get re-tuned toward a pass.

**Structural-condition sub-hypotheses (to be measured, report-only in Phase 0):**
- H1: bracket advantage concentrates in high-realized-vol regimes (ATR-percentile-conditioned).
- H2: bracket advantage is negative on gap-dominated days (overnight gaps front-run the intraday stop → the whiplash penalty, §4, dominates).
- H3: the calendar-exit fallback (Friday close) is where most P&L is realized; brackets are a tail-shaping overlay, not the primary alpha source.

---

## §3 Signal definition core

A baseline cross-sectional momentum/reversal engine, **deliberately concentrated** to maximize alpha intensity per name and to make the futures liquidity/impact assumption defensible.

- **Universe:** point-in-time **F&O-eligible** NIFTY-200 constituents (see §6 — the eligible set is historical and time-varying; *not* today's F&O list, and *not* every NIFTY-200 name — many lack liquid single-stock futures).
- **Concentration:** **Top 5% / ≤10 names** per side. The concentration is a design commitment: it is what makes a per-name impact model tractable and what the alpha-intensity thesis rests on. It is also the source of the §7 evaluation-method change (10 names is not a cross-section — see §7).
- **Base factor (pinned default, open for §11 ratification):** a **12-1 style cross-sectional momentum** score (11-month trailing return, most-recent month excluded to strip short-term reversal), ranked within the eligible universe, long the top ≤10 by score. A reversal variant (sign-flipped short-horizon) is a **candidate-defining alternative**, not a free parameter to sweep after seeing results — exactly one of {momentum, reversal} is pinned at freeze.
- **Rebalance cadence:** the factor forms on a **fixed calendar grid** (weekly formation is admissible here **because futures friction is ~1/3 of delivery** — the cash-equity "monthly-or-slower only" rule was a *fee* constraint, not a signal constraint, and it is lifted by the instrument shift). Cadence is pinned at §11 freeze; default candidate = **weekly formation, holding horizon one week (Friday-to-Friday), bracket overlay intra-week.**
- **Strategies stay dumb (Architecture Principle 1):** F1 emits ranked scores only. Sizing, the bracket state machine, and impact accounting live in the execution layer, never in the signal.

---

## §4 Path-dependency handling rules (conservative daily-OHLC bracket model)

F1's bracket exits are resolved from **daily roll-adjusted futures OHLC**, using the standard **conservative worst-case** sequence. This is deliberate: the "worst-case whiplash" penalty is the device that lets the study run on *daily* bars without tick data, by refusing to assume the favorable leg filled first whenever the day's range spans both brackets. The resolution is a deterministic priority ladder evaluated per holding day, in this exact order:

1. **Daily Open gap assessment (first priority).** If the day *opens* beyond a bracket — open ≤ SL (for a long) or open ≥ TP — the position exits **at the open price**. Gaps front-run intraday levels; they are resolved before any within-day logic. (Directly measures sub-hypothesis H2.)
2. **Worst-case Whiplash Day penalty (conservative tie-break).** If, on a non-gapped day, **both** the SL and TP lie within the day's `[Low, High]`, assume the **adverse leg (SL) fills first**. This is the conservative assumption that removes the need for intraday data — it never credits the favorable sequence to an ambiguous day.
3. **High/Low threshold intercept.** If exactly one bracket lies within `[Low, High]`, that bracket fills (TP at the take-profit price, SL at the stop price). Fills are at the bracket level, not the extreme.
4. **Friday close fallback (calendar exit).** If no bracket is intercepted by the end of the holding horizon, the position exits at the horizon-end close (the calendar/time exit). This fallback is the blind-exit baseline that §2's primary hypothesis is measured *against*.

**Fill-price convention:** gap exits at the open; bracket exits at the bracket price (no slippage credited *into* the fill price — slippage/impact is accounted separately in §7 so the two effects never net silently). This convention is pinned; it is not tunable.

---

## §5 Out-of-sample bracket-derivation discipline (the anti-snooping core)

This section exists to make the "not a C2 reopen" defense concrete. The single most dangerous move available here is reading TP/SL thresholds off the 2012–2022 excursion distribution (observed MFE/MAE) — that is post-hoc, in-sample fitting and is explicitly forbidden by the CLAUDE.md guard note.

**Pinned discipline:**

1. **Brackets are parameterized by volatility, not by observed excursions.** TP and SL are set as multiples of a **rolling ATR** computed *causally* from data strictly prior to the formation day: `SL = k_sl × ATR_n(t−1)`, `TP = k_tp × ATR_n(t−1)`. No bracket level is ever read from the realized High/Low/MFE/MAE distribution of the evaluation data.
2. **The multipliers `(k_sl, k_tp, n)` are chosen on an explicit training fold *only*** — never on the holdout, never on the sealed window, and never on the pooled 2012–2022 excursions. Selection is by cross-validated training-fold expectancy under §7's metrics, with the grid of admissible `(k_sl, k_tp, n)` declared in this document at §11 freeze (a small, pre-registered grid — not an open search).
3. **The exit rule is committed before any path (High/Low) data of the holdout or sealed window is touched.** Once frozen, `(k_sl, k_tp, n)` and the §4 ladder are immutable across the holdout and sealed reads.
4. **Regime parameterization is admissible, in-sample fitting is not.** ATR-percentile or structural-regime *conditioning* of the multipliers is allowed **iff** the conditioning map is itself fit only on the training fold and pinned before holdout. "Dynamic" must mean "a pre-committed function of causally-available state," never "re-optimized when the holdout disappoints."

---

## §6 Data substrate — **BLOCKING GATE (substrate does not yet exist)**

**This is the gate that determines whether F1 can run at all. It is stated honestly and up front.**

**Finding (verified 2026-07-18):** the repository contains **no stock-futures price history**. The only F&O artifact is `data/instruments/nse_fo_instruments.duckdb` — an *instrument master* (contract definitions), not OHLC. Every candle / bhavcopy store is cash equity or cash index.

**What F1 requires (and does not have):**

| Requirement | Status | Note |
|---|---|---|
| Daily roll-adjusted single-stock **futures OHLC**, 2012→present | **MISSING** | Ingestible via NSE historical **F&O bhavcopy** through the same path as the existing cash `bhavcopy_raw` pipeline. Surmountable, but requires an ingestion job that does not exist. |
| Point-in-time **F&O-eligible universe** (time-varying SEBI list) | **MISSING** | The eligible set changes over time; the §3 universe must be drawn from the *historical* list at each formation date. |
| Era-accurate **futures fee model** (analogue of `core/execution/equity/delivery_fees.py`) | **MISSING** | A required Phase-1 deliverable: sell-side STT at the derivatives rate, exchange txn charges, SEBI/GST/stamp, per era. **Do not hardcode ~6–8 bps** — pin a model. |
| **Continuous-series roll + back-adjustment convention** | **UNPINNED** | See below — the #1 new snooping surface. |

**Roll + back-adjustment (must be pinned before any data read — the futures analogue of PSB's entity-resolution / CA-adjustment discipline):**
- **Roll trigger** (pinned default, §11 ratification): roll near-month → next-month on **volume/OI confirmation** (first day next-month volume exceeds near-month), **capped at expiry-day close**. Calendar-only rolls are the fallback if OI history is unavailable.
- **Back-adjustment method** (pinned default): **ratio (proportional) adjustment**, which preserves percentage returns and scales cleanly with ATR-parameterized brackets (§5). Difference adjustment is rejected because it distorts ATR-relative bracket widths at historical price levels.
- Roll and adjustment choices can **manufacture or destroy** returns; they are pinned in this document and frozen before the first byte of futures data is scored. No post-hoc roll re-selection.

**Ingestion authorization (operator gate):** prior operator decision **D4** (carried through PSB-1 and PSB-2) forbade *any new data ingestion inside a screening battery*. F1's substrate provisioning therefore sits **outside and before** the battery: it is a **Phase −1 operator-authorized ingestion + certification step**, not a battery action. **No F1 candidate score may run until a certified futures substrate exists.** This mirrors PSB-2 §11's "no Phase 1 without a certified substrate" gate.

---

## §7 Evaluation and risk-management metrics

**Method change — retire the IC / noncentral-t machinery.** PSB-1/PSB-2 evaluated broad cross-sections with Spearman rank IC and a noncentral-t power projection. **That machinery is invalid for a ≤10-name concentrated book** — rank IC on 10 names is noise, and the noncentral-t projection assumes a wide cross-section. F1 is evaluated at the **portfolio (return-series) level**, which also happens to be exactly the user's declared risk-metric set:

| Metric | Definition | Role |
|---|---|---|
| **Expectancy** | Mean net P&L per round-trip (after §6 fees + §7 slippage/impact) | Primary — the §2 falsifiable prediction is stated in expectancy + max DD |
| **System Max Drawdown** | Peak-to-trough on the compounded portfolio equity curve | Primary — the bracket-vs-calendar comparison (H1–H3) turns on DD, not mean return |
| **Capital Efficiency (Days Held)** | Mean holding duration per round-trip; return-per-day-of-exposure | Distinguishes a bracket that exits fast + redeploys from one that merely cuts winners |
| **Realized Turnover Drag** | Annualized cost of realized turnover, decomposed into **fees (§6)** and **slippage/impact κ (per-side, concentration-aware)** | The new binding constraint. Impact — not STT — is expected to dominate in a 10-name book. |

**Significance / power projection:** by **return-series bootstrap** (block bootstrap of the portfolio return series to respect autocorrelation from overlapping holds), **not** noncentral-t. The sealed-read power hurdle and its exact bootstrap construction are pinned at §11 freeze. Bracket-vs-calendar is compared as **paired** return series (same signal, same formations, exit rule the only difference), so the comparison is not confounded by the base factor's own edge.

---

## §8 Train / holdout / sealed-window structure

Three disjoint temporal partitions, pinned before any data read. Exact boundaries are ratified at §11 freeze; the default structure:

| Partition | Window (default) | Use |
|---|---|---|
| **TRAIN** | 2012 → 2018 | Factor sign pinned; `(k_sl, k_tp, n)` bracket grid selected here **only** (§5); regime-conditioning map fit here **only** |
| **HOLDOUT** | 2019 → 2022 | Single out-of-sample confirmation of the frozen construct. One read. No re-tuning. |
| **SEALED** | 2023 → present | **Untouched.** Spent at most once, only if HOLDOUT confirms, only under a ratified freeze. Fenced CSMP-style (loaders assert `MAX(date)` on TRAIN/HOLDOUT). |

The C2 retirement is the cautionary precedent: C2's power projection rested on a 55-observation, 2.3-year SD estimate and did not survive a wider SD re-estimation on extended history. F1's TRAIN window is deliberately long (2012→2018) so the bracket-parameter SD estimate is not built on a thin recent sample.

---

## §9 What this stub does **not** authorize

- **No sealed read.** The 2023→present window is untouched and stays that way. Phase 0 earns, at most, the right to *propose* spending it later.
- **No data ingestion.** F1 cannot run until an operator authorizes the Phase −1 futures-bhavcopy ingestion + certification (§6). This document does not authorize that ingestion; it specifies what the ingestion must deliver.
- **No strategy code, no consumer.** Nothing lands in `core/strategies/`.
- **No parameter sweeps after results exist.** The §5 bracket grid and §3 factor are pinned at freeze; §11 lists exactly what freeze must fix.
- **No immutability apparatus yet.** This is a stub. The PSB-2-style §9 immutability ledger is written only at freeze, once §11 is ratified.

---

## §10 Discipline cross-checks

**10.1 — Fee dominance (the recurring repo lesson).** The `C#` sequence proved delivery STT dominates sub-monthly cash constructs three times. F1's entire premise is that the futures fee structure removes that specific wall — but §7 explicitly re-tests for the *replacement* wall (impact in a concentrated book). F1 is not exempt from fee dominance; it relocates it and measures it.

**10.2 — Trailing-stop caution.** CLAUDE.md: "Trailing stops on intraday equity **hurt** — cut winners on normal pullbacks." F1's brackets are **fixed** (ATR-scaled at entry), not trailing, and §2's falsification test (worsened max DD ⇒ hypothesis rejected) is precisely the tripwire for the cut-winners failure mode.

**10.3 — "Not a C2 reopen," discharged concretely.** The guard permits this *only* as a new pre-registration with (a) train/holdout/sealed structure — §8; (b) an exit rule pinned before path data — §5.3; (c) brackets not fitted to observed excursions — §5.1. All three are pinned above. F1 also carries a different instrument class (§1), a different evaluation method (§7), and a different binding cost (impact, §7) — it is not C2 with a futures label.

---

## §11 Open decisions to pin at freeze (before this stub becomes a protocol)

Freeze is the SFB analogue of PSB-2 Rev 4. It cannot happen until the operator ratifies:

1. **Factor:** momentum vs. reversal (exactly one), lookback, formation cadence, holding horizon.
2. **Concentration:** exact N (≤10) and weighting (equal vs. score-tilted).
3. **Bracket grid:** the admissible `(k_sl, k_tp, n)` set and the ATR definition/window.
4. **Roll + back-adjustment:** ratify the §6 defaults or amend.
5. **Fee + impact model:** the era schedule and the concentration-aware κ/impact function.
6. **Windows:** exact TRAIN/HOLDOUT/SEALED boundaries and the bootstrap power hurdle.
7. **Phase −1 ingestion authorization:** the operator decision that lifts D4 *for the pre-battery ingestion step only* (not inside the battery).

Until §11 is ratified and the §6 substrate is certified, F1 is a blueprint and nothing runs.

---

*Authored as Lead Quantitative Architect, 2026-07-18. Roles unchanged from the CSMP/PSB lineage: Claude writes pre-registration + reviews; implementation of any harness/ingestion is a separate prompted deliverable; the operator decides. This stub reads no data and consumes no sealed window.*
