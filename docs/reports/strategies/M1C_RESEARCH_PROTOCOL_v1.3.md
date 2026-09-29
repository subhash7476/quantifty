# M1c: Single-Instrument Extreme Reversion — Research Protocol v1.3 (FROZEN)

**Status:** PROTOCOL FROZEN v1.3 (text immutable from this commit — no runs authorized by this document).
**Date / FREEZE_DATE:** 2026-09-29. **Supersedes:** `M1C_RESEARCH_PROTOCOL_v1.2.md` (commit `bb58393`,
whose reviewed text is preserved immutably and unchanged).
**Governing boundary:** `docs/reports/external/RESEARCH_MECHANISM_COVERAGE_MAP_v1.1_2026-09-29.md`
(**MAP**, FROZEN v1.1). M1c is status **C** (C/B borderline, MAP §4 row M1c, §8, §9).
**Freeze authority:** `M1C_PROTOCOL_V1_2_FREEZE_REVIEW_2026-09-29.md` — no blockers, one material issue
(F-1) plus F-2–F-7, all applied here (Change Log). Per the review the amendments are mechanical and need
no further review.
**Execution gating (unchanged):** frozen text is not run authorization. The first read additionally
requires the frozen RFA declaration and the §15.5 checklist pass; §12 blocks all reads until then.
**Design-only: no backtest, no implementation code, no data window spent, no gate consumed.** No read of
any kind has occurred under this protocol; every choice below is pre-data by construction.

---

## 1. Research question and falsifiable hypothesis

**Research question.** Does an unusually extreme move in an individual instrument, measured relative to
that instrument's own recent history, produce subsequent mean reversion **without imposing the MRLC
sweep/volume conditions** (no level-breach test, no reclaim test, no volume filter)? Independence is
operationalized as (a) no sweep/volume condition in the formation rule (§4) and (b) formation-time
breach-structure overlap quantified report-only (§9.1), with no effect on pinning or pass/fail.

**Falsifiable hypothesis (H1).** For the single family/horizon combination pinned by the §9 rule, the
expected **absolute** signed contrarian forward return (§6, §8) is positive: instruments in their own
down-tail subsequently rise, and instruments in their own up-tail subsequently fall, in absolute
close-to-close terms.

**Null (H0).** The expected absolute signed contrarian forward return is ≤ 0 (one-sided test, §10).

**Market-wide component (disclosed, not separated).** The estimand is absolute by MAP definition, so any
market-wide reversal shared by extreme names on market-wide days is *part of* H1/H0 — a pass establishes
absolute reversion of own-history extremes (the M1c cell), not isolated single-instrument exhaustion
attribution. No universe-netted or market-residual construction is used anywhere in this experiment
(§14); the v1.1 netting is withdrawn by the R-1 resolution (Change Log).

The hypothesis is falsified by a failure to reject H0 at any confirmatory stage (§11–§13). The sign is
pinned **before** any read: down-tail → long, up-tail → short. A significant continuation result is a
null for M1c (it belongs to M2c), not a re-interpretation.

---

## 2. Exact mechanism definition

**M1c mechanism (from MAP §3–§4) — motivating hypothesis, not the tested claim (F-6).** Absolute,
single-instrument, time-series reversion from an own-history extreme: a move large relative to what
*this instrument* recently did exhausts the marginal flow (seller/buyer exhaustion, inventory pressure,
stop-cluster depletion), so price drifts back toward its prior level over the next several sessions.
The exhaustion narrative above motivates the experiment; the test supports only the absolute-reversion
cell (own-history extremes revert in absolute terms). A pass does not establish the exhaustion mechanism.

**What it is not (boundary policing, per MAP §3.1 and §5):**

- Not M3b: no breach of a visible level, no sweep, no reclaim trigger is imposed. Coincidence between
  tail events and breach structure is admitted (a ≤5th-percentile 5-session return will often sit below
  a recent low) and is quantified report-only in §9.1; it does not void the interpretation and does not
  alter any gate.
- Not M1a/M1b: no peer ranking, no cross-sectional sort, no market-residual construction — in the event
  definition (§4–§5) **and** in the estimand (§6, R-1 Option A). The reference distribution is the
  instrument's own history, never the cross-section, and forward returns are never netted against the
  universe.
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
  `MRLC_TEST_2026-08-30.md` §9). This is the broad listed-equity panel, not the ~200-name F&O list.
  A name is eligible on session *t* only if listed on *t*.
- **No additional liquidity/ADV filter is applied beyond the completeness rule below — and that rule is
  itself a de facto activeness filter, stated plainly:** the effective universe is names trading every
  session over the trailing span. Equal weighting is therefore seasoned-name-weighted relative to the
  listed panel, and distressed/suspended names are underrepresented at formation. The bias direction is
  disclosed (it favours H1 on the down leg, §3.2), not corrected by judgement; it is bounded by the
  pre-specified sensitivity (§3.2) for attrition among eligible names. Selection of the eligible set
  itself (names never eligible under the 316-session rule) is reported via the eligible/listed fraction
  (§3.2) and is otherwise outside any data-derived bound — disclosed as a limitation, with no invented
  correction.
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
  return accrues to the **last available adjusted close**, with no further accrual.
- These three rules are exhaustive: every (formation, session) pair maps to exactly one of
  traded-as-pinned / dropped / terminal-truncated, with no residual discretion.

### 3.2 Attrition accounting and worst-case sensitivity (pre-specified, no discretion)

- **"Attrited" defined (F-3).** Only a tail-classified formation (s ≠ 0 assigned at *t*) can be attrited:
  its forward window is either dropped (suspension-with-resumption rule, §3.1) or truncated (terminal
  rule, §3.1). Trailing-span drops occur before any classification and are never attrited; they enter
  only the eligible/listed fraction below.
- **Report-only diagnostics (every stage, no gate):** per-leg counts of attrited formations split by
  dropped vs terminal-truncated (four counts); the eligible/listed fraction per stage; **E[s]** (mean
  signed score over all eligible name-sessions evaluated in the stage) and the **unconditional mean
  forward return** (equal-weighted H-window raw return over all eligible names with valid windows) per
  stage (F-7 — acknowledges the H0 drift term; design unchanged); the identity (entity, formation
  session *t*, leg, observed *f*) of every formation attaining `m_L` or `M_S`, and — on gated stages
  (VAL, HOLDOUT) only — the per-leg break-even attrition fractions defined below (F-2).
- **Worst-case-bound sensitivity (VAL and HOLDOUT; TRAIN descriptive only):** `m_L` = the minimum
  retained formation forward return on the long (down-tail) leg in the stage, and `M_S` = the maximum
  retained formation forward return on the short (up-tail) leg in the stage (worst for a short = largest
  adverse raw move), both over non-attrited formations only. Dropped formations (no observed return) are
  replaced at the leg worst outright. **Terminal-truncated formations are replaced only if the
  replacement is worse for that leg than their observed return** — longs get `min(m_L, f_obs)`, shorts
  get `max(M_S, f_obs)` (F-1: the bound can only ever worsen an attrited outcome, never flatter the
  population it exists to cover; partial-vs-full-window scale mixing is accepted because the min/max
  operation is conservative-or-equal by construction). Recompute the §8.1 session series and the §10
  t-statistic with the same NW lag. If either leg's retained set is empty, the stage result is void →
  STOP (substrate-failure class, §12).
- **Break-even attrition fraction (per leg, F-2):** order the leg's retained formations
  most-favorable-first (longs: *f* descending; shorts: *f* ascending); iteratively re-impute each at the
  leg worst value, recomputing the session series and t-statistic identically at each step; k* = the
  first step count at which the stage verdict flips (sign flip or p ≥ gate); the fraction is k* ÷ total
  formations in the leg that stage (1.0 if the verdict never flips). Reported beside the observed
  attrition fraction (attrited ÷ total in leg). Computed on VAL and HOLDOUT only — TRAIN carries no
  verdict to flip against.
- **Harshness accepted by design (F-2):** single-observation extremes, differing VAL/HOLDOUT stringency,
  and verdicts driven by attrition-rate × worst-value rather than signal strength all err toward harder
  passes. Stated and accepted, not tuned.
- **Fragility rule (mechanical):** if the recomputation flips the sign of the stage mean or the stage
  p-value no longer clears its gate (VAL: p ≥ 0.025; HOLDOUT: p ≥ 0.05), the stage result is labelled
  **attrition-fragile**. A fragile VAL pass → STOP as unsupported (§12); a fragile HOLDOUT pass → retire
  as unvalidated (§12). The sensitivity can never rescue a failed gate.
- **Limitation disclosed:** the bound covers attrition *among eligible names* at the within-sample worst
  case. Names never eligible under the 316-session rule, and beyond-sample wipeouts worse than any
retained outcome, are outside any bound derivable without invented constants — none are invented. The
freeze reviewer judges sufficiency; this protocol does not assert it.

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
- Signed formation return (primary estimand, absolute per §1/H0):
  `f = s · R_fwd`, where `R_fwd = C(t+1+H)/C(t+1) − 1` on adjusted closes (terminal-price rule,
  §3.1, if the series ends inside the window). Positions are held passively inside the window, without
  rebalancing. No universe leg, no netting, no residual construction exists in this experiment.

---

## 7. Entry/observation timing

- Measurement close: session *t*'s **official bhavcopy close**, pinned identically in every stage
  (whatever the era's definition of that close is — see CAS paragraph). TRAIN (2012–17) and VAL
  (2018–22) windows lie entirely before CAS went live (2026-08-03), so their closes are the pre-CAS
  official closes of their era.
- **CAS regime.** CAS went live 2026-08-03 — after every TRAIN/VAL session and before every HOLDOUT
  session. TRAIN and VAL are therefore single-close-regime windows; HOLDOUT is CAS-era throughout:
  Category I (F&O) names print an auction-equilibrium official close (continuous trading ends 15:15,
  auction 15:30–15:35), Category II names keep VWAP closes, and the first ~316 lookback sessions of
  early HOLDOUT formations mix pre- and post-CAS close definitions in the percentile reference.
  Auction-print noise is a HOLDOUT non-stationarity confound for a reversion test (a spurious auction
  deviation at *t* reversing by *t+2* flatters reversion — pro-H1 direction, disclosed); the §9.2 split
  contextualizes it without touching any gate.
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
   observation: the equal-weighted mean signed absolute forward return `f` over formations **formed
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
| TRAIN (exploratory) | 2012-01-02 → 2017-12-29 (daily bhavcopy) | Estimate all three families × H ∈ {1,5,10} descriptively; estimate MRLC-overlap diagnostic (§9.1); report attrition diagnostics (§3.2) and per-combination attrition (dropped + terminal counts per leg for each family × H, descriptive — the pro-H1 attrition bias grows with H, so H-comparisons are read with their attrition table attached) | Pin **one** family + **one** horizon by the rule below; nothing else |
| VALIDATION (confirmatory) | 2018-01-01 → 2022-12-30 | Single pinned test (§10) + attrition sensitivity (§3.2) | Nothing — run as pinned or STOP |
| HOLDOUT (validation) | **Forward accumulation: the 250 trading sessions immediately following FREEZE_DATE = 2026-09-29** (sessions counted on `trading_calendar`), read **once**, after the last session's pinned-H forward window is complete. The accumulation pipeline is write-only and blinded: no HOLDOUT session's forward return is inspected until the floor is reached. No 2023+ historical read is used in any stage of this experiment. CAS-era throughout (§7, §9.2). | One-shot validation of the pinned spec + attrition sensitivity (§3.2) | Nothing — PASS/retire |

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

### 9.1 MRLC-overlap diagnostic (report-only; formation-time information only)

Breach-structure proxy, computed **exclusively from closes on or before the formation session** (no
forward prices enter; the v1.1 reclaim leg is deleted as outcome-contaminated):

- **Down-tail proxy:** `C(t)` is strictly below `min(C(t−10)..C(t−1))` on adjusted closes — i.e. the
  formation close breaches its own prior-10-session low as of *t*. Exact threshold, exact timing, no
  reclaim condition. (The 10-session lookback is MRLC's own sweep reference, not a tuned parameter.)
- **Up-tail mirror:** `C(t)` is strictly above `max(C(t−10)..C(t−1))` on adjusted closes.
- Report the fraction of down-tail events carrying the down proxy and of up-tail events carrying the up
  proxy, on TRAIN (descriptive) and computed identically on VAL (**"replicated" = computed by the
  identical rule and recorded; replication carries no threshold and no gate**).
- **"Near-total overlap" is stipulatively defined as ≥ 90% on either leg on TRAIN**, pinned before any
  read and applied identically across stages. Pre-stated reading: overlap is admitted (M3); high overlap
  does not invalidate (no level condition is imposed); a near-total reading is recorded as a limitation
  on the "independence" claim in §1 — without changing any pass/fail outcome.

### 9.2 HOLDOUT CAS split (report-only; not a gate)

The §8.1 session series is additionally computed over two descriptive sub-series — formations in
Category I names only, and formations in Category II names only — with the same t-statistic and no
thresholds. Formation category is resolved per session from the CAS category register
(`data/cas/cas_category.duckdb`) as built by committed code at HOLDOUT-read time; names absent from the
register resolve to Category II (the register covers Category-I names; stated assumption, no discretion).
The split contextualizes the §7 CAS confound only: it cannot overturn, rescue, or modify any §11/§12
outcome, and no per-category claim is made regardless of the numbers. No split is needed on TRAIN/VAL
(single pre-CAS close regime — that is why none is defined there).

---

## 10. Statistical tests and multiple-testing controls

- **Estimand:** the session series of §8.1 (absolute signed forward returns, cohort-by-formation-date).
- **VALIDATION test (single, pinned):** one-sided t = mean / NW_SE(lag = H) against H0: μ ≤ 0 at
  **α = 0.025** (the one-sided 0.025 confirmatory convention). Reject → proceed to HOLDOUT accumulation
  read; fail → STOP (§12).
- **HOLDOUT test (single, pinned spec, one-shot):** same statistic on the 250-session forward series,
  one-sided at **α = 0.05**. The two gates are sequential (HOLDOUT is read only after VAL passes), so no
  simultaneity adjustment applies; each gate's error rate stands alone. The 9-combination TRAIN search
  never enters VAL/HOLDOUT inference (TRAIN selection is fenced by the §9 rule).
- **Scope limit:** a pass supports **only the pinned family at the pinned horizon, in the
  continuously-trading effective universe only** — F1–F3 are heavily overlapping event sets, not
  independent lenses, and a VAL pass is not support for "M1c in general."

---

## 11. Minimum evidence required to call the mechanism supported

All five required, in order; the first failure stops the sequence:

1. TRAIN: the pinned combination is right-signed with |t| ≥ 1.0 (selection record under §9, not evidence).
2. VALIDATION: reject H0 one-sided at p < 0.025 on the pinned spec (§10).
3. HOLDOUT: same sign, one-sided p < 0.05 on the pinned spec (§10), **and** net-of-fees point estimate > 0,
   where fee drag = realized formation turnover (each formation = one round trip over its window) × the
   era-accurate delivery-equity model in `core/execution/equity/delivery_fees.py`, applied to
   **formation legs only**: there is no universe/hedge leg in this experiment, and no short-side or
   hedge fee model is invented — every formation round trip is priced on the existing long-side schedule
   as a conservative cost-scale proxy (delivery STT dominates any intraday/short schedule per the repo's
   fee record). The fee rule is a magnitude-relevance check, not a P&L claim; short-leg multi-session
   implementability (borrow mechanics) is out of scope for a mechanism test and is asserted nowhere.
4. Overlap diagnostic computed on VAL by the identical §9.1 rule ("replicated") with its pre-stated
   reading recorded alongside the claim.
5. Attrition sensitivity non-fragile (§3.2) on VAL and on HOLDOUT.

---

## 12. Explicit failure/stop criteria

- Frozen RFA declaration returns ABANDON (or does not cover the session-portfolio test at VAL and
  HOLDOUT sizes) → **no data read at any stage**; the protocol returns to draft.
- TRAIN pins nothing (§9 rule) → **STOP**: no VAL run, no re-ranking, no second family, no horizon change.
- VAL fails to reject → **STOP**: no HOLDOUT read ever occurs; any forward store accumulated blinded
  to that point is discarded unread. No re-specification.
- VAL passes statistically but is attrition-fragile (§3.2) → **STOP as unsupported**: fragility blocks
  the support call; the sensitivity can never be waived.
- HOLDOUT fails (wrong sign, p ≥ 0.05, net-of-fees ≤ 0, or attrition-fragile) → **retire the construct**:
  no second family, no horizon change, no window extension, no per-category rescue via §9.2. A successor
  requires a new pre-registration and may not reuse the TRAIN/VAL windows for the same mechanism.
- Substrate failure (feed gaps, missing adjusted view, calendar break, empty retained leg in §3.2,
  CAS register unavailable at HOLDOUT read) → halt; no vendor patch, no manual fill. A fix-and-rerun is
  a protocol amendment, not an implementer decision.

---

## 13. What would constitute a null result

- Failure to reject H0 at VAL: "M1c unsupported in the pinned family/horizon form on 2018–22." No
  statement is made about other families, horizons, universes, or cadences.
- Attrition-fragile VAL pass: "unsupported — the statistical pass does not survive its own pre-stated
  attrition bound." Recorded as a fragility null, not a statistical null.
- Rejection at VAL followed by HOLDOUT failure (any of §12): "not validated; treated as unsupported."
  The VAL pass is then on record as a non-replicating in-window result, consistent with the
  prior-exposure clause (§9).
- A statistically significant **continuation** result at any stage is a null for M1c (M2c territory), not
  support under a re-signed hypothesis.
- Near-total §9.1 overlap (≥ 90% on either leg, formation-time proxy): the tail rule coincides with a
  breach rule in practice. This limits the independence reading (§1) without rescuing or sinking the
  statistical gates.

---

## 14. What must NOT be tested in this first experiment

Per MAP §7 ("do not test yet") and the M1c eligibility row (MAP §8: extreme reversion **not conditional
on a sweep**):

- Any sweep, reclaim, level-break, or volume/delivery condition, joint or standalone (M3b form and
  MRLC re-thresholded cells; M5a/M5b conditioning).
- Cross-sectional ranks of any kind (M1a/M1b/M1d/M2a/M2b/M2e), universe-netted or market-residual return
  constructions, sign rules without an extremeness threshold.
- Indicator-zoo triggers as event definitions: RSI, Stochastic, KDJ, CCI, Williams, Bollinger,
  MACD, Ichimoku, SAR, Supertrend.
- Re-parameterized long/flat daily SMA/TSMOM or Donchian rules on RELIANCE (M2c/M3a B-covered forms).
- Grid/martingale/DCA overlays, Combo conjunctions, ML-labelled re-runs of the above.
- VWAP, intraday/1m substrate, stop/target bracket variants (M13) — reserved for later experiments.
- Any 2023+ historical read (sealed-era, MRLC-read). RFA bypass: no read precedes the frozen declaration.

---

## 15. Decisions before implementation (all pre-read, under governance)

1. **HOLDOUT — resolved (§9).** Forward 250-session accumulation post-freeze (FREEZE_DATE pinned
   2026-09-29 above), blinded write-only pipeline, one-shot read; CAS-era throughout with the report-only
   §9.2 split. No sealed spend, no post-VAL window choice.
2. **RFA declaration content.** The frozen declaration (separate governed artifact) must state the metric
   for the absolute session-portfolio test, defend its effect-size band independently (not inherited from
   TRAIN), and cover both VAL and HOLDOUT sizes. Freeze of *execution* is blocked on ABANDON. Band values
   live in that declaration, which predates all reads.
3. **FREEZE_DATE — resolved at freeze: 2026-09-29** (header). The symbolic references in §9 resolve to
   this date; HOLDOUT is the 250 trading sessions following it.
4. **RELIANCE inclusion — resolved: include, with disclosure.** RELIANCE was the M2c/M3a test name, but
   excluding our most-studied name post-hoc would itself be a discretionary cut. It is included under the
   same rules; a RELIANCE-excluded sensitivity is reported alongside (report-only, no gate).
5. **Pre-read verification checklist (mechanical, no judgement):** adjusted-view coverage of 2012–22 for
   the panel; disposition-register currency; `trading_calendar` session counts for the three windows;
   `delivery_fees.py` interface for the §11 fee rule; CAS category register availability for the §9.2
   split. Any check failing returns the protocol to draft; the first read requires the checklist pass
   *and* the frozen RFA declaration (§12).
6. **Freeze-review F-1–F-7 — applied in this text (Change Log).** Per the freeze recommendation the
   amendments are mechanical and require no further review cycle for these items.

---

## Change Log (v1.2 → v1.3 FROZEN; freeze-review disposition)

(The v1 → v1.1 log is retained immutably in `M1C_RESEARCH_PROTOCOL_v1.1.md`, commit `cd0d670`.)

- **F-1 (MATERIAL; anti-conservative terminal bound) → §3.2, one operative sentence.** Terminal-truncated
  formations are now replaced only if the replacement is worse for that leg than their observed return
  (longs: `min(m_L, f_obs)`; shorts: `max(M_S, f_obs)`); dropped formations keep full replacement. The
  bound can therefore only worsen attrited outcomes, never flatter the population it covers. `m_L`/`M_S`
  remain full-window retained-only extremes (scale-coherent); the min/max operation is
  conservative-or-equal by construction, which is all a bound requires.
- **F-2 (single-observation extremes) → §3.2, report-only.** Identity (entity, session, leg, observed *f*)
  of every `m_L`/`M_S` formation is reported; the per-leg break-even attrition fraction is pinned as a
  greedy most-favorable-first re-imputation count (k* ÷ leg total; 1.0 if never flips), reported beside
  the observed attrition fraction. Single-observation harshness and VAL/HOLDOUT stringency differences
  are stated as accepted conservative design, not tuned.
- **F-3 ("dropped" ambiguity) → §3.2 definition.** "Attrited" = tail-classified formations whose forward
  window is dropped or truncated; trailing-span drops pre-date classification and enter only the
  eligible/listed fraction. Per-leg attrition counts are therefore always well-defined.
- **F-4 (TRAIN pinning not attrition-adjusted) → §9 TRAIN cell.** Per-combination attrition (dropped +
  terminal counts per leg, each family × H) is reported descriptively so H-comparisons are read with
  their attrition table attached; VAL remains fenced by the fragility rule. No gate added on TRAIN.
- **F-5 (unbounded scope) → §10 scope sentence.** Support is now claimed "in the continuously-trading
  effective universe only." The 316-rule screen and beyond-sample wipeouts remain correctly disclosed as
  unbounded; the claim is scoped to match.
- **F-6 (mechanism vs test) → §2 header sentence.** The exhaustion narrative is labelled the motivating
  hypothesis; the test supports the absolute-reversion cell only. No design change.
- **F-7 (H0 drift term) → §3.2 diagnostics.** E[s] and the unconditional mean forward return are reported
  per stage, report-only. No design change.
