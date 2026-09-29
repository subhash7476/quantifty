# M1c: Single-Instrument Extreme Reversion — Research Protocol v1

**Status:** PROTOCOL DRAFT v1 (design only — not frozen, not approved, no runs authorized by this document).
**Date:** 2026-09-29
**Governing boundary:** `docs/reports/external/RESEARCH_MECHANISM_COVERAGE_MAP_v1.1_2026-09-29.md`
(**MAP**, FROZEN v1.1). M1c is status **C** (C/B borderline, MAP §4 row M1c, §8, §9).
**This document runs no backtest, writes no implementation code, spends no data window, and consumes
no gate.** Implementation additionally requires a frozen RFA declaration and a frozen pre-registration;
neither is created here.

---

## 1. Research question and falsifiable hypothesis

**Research question.** Does an unusually extreme move in an individual instrument, measured relative to
that instrument's own recent history, produce subsequent mean reversion **independently of the MRLC
sweep/volume conditions** (no level breach, no reclaim, no volume filter)?

**Falsifiable hypothesis (H1).** Instruments whose trailing 5-session return falls in the ≤5th or ≥95th
percentile of their own trailing 1-year distribution (score defined in §4–§5) earn contrarian forward
returns over the next 5 sessions (measured from a 1-session gap, §7) that are positive in expectation,
unconditionally — i.e. without any sweep, reclaim, volume, peer-rank, or news condition.

**Null (H0).** The expected signed contrarian forward return is ≤ 0 (one-sided test, §10).

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

- Not M3b: no breach of a visible level, no sweep, no reclaim trigger. A level event anywhere in the
  formation voids the M1c interpretation.
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

- **Universe:** per-session PIT F&O equity membership (the same grain as the MRLC 2012–22 daily panel:
  ~2,300 PIT symbols; MAP §2.1). Membership is per-session; a name is eligible on session *t* only if
  PIT-listed on *t*.
- **Entity correctness:** entity resolution via CSMP `symbol_entity_intervals` with ISIN issuer-prefix
  linkage (recycled tickers and face-value ISIN re-issues must not create false extremes). Any session
  whose entity mapping is ambiguous is dropped, not imputed.
- **Survivorship:** names enter while listed and leave on delisting; no backfilled history, no
  listed-today universe projected backward.
- **Lookback completeness:** a formation requires the full trailing window (§5, 252 sessions of adjusted
  closes) present for that entity. Partial windows never form.
- **Return continuity:** all trailing and forward returns are computed on the corporate-action-adjusted
  series consistently (the 1m store is adjusted while `equity_bhavcopy` is as-traded — the implementer
  uses the certified adjusted view, never a mixed join). Sessions around ex-dates with unresolvable
  adjustment status are dropped.
- **Calendar:** the 2012-11-11 Sunday bhavcopy artifact is excluded by rule. Trading sessions come from
  `core/market/nse_holidays.py` / `trading_calendar`, never from stored-date inference.

---

## 4. Event/formation definition

A formation is an **(instrument, session *t*)** pair satisfying all of the following, evaluated at the
close of *t*:

1. Universe- and PIT-eligible on *t* (§3), with complete lookback.
2. The trailing 5-session return `R5(t) = C(t)/C(t−5) − 1` (adjusted closes) scores in the **tails of its
   own trailing 252-session distribution** under the single pinned measurement family (§5): score ≤ 5th
   percentile (down-tail, signed +1 / long) or ≥ 95th percentile (up-tail, signed −1 / short).
3. **No other condition.** In particular: no level-breach test, no reclaim test, no volume test, no
   peer comparison, no volatility-regime gate, no news filter (v1 choice — information-driven moves are
   part of the null population, which biases *toward* H0 and is therefore conservative; disclosed, §15.8).

Non-tail pairs score 0 (no position, no observation). The signed score `s ∈ {+1, −1, 0}` is the **only**
signal this experiment tests.

---

## 5. Permissible measurement families and why they represent the same mechanism

No indicator is admitted because it is familiar. **RSI, Stochastic, KDJ, CCI, Williams, Bollinger %B,
MACD, and any band-oscillator trigger are excluded as event definitions in this first experiment**
(MAP §7: indicator-level novelty without economic distinction is not tested). Three families are
permitted because each is a distinct lens on the *same* mechanism — "this instrument's recent move is
extreme relative to what it usually does" — with no level, peer, volume, or breach content:

| Family | Score construction (all trailing, causal, same tail rule) | Why it is the same mechanism |
|---|---|---|
| F1. Own-percentile trailing return | Percentile of `R5(t)` within the trailing 252-session empirical distribution of overlapping 5-session returns, same entity | Direct extremeness: rank of the move in its own history |
| F2. Vol-scaled excursion | `R5(t) / σ(t)`, where `σ(t)` = trailing 63-session daily-return SD (one quarter); tail rule applied to the trailing 252-session distribution of the scaled series | Same extremeness, normalized for the instrument's current variability — a volatile name needs a larger move to qualify |
| F3. Range-expansion excursion | `|R5(t)| / median(|R5| over trailing 252 sessions)`; event if the ratio sits at/above its own trailing 95th percentile (direction from the sign of `R5`) | Same extremeness via the range lens rather than the return-distribution lens |

Uniformity rule: the **same** N (= 5 sessions, one trading week — the short-horizon precedent of M1a/M1b),
the **same** reference length (252 sessions, one annual cycle), and the **same** 5%/95% tail rule apply to
all three families. N, W, and tail cut are defended by precedent (weekly horizon; annual reference), not
tuned — no other values may be tried in this experiment. All three families are estimated descriptively
on TRAIN; **at most one** is pinned for confirmatory testing by the pre-stated rule in §9.

---

## 6. Forward horizons

- Observation window for a formation at *t*: sessions *t+2* through *t+1+H* (the 1-session gap is §7).
- Candidate horizons for TRAIN exploration (descriptive only): H ∈ {1, 5, 10}.
- **One** horizon is pinned for confirmatory testing by the §9 rule. Proposed default: **H = 5**
  (one trading week, symmetric with the formation window; multi-day, matching the "M1c … multi-day"
  remainder in MAP §6). The implementer may pin H ∈ {1, 5, 10} only via the TRAIN rule, never by VAL results.
- Forward return is close-to-close over the window on the adjusted series, signed by *s* (§4):
  `f = s · (C(t+1+H)/C(t+2 open…))`. Precise convention: `f = s · (C(t+1+H)/C(t+1) − 1)` using closes,
  held without rebalancing inside the window. (Entry-execution semantics — next-open vs close — affect
  only the later trading implementation, not this mechanism test; the close-based convention is pinned
  here to keep the test auditable.)

---

## 7. Entry/observation timing

- Measurement close: session *t* close (daily bhavcopy close; pre-CAS windows per §9 need no auction handling).
- **Gap session *t+1*: never traded, never measured.** This kills bid-ask bounce, nonsynchronous-close
  effects, and same-day signal/return pairing of the RELIANCE-R1 type (MAP §2.1 R1: unshifted-signal ICs
  are contemporaneous and inadmissible — all associations here are gap-separated by construction).
- Observation: *t+2 → t+1+H* as in §6. No stop-loss, no take-profit, no trailing, no time-stop inside the
  window in this experiment — exits are bracket machinery (M13), a different mechanism.

---

## 8. Overlapping-event and dependence treatment

Tail events cluster: an instrument stays in-tail across consecutive sessions, and many instruments enter
tails on the same session. Both dependences are pre-treated, not modeled away afterward:

1. **Cross-sectional dependence** is removed by aggregation: each session τ contributes **one**
   observation — the equal-weighted mean signed forward-window return across all formations active that
   session (each formation held passively over its window; overlapping cohorts stack as concurrent
   positions). No instrument-level test statistic is computed.
2. **Time dependence** from overlapping H-session holds induces MA structure by construction. The
   confirmatory test (§10) uses **Newey–West HAC standard errors with lag = H** (covers H−1 overlap lags
   plus one), pre-specified, not selected.
3. No clustered/Driscoll–Kraay substitution, no cohort-deduping, no "one event per instrument per month"
   thinning — the session-portfolio + HAC pipeline is the complete dependence treatment. If residual
   autocorrelation beyond lag H is detected diagnostically on TRAIN, it is reported, not patched: the VAL
   test runs as pinned.

---

## 9. Train/validation/holdout design

Hypothesis (§1–§2), exploratory choices, confirmatory test, and holdout are four separate stages with
no information flowing backward:

| Stage | Window (daily bhavcopy, pre-seal) | Role | What may be decided here |
|---|---|---|---|
| TRAIN (exploratory) | 2012-01-02 → 2017-12-29 | Estimate all three families × H ∈ {1,5,10} descriptively; estimate MRLC-overlap diagnostic (§9.1); confirm power feasibility | Pin **one** family + **one** horizon by the rule below; nothing else |
| VALIDATION (confirmatory) | 2018-01-01 → 2022-12-30 | Single pinned test (§10) | Nothing — run as pinned or STOP |
| HOLDOUT (validation) | **UNDECIDED — §15.1** (candidate: forward accumulation post-freeze; the 2023+ window is sealed-era and MRLC-read, so it cannot serve silently) | One-shot validation of the pinned spec | Nothing — PASS/retire |

**Pinning rule (pre-stated, TRAIN-only):** among the 3 families × H ∈ {1,5,10} descriptive estimates, pin
the combination with the largest |t| (session-portfolio mean, NW lag = H) **provided** its sign matches
H1 (reversion) and its TRAIN |t| ≥ 1.0. If no combination clears the descript
...[truncated 6154 chars]