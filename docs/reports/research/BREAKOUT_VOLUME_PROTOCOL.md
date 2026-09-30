# BKV-1 — M3a × M5b: Range Breakout + Abnormal-Volume Confirmation — Research Protocol v1.0 (FROZEN)

**Status:** FROZEN at the freeze commit recorded in `breakout_volume_FREEZE.json`. **No forward return existed
before the freeze:** the only pre-freeze data reads were the snapshot build (prices ≤ 2022-12-30, no HOLDOUT
price in it), outcome-free event counts (`diagnostics.py`), and a synthetic-data dry run of the whole pipeline.
**Branch / worktree:** `research/breakout-volume` in `F:\Nifty_bkv` (cut from `origin/main` `6ad150a`; the live
orchestrator checkout `F:\Nifty` stays on `main`).
**Governing vocabulary:** the closure ledger `docs/reports/external/RESEARCH_CLOSURE_LEDGER_2026-09-29.md`
(C0–C9; **not on `main`** — it lives on branch `docs/vwap-ledger-closure`, commit `5144d52`) and the
M1c/VWAP precedents (`M1C_RESEARCH_PROTOCOL_v1.3.md`, `VWAP_EXTREME_REVERSION_RESEARCH_REPORT.md`).
**No RFA is created** — the frozen process did not require one for this construct; the study reports the
minimum detectable effect (MDE) instead (§14). The Vault governance framework is not modified.

---

## 1. Question and hypotheses

**Question.** When an individual stock breaks out of a multi-day closing range, does unusually high
contemporaneous volume distinguish breakouts that continue from breakouts that fail?

**Direction convention.** Upside breakout → long; downside breakout → short; the estimand is signed so that
**continuation is positive**. A significant *negative* result (failure/reversal) is a distinct finding,
reported and never counted as support.

**Primary hypothesis (per cell c = (N, H, side)).** μ_c = E[ f_B − f_C ] > 0, where f is the direction-signed,
market-excess forward return (§6) of a breakout with abnormal volume (B) and without (C), paired by formation
date. **H0: μ_c ≤ 0.** The contrast is primary because the question is whether *volume distinguishes*
breakouts, not whether breakouts as such continue.

**Secondary (descriptive, non-classifying, unadjusted):** the four arm means A, B, C, D against zero (§5, §7.4).

## 2. Why this construct, and what the Vault already says

* Coverage map v1.1: **M3a** (range-escape continuation) status **B**, evidence = RELIANCE long/flat
  `donchian_{63,252}` — one name, no pre-registration, IC defect R1; **M5b** (volume-confirmed moves) status
  **C**, evidence = a *conjunct* inside MRLC. Ledger §3: M3a **B**, M5b **C** — "open".
* MRLC (M3b) used "close below the prior-10-session low on ≥ 2× usual volume, then reclaim" — a
  **reversal** construct. Its downside-breakout-with-volume cell overlaps this study's dn/B arm at
  *formation*; the outcome measured here (continuation of the breakout, no reclaim conditioning) is different.
* No prior experiment measures breakout continuation, with and without volume, over a PIT liquid panel.

## 3. Prior exposure and window status (disclosed before any read; register `governance/exposure/RESEARCH_EXPOSURE_REGISTER.md`)

* **Equity EOD 2012 → 2022-12-30 is already signal-spent** by PSB-1/PSB-2/C2 Phase 0.5 (rows Q-1…Q-3), the
  Gann Stage-1 screen (G-S1), MRLC (2012–22 daily, E-3) and the N200 regime HMM (feature, Q-4). Under
  GR-1.3 a spent window **can never be confirmatory**. TRAIN and VAL here are therefore **not naive**: a VAL
  pass is a consistency check whose confirmatory weight would rest on the HOLDOUT.
* **Equity EOD 2023-01 → present is "largely unread at signal level"** (register §6) but (i) MRLC read 2023+
  1m equity breadth (E-3), (ii) row **Q-6** reserves 2023-01 → 2026-06 for the CSMP 12-1 momentum lineage
  (lineage-local, not global). Reading it as HOLDOUT spends a window a successor might want → **operator
  decision** (§8): it is read only if VAL confirms *and* the operator authorises; the authorisation record and a
  new register row are prerequisites.
* N = 20 / 63, the 2× volume threshold, and H = 5 / 20 were chosen with knowledge of the RELIANCE
  (`donchian_63`) and MRLC (2× volume) precedents and standard practice (one month; one quarter; one week;
  one month) — defended by precedent, **not tuned**, and no other values are tried in the primary analysis.

## 4. Data and substrate

* **Store:** `data/market_data/equity_bhavcopy.duckdb` → `equity_bhavcopy_adjusted` (CA-adjusted OHLC; `volume`
  divided by the cumulative bonus/split factor; certified by the PSB-1 four-arm contract suite). Adjusted
  prices and adjusted volume are used everywhere; raw as-traded rows are used only by the independent checks.
* **Snapshot (once, hashed, before the freeze):** `scripts/breakout_vol/prep.py --` writes
  `panel_dev / calendar_dev / membership_dev.parquet` under `data/research/breakout_volume/` with panel_max_date
  **2022-12-30** while the store runs to 2026-09-29 (the fence is proven non-vacuous in `manifest_dev.json`).
  SHA-256: panel `46de7d4d…`, calendar `73addee2…`, membership `db87add8…` (full hashes in the freeze record).
  1,341,582 panel rows; 0 duplicate (entity, date) listings.
* **Universe (single, no alternative):** the CSMP point-in-time **top-200 by trailing-6-month median turnover**
  (`universe_membership`, method `turnover_top200`, monthly rebalance on the last full session; entity via
  `universe_eligibility`, recycled tickers and ISIN re-issues handled by the certified `symbol_entity_intervals`).
  Membership on session t = the members of the **last rebalance strictly before t** (a rebalance-day
  ranking uses that day's turnover, so it is not used on that day). Names delisted later are included while
  listed; nothing is projected backwards from a current list.
* **Regular-session calendar (mechanical, rule-based):** `trading_calendar` dates with `n_symbols ≥ 200`
  (missing → 0), Monday–Friday, **and** total EQ-series turnover ≥ 0.40 × the centred 21-session median (removes
  Diwali Muhurat sessions, special Saturdays and defect days). Dropped in the snapshot span: 26 dates (22 inside 2012–2022), listed in
  `breakout_volume_diagnostics_outcome_free.json`: weekend specials, the Muhurat sessions, **2016-04-19** (a regular Tuesday
  that the store lists as `unresolved` with no rows) and **2017-07-10** (turnover ratio 0.26 of its neighbourhood; cause
  unverified — removed by the rule, not by judgement). Returns spanning a dropped date simply span it.
* **Valid row:** open, high, low, close, volume all present and > 0; every other (entity, session) is *missing*
  (never imputed, never forward-filled).
* **Eligibility for signal evaluation at session t:** valid rows on **every** session t−83 … t (84 sessions =
  63 + 20 + 1) **and** PIT member at t. One uniform requirement for N = 20 and 63 so the eligible set is
  identical for both.

## 5. Event definitions (all information through the CLOSE of t; nothing later)

Notation, per entity and session index t of the regular calendar: O, H, L, C, V = adjusted open, high, low, close;
adjusted volume (shares).

1. **Closing-range breakout (M3a).** `Mx_N(t) = max(C_{t−N}, …, C_{t−1})`, `Mn_N(t) = min(C_{t−N}, …, C_{t−1})`
   (today excluded, **closes**). `UP_N(t) = [C_t > Mx_N(t)]`, `DN_N(t) = [C_t < Mn_N(t)]`.
2. **Onset only.** `UPon_N(t) = UP_N(t) ∧ (UP_N(s) = 0 ∀ s ∈ [t−20, t−1])`; same for DN. The 20-session
   quiet period equals the longest holding period, so a name's holding windows on the same side never overlap.
   The rule uses **only the breakout flags**, never volume, so the volume split cannot alter which events exist.
3. **Abnormal volume (M5b).** `AV(t) = V_t / median(V_{t−20}, …, V_{t−1})` (today excluded).
   `ABN(t) = [AV(t) ≥ 2.0]`. Volume is the full-session volume of t (known at the close), adjusted for
   bonus/split; a turnover-based cross-check is in §11.
4. **Arms**, for each N and side:
   * **A** = onset breakouts (`UPon` / `DNon`); **B** = A ∧ ABN; **C** = A ∧ ¬ABN — so **A = B ⊔ C exactly**.
   * **D (control)**: `ABN(t) ∧ ¬UP_N(t) ∧ ¬DN_N(t) ∧ (ABN(s) = 0 ∀ s ∈ [t−20, t−1])`; D_up if `C_t > C_{t−1}`,
     D_dn if `C_t < C_{t−1}` (abnormal volume without a breakout, signed by the day's own direction).
5. **Sides:** *up* ↔ (UPon arms, D_up), *dn* ↔ (DNon arms, D_dn). Up-side events are long, down-side short.

## 6. Forward return, benchmark, units

* **Timing.** Signal known at the close of t → **entry at the adjusted open of t+1 → exit at the adjusted close of
  t+H**, H ∈ {5, 20} sessions. `R = C_{t+H} / O_{t+1} − 1`. The overnight gap `G = O_{t+1}/C_t − 1` is part of R
  (observable and tradable at the open) and is reported as a decomposition, never used to select anything. No
  same-day pairing of signal and return exists anywhere (the RELIANCE R1 defect).
* **Market benchmark.** `R_m(t,H)` = equal-weight mean of R over **all PIT members at t with a resolved window**
  (not only eligible-history names; events are included in their own benchmark, which is conservative), and it
  must contain ≥ 100 names, else the (date, H) has no benchmark and the event is excluded (counted).
* **Estimand.** `f = sign · (R − R_m) · 10⁴` **bp**, sign = +1 (up, D_up) / −1 (dn, D_dn). Also reported:
  `raw = sign · R · 10⁴` bp. Units are basis points of the entry-open notional throughout.
* **Window resolution (mechanical, exhaustive):** every session t+1…t+H valid → *normal*; the series ends
  (no valid row afterwards) with ≥ 60 sessions of panel remaining after the break and entry valid → *terminal*
  (exit at the last valid close; the return accrues to it); anything else (missing entry, a hole with the series
  resuming, an unresolved hole near the panel end) → *dropped*. Dropped events are never imputed; they enter only
  the attrition bound (§7.5).
* **Stage containment.** An event belongs to a stage only if its formation session **and its whole window (or
  terminal exit)** lie inside the stage. Lookback history may cross a stage boundary (prior information).

## 7. Estimand, inference, multiplicity

1. **Cohort series (dependence).** For each cell and arm X the observation at formation session t is the
   equal-weighted mean of f over the arm-X events formed at t. Cross-sectional dependence on a date is removed
   by construction; sessions with no event contribute nothing.
2. **Primary statistic.** `d(t) = m_B(t) − m_C(t)` on sessions with ≥ 1 B **and** ≥ 1 C event; `d̄ = mean d(t)`.
3. **Test.** One-sided (H1: d̄ > 0) t = d̄ / SE, SE from a **calendar-aware Newey–West (Bartlett) estimator with lag L = H**:
   z_i = d_i − d̄; g₀ = Σ z²/n; g_k = Σ over observation pairs exactly k sessions apart of z_i z_j / n; LRV = g₀ +
   2 Σ_{k=1..H} (1 − k/(H+1)) g_k; SE = √(LRV/n); p from Student-t with n−1 df. (Overlapping H-session windows
   induce MA structure up to lag H−1; the lag is pre-specified, not selected; gaps in the date index contribute no
   cross-products.)
4. **Family.** 8 primary cells = N ∈ {20, 63} × H ∈ {5, 20} × side ∈ {up, dn}. **VAL:** Holm over the 8 cells,
   α = 0.05 one-sided; a cell is **VAL-confirmed** iff Holm-adjusted p < 0.05, d̄ > 0 and it is not
   attrition-fragile. **HOLDOUT:** Holm over the VAL-confirmed cells only, α = 0.05, same conditions. TRAIN takes no
   decision. Arm-level tests (A/B/C/D vs 0), the event-weighted contrast, the two-way-clustered event contrast,
   the within-date permutation p and the block-bootstrap CI are **report-only** (unadjusted; not gates).
5. **Attrition bound (pre-specified, no discretion).** Recompute d̄ and its p with: dropped B events replaced by the
   smallest retained B value of the cell, dropped C events by the largest retained C value (both on their own
   formation date), terminal windows replaced only if the replacement is worse for the claim (the M1c v1.3 F-1
   rule). A cell is **attrition-fragile** if the bound flips the sign of d̄ or its Holm-adjusted bound-p ≥ 0.05.
6. **Weighting.** The primary statistic is cohort-by-date (each formation date once, whatever its event count).
   Because that weighting is not an implementable allocation, the **event-weighted** contrast and the economic
   gate (which uses event-weighted B returns) are reported beside it.

## 8. Stages and the HOLDOUT condition

| Stage | Formation & window | Role |
|---|---|---|
| TRAIN | 2012-01-02 → 2017-12-29 (1,474 sessions) | Descriptive only; **no parameter is pinned or changed on it** (all are pre-declared). Debugging of defects only, logged. |
| VAL | 2018-01-01 → 2022-12-30 (1,233 sessions) | Single confirmatory family (§7.4) — run as pinned or STOP |
| HOLDOUT | 2023-01-02 → 2026-09-29, one-shot | **Read only if (a) ≥ 1 VAL cell is confirmed, (b) the operator explicitly authorises the spend (record `breakout_volume_HOLDOUT_AUTHORISATION.json`), (c) a register row is added.** The full snapshot's file hashes and the store's unfenced max date are written into the one-shot read marker, so the read is reconstructable even though the store is mutated nightly. Otherwise it is never read, and the full-panel snapshot is never built. |

If VAL confirms nothing → **STOP: no HOLDOUT read, no re-specification, no second family/N/H.**

## 9. Economic analysis

Per event, one round trip on a ₹5,00,000 notional: BUY at the entry-open date and SELL at the exit date priced by
`core/execution/equity/delivery_fees.py` (era-accurate STT 0.1 % per leg, exchange, SEBI, stamp on the buy leg,
GST, DP charge on the sell leg) — the **existing delivery-equity methodology**, applied to *both* directions as a
conservative cost-scale proxy exactly as in M1c v1.3 §11 (a multi-day short in cash delivery is not implementable
and no short fee schedule is invented; the down-side is mechanism evidence, not a strategy). Slippage κ bp per side,
scenarios {0, 2.5, 5, 10}, **base 5** (judgement for opening-print entries on breakout days — disclosed as an
assumption; the break-even κ is reported so the conclusion does not depend on it). **Economic gate** (HOLDOUT-confirmed
cell only): event-weighted B net-of-cost mean > 0 at κ = 5 **and** the block-bootstrap one-sided lower bound at level
α/m > 0. Costs are descriptive on TRAIN/VAL.

## 10. Classification (Vault closure-ledger vocabulary; mapping fixed here, before any result)

| Label | Condition (first match, top to bottom) |
|---|---|
| **C4** | a pre-listed defect trigger fires: frozen file hash mismatch; an independent-verification disagreement beyond tolerance (`stop=True`); accounting identity failure; benchmark identity failure |
| **C5** | the pre-registered criterion was tested on data and failed: **no VAL-confirmed cell**, or VAL-confirmed cells that the one-shot HOLDOUT did not confirm — always **"construct-scoped"** |
| **C6** | ≥ 1 VAL-confirmed cell and the HOLDOUT unread (unspent or not authorised): positive but incomplete |
| **C7** | HOLDOUT-confirmed (clean, non-fragile) but the economic gate fails |
| **C8** | HOLDOUT-confirmed and the economic gate passes |
| **C9** | independent replication window — unreachable on this substrate (stated, not pursued) |

A failed HOLDOUT after a VAL pass is **C5 (never C6)** — the ledger scores that shape as C5 (IVOL, Analog Path,
VWAP). Any category is quoted with its scope (the specified construct; M3a and M5b stay open as mechanisms).
Results that cannot be reproduced by the independent paths are labelled **NOT AUDITABLE** and are not used.

## 11. Independent verification (pre-declared; `verify_independent.py`, frozen; a disagreement STOPs the run)

| # | Check | Two methods | Tolerance |
|---|---|---|---|
| VP1 | every event: existence, arm, AV, R, R_m, f | numpy/pandas engine vs **pure-SQL** window-function re-derivation from the same snapshot (its own calendar, membership, flags, windows, terminal rule, benchmark) | sets equal; arms equal; f within 1e-6 bp |
| VP2 | seeded event sample (3 per N×kind×arm); events with any adjustment factor in [t−83, exit] are skipped and counted | engine vs **plain-Python loops over the RAW as-traded table** (own Mx/median/AV/entry/exit/R). Compared quantities are **scale-free** (AV, R, breakout margin `C_t/level − 1`): adjusted price *levels* differ from raw ones for any name with a *later* bonus/split, by construction | 1e-9 |
| VP3 | every cell: cohort d(t), d̄, SE, t, p | table vs dict arithmetic from the event ledger + a pure-Python NW + `statsmodels.stats.sandwich_covariance.S_hac_simple` kernel | 1e-6 |
| VP4 | accounting: formed = resolved + dropped + contained-out + no-benchmark; A = B ⊔ C; unique event keys; one R_m per (date, H) | identity | exact |
| VP5 | volume: (a) adjusted = raw volume on names with no bonus/split (gate); (b) abnormal-flag agreement between volume-based and turnover-based (CA-invariant) AV (reported); (c) for names *with* a bonus/split, adjusted close and volume rebuilt from `adjustment_factors` (price = raw × Π later factors, volume = raw ÷ Π later bonus/split factors) — agreement rate reported | (a) 1e-6 |
| VP6 | fees: one BUY + one SELL by hand from the schedules vs the library | arithmetic | 1e-9 |

Report-only agreement checks (no pass/fail, but a sign flip of significance at 0.05 between the NW and the
within-date permutation p is investigated and disclosed): NW p vs permutation p vs two-way-clustered event p.
The pipeline was validated on a synthetic snapshot with delistings and holes (`tests/breakout_vol/test_pipeline_dryrun.py`)
before the freeze: the two engines agree exactly there, and the verifier fails on a deliberately tampered ledger.

## 12. Leakage / bias audit (each item has a control and an evidence pointer)

| Risk | Control | Evidence |
|---|---|---|
| Look-ahead in the signal | Mx/Mn/median use t−N…t−1 only; entry at the open of t+1; a test perturbs everything after t and shows the events up to t unchanged | `test_signal_is_causal…` |
| Today's volume in its own baseline | median over t−20…t−1; test: multiplying today's volume changes AV but not the baseline | `test_volume_baseline_excludes_today` |
| Volume/price timestamp mismatch | one row per (entity, date) from one source table, same calendar index for OHLC and V | VP1/VP2 |
| Membership look-ahead | last rebalance **strictly before** t | `test_membership_is_strictly_prior…` |
| Survivorship | PIT membership; delisted names stay while listed; terminal-price rule for series that end; attrition bound | §6, §7.5 |
| Universe changes | monthly PIT rebalance; benchmark defined on the same date's members | §4, §6 |
| Overlapping events (same name) | onset-only with a 20-session quiet period = the longest H | §5 |
| Event clustering (dates) | cohort-by-date observation; HAC with lag H; permutation and clustered checks | §7 |
| Duplicated observations | unique (entity, t, N, kind); PSB rn = 1 listing pick; test + VP4 | VP4 |
| Weighting mistakes | cohort-weighted primary + event-weighted beside it; `A = B ⊔ C` identity | §7.6, VP4 |
| Corporate-action basis | certified adjusted view for prices and volume; no 1m/bhavcopy join; events with a CA in the span reported as a post-primary exclusion sensitivity | §13 |
| Special / short sessions | rule-based removal of 26 snapshot-span dates (§4). The centred 21-session median uses ten future sessions' turnover; checked outcome-free that a strictly-prior trailing-21 median drops the **identical** 10 short-session dates (max dropped ratio 0.30 vs min kept 0.52 — the 0.40 cut sits in a wide empty gap), so the calendar is not sensitive to the look-ahead | `breakout_volume_diagnostics_outcome_free.json`, log L8 |
| Denominator errors | every count reconciles by identity (`accounting_*.json`) | VP4 |
| Multiple testing / parameter selection | 8-cell family, Holm; nothing tuned on TRAIN; post-primary variants are disclosure only | §7.4, §13 |
| Cost assumptions | existing delivery-fee model; κ disclosed, break-even reported; short leg is proxy-priced | §9 |

## 13. Declared post-primary analyses (disclosure only; cannot change any label or be promoted)

(R1) high/low-based range instead of closes; (R2) AV thresholds 1.5 and 3.0; (R3) non-declustered events (expected to be
a look-ahead-weighting artefact — the VWAP report's non-declustered variant was one); (R4) exclude events with any
bonus/split/special-dividend adjustment in [t−83, t+H+1]; (R5) overnight-gap vs post-open decomposition of f;
(R6) turnover-based AV flag; (R7) by calendar year (stability); (R8) excluding terminal-truncated windows; **(R9) move-size confound**: B days are by construction larger-move days (bigger day-t return, deeper breakout, likely a bigger t+1 gap), so a positive B − C could mean "deep breakouts continue" rather than "volume confirms". Declared now, report-only: the paired B − C contrast (same NW) **within terciles of breakout penetration depth** `|C_t/level − 1|`, with tercile cut points fixed **once per (N, side) from the pooled TRAIN ∪ VAL A-arm events** and applied unchanged to any later stage, plus the share of B events in each tercile. It gates nothing.
Anything else is a new pre-registration.

## 14. Power, and what a null can and cannot say

No RFA is run. The **MDE at 80 % power** (one-sided, from the NW SE of each cell) is reported per cell and per stage.
Pre-run expectation (stated to be falsifiable): with roughly one B and one C event per formation date, the H = 20 cells
are likely to have MDEs larger than any plausible continuation premium, so **the modal outcome is "no VAL cell
confirmed" (C5)**. That is a statement about what this design can demonstrate, not evidence that volume does not matter:
a C5 here means the pre-registered criterion failed on data, and M3a and M5b remain open as mechanisms.

**Pre-run mechanical predictions (checked in the report):** (i) A = B ⊔ C exactly in every cell; (ii) the mean over the
whole benchmark set of (R − R_m) is 0 to machine precision on every date; (iii) the event counts in
`diagnostics_outcome_free.json` reproduce; (iv) VP1 agrees with the ledger event-for-event with zero exceptions;
(v) fewer than one of the eight VAL cells confirms under H0 with probability ≈ 1 − 0.05.

## 15. Refused in advance (rescues)

Any change of N, H, threshold, range definition (closes → highs), universe, estimand, weighting, or event definition
after seeing a result; a second HOLDOUT read; promoting a post-primary variant, a subgroup, a single year, or a single
side; re-labelling a failed HOLDOUT as C6; pooling TRAIN into a confirmatory statement.

## 16. Reproducibility

```bash
git worktree add -b research/breakout-volume ../Nifty_bkv origin/main
python -m scripts.breakout_vol.prep                 # dev snapshot (<= 2022-12-30), hashed
python -m scripts.breakout_vol.diagnostics          # outcome-free counts
python -m pytest tests/breakout_vol -q              # unit + governance + synthetic end-to-end
python -m scripts.breakout_vol.freeze               # only on a clean tree, before any outcome
python -m scripts.breakout_vol.run_stage TRAIN ; python -m scripts.breakout_vol.run_stage VAL
python -m scripts.breakout_vol.verify_independent TRAIN ; ... VAL
python -m scripts.breakout_vol.run_stage CLASSIFY
```
Determinism: seeded bootstrap (20260930) and permutation (20260931); every threshold is a function of prior sessions;
results reproduce byte-for-byte from the hashed snapshot.

---

## Amendments (append-only; each is logged in the freeze record `history` and the research log)

**A1 — 2026-09-30, verifier population only (VP2 skip rule, VP5 "clean" set and rebuild).** VP5(a) as frozen defined
"names with no bonus/split" at the **symbol** level. Run on TRAIN it failed (max |adjusted − raw| = 2.4e7 shares on 103 of
4,000 sampled rows). Diagnosis: all 11 offending entities had a bonus/split keyed to *another symbol of the same entity*
(PHILIPCARB→PCBL, SRTRANSFIN→SHRIRAMFIN, NIITTECH→COFORGE, …); the certified view adjusts per **entity**, so the check's
population, not the data or the engine, was wrong. Corrected to entity level in three places: VP5(a) clean set, VP5(c)
rebuild (factors of every symbol of the entity), and the VP2 skip rule (any factor of any symbol of the entity in
[t−83, exit]). The synthetic dry run now contains a rename chain with the split keyed to the new symbol; the symbol-level
check fails on it and the entity-level check passes. **No engine, analysis, classification or protocol-parameter code
changed; TRAIN results were computed before the amendment and are unchanged** (VP1, VP3, VP4 are unaffected by A1).
