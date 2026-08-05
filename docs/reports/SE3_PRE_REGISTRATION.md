# SE-3 — Index-versus-Constituent Dispersion: Pre-Registration

**Status:** **FROZEN 2026-08-05** by operator approval, all §9 items resolved. No construct code
exists. The confirmatory window has not been opened.
**Digest:** SHA-256 over this whole file, recorded in `SE3_IMPLEMENTATION_PROMPT.md` and `CLAUDE.md`
— **deliberately not written into this file**, because a digest taken over the whole file cannot be
recorded inside it without being self-referential (the `cb_n50.py` defect, `CLAUDE.md` RFA §).
**Declaration:** `governance/rfa/declarations/se3.py`, SHA-256 `fd91b1d5…` — **RFA PROCEED**,
max power 1.0000 (`SE-3_RFA.md`).
**δ band derivation:** `SE3_DELTA_ANCHOR_LITERATURE.md`. **sd source:** `SE3_BREADTH_PROBE_REPORT.md`.

---

## 0. What this document is

The frozen declaration's `window` field requires that **every parameter be pinned before the
confirmatory window is opened**, because the burned 2023–2025 window is the only surface on which a
rule could have been discovered and it is already spent.

This document does that pinning. It is the specification an implementer builds against; it is not
itself an implementation.

**Two things it must be read against:**

1. **PROCEED is a floor, not authorization.** The gate said "not provably infeasible." §7 and §9
   record the three risks the noncentral-t gate structurally cannot see.
2. **The author has read the probe output.** §3 is the mitigation: every parameter is traced either
   to the probe *spec* (written before anything ran) or marked as a new choice with its reason. The
   delta is auditable in one table rather than dispersed in prose.

---

## 1. Construct

### 1.1 Primary hypothesis

**Stock-level cross-sectional prediction.** On each trading day, can Nifty 50 constituents be ranked
by the richness of their own ATM options such that the ranking predicts the cross-section of
subsequent **delta-hedged** option returns?

```
per-date cross-sectional OLS: sigma_i = a + b * rv_i + eps_i
richness_i = eps_i                       (positive = option rich vs its own realized vol)
target     = vega-scaled delta-hedged return, t+1 -> t+2
metric     = daily cross-sectional Spearman rank IC
```

**Expected sign: NEGATIVE** — rich options subsequently underperform delta-hedged. This is the
variance risk premium, and the sign is fixed *a priori* by mechanism, independently confirmed by the
sign of Cao & Han's `VOL_deviation` coefficient. The declared test is nonetheless **two-sided**,
because the IVOL sleeve sign-flipped at SEALED on this same universe.

### 1.2 Variant A only

The probe measured two variants. **This pre-registration runs variant A and only variant A.**

Variant B (trailing 60-day β of name IV on index IV) **must not be computed on the confirmatory
window.** The δ band is anchored on Cao & Han's `VOL_deviation`, which is variant A's construction;
the literature says nothing about B. Running B would be an undeclared second test that reintroduces
the m = 2 already paid for on *a priori* grounds.

### 1.3 What this is NOT

| Rejected form | Reason |
|---|---|
| Index vol vs basket (the classic dispersion trade) | One number per day → `per_trade_pnl`, blocked by the √T wall |
| Any wing / skew / risk-reversal feature | **Voids the permissive window reading** — see §2.2 |
| Implied correlation `rho_imp` as a per-name signal | One number per day; per-name it is degenerate. Diagnostic only |
| An index view under a constituent veneer | CB-N50 binding constraint #3. The primary hypothesis must genuinely be stock-level |
| Variant B, or an A/B comparison | §1.2 |

---

## 2. Window structure

### 2.1 One shot. No TRAIN, no HOLDOUT, no reserve.

| Window | Dates | n | State |
|---|---|--:|---|
| **CONFIRMATORY** | 2016-02-11 → 2022-12-31 | **1,701** | Unread on index leg; Skew-exposed but unspent on stock leg |
| Burned (rule-discovery surface) | 2023-01-02 → 2025-12-31 | 713 | **Spent** by the breadth probe |
| Reserved forward tail | 2026-01-01 → 2026-07 | ~140 | **Unread — explicitly held back** |

**No split is permitted, and this is a hard constraint rather than a preference.** The frozen
declaration pins `n_available = 1701` over the whole span. Carving a TRAIN out of it would mean the
gate was run on an `n` that is not the confirmatory sample — which requires a **new declaration at
the lower n, re-approved and re-frozen**, not a reinterpretation of `fd91b1d5…`. It would also trade
away the central case for nothing: a ~740-formation confirmatory clears the optimistic corner (288)
but falls below central (756).

**No TRAIN is needed**, because the parameters were pinned in the probe spec before anything ran
(§3). This is SE-1's structure: the whole sample is confirmatory, there is no reserve, and every
choice must therefore be made now.

**The 2026 tail is reserved deliberately.** It is free to hold and is the only forward check that
will exist.

### 2.2 The falsification condition on the permissive reading

Restated from the frozen declaration, because it constrains §1 directly:

> **If SE-3's signal drifts from ATM level richness toward wing or skew features, the Skew sleeve's
> exposure becomes a spend, n falls to ≈495, and the permissive reading is void.**

At n ≈ 495 the band's central power is 0.6203. **This pre-registration therefore pins the signal to
ATM level richness** (§3, moneyness band `|ln(strike/F)| ≤ 0.10`) and admits no wing feature. Any
future amendment introducing one requires a new declaration at the strict n.

---

## 3. Parameters — provenance-marked

### 3.A Inherited verbatim from `SE3_BREADTH_PROBE_PROMPT.md` §3

These were pinned **before any SE-3 data was read** and are adopted unchanged. This is the *a priori*
pin that substitutes for a TRAIN.

| # | Parameter | Value | Probe § |
|---|---|---|---|
| A1 | Universe | PIT Nifty 50 via MCWB, month *M* → dates in *M+1* only; `DUMMY*`/`TMPV*` excluded | 3.1 |
| A2 | F&O-live guard | ≥1 `FUTSTK` row for that underlying on that date | 3.1 |
| A3 | Expiry selection | nearest expiry with `DTE ≥ 7`, subject to `DTE ≤ 60`; else drop and count | 3.2 |
| A4 | Forward | `FUTSTK` settle for the matching expiry; parity fallback; else drop | 3.3 |
| A5 | Traded filter | `contracts > 0` **and** `open_int > 0` — **not optional**; settle-only strikes are theoretical | 3.4 |
| A6 | Price floor | `settle ≥ 0.50` | 3.4 |
| A7 | Moneyness band | `\|ln(strike/F)\| ≤ 0.10` | 3.4 |
| A8 | ATM IV | mean of nearest-OTM call and nearest-OTM put Black-76 IV; whichever exists if only one | 3.4 |
| A9 | Inversion | `brentq` over σ ∈ [0.01, 5.0], tol 1e-6; discard non-convergent; **do not widen** | 3.4 |
| A10 | Realized vol | 21 trading days of front-month `FUTSTK` log returns, √252, ≥18 obs, **roll-gap returns dropped** | 3.5 |
| A11 | Richness (variant A) | per-date OLS `sigma_i = a + b·rv_i`; residual; **≥20 names** else drop date | 3.6 |
| A12 | Return construction | `(V_{t+1} − V_t) − Δ_t(F_{t+1} − F_t)`, scaled by `max(vega_t, 1e-6)`; call/put averaged | 3.7 |
| A13 | Metric | daily cross-sectional **Spearman** rank IC; ≥20 paired names | 3.9 |
| A14 | Black-76 code | imported from `scripts/osc/sd_probe.py` — **no reimplementation** | 1.7 |

### 3.B New choices — the auditable delta

Each is a decision the probe did not need, because the probe measured a property rather than
specifying a strategy. **Every one is marked with its reason so the operator audits the delta rather
than trusting the whole.**

| # | Choice | Pinned value | Reason it is not tuning |
|---|---|---|---|
| B1 | **Target horizon** | **skip-a-day: richness at `t` vs return over `t+1 → t+2`** | Adopted from the probe's *corrective run*, not its original spec — so it IS a delta and is marked. Forced by CRITICAL-1: in the same-day form `V_t` enters signal and return with opposite signs, so settle bounce drives the IC negative mechanically. **It is also the executable timeline** (signal from close `t`, act `t+1`, exit `t+2`) — the same shape as CB-N50. Statistical necessity and tradability coincide |
| B2 | **Signal winsorization** | **none** | Spearman rank IC is invariant to any strictly monotone transform, so winsorizing before ranking cannot change the metric. Adding it would be a free parameter with zero effect on the primary hypothesis — omitted rather than decorative |
| B3 | **Neutralization** | **none beyond A11's regression** | A11 already removes the vol-level component cross-sectionally. Adding beta/sector neutralization (as Carry does) is a new degree of freedom with **no literature anchor** — Cao & Han's coefficient is on a raw `VOL_deviation`, not a sector-neutral residual. Declining it keeps the construct matched to its own δ source |
| B4 | **Inference** | Newey–West, **lag 5**, on the daily IC series; **AC₁ reported unconditionally** | The gate applies no autocorrelation haircut, so PROCEED depends on the bands holding at reduced effective n. Lag 5 matches the probe's reporting. Probe measured AC₁ = −0.0248 (A skip-a-day) — favourable, but the disclosure is pinned regardless |
| B5 | **α** | **0.05, two-sided, single test** | One hypothesis, one window, one read. m = 1. The variant selection (m = 2) was resolved *a priori* in §1.2, not by testing both |
| B6 | **P&L construction** | quintile L/S on richness, equal-weight, daily formation, vega-scaled | Diagnostic only — see §4. Simplest construction that expresses the ranking; no banding, no sizing rule, no turnover control, because each would be an unanchored parameter |
| B7 | **Cost treatment** | **sensitivity ladder, not a point estimate** | Forced by the §5 substrate finding. See §5 |
| B8 | **Minimum-N for a date** | ≥20 names (A11/A13), applied identically to signal and IC | Inherited, restated here because it now also gates the P&L diagnostic |

**Nothing else may be added.** If implementation reveals a genuinely unspecified case, it is reported
and the run stops — it is not resolved by the implementer's judgement.

---

## 4. The P&L question — pre-declared, before the read

**The primary hypothesis is the daily cross-sectional IC. P&L is a reported diagnostic and CANNOT
falsify the IC claim.**

This is pinned in advance because it is where CB-N50 died: it chose an execution vehicle whose
directional check was already known to fail, and spent gates on it. The frozen SE-3 declaration
already records the reason a P&L gate is the wrong instrument here — **`N_eff` = 5.9** (itself an
upper estimate). A ~46-name book with ~6 independent bets is not the same object as a 29.4-breadth
rank statistic, and a `rank_ic` PROCEED does not imply a `per_trade_pnl` PROCEED.

Outcome matrix, declared now:

| IC | P&L (net) | Reading | Action |
|---|---|---|---|
| Significant, correct sign | Positive | Prediction and harvest both demonstrated | Candidate for design; still not a build authorization |
| **Significant, correct sign** | **Negative or indistinguishable** | **"Real but unharvestable"** | **NO-BUILD. The IC finding stands and is recorded. This is the expected outcome given `N_eff` 5.9 and §5** |
| Not significant | either | Construct falsified | Closed. No successor authorized by this outcome |
| Significant, **wrong sign** | either | Mechanism contradicted — the IVOL failure mode | Closed. A sign flip is not a signal to re-specify |

**No fallback branch is declared.** At one confirmatory window a documented failure *is* the outcome,
and a pre-registered "if it fails, try X" is a second test.

---

## 5. Substrate finding — the mandatory cost gate is NOT measurable historically

The frozen declaration commits to a net-of-cost read as "a mandatory design-stage gate." **Verified
2026-08-05: it cannot be run on the confirmatory panel.**

`DESCRIBE stock_options_bhavcopy` and `DESCRIBE option_bhavcopy` both return:

```
underlying/symbol, expiry_dt, strike, option_type,
open, high, low, close, settle, contracts, val_in_lakh, open_int, chg_in_oi, trade_date
```

**There is no bid and no ask.** Cao & Han's entire cost result is expressed as a *fraction of the
quoted spread* — and their effect dies at 50% of it. The one number that decides whether SE-3 is
worth building is therefore **not recoverable from 2016–2022 data at any effort.**

Stating this now rather than discovering it mid-run. Consequences, pinned:

1. **Costs enter as a sensitivity ladder, not a measurement** (B7). Report net P&L at assumed
   round-trip option costs of **0 / 25 / 50 / 100 bps of premium**, plus statutory charges
   (options STT is sell-side on premium; exchange, SEBI, stamp, GST) and the futures-leg hedge cost.
   The ladder mirrors Cao & Han's own 0 / 25% / 50% structure so the two are comparable.
2. **The ladder is labelled an assumption everywhere it appears.** It is not evidence about Indian
   single-stock option spreads.
3. **The real spread measurement is forward-only.** `core/analytics/options_selection.py` already
   screens live bid/ask (`MAX_SPREAD_PCT = 5%`, `MIN_OI = 100`). Calibrating an honest Indian
   single-stock option spread distribution is a **forward collection task that costs no historical
   window** and should run independently of this construct.
4. **Weak proxies are not substituted.** `val_in_lakh / contracts` gives an average traded price that
   could be compared to settle, and `high − low` gives a daily range — neither is a quoted spread,
   and both are confounded by intraday drift. Using either as if it measured cost would be the
   "printed but never asserted" failure the repo already has a pitfall entry for.

---

## 6. Phases and gates

### Phase 1 — Substrate certification (no returns computed)

Structural counts only, on the SE-1 counting-pass precedent. **Runs AFTER this document is frozen**;
running it first would let survival counts select the filter thresholds, which is tuning on the
confirmatory window through the back door.

| Check | Requirement |
|---|---|
| S1 | PIT membership resolves for every date in span; `DUMMY*`/`TMPV*` excluded and reported |
| S2 | Names/day surviving A1–A11 — **report distribution; do not adjust filters in response** |
| S3 | Usable formation dates, reconciled against `n = 1,701` — **explicit PASS/FAIL against `S3_MIN_USABLE_DATES = 756`** (§9.4) |
| S4 | Expiry coverage: no month with zero admissible expiry under A3 |
| S5 | IV inversion discard rate (A9) |
| S6 | Fence assertion: no read outside 2016-02-11 → 2022-12-31 |

**S3 is the one that can stop the project.** If usable dates fall **below 756**, the frozen
`n_available` is wrong in a way that matters and **the declaration must be re-approved at the true n
before any IC is computed** — not reinterpreted afterward. A shortfall that leaves the count at or
above 756 is reported, not acted on: it does not change which corner of the declared band is
demonstrable.

**No return, IC, or P&L may be computed in Phase 1.**

### Phase 2 — Confirmatory read (one shot, never re-run)

| Gate | Criterion |
|---|---|
| **G1 (primary)** | Mean daily cross-sectional rank IC significant at **α = 0.05 two-sided**, Newey–West lag 5. AC₁ reported |
| G2 (sign) | Sign is **negative**, as declared. A significant positive IC is a **falsification**, not a re-specification opportunity (§4) |
| D1 (diagnostic) | Quintile L/S P&L across the §5 cost ladder — **reported, not gating** |
| D2 (diagnostic) | Realized `sd_IC` on the confirmatory window vs the declared band [0.1877, 0.26] — the C2 check |
| D3 (diagnostic) | Realized `N_eff` and `rho_bar`, comparable to the probe's 5.9 / 0.150 |

All outputs frozen in `SE3_CONFIRMATORY_SNAPSHOT.json`.

**D2 deserves its own note.** If realized `sd_IC` lands outside [0.1877, 0.26], the declaration's sd
band was wrong. That does not retroactively invalidate G1 — the test is run on the realized data
either way — but it must be reported prominently, because it is exactly the failure that retired C2.

---

## 7. What a PASS does and does not authorize

**Does not authorize a build.** Even G1 PASS + positive P&L leaves untouched:

- **The correlation tail.** `STRUCTURAL_ALPHA_DOSSIER_2.md` §G: *a dispersion book reports an
  attractive Sharpe until correlation goes to one*, and neither the noncentral-t gate nor a rank IC
  sees that. Nothing in this pre-registration measures it.
- **Implementation difficulty: "Very High"** — simultaneous single-stock option positions with daily
  delta hedging across ~46 names, at retail scale.
- **The cost question**, which §5 establishes is unanswerable from history.

A PASS means: *the cross-sectional prediction is demonstrable.* That is all it means.

---

## 8. Prior exposure

Carried from the frozen declaration (`se3.py`, `prior_exposure`) and not restated in full. In brief:
two structural-alpha dossiers; the SE-3 breadth probe (which **spent** the OPTSTK 2023–2025 leg and
whose `mean_IC` is **prohibited** as the δ anchor); the Skew sleeve's 2016–2020 TRAIN read, treated as
disclosed exposure under the operator's permissive decision; OSC's abandoned probe on the same index
window; and the m = 2 variant selection resolved *a priori*.

**No SE-3 return has ever been computed outside the burned window.**

---

## 9. Operator decisions — RESOLVED at freeze, 2026-08-05

All four were open in the draft and are settled here. **Each is now a pinned term of this
pre-registration and carries the same force as §3's parameters** — none may be revisited in response
to a result.

1. **Run the D1 P&L diagnostic — DECIDED: YES, labelled a sensitivity.** §4 predicts "real but
   unharvestable" is the likely outcome and §5 shows costs cannot be measured, so the number will be
   tempting to over-read. It runs anyway, because it costs no extra window (same read) and **§4's
   outcome matrix binds how it is read**: significant IC with negative or indistinguishable P&L is
   pre-declared **NO-BUILD with the IC finding standing**, not a failure of the hypothesis.
2. **Forward spread collection (§5.3) — DECIDED: YES, starts independently.** It costs no window and
   is the only route to an honest Indian single-stock option spread distribution. It is **not a
   dependency of this run** and its absence does not delay Phase 1 or Phase 2; §5's ladder remains
   an assumption regardless of when collection starts.
3. **S3 is a stop-and-re-approve — DECIDED: confirmed, and enforced in code rather than understood.**
   `SE3_IMPLEMENTATION_PROMPT.md` §1.6 requires Phase 2 to refuse to start unless the Phase-1 report
   records S3 PASS — a hard exit, not a warning, not bypassable by a flag. The repo's own pitfall
   applies: a value that is printed but never asserted is documentation, not a control.
4. **`S3_MIN_USABLE_DATES` — DECIDED: 756.** This is the declared band's **central** `n_required`
   (`SE-3_RFA.md`; 288 optimistic corner, 2,492 pessimistic floor). Rationale: it is the only
   candidate tied to something this declaration actually asserts. At or above 756, every claim made
   about the central case survives the shortfall and the run proceeds with the shortfall reported;
   below it, only the optimistic corner remains demonstrable — a materially different claim from the
   one approved, which is exactly the condition that requires re-approval at the true n. A
   percentage-of-1,701 threshold was considered and rejected as arbitrary.

---

## 10. References

- `governance/rfa/declarations/se3.py` — frozen declaration, SHA-256 `fd91b1d5…`
- `docs/reports/SE-3_RFA.md` — gate report, PROCEED, max power 1.0000
- `docs/reports/SE3_DELTA_ANCHOR_LITERATURE.md` — δ band derivation from four primary sources
- `docs/reports/SE3_BREADTH_PROBE_{PROMPT,REPORT}.md` — the *a priori* parameter pin and the sd measurement
- `docs/reports/SE3_BREADTH_PROBE_REVIEW{,_2}.md` — reviews; operator decision adopting n = 1,701
- `docs/reports/CB_N50_PRE_REGISTRATION.md` — structural template; its binding constraint #3
- `docs/reports/OSC_RFA_ABANDON.md` — why breadth was measured before anything was declared
- Cao & Han (JFE 2013); Bakshi & Kapadia (JoD 2003, RFS 2003); Driessen, Maenhout & Vilkov (JF 2009);
  Goyal & Saretto (JFE 2009) — full citations in `SE3_DELTA_ANCHOR_LITERATURE.md`
