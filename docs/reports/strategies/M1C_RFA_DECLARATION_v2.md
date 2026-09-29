# M1c RFA Declaration v2 (FROZEN)

**Status:** FROZEN v2, 2026-09-29. Supersedes v1 (committed, immutable). This version corrects the
power mapping only: annualized Sharpe is retained as the effect-size parameter, but its translation to
the frozen test's noncentrality is re-derived for the NW-HAC session-mean test. No band value, window,
α, hurdle, or protocol text changes. **Verdict re-derived below: ABANDON** (more strongly than v1).
**Governing protocol:** v1.3 (`a69f23a`), unchanged. **Methodology:** 2.0.0, hurdle 0.80,
optimistic-corner standard. **No market data read, no backtest, no TRAIN, no new hypothesis.** The
derivation in §2 is pure time-series algebra on the protocol's own overlap geometry — no M1c results
consulted or needed.

## 1. What was wrong in v1

v1 used `ncp = S·√T` (the `gate.py` cadence-invariance identity) for a session series whose
observations are H-session overlapping sums reformed every session. That identity holds for iid
per-period observations; the frozen test's observations are MA-structured by construction (§8 v1.3),
so v1 overstated power by up to √H (×2.2 at H=5, ×3.2 at H=10; exact only at H=1). The 0.9-session
haircut had no derivation from the HAC structure and is withdrawn — not patched — below.

## 2. Exact Sharpe → HAC-test relationship (derived, not assumed)

Let x_τ be the session observation (cohort-τ mean signed forward return), window τ+2..τ+1+H.
Write x_τ = Σ_{j=2}^{H+1} d_{τ,j} with d cohort-mean signed daily returns (mean m_d, per-day scale v).
Cohorts τ, τ+k share H−k calendar days (0 ≤ k ≤ H; disjoint beyond). With daily innovations white,
Cov(x_τ, x_{τ+k}) = (H−k)·c_k (k ≥ 1) with c_k ≤ v by Cauchy–Schwarz, and Var(x_τ) = H·v. Long-run
variance: S_0 = Hv + 2Σ_{k=1}^{H−1}(H−k)c_k ≤ Hv + 2v·H(H−1)/2 = v·H². Hence S_0/σ_x² ≤ H, and the
HAC t-statistic's noncentrality obeys ncp = μ√n/√S_0 ≥ S_ann·√(T/H), with equality for identical
cohorts. The floor (v/c = 1) is the unique assumption-free choice: it can only understate power, never
overstate it. Endpoint checks: H=1 gives ncp = S√T exactly (v1 reproduced — the correction nests the
original); H=n degenerates to a single effective observation. Structural note (protocol arithmetic, no
data): R5(t), R5(t+1) share 5 of 6 closes, so tail classifications — hence adjacent cohorts' names and
signs — are mechanically persistent; c_k sits near v in practice, i.e. the floor is approximately the
truth, not merely a bound. Finite-sample HAC estimation noise around S_0 is second-order and disclosed
as ignored, either direction. NW lag = H covers all nonzero lags of the triangular MA(H−1) structure.

Consequences: (a) H does not disappear from power — effective years are T/H; (b) the 0.9 haircut is
deleted, replaced by the derived factor; (c) Sharpe remains the correct parameter (standardized session
mean); only the n→ncp translation changes, so the §6 v1 band stands (its defense never depended on the
mapping).

## 3. VAL design (2018-01-01 → 2022-12-30, α = 0.025, T ≈ 4.96 y)

Same α-construction note as v1 (normal approximation, n > 1,000). Power = Φ(ncp − 1.96),
ncp = S·√(4.96/H):

| H | T_eff (y) | MDE S (80%) | S=0.2 | S=0.5 | S=1.0 opt | S=2.0 robustness |
|---|---|---|---|---|---|---|
| 1 | 4.96 | 1.26 | 0.06 | 0.20 | 0.61 | 0.99 |
| 5 | 0.99 | 2.81 | 0.04 | 0.07 | 0.17 | 0.51 |
| 10 | 0.50 | 3.98 | 0.03 | 0.05 | 0.10 | 0.29 |

Sessions required at the optimistic corner: 1,962·H (H=1: 1,962 > ≈1,240 available).

## 4. HOLDOUT design (250 sessions post-freeze, α = 0.05, T = 1.0 y)

Covered exactly by `power.py` at ALPHA = 0.05 up to the H factor. Power = Φ(ncp − 1.6449):

| H | T_eff (y) | MDE S (80%) | S=0.2 | S=0.5 | S=1.0 opt | S=2.0 robustness |
|---|---|---|---|---|---|---|
| 1 | 1.00 | 2.49 | 0.07 | 0.13 | 0.26 | 0.64 |
| 5 | 0.20 | 5.56 | 0.06 | 0.08 | 0.12 | 0.23 |
| 10 | 0.10 | 7.86 | 0.06 | 0.07 | 0.09 | 0.16 |

Sessions required at the optimistic corner: 1,546·H (H=1: 1,546 > 250 available).

## 5. H treatment and band standing

Power differs by H (tables above); fees already differ by H (v1 §8 retained: drag ≈ 125/H %/yr, so only
H=10 is arguably feasible); selection is unchanged (v1 §9 retained). The band [0.2, 0.5, 1.0] is
retained verbatim: it bounds plausible session-series Sharpe magnitudes, a question independent of the
ncp mapping, and is applied uniformly across H as a generous envelope (a narrower H-specific band could
only lower the optimistic corner). Contributing-session shortfall needs no invented count: tables use
nominal n (generous — any shortfall strengthens ABANDON).

## 6. PASS / ABANDON (mechanical, per pinned H)

**PASS iff optimistic-corner power ≥ 0.80 at BOTH VAL and HOLDOUT for the pinned H.** Evaluated: the
best cell anywhere is VAL/H=1 at 0.61; the best HOLDOUT cell is 0.26. Every H fails both stages at every
defended level; even undefended S = 2.0 fails HOLDOUT at all H (best 0.64) — only S ≥ 2.49 (H=1) would
pass HOLDOUT, a band top no adjacent evidence supports and this declaration does not supply.
**Verdict: ABANDON.** Per frozen §12: no data read at any stage; the protocol returns to draft. The v1
ABANDON is preserved on corrected arithmetic, not for convenience — v1's H=1 row is reproduced exactly,
and the correction moves H=5/10 strictly downward.

## 7. Pre-read inputs and governance

Frozen: this file (commit hash), protocol v1.3, band/method/α/hurdle as above; exact VAL count from
`trading_calendar` (lookup, not decision); companion `.py` transcription unchanged in values. This v2
amends only the mapping; v1 stays immutable per governance. No M1c result was consulted at any point;
nothing herein permits or requires one.

## Change Log

- v2 (2026-09-29, FROZEN): methodology correction — Sharpe→HAC mapping re-derived (§2: floor
  ncp = S·√(T/H)); 0.9 haircut withdrawn as underived; per-H power/MDE tables (§§3–4); band, windows,
  α-levels, hurdle, fee/selection analysis, and ABANDON verdict basis retained; verdict ABANDON,
  strengthened. v1 retained immutably in history.
