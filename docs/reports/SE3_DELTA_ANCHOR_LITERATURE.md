# SE-3 — δ Anchor: External Literature Pass

**Date:** 2026-08-05
**Author:** Claude (lead)
**Status:** **Proposed band, awaiting operator approval.** No declaration is frozen, no SHA is
pinned, no RFA gate has been run, no construct code exists.
**Prerequisite read:** `SE3_BREADTH_PROBE_REPORT.md` (supplies `sd_IC`), `SE3_BREADTH_PROBE_REVIEW_2.md`
(ladder final + operator decision), `SE3_BREADTH_PROBE_PROMPT.md` §8 (why this pass exists).

---

## 0. What this is, and what it is not

The breadth probe supplied the **SD half** of SE-3's RFA input and deliberately left the **δ half**
open. Its §7 forbids the measured `mean_IC` from becoming that anchor, and its §8 names the
external sources the anchor must come from instead. This document performs that pass.

**It produces one thing: a defended δ band for `metric="rank_ic"`, with its derivation exposed.**

It does not pre-register SE-3, does not freeze a declaration, does not run the gate, and does not
authorize construct code.

### Disclosure required before the band is read

**I knew the decision thresholds before deriving this band.** Specifically: the probe's ladder
anchors (δ = 0.015 Green / 0.020 Amber / 0.029 Red-amber) are in a prompt I wrote, and I computed
the exact break-even (δ = 0.01276 at `sd` = 0.1877, n = 1,701) in the same working session as the
translation below.

This is stated because SE-1's own declaration header forbids "a band widened because the first one
abandoned," and that prohibition is meaningless if the author's knowledge of the threshold goes
unrecorded. The derivation below fixes each component from a published number **before** any
comparison to a threshold, and §7 states in advance what would move the band. A reader who
distrusts this should test §4's components against the sources directly — every input is a quoted
figure with a page-level provenance, not a judgement call.

---

## 1. The central obstacle: every candidate δ is a derivation, not a citation

**No paper in this literature reports a daily cross-sectional Spearman rank IC.** The quantity SE-3's
gate needs does not exist in published form. What exists is:

| Source | Reports | Units |
|---|---|---|
| Bakshi & Kapadia (JoD 2003) | mean delta-hedged gain | % of underlying / % of option price |
| Goyal & Saretto (JFE 2009) | long-short decile portfolio return | % per month |
| Cao & Han (JFE 2013) | quintile spread + Fama–MacBeth coefficients | % per month, regression β |
| Driessen, Maenhout & Vilkov (JF 2009; 2013 companion) | variance/correlation risk premia | annualized vol points |

So the anchor **must** be translated, and an undisclosed translation is precisely the O1
crossed-corner error. §3 states each source in its own units; §4 performs the translation in the
open.

---

## 2. Sources, verified against primaries

All four were read as primary text (PDFs extracted and grepped), not from abstracts or summaries.
Where a secondary source disagreed with a primary, the primary won — see §2.4.

### 2.1 Cao & Han (2013), *Cross section of option returns and idiosyncratic stock volatility*, JFE

**The load-bearing source.** Sample **January 1996 – October 2009**, OptionMetrics, **213,640
call-option observations across 6,141 stocks**, ATM (~50 days to maturity), monthly formation,
**daily delta-rebalancing**.

Table 1 summary statistics, verbatim:

| Quantity | Mean | SD |
|---|--:|--:|
| Delta-hedged gain until maturity / (Δ·S − C) | **−1.13%** | **8.07%** |
| Delta-hedged gain until **month-end** / (Δ·S − C) | **−0.81%** | **5.13%** |
| Delta-hedged gain until maturity / (P − Δ·S) — puts | −0.82% | 6.46% |
| `VOL_deviation` = ln(VOL/IV) | −0.09 | **0.29** |

Fama–MacBeth cross-sectional regressions (Newey–West t in parentheses), **calls**:

| Regressor | Until maturity | Until month-end | **Until next week** |
|---|--:|--:|--:|
| `VOL_deviation` | 0.0639 (17.28) | **0.0512 (17.93)** | **0.0168 (15.01)** |
| Average adj. R² | 0.0941 | 0.1237 | 0.0594 |

And in the specification that carries both volatility variables jointly: `IVOL` enters at
t = −15.78, `VOL_deviation` at **+0.0604 (t = 17.12)**, with average adj. R² rising from 0.0242 to
0.0757 when `VOL_deviation` is added.

**The "until next week" column is the single most valuable number in this pass** — it is a
*measured* short-horizon coefficient, which converts the horizon translation in §4.2 from an
assumption into an interpolation between two published points.

**Transaction costs (their §on profitability):** the IVOL quintile spread earns **1.4%/month at
mid-quotes**, **0.79%** at 25% of the quoted spread, and **0.17%** at 50% of the quoted spread —
"no longer statistically or economically significant." Their own words: the pattern "lies within
the no-trade band."

### 2.2 Bakshi & Kapadia (2003), *Volatility Risk Premiums Embedded in Individual Equity Options*, Journal of Derivatives

The individual-equity companion to the index paper. **1991–1995, 25 stocks + SPX**, daily-rebalanced
delta-hedged calls held to maturity.

- Across the 25 stocks, the delta-hedging strategy loses **0.03% of underlying asset value**.
  The same strategy on the index loses **0.07%**.
- Mean IV − RV: **3.3%** for SPX calls; **1.5%** averaged across the 25 stocks (**1.07%** after
  excluding dividend-paying observations).
- Average delta-hedged gain is negative for **14 of 25** stocks; 7 significantly negative at 99%,
  4 significantly positive.
- Verbatim: individual equity options embed a negative market volatility risk premium *"although
  much smaller than for index options,"* and **"idiosyncratic volatility does not appear to be priced."**

**The cross-sectional dispersion in their Exhibit 2 is the quietly important part.** Per-stock mean
Π/C ranges from **−11.01% (BankAmerica) to +11.76% (Schlumberger)** around a small negative centre.
A large dispersion around a near-zero mean is a *low* signal-to-noise cross-section — which is
exactly what a rank IC measures, and it is why the δ derived in §4 is small.

### 2.3 Driessen, Maenhout & Vilkov — JF 2009 and the 2013 companion

**This is the counter-evidence, and it is on SE-3's own mechanism.**

From the 2013 companion (*Option-Implied Correlations and the Price of Correlation Risk*), read
directly:

- S&P 500: realized vol **20.69%** vs model-free implied **23.09%** — null of equality *"strongly
  rejected."*
- Individual options: realized **41.99%** vs implied **43.38%** — **"not statistically
  significantly different."**
- Testing stock by stock, the null of zero variance risk premium at 30-day maturity **"is not
  rejected at the 5% confidence level for 503 stocks out of the 919 stocks"** in the S&P 500; for
  DJ30, not rejected for **27 of 43**.
- Self-citing DMV (2009): they *"cannot reject the null hypothesis of a zero variance risk premium
  in individual options for the large majority of stocks considered."*
- Implied vs realized **correlation**: 39.5% vs 32.5% (S&P 500), 46.0% vs 35.5% (DJ30).
- DMV 2009's own abstract: the correlation risk premium **"cannot be exploited with realistic
  trading frictions,"** which they read as limits-to-arbitrage.

Cao & Han independently corroborate in a footnote: DMV *"find no evidence for the presence of a
significant volatility risk premium in individual stock options."*

### 2.4 Goyal & Saretto (2009), *Cross-section of option returns and volatility*, JFE

Sorts on the difference between historical realized and ATM implied volatility; long-short decile
straddle portfolio returns ~22.7%/month with Sharpe 0.710, and significant returns to the
corresponding delta-hedged call portfolios.

**The straddle number is not usable here** — straddles are not delta-hedged and their return
distribution is not the quantity SE-3 measures. Goyal & Saretto enters this pass as the
*sign-and-existence* authority for the richness variable; **Cao & Han supplies the magnitudes**,
because Cao & Han reports the cross-sectional SD that a rank-IC translation requires and Goyal &
Saretto does not.

**A sign correction, recorded because it nearly propagated.** A secondary source (Cao 2018, HEC
working paper) describes Goyal & Saretto as finding a *"significant negative relation of
VOL_deviation and delta-hedged option return."* **That is backwards relative to the primary.** Cao &
Han's own table has `VOL_deviation` = ln(VOL/IV) entering with a **positive** coefficient
(+0.0512, t = 17.93). Since richness is IV *high* relative to RV — i.e. *low* ln(VOL/IV) — the
delta-hedged return is **decreasing in richness**.

**This confirms SE-3's pre-registered negative expected sign from an independent source**, and it
is why the primary table was checked rather than the secondary description trusted.

---

## 3. What the literature says about SE-3 specifically

Three findings, and they do not all point the same way.

**(a) The cross-sectional effect is real, strong, and on the right variable.** `VOL_deviation` is
the closest published analogue to SE-3's variant-A richness residual, and it survives at t ≈ 18 in a
6,141-stock panel with controls.

**(b) The *level* premium on constituent options is close to zero — and that is fine, because SE-3
does not bet on the level.** DMV's result kills the index-vs-basket dispersion trade on the
constituent leg, but that form was already blocked (one number per day). SE-3's cross-sectional form
needs richness *dispersion* to predict return *dispersion*, which is a different claim and is the
one Cao & Han establishes. **This distinction is load-bearing and must survive into the
pre-registration: SE-3's demonstrable form does not inherit the index VRP.**

**(c) The consequence: India's special mechanism supports the leg SE-3 cannot bet on.** The dossier
§B grounds SE-3 in retail dominance of *index* options and states there is no comparable
single-stock retail demand. That story is about the index leg. **The constituent cross-section rests
on a US-documented effect with no Indian amplification**, and the band in §5 must not be inflated by
the Agarwal et al. retail evidence. It is not.

### Is SE-3 IVOL-in-disguise? — asked, and answered no

The repo has standing reason to ask: **IVOL sorted this exact universe on vol level, passed TRAIN
and HOLDOUT, and sign-flipped at SEALED** (IC +0.018, net −13.78%). SE-3's variant-A residual
`σ_i − (a + b·rv_i)` is mechanically correlated with vol level, and the LAG sleeve died on exactly
this subsumption test.

**Cao & Han answers it directly and favourably: `IVOL` (t = −15.78) and `VOL_deviation` (t = +17.12)
are jointly significant with opposite signs in the same Fama–MacBeth specification.** They are not
the same variable, and richness is not subsumed by vol level. Note also that the repo's IVOL sleeve
sorted *equity* returns in an equity L/S book, whereas Cao & Han's IVOL result is about *option*
returns — related but distinct constructs.

**This is not a discharge.** A subsumption guard against the repo's own Trend/IVOL signals must
still run at design time on this substrate, exactly as the LAG sleeve's did. What the literature
establishes is that the guard is not *expected* to fire.

---

## 4. The translation, in the open

### 4.1 Monthly cross-sectional correlation

Two independent routes, both from Cao & Han:

**Route A — Fama–MacBeth coefficient.** A 1-SD move in `VOL_deviation` (SD = 0.29) shifts the
month-end delta-hedged gain by `0.0512 × 0.29 = 1.485%`, against a cross-sectional SD of 5.13%:

```
IC_monthly = 1.485 / 5.13 = 0.2894
```

**Route B — R² increment.** Adding `VOL_deviation` lifts average adj. R² from 0.0242 to 0.0757:

```
IC_monthly = sqrt(0.0757 - 0.0242) = 0.2269
```

Route B is the conservative one and is used for the band floor; Route A for the ceiling.

*(Sanity check on a third route: Cao & Han's IVOL quintile spread of 1.4%/month against σ_cs = 5.13%
implies IC = 1.4 / (2.7996 × 5.13) = 0.0975, using the standard-normal quintile spread factor 2.80.
That is the weaker IVOL variable rather than richness, so it is a floor on plausibility, not an
input.)*

### 4.2 Horizon: monthly → daily

SE-3 forms daily; Cao & Han forms monthly. If a signal's edge accrues linearly in horizon `h` while
noise accrues as `√h`, then `IC ∝ √h`. The published "until next week" column lets this be
**checked rather than assumed**:

```
IC_week  = 0.0168 × 0.29 / (5.13 × sqrt(5/21)) = 0.1946
IC_month = 0.0512 × 0.29 / 5.13                = 0.2894
observed ratio = 0.6725     sqrt(h) predicts = 0.4880
=> empirical exponent p = 0.2765  (IC ~ h^p)
```

The measured decay is **slower** than `√h` — the signal is front-loaded. This is favourable, and it
is deliberately **not** used in the ceiling:

| Horizon model | Daily IC from monthly |
|---|--:|
| `√h` (standard, conservative) | 0.0632 |
| empirical `h^0.2765` | 0.1247 |

Extrapolating below the shortest *measured* horizon (1 week → 1 day) is extrapolation, not
interpolation, so **`√h` is used for both ends of the band.** The empirical exponent is recorded as
an upside the band does not claim.

### 4.3 Haircuts

| Haircut | Factor | Basis |
|---|--:|---|
| Out-of-sample shrinkage | **0.492** | CB-N50 measured 50.8% shrinkage (TRAIN +0.059 → HOLDOUT +0.029) on the *same* daily cross-sectional rank-IC method in *this* repo |
| US → India transport + univariate-vs-multivariate | **0.60** | Cao & Han's coefficient is a *partial* effect with controls; SE-3's IC is univariate. Indian single-stock option books are thinner and PIT-eligible names fewer (~46 vs 6,141) |

The India/univariate haircut is applied to the **floor only**. Defending it on the ceiling would
require asserting that the effect is *no larger* in a less efficient market, which is not
established either way.

---

## 5. THE PROPOSED BAND

```
delta_lo = 0.2269 × 0.2182 × 0.492 × 0.60 = 0.01462
delta_hi = 0.2894 × 0.2182 × 0.492        = 0.03107
```

| Parameter | Value |
|---|---|
| `metric` | `rank_ic` |
| **`delta_lo`** | **0.0146** |
| **`delta_hi`** | **0.0311** |
| **`sd_lo`** | **0.18** |
| **`sd_hi`** | **0.26** |
| `test_type` | two-sided |
| `n_available` | 1,701 (permissive) — 495 recorded as sensitivity |

**Corners are not crossed.** `delta_hi` takes the optimistic IC route and the lighter haircut but
holds the horizon model at the conservative `√h`. Taking the empirical exponent as well would give
**0.0614**, which is not claimed.

### The sd band, and why it is not the two measured points

The probe measured `sd_IC` = 0.1877 (A) / 0.1814 (B) on 713/483 dates in a single three-year window.
The gate reads the **optimistic** corner — high δ, **low** sd — so `sd_lo` is where a verdict can be
silently manufactured, and it is set at **0.18**, essentially the measured floor. **It is not set
below the measurement**, because nothing supports that.

`sd_hi` = 0.26 (≈ +40%) carries the C2 lesson explicitly: C2 was retired precisely because an SD
estimated on a short window did not survive a wider one. SE-3's confirmatory window
(2016-02-11 → 2022-12-31) spans **COVID**, and 2023–2025 does not. Cross-sectional IC dispersion is
regime-dependent and a wider window should raise it.

---

## 6. Reconciling `sd_IC` = 0.1877 with `N_eff` = 5.9

These look contradictory and are not. Recording the resolution because it would otherwise surface as
a late objection.

| Breadth notion | Implied `sd_IC` = 1/√(N−1) |
|---|--:|
| nominal N = 50 | 0.1429 |
| median populated N = 46 | 0.1491 |
| **observed `sd_IC` = 0.1877 ⇒ N = 29.4** | — |
| raw `N_eff` = 5.9 | 0.4518 |
| demeaned `N_eff` = 44.1 | 0.1517 |

If breadth for IC purposes were the raw `N_eff` of 5.9, the observed `sd_IC` would be ≈ 0.45. It is
0.1877.

**They measure different things and are not required to agree.** `N_eff` was computed on the
*levels* of `dh_return_scaled`, so a market-wide vol shock that moves all 50 names together inflates
`rho_bar` and collapses `N_eff`. But a **Spearman rank IC depends only on the within-day ordering of
returns, and a common additive shift leaves that ordering unchanged** — so the common factor that
destroys `N_eff` is very nearly invisible to the IC.

The IC-implied breadth of **29.4** sits between the raw 5.9 and the demeaned 44.1, which is exactly
where a rank statistic should land: above the level-based figure because the common factor is
neutralized, below the demeaned figure because demeaning over-corrects by construction.

**Consequence, and it cuts both ways.** For the `rank_ic` gate the relevant dispersion is the one
**directly measured** — `sd_IC` — and it needs no derivation from `N_eff` at all. But `N_eff` = 5.9
remains the honest breadth for anything expressed in **P&L**: a book of ~46 names with ~6 independent
bets. **A `rank_ic` PASS therefore does not imply a `per_trade_pnl` PASS**, and CB-N50's binding
constraint #3 applies in full — SE-3's primary hypothesis must genuinely be stock-level
cross-sectional prediction, not an index view wearing a cross-sectional veneer.

---

## 7. What would falsify this band

Stated now, before any gate is run, so it cannot be renegotiated later.

1. **The horizon translation is the biggest single lever.** The `√h` assumption is checked against
   *one* published short-horizon point. If SE-3's true daily IC decays faster than `√h` below the
   one-week horizon — plausible if daily delta-hedged returns are dominated by settle-price
   microstructure noise, which the probe's own same-day contamination finding shows is present —
   `delta_hi` falls. **A drop to 0.394× of the claimed value flips the permissive verdict.**
2. **Cao & Han's effect is largely eliminated by transaction costs** (1.4% → 0.17%/month at 50%
   effective spread). The gate's δ is gross, so this does not bear on the gate — but it bears
   heavily on whether SE-3 is *worth* building, and Indian single-stock option spreads are wider than
   US ones. **A net-of-cost read is a mandatory design-stage gate, not an afterthought.**
3. **If the signal drifts from ATM level richness toward wing/skew features**, the Skew sleeve's
   exposure becomes a spend, n falls to ≈495, and the operator's permissive decision is void
   (`SE3_BREADTH_PROBE_REVIEW_2.md`). This band does not rescue that — see §8.
4. **If a subsumption guard shows richness is largely Trend or IVOL in disguise** on this substrate,
   §3's favourable reading is void regardless of what Cao & Han found in the US.

---

## 8. Projected gate arithmetic — **NOT a gate run**

Computed with `scripts/rfa/power.py`, two-sided, α = 0.05, target power 0.80. **No declaration is
frozen and no SHA is pinned; this is a sensitivity, and the real verdict is whatever the gate returns
against an approved, frozen declaration.**

| Reading | Optimistic corner (δ=0.0311, sd=0.18) | Central | Pessimistic (δ=0.0146, sd=0.26) |
|---|--:|--:|--:|
| **Permissive n = 1,701** | ncp 7.12, power **1.0000** | 0.9898 | 0.6397 |
| **Strict n = 495** | ncp 3.84, power **0.9695** | 0.6353 | 0.2384 |

`n_required` at the optimistic corner: **266**. At the band floor: **2,485**.

Three things worth stating plainly:

- **The strict/permissive distinction stops binding.** The operator decision of 2026-08-05 adopted
  the permissive reading and recorded strict as a sensitivity. At a literature-defended
  `delta_hi` = 0.0311 — just above the ladder's Red-amber anchor of 0.029 — **both readings clear**.
  The decision is materially de-risked, though its falsification condition (§7.3) still stands.
- **At the band floor SE-3 is not demonstrable even on the full permissive window** (`n_required`
  2,485 > 1,701 available). The gate reads the optimistic corner by design, so this does not change
  the verdict; it is the honest statement of what a pessimistic truth would mean.
- **This gate will say PROCEED and that is close to a formality.** A δ_hi above ~0.0128 clears, and
  that is a low bar for any real cross-sectional signal. **PROCEED means "not provably infeasible."**
  SE-3's actual risks — the dossier §G warning that *a dispersion book reports an attractive Sharpe
  until correlation goes to one*, and its "Very High" implementation difficulty — are **invisible to
  the noncentral-t gate.** A comfortable band is not validation.

### On the probe's measured `mean_IC`

The probe measured a skip-a-day `mean_IC` of **−0.113**, against this pass's pre-haircut daily range
of **[0.063, 0.125]**. The magnitudes agree closely, which is mild corroboration that the
translation is not absurd.

**It changes nothing.** The probe's number remains prohibited as the anchor (`SE3_BREADTH_PROBE_PROMPT.md`
§7) — it comes from a window that is prior-exposed on the index leg and now spent on the stock leg,
and inheriting an effect size from a short contaminated read is the specific error that retired C2.
The agreement is reported as a consistency check, **not** as evidence, and no band component above
was chosen with reference to it.

---

## 9. What this does not authorize

Unchanged from the probe's §8 and the operator decision, and restated so nothing is assumed
discharged:

1. **No construct code.** No signal module, no backtest, no `governance/rfa/declarations/se3.py`.
2. **No window is opened.** The 1,701-date index-option window (2016-02-11 → 2022-12-31) and the
   joint-clean 2021–2022 stock-option window remain untouched. **This pass read no market data.**
3. **The variant choice (A vs B) is a selection with m = 2** and must be declared. MEDIUM-2 of the
   round-2 review means the natural comparison is confounded, so the variant must be chosen on
   *a priori* mechanism grounds, not on the 0.1877-vs-0.1814 gap.
4. **The pre-registration must pin the signal to ATM level richness** (§7.3), or accept the strict
   reading from the outset.

**Next step is an operator decision on the band in §5** — approve, amend, or reject. Only after
approval does a frozen declaration and a gate run follow.

---

## Sources

- [Cao & Han (2013), *Cross section of option returns and idiosyncratic stock volatility*, JFE](https://www-2.rotman.utoronto.ca/facbios/file/Han_JFE_published.pdf)
- [Bakshi & Kapadia (2003), *Volatility Risk Premiums Embedded in Individual Equity Options: Some New Insights*, Journal of Derivatives](https://people.umass.edu/~nkapadia/docs/Bakshi_Kapadia_JoD_Fall_2003.pdf)
- [Bakshi & Kapadia (2003), *Delta-Hedged Gains and the Negative Market Volatility Risk Premium*, RFS](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=267106)
- [Driessen, Maenhout & Vilkov (2013), *Option-Implied Correlations and the Price of Correlation Risk*](https://www.netspar.nl/assets/uploads/061_Driessen.pdf)
- [Driessen, Maenhout & Vilkov (2009), *The Price of Correlation Risk: Evidence from Equity Options*, Journal of Finance 64(3)](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2009.01467.x)
- [Goyal & Saretto (2009), *Cross-section of option returns and volatility*, JFE 94, 310–326](https://www.sciencedirect.com/science/article/abs/pii/S0304405X09001251)
