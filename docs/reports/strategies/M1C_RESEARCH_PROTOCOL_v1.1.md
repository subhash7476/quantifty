# M1c: Single-Instrument Extreme Reversion — Research Protocol v1.1

**Status:** PROTOCOL DRAFT v1.1 (design only — not frozen, not approved, no runs authorized by this document).
**Date:** 2026-09-29. **Supersedes:** `M1C_RESEARCH_PROTOCOL_v1.md` (commit `d0dfb30`, truncated — see Change Log B1).
**Governing boundary:** `docs/reports/external/RESEARCH_MECHANISM_COVERAGE_MAP_v1.1_2026-09-29.md`
(**MAP**, FROZEN v1.1). M1c is status **C** (C/B borderline, MAP §4 row M1c, §8, §9).
**Review disposition:** `M1C_PROTOCOL_HOSTILE_REVIEW_2026-09-29.md` (B1, B2, M1–M8, m1–m5, N1–N6).
Every BLOCKER and MATERIAL item is resolved in text below (Change Log); N1–N6 required no change and are
preserved as stated. **Freeze is not claimed here** — it awaits independent re-review of the restored
§9–§15, a frozen RFA declaration, and operator approval.
**This document runs no backtest, writes no implementation code, spends no data window, and consumes
no gate.**

---

## 1. Research question and falsifiable hypothesis

**Research question.** Does an unusually extreme move in an individual instrument, measured relative to
that instrument's own recent history, produce subsequent mean reversion **without imposing the MRLC
sweep/volume conditions** (no level-breach test, no reclaim test, no volume filter)? Independence is
operationalized as (a) no sweep/volume condition in the formation rule (§4) and (b) price-only overlap
with MRLC-type breach structure quantified report-only (§9.1), with no effect on pinning or pass/fail.

**Falsifiable hypothesis (H1).** For the single family/horizon combination pinned by the §9 rule, the
expected **market-netted** signed contrarian forward return (§6, §8) is positive: down-tail formations
followed long and up-tail formations followed short earn more than the same-window universe mean.

**Null (H0).** The expected market-netted signed contrarian forward return is ≤ 0 (one-sided test, §10).

The hypothesis is falsified by a failure to reject H0 at any confirmatory stage (§11–§13). The sign is
pinned **before** any read: down-tail → long, up-tail → short. A significant continuation result is a
null for M1c (it belongs to M2c), not a re-interpretation.

---

## 2. Exact mechanism definition

**M1c mechanism (from MAP §3–§4).** Absolute, single-instrument, time-series reversion from an
own-history extreme: a move large relative to what *this instrument* recently did exhausts the marginal
flow (seller/buyer exhaustion, inventory pressure, stop-cluster depletion), so price drifts back toward
its prior level over the next several sessions.

**What it is not (boundary policing, per MAP §3.1 and §5):**

- Not M3b: no breach of a visible level, no sweep, no reclaim trigger is imposed. Overlap between
  tail events and breach structure is admitted (a ≤5th-percentile 5-session return will often sit below
  a recent low) and is quantified report-only in §9.1; it does not void the interpretation and does not
  alter any gate.
- Not M1a/M1b: no peer ranking, no cross-sectional sort, no market-residual construction. The reference
  distribution is the instrument's own history, never the cross-section.
- Not M2c: the predicted sign is opposite (reversion vs continuation). Continuation is the alternative
  hypothesis, not a variant.
- Not M5b: no volume or delivery condition, joint or otherwise. Volume is never read in this experiment.
- Not a sign rule: `reversal_5`-style "down day → long" without an extremeness threshold is a different,
  already-narrowly-tested construct (MAP §4 M1c) and is excluded here.
- Not sizing: martingale/DCA/grid overlays are non-mechanisms and are excluded.

---

## 3. Universe and PIT requirements

- **Universe (single, no alternative):** all NSE equity symbols with point-in-time listing on session *t*
  in the certified corporate-action-adjusted equity store — i.e. the same construction as the MRLC
  2012–22 daily panel ("2,300 symbols … point-in-time membership (includes names later delisted)",
  `MRLC_TEST_2026-08-30.md` §9). The v1 phrase "PIT F&O equity membership" is deleted: this is the broad
  listed-equity panel, not the ~200-name F&O list. A name is eligible on session *t* only if listed on *t*.
- **No liquidity filter is applied.** Equal weighting over the broad panel is therefore
  small/illiquid-name-dominated by construction — disclosed here as a limitation on the tradability
  reading, not on the mechanism test. (Precedent context: the MRLC size-split found its edge weaker in
  the large-cap 100; that comparison is descriptive context from another construct, not a claim about M1c.)
- **Entity correctness:** entity resolution via CSMP `symbol_entity_intervals` with ISIN issuer-prefix
  linkage (recycled tickers and face-value ISIN re-issues must not create false extremes). Any session
  whose entity mapping is ambiguous is dropped, not imputed.
- **Survivorship:** names enter while listed and leave on delisting; no backfilled history, no
  listed-today universe projected backward. Delisting *inside* a forward window is handled by the
  terminal-price rule (§3.1), not by dropping the formation.
- **Lookback completeness (uniform):** a formation requires **316 consecutive calendar trading sessions**
  ending on *t*, each with an available adjusted close (§5 arithmetic). Partial spans never form. The
  uniform span is the maximum across families so the eligible set is identical for F1–F3.
- **Return continuity:** all trailing and forward returns are computed on the certified adjusted view,
  never on a mixed adjusted/as-traded join. Coverage *is* the adjusted view: an (entity, session) absent
  from it is dropped by rule. Adjustment status is resolved solely from the committed disposition
  register and the certified view build — there is no implementer judgement call.
- **Calendar:** the 2012-11-11 Sunday bhavcopy artifact is excluded by rule. "Sessions" everywhere in
  this protocol means calendar trading sessions from `core/market/nse_holidays.py` / `trading_calendar`,
  never bar counts, never stored-date inference.

### 3.1 Mechanical missing-data rules (no judgement)

- Missing adjusted close anywhere in the required trailing span → formation dropped.
- Missing close inside the forward window with the series continuing (suspension with resumption) →
  formation dropped (no imputation).
- Series ends inside the forward window (delisting, no resumption) → terminal-price rule: the forward
  return accrues to the **last available adjusted close**, with no further accrual. The same rule applies
  to names in the market leg (§6).
- These three rules are exhaustive: every (formation, session) pair maps to exactly one of
  traded-as-pinned / dropped / terminal-truncated, with no residual discretion.

---

## 4. Event/formation definition

A formation is an **(instrument, session *t*)** pair satisfying all of the following, evaluated at the
close of *t*:

1. Universe- and PIT-eligible on *t* (§3), with complete lookback.
2. The trailing 5-session return `R5(t) = C(t)/C(t−5) − 1` (adjusted closes) scores in the **tails of its
   own trailing 252-session distribution** under the single pinned measurement family (§5), by the weak
   percentile convention: down-tail iff
   `(#{ref < x} + 0.5 · #{ref == x}) / 252 ≤ 0.05` (signed +1 / long); up-tail iff the symmetric
   condition holds at ≥ 0.95 (signed −1 / short). The current value is **excluded** from its own
   reference set; ties are averaged by the 0.5 term. No interpolation method is needed beyond this formula.
3. **No other condition.** In particular: no level-breach test, no reclaim test, no volume test, no
   peer comparison, no volatility-regime gate, no news filter (information-driven moves are part of the
   null population, which biases *toward* H0 and is therefore conservative; disclosed).

Non-tail pairs score 0 (no position, no observation). The signed score `s ∈ {+1, −1, 0}` is the **only**
signal this experiment tests.

---

## 5. Permissible measurement families and why they represent the same mechanism

No indicator is admitted because it is familiar. **RSI, Stochastic, KDJ, CCI, Williams, Bollinger %B,
MACD, and any band-oscillator trigger are excluded as event definitions in this first experiment**
(MAP §7: indicator-level novelty without economic distinction is not tested). Three families are
permitted because each is a distinct lens on the *same* mechanism — "this instrument's recent move is
extreme relative to what it usually does" — with no level, peer, volume, or breach content:

| Family | Score construction (all trailing, causal) | Why it is the same mechanism |
|---|---|---|
| F1. Own-percentile trailing return | Weak-percentile (§4) of `R5(t)` within the 252 reference values `R5(s)`, s ∈ [t−252, t−1] (overlapping by construction), same entity | Direct extremeness: rank of the move in its own history |
| F2. Vol-scaled excursion | `z(t) = R5(t)/σ(t)`, `σ(t)` = SD of the 63 daily returns ending on *t* (**including** the 5 formation sessions — a contemporaneous-scale normalization, stated); reference = `z(s) = R5(s)/σ(s)` with each date's own σ(s), s ∈ [t−252, t−1]; same weak-percentile tail rule | Same extremeness, normalized for current variability — a volatile name needs a larger move to qualify |
| F3. Range-expansion excursion | `q(t) = |R5(t)| / median(|R5| over the 252 reference sessions)`; reference = historical ratios `q(s)`, each computed with its **own** trailing median (fully causal); event iff weak-percentile of q(t) ≥ 0.95, direction from sign(R5(t)) | Same extremeness via the range lens. Disclosed asymmetry: F3 selects ≈5% of name-sessions one-sided, vs ≈10% total across both tails for F1/F2; event-rate differences are reported on TRAIN as properties, not flaws |

Uniformity rule: the **same** N (= 5 sessions, one trading week — the short-horizon precedent of M1a/M1b),
the **same** reference length (252 sessions, one annual cycle), and the **same** 5%/95% tail rule apply to
all three families. N, W, and tail cut are defended by precedent (weekly horizon; annual reference), not
tuned — no other values may be tried in this experiment. Eligibility arithmetic (auditable): F1/F3 need
closes t−257..t (258 sessions); F2 needs closes t−315..t (316 sessions: each σ(s) needs 64 closes, earliest
s = t−252); the uniform §3 rule is therefore 316. All three families are estimated descriptively
on TRAIN; **at most one** is pinned for confirmatory testing by the pre-stated rule in §9.

---

## 6. Forward horizons

- Observation window for a formation at *t*: sessions *t+2* through *t+1+H* (the 1-session gap is §7).
- Candidate horizons for TRAIN exploration (descriptive only): H ∈ {1, 5, 10}. No default: H is pinned
  **only** via the §9 TRAIN rule, never by prior preference and never by VAL results.
- Signed formation return (primary estimand, market-netted per §1/H0):
  `f = s · (R_fwd − U_fwd)`, where `R_fwd = C(t+1+H)/C(t+1) − 1` on adjusted closes (terminal-price rule,
  §3.1, if the series ends inside the window), and `U_fwd` is the same-window equal-weighted mean raw
  forward return over all universe names PIT-eligible on *t* with complete trailing span and valid
  forward span (same tradability rules, including the terminal rule). Positions are held passively inside
  the window, without rebalancing.
- TRAIN-only descriptive attribution also reports the non-netted series (`s·R_fwd`); it carries no gate
  and enters no test.

---

## 7. Entry/observation timing

- Measurement close: session *t* close (daily bhavcopy close; all §9 windows are pre-CAS, so no auction
  handling is needed).
- **Gap session *t+1*: never traded, never measured.** This kills bid-ask bounce, nonsynchronous-close
  effects, and same-day signal/return pairing of the RELIANCE-R1 type (MAP §2.1 R1: unshifted-signal ICs
  are contemporaneous and inadmissible — all associations here are gap-separated by construction).
- Observation: *t+2 → t+1+H* as in §6. No stop-loss, no take-profit, no trailing, no time-stop inside the
  window in this experiment — exits are bracket machinery (M13), a different mechanism.

---

## 8. Overlapping-event and dependence treatment

Tail events cluster: an instrument stays in-tail across consecutive sessions, and many instruments enter
tails on the same session. Both dependences are pre-treated, not modeled away afterward:

1. **Session observation (pinned: cohort-by-formation-date).** Each formation session τ contributes **one**
   observation: the equal-weighted mean signed market-netted forward return `f` over formations **formed
   at τ** (each held passively over its own window). Sessions are equal-weighted regardless of cohort
   size. Sessions with zero formations contribute no observation and are dropped from the series; the
   count of contributing sessions is reported. No instrument-level test statistic is computed, so
   cross-sectional dependence is removed by construction.
2. **Time dependence** from overlapping H-session holds induces MA structure by construction. The
   confirmatory test (§10) uses **Newey–West HAC standard errors with lag = H** (covers H−1 overlap lags
   plus one), pre-specified, not selected.
3. No clustered/Driscoll–Kraay substitution, no cohort-deduping, no thinning — the §8.1 series + HAC
   pipeline is the complete dependence treatment. **PASS/FAIL rests on the lag-H test alone**: if
   residual autocorrelation beyond lag H is detected diagnostically on TRAIN, it is reported, not
   patched, and the VAL test runs as pinned.

---

## 9. Train/validation/holdout design

Hypothesis (§1–§2), exploratory choices, confirmatory test, and holdout are four separate stages with
no information flowing backward:

| Stage | Window | Role | What may be decided here |
|---|---|---|---|
| TRAIN (exploratory) | 2012-01-02 → 2017-12-29 (daily bhavcopy) | Estimate all three families × H ∈ {1,5,10} descriptively; estimate MRLC-overlap diagnostic (§9.1); report raw-vs-netted attribution | Pin **one** family + **one** horizon by the rule below; nothing else |
| VALIDATION (confirmatory) | 2018-01-01 → 2022-12-30 | Single pinned test (§10) | Nothing — run as pinned or STOP |
| HOLDOUT (validation) | **Forward accumulation: the 250 trading sessions immediately following FREEZE_DATE** (the operator-recorded freeze session; sessions counted on `trading_calendar`), read **once**, after the last session's pinned-H forward window is complete. The accumulation pipeline is write-only and blinded: no HOLDOUT session's forward return is inspected until the floor is reached. No 2023+ historical read is used in any stage of this experiment. | One-shot validation of the pinned spec | Nothing — PASS/retire |

**Stage containment (mechanical):** a formation belongs to a stage only if its formation date *t* and its
entire forward window (or terminal truncation, §3.1) lie inside that stage's window; each H ∈ {1,5,10}
is therefore evaluated on TRAIN over formations whose span fits that H. Trailing lookback spans may
extend backward across a boundary (prior information, disclosed as standard) — containment constrains
formation dates and forward windows only, so no forward return is ever shared across stages.

**Pinning rule (pre-stated, TRAIN-only):** among the 3 families × H ∈ {1,5,10} descriptive estimates,
pin the combination with the largest |t| (session-portfolio mean, NW lag = H) **among right-sign
(reversion) combinations with TRAIN |t| ≥ 1.0**. If several tie exactly, break ties by smaller H, then
F1 < F2 < F3. If no combination is right-signed with |t| ≥ 1.0, **pin nothing: STOP, no VAL run.**
Power is assessed **only** via the frozen RFA declaration (a data-free gate): TRAIN estimates are
winner's-curse-inflated by selection (the C2/CB-N50 lesson) and no feasibility claim is drawn from them.

**Prior-exposure clause (PSB-2 D2 style).** TRAIN and VAL overlap data read by earlier constructs on
overlapping panels: the MRLC 2012–22 daily stretch construct (MAP §4 M3b), PSB-1 C1/C2 2012–22 weekly
reversal (MAP §4 M1a/M1b), and the RELIANCE `reversal_5` sign rule. N = 5 / W = 252 were chosen with
knowledge of that literature. VAL is therefore **not naive** to this construct family: a VAL pass is a
consistency check whose confirmatory weight is carried by the forward, never-before-read HOLDOUT.

### 9.1 MRLC-overlap diagnostic (report-only, restored)

Price-only sweep proxy (volume is unread in this experiment, news unfiltered by §4.3): formation *t*
carries the proxy iff `C(t)` closed below its prior-10-session low and closed back above that low
within 3 sessions (closes only; MRLC's volume and news conjuncts omitted by design, disclosed).
Report the fraction of M1c events carrying the proxy on TRAIN (descriptive) and replicate on VAL
(report-only, no gate). Pre-stated reading: overlap is admitted (M3); high overlap does not invalidate
(no level condition is imposed); near-total overlap would mean the tail rule is empirically a breach
rule, which is then recorded as a limitation on the "independence" reading — without changing any
pass/fail outcome.

---

## 10. Statistical tests and multiple-testing controls

- **Estimand:** the session series of §8.1 (market-netted signed forward returns, cohort-by-formation-date).
- **VALIDATION test (single, pinned):** one-sided t = mean / NW_SE(lag = H) against H0: μ ≤ 0 at
  **α = 0.025** (the one-sided 0.025 confirmatory convention). Reject → proceed to HOLDOUT accumulation
  read; fail → STOP (§12).
- **HOLDOUT test (single, pinned spec, one-shot):** same statistic on the 250-session forward series,
  one-sided at **α = 0.05**. The two gates are sequential (HOLDOUT is read only after VAL passes), so no
  simultaneity adjustment applies; each gate's error rate stands alone. The 9-combination TRAIN search
  never enters VAL/HOLDOUT inference (TRAIN selection is fenced by the §9 rule).
- **Scope limit:** a pass supports **only the pinned family at the pinned horizon** — F1–F3 are heavily
  overlapping event sets, not independent lenses, and a VAL pass is not support for "M1c in general."

---

## 11. Minimum evidence required to call the mechanism supported

All four required, in order; the first failure stops the sequence:

1. TRAIN: the pinned combination is right-signed with |t| ≥ 1.0 (selection record under §9, not evidence).
2. VALIDATION: reject H0 one-sided at p < 0.025 on the pinned spec (§10).
3. HOLDOUT: same sign, one-sided p < 0.05 on the pinned spec (§10), **and** net-of-fees point estimate > 0,
   where fee drag = realized formation turnover (each formation = one round trip over its window) × the
   era-accurate delivery-equity model in `core/execution/equity/delivery_fees.py`. The fee rule references
   existing code; no new cost model is invented.
4. Overlap diagnostic replicated (§9.1) with its pre-stated reading recorded alongside the claim.

---

## 12. Explicit failure/stop criteria

- Frozen RFA declaration returns ABANDON (or does not cover the session-portfolio test at VAL and
  HOLDOUT sizes) → **no data read at any stage**; the protocol returns to draft.
- TRAIN pins nothing (§9 rule) → **STOP**: no VAL run, no re-ranking, no second family, no horizon change.
- VAL fails to reject → **STOP**: no HOLDOUT read ever occurs; any forward store accumulated blinded
  to that point is discarded unread. No re-specification.
- HOLDOUT fails (wrong sign, p ≥ 0.05, or net-of-fees ≤ 0) → **retire the construct**: no second family,
  no horizon change, no window extension. A successor requires a new pre-registration and may not reuse
  the TRAIN/VAL windows for the same mechanism.
- Substrate failure (feed gaps, missing adjusted view, calendar break) → halt; no vendor patch, no manual
  fill. A fix-and-rerun is a protocol amendment, not an implementer decision.

---

## 13. What would constitute a null result

- Failure to reject H0 at VAL: "M1c unsupported in the pinned family/horizon form on 2018–22." No
  statement is made about other families, horizons, universes, or cadences.
- Rejection at VAL followed by HOLDOUT failure: "not validated; treated as unsupported." The VAL pass is
  then on record as a non-replicating in-window result, consistent with the prior-exposure clause (§9).
- A statistically significant **continuation** result at any stage is a null for M1c (M2c territory), not
  support under a re-signed hypothesis.
- Near-total §9.1 overlap quantifies the boundary case: the tail rule implemented as a breach rule in
  practice. This limits the independence reading (§1) without rescuing or sinking the statistical gates.

---

## 14. What must NOT be tested in this first experiment

Per MAP §7 ("do not test yet") and the M1c eligibility row (MAP §8: extreme reversion **not conditional
on a sweep**):

- Any sweep, reclaim, level-break, or volume/delivery condition, joint or standalone (M3b form and
  MRLC re-thresholded cells; M5a/M5b conditioning).
- Cross-sectional ranks of any kind (M1a/M1b/M1d/M2a/M2b/M2e), market-residual construction, sign rules
  without an extremeness threshold.
- Indicator-zoo triggers as event definitions: RSI, Stochastic, KDJ, CCI, Williams, Bollinger,
  MACD, Ichimoku, SAR, Supertrend.
- Re-parameterized long/flat daily SMA/TSMOM or Donchian rules on RELIANCE (M2c/M3a B-covered forms).
- Grid/martingale/DCA overlays, Combo conjunctions, ML-labelled re-runs of the above.
- VWAP, intraday/1m substrate, stop/target bracket variants (M13) — reserved for later experiments.
- Any 2023+ historical read (sealed-era, MRLC-read). RFA bypass: no read precedes the frozen declaration.

---

## 15. Open questions requiring a decision before implementation

All items below are resolved **before any read**, under governance — none permits discretion after results:

1. **HOLDOUT — resolved in v1.1 (was §15.1/B2).** Forward 250-session accumulation post-freeze, blinded
   write-only pipeline, one-shot read (§9). No sealed spend, no post-VAL window choice.
2. **RFA declaration content.** The frozen declaration (separate governed artifact) must state the metric
   for the session-portfolio test, defend its effect-size band independently (not inherited from TRAIN),
   and cover both VAL and HOLDOUT sizes. Freeze is blocked on ABANDON. Band values live in that
   declaration, which predates all reads.
3. **FREEZE_DATE value.** Set by the operator at freeze and recorded in the frozen document; the protocol
   references it symbolically. This is a calendar act, not a research decision.
4. **RELIANCE inclusion — resolved: include, with disclosure.** RELIANCE was the M2c/M3a test name, but
   excluding our most-studied name post-hoc would itself be a discretionary cut. It is included under the
   same rules; a RELIANCE-excluded sensitivity is reported alongside (report-only, no gate).
5. **Pre-freeze verification checklist (mechanical, no judgement):** adjusted-view coverage of 2012–22 for
   the panel; disposition-register currency; `trading_calendar` session counts for the three windows;
   `delivery_fees.py` interface for the §11 fee rule. Any check failing returns the protocol to draft.

---

## Change Log (v1 → v1.1; hostile-review disposition)

- **B1 (truncated file):** restored the complete protocol — full §9 (fallback rule, §9.1 diagnostic),
  §10 (test spec), §11–§13 (evidence/failure/null), §14 (must-not-test), §15 (decisions). Re-review of the
  restored sections is explicitly invited; freeze is not claimed.
- **B2 (undecided holdout):** resolved in §9 — forward 250-session accumulation post-FREEZE_DATE, blinded
  write-only pipeline, one-shot read after the last forward window completes; no 2023+ historical read in
  any stage. §15.1 closed into item 1.
- **M1 (universe contradiction):** §3 now names one universe — the broad PIT listed-equity panel on the
  certified adjusted store (the MRLC 2012–22 daily construction, delisted-included); the "PIT F&O" phrase
  is deleted. No liquidity filter is applied, with the small-name dominance disclosed as a limitation.
- **M2 (H0 not the no-signal null):** adopted fix (i) — primary estimand is the market-netted signed
  forward return (§1, §6, §8.1, §10); the market leg is the same-window equal-weighted universe return
  under identical tradability rules. Raw series kept TRAIN-descriptive only. Event definition unchanged.
- **M3 (M3b isolation contradiction):** deleted the §2 "voids" sentence; overlap is admitted and quantified
  report-only via the restored §9.1 price-only sweep proxy (closes only — volume stays unread), with no
  effect on pinning or pass/fail. §4.3 ("no other condition") retained as a rule about imposed conditions.
- **M4 (measurement ambiguities):** §4 pins the weak-percentile formula with ties averaged and the current
  value excluded; §5 pins F2's σ as including the formation window with per-date own-σ references, F3's
  ratios as each-with-own-median with the one-sided-95th rule and its ≈5%-vs-≈10% asymmetry disclosed, and
  the uniform 316-session eligibility with per-family arithmetic shown (F1/F3: 258; F2: 316).
- **M5 (session observation ambiguity):** §8.1 pins cohort-by-formation-date (option (a)); NW lag = H
  retained as correct for (a). Empty sessions drop out with counts reported; sessions equal-weighted
  regardless of cohort size.
- **M6 (pinning rule):** §9 pins "largest |t| among right-sign combos with |t| ≥ 1.0; none → STOP; exact
  ties → smaller H, then F1<F2<F3"; the §6 "proposed default H = 5" sentence is deleted; the TRAIN power
  check is replaced with "power assessed only via the frozen RFA declaration" (TRAIN maxima are
  winner's-curse-inflated).
- **M7 (prior exposure):** §9 carries a PSB-2-D2-style clause (MRLC 2012–22 daily, PSB-1 C1/C2, RELIANCE
  `reversal_5`; N = 5/W = 252 chosen with knowledge of that literature); VAL is a consistency check and
  confirmatory weight rests on the naive forward HOLDOUT.
- **M8 (missing-data judgement):** §3.1 gives exhaustive mechanical rules — trailing/forward gaps drop the
  formation; series-end truncation uses the last-available-close terminal rule (both legs); coverage *is*
  the adjusted view with status from the committed disposition register only; "sessions" are calendar
  trading sessions throughout.
- **Minors:** m1 (garbled formula deleted; §6 rewritten around the netted estimand); m2 (H1 restated for
  the pinned combination); m3 (stage-containment rule in §9 — formation date plus full forward window
  inside the stage; trailing spans may extend backward); m4 (§8.3: PASS/FAIL rests on the lag-H test
  alone); m5 (§10–§11 scope sentence: a pass supports only the pinned family at the pinned horizon).
