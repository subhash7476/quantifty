# Research Library Triage — 2026-09-26 (full read)

**What this is:** a triage of the paper-summary library downloaded on 2026-09-26. Every paper that touches a live surface in this repo is mapped to it, with an action class. This version supersedes the earlier partial triage from the same day, which read about 20 files, mostly only their first 3–4 KB.

## 1. Coverage and method

- **Source:** 11 zips in `C:\Users\devou\Downloads\`: 647 Markdown files.
  - Near-duplicates collapsed to **370 unique papers**, keeping the longest copy of each (7.8 M characters).
  - The files are **secondary summaries** of unknown provenance, and some filenames show libgen origin.
  - Numbers quoted from them are marked **[summary]** and were not checked against the original papers.
- **Read in full:** all 370, by five parallel readers working from one written card of the repo's live surfaces, closed areas and constraints. Every paper got a verdict line: 106 findings, 264 with no actionable finding.
- **Verified by me, against the summary text and/or the repo:**
  - Dao et al.'s strangle/hedging identity (§8 of that paper)
  - Gatheral eq. 11.4
  - Johnson's sign of the SLOPE effect
  - Constantinides et al. on puts (inconclusive, which corrects one reader's note)
  - Clarke–de Silva–Thorley's IC SD of 0.079 vs 0.045
  - Mitchell–Pulvino's β_L = 0.492 below a −4% threshold
  - `ca_in_hold` in `build_stock_straddles.py`
  - `scripts/rfa/power.py` and the missing overlap fields
  - CB-N50's autocorrelation disclosure
  - the N200 spec's persistence baseline
  - NiftyShield's legs and √t bracket scaling
  - the dashboard's IV source
  - the chain-snapshot store (§3.4)
- **Reader-reported, not re-checked by me:** every other paper number, including:
  - Kim–Tse–Wald's power arithmetic
  - Lo 2007's sign flip on coarsening
  - Barroso's and Lewellen's slopes
  - Hou–Xue–Zhang's 65%
  - Grinold's breadth = g·N
  - Almgren's constants
  - Brooks–Kat's moments
  - the Lo 2001 tail arithmetic (this one is standard binomial and correct)

  Treat these as leads to confirm in the paper before relying on them.
- **Not covered — 7 papers exist only as corrupt `.xz` files:**
  - Kumar et al., *Gambling and Comovement*
  - Hirshleifer–Hou–Teoh, *The Accrual Anomaly*
  - Gabaix et al., *A Theory of Power-Law Distributions*
  - Shephard–Andersen, *Stochastic Volatility Modeling*
  - Campbell–Shiller 1988, *Stock Prices, Earnings and Expected Dividends*
  - AQR, *Understanding Managed Futures*
  - Jarrow–Turnbull, *The Intersection of Market and Credit Risk*
- **Summaries too thin to judge the book:** Hull (*Risk Management and Financial Institutions*: chapters 1–2 only), Lando (*Credit Risk Modeling*: mostly repeated padding) and Galariotis–Zopounidis (*Quantitative Financial Risk Management*: regime chapter present only as a table of contents).

### Action classes

- **(a) Explanatory** — a citation or wording change; reads no data.
- **(b) Diagnostic / infrastructure** — shadow facts, attribution, cost or risk models, QA.
  - Reads no unspent window and changes no frozen rule.
- **(c) New construct** — its gate depends on the surface:
  - A research construct needs an RFA declaration.
  - A NiftyShield rule change goes through the MM12.5 promotion pipeline: new execution identity and a window restart.

**Nothing in this report is a reason to re-tune a frozen or closed construct.**

## 2. Where the library adds most — summary

| # | Surface | What | Class | Papers |
|---|---|---|---|---|
| 1 | NiftyShield | Per-session P&L attribution: implied variance sold vs realized variance vs **intraday-trend term**, plus exit-rule cost | (b) | Dao et al. 2016; Bhansali–Holdom 2024; Gatheral 2006; Bruder–Gaussel 2011; Fung–Hsieh 2001 |
| 2 | NiftyShield | The bracket's √t scaling and the trend term are **one measurable spot-only quantity** (13:00→close variance ratio) | (b) | Dao et al.; Briner–Connor 2007 |
| 3 | NiftyShield | Market-implied state it never reads: IV term-structure slope, model-free fair variance, risk-neutral P(breach) | (b) | Johnson 2017; Gatheral; Breeden–Litzenberger; Jackwerth–Rubinstein; Dupire |
| 4 | NiftyShield | A fixed-structure shadow book to credit the DayType/VIX selector. It can be rebuilt from stored chain snapshots (§3.4). | (b) | Kim–Tse–Wald 2016 |
| 5 | NiftyShield eval | Sharpe is the wrong sole yardstick for a short-gamma book | (b) | Brooks–Kat 2001; Amin–Kat; Lo 2001; Constantinides et al. 2010 |
| 6 | Straddle selling | A named test for the `ca_in_hold` measurement: CA-verified vs pure-move split, then kinked market beta | (b) | Mitchell–Pulvino 2000; Jacobs–Levy (ch. 7); Daniel–Moskowitz |
| 7 | RFA gate | IC horizon/overlap has no field in the contract; IC SD has a floor; a lab-wide trial ledger; Holm instead of Bonferroni | (b) | Grinold 2007; Grinold–Kahn; Qian–Hua–Sorensen; Clarke–de Silva–Thorley 2005; Harvey–Liu–Zhu; Hou–Xue–Zhang; Barroso 2016; Lewellen 2015 |
| 8 | TS combo paper | Set the futures-P&L expectation before forward months arrive; attribution of signal vs construction | (b) | Fama–French 1987; Clarke–de Silva–Thorley; Paleologo 2025; Lo 2007 |
| 9 | Cost model | Flat κ contradicted — impact scales with σ × participation^0.5–0.6 | (b) | Almgren et al. 2005; Almgren 2008; Bouchaud; Gatheral 2010; GS shortfall model |
| 10 | Closed areas | Literature accounts of the basis-family, IVOL and pair-study outcomes | (a) | several; see §9 |

---

## 3. NiftyShield

**Repo facts checked:**
- `strategies/nifty_shield_v1/config.py` selects a strangle or iron fly by VIX percentile, so it holds short calls *and* short puts.
- Exits are a TP/SL bracket at spot ± 1σ over the hold (`bracket_sigma: 1.0`, `hold_hours: 2.5`).
- `core/execution/options/nifty_shield_pricing.py:173` scales IV by √(hold_hours / (252·6.25)): **pure √t scaling**.
- Delta is a flatten-gate; there is no hedging.

### 3.1 P&L attribution — the trend term (HIGH, (b); verified)

**Dao et al. 2016** (*Tail Protection for Long Investors: Trend Convexity at Work*), §8:
- A continuum of strangles pays ½(S_T − S₀)². Delta-hedging it converts that into ½ΣD_t² (the sum of short-interval squared moves).
- The difference is an exact identity: (S_T − S₀)² − ΣD_t² = 2Σ_{i<j}D_iD_j. That is the **autocorrelation (trend) term**.
- NiftyShield sells the structure and, by operator decision, does not hedge, so it pays premium against (S_exit − S_entry)², *not* against ΣD².
- **It therefore loses to intraday trend on top of realized volatility, and gains on mean-reverting afternoons.**

The same identity appears in:
- **Bhansali–Holdom 2024:** the short-option book earns theta and pays ½ΣΓ(ΔS)².
- **Gatheral:** eq. 3.5 — implied variance is a gamma-weighted average of the realized path.
- **Chan 2017** (*Machine Trading*).

These are one finding, not four.

**Action — a per-session shadow row, outside the hashed files:**
- implied variance sold (ATM IV² × hold),
- realized ΣD² from 1m Nifty bars,
- realized (S_exit − S_entry)²,
- the split of realized P&L into a *volatility-mispricing* term and a *trend* term,
- the DayType fact and VIX bucket.

It reads the forward chain and 1m bars only.

**Extensions from the same family:**
- **Bruder–Gaussel 2011:** any stop or flatten rule is a static option profile paid for through the path. So log the counterfactual hold-to-planned-exit P&L of the entered structure (chain marks) against the bracketed P&L. The gap is what the bracket and flatten-gate actually cost or earn. The rule itself stays frozen.
- **Fung–Hsieh 2001:** a stop bracket turns a short straddle toward a short *lookback* straddle, i.e. short intraday range. Regress session P&L on the terminal move and, separately, on the post-entry range. Whichever explains more is what the selector should be forecasting.
- **Mauchand–Brument 2022:** a rolling fit of session P&L on the Nifty move and its square gives a realized short-gamma coefficient by VIX / DayType bucket. It is a cheap summary of the above. (LOW)

### 3.2 One spot-only measurement answers two questions — do this first (HIGH, (b))

**What the bracket assumes.** It scales IV by √(2.5 / (252 × 6.25)). That builds in two assumptions:
- daily variance is spread **uniformly** over the 6.25-hour session, with **none** of it overnight;
- no autocorrelation within the hold.

IV prices close-to-close variance *including* the overnight gap, and intraday volatility is U-shaped. So the first assumption is probably the bigger error.

**Measurements** — all on 1m `NSE_INDEX|Nifty 50` bars, 2023 onward:
1. **Afternoon variance share (direct test of the uniform assumption).** Σ(1-min D²) over the hold window, divided by close-to-close variance, pooled as a ratio of sums, compared with the bracket's implied share of 2.5/6.25 = 0.40.
2. **Trend term (Dao et al.; Briner–Connor 2007).** The mean of (S_end − S_13:00)² − ΣD² with a block-bootstrap confidence interval, grouped by the DayType fact. Use the difference or ratio-of-sums form, not a mean of per-session ratios, which outliers dominate.
   - Positive means afternoons trend: √t under-sizes the move and the stops sit too tight. Negative means the reverse.
   - If trend-type DayTypes carry most of it, that is the mechanical reason the regime gate matters.

**Data caveats (checked):**
- The 1m store holds **no Nifty futures bars**; `NSE_EQ` and `NSE_INDEX` only. So Ferson 2006's stale-constituent correction cannot be done at 1m.
- `is_synthetic` is an `NSE_EQ` predicate and says nothing about index bars.
- **From 2026-08-03 (CAS)** most Nifty constituents stop continuous trading at 15:15, so the index is stale from 15:15 until the auction print, while options keep trading. End the window at 15:15 for post-CAS sessions and report the pre-CAS and post-CAS eras separately.

**Constraints:** it uses **no options history** (the protected 2016–22 window is untouched), reads only past spot returns, and changes no rule.

### 3.3 Market-implied state it never reads (MEDIUM–HIGH, (b))

All of these are shadow facts from the live 5-second chain, logged at the 13:00 entry, and none of them gates anything.

- **Term-structure slope — Johnson 2017.**
  - The level of the VIX curve (its first principal component, ~95% of variance) carries almost no information about future variance-asset returns. The slope (second component, ~4.5%) carries nearly all of it [summary].
  - An inverted front end predicts poor returns to short variance. The direction is stated consistently throughout the summary (negative coefficients, "sell variance when SLOPE is high").
  - NiftyShield conditions on the level only, which is the thing this paper finds uninformative.
  - **Pin one definition:** ATM IV of the first weekly expiry with DTE ≥ 2, minus ATM IV of the next monthly expiry. Exclude legs at ≤ 1 DTE.
  - `data/options/wall_scan_results.duckdb` has **no** term-structure field today: only single-expiry `atm_iv`, `realized_vol` and `iv_minus_rv`.
  - The evidence is SPX with 1–12-month tenors, so it may not transfer to Nifty weeklies.
- **Model-free fair variance — Gatheral eq. 11.4.** Fair variance = 2{∫ OTM puts dk + ∫ OTM calls dk} per weekly expiry, which gives the implied-variance leg of §3.1 without a model. Weekly wings are sparse; use Lee moment bounds for extrapolation, and note that jumps bias it.
- **Risk-neutral P(breach) — Breeden–Litzenberger; Jackwerth–Rubinstein; Dupire.**
  - The second strike-derivative of the call price, ∂²C/∂K², gives the risk-neutral density, so a butterfly price is the probability mass at its strike.
  - Log P(S_T beyond each short strike) and P(S_T beyond each wing) from a smoothed, convex call fit. Never difference raw quotes.
  - Get the forward from put–call parity.
  - Snapshots that violate butterfly or calendar arbitrage double as a chain-quality flag for the dashboard and poller.
- **Volatility forecast vs IV — Rosenberg–Engle 2001; Constantinides et al. 2010.** Two candidates:
  - a GJR-GARCH one-session volatility forecast from the 1d Nifty store (2012+);
  - "bias-adjusted ATM IV" (IV minus its running mean IV−RV gap), which was the best predictor of realized volatility in Constantinides et al. [summary].
  - Either gives an IV-minus-forecast VRP proxy per session.
- **Caveat — Grinold 1999:** a gap between the market bid and any physical-density price is *model disagreement* until forward P&L shows otherwise. Report it as such.

**Dashboard note:** `core/analytics/options_analytics.py` takes IV from Upstox's `option_greeks["iv"]`. The spot-vs-forward basis of the broker's IV is unknown. A parity-forward recomputation (Jackwerth–Rubinstein) would make the smile independent of it. (LOW)

### 3.4 Credit the selector separately — time-sensitive (MEDIUM, (b))

- **Kim–Tse–Wald 2016:** a conditional rule must be benchmarked against the unconditional version that shares every other component. TSMOM's famous alpha was mostly its volatility scaling.
- **Action:** run a shadow book with the same sizing, bracket, fees and R7 model, but **one fixed structure every day**. Report the paired per-session difference.
- **Timing (checked):** `data/options/wall_chain_snapshots/{date}.duckdb` stores intraday snapshots of the **nearest** Nifty weekly expiry, with bid/ask, IV and greeks. Daily files have been retained since 2026-09-04; `chain_cache.duckdb` keeps only the latest snapshot.
  - So this shadow, and the §3.1 attribution, **can be rebuilt afterwards from stored marks**. There is no 09-28 deadline, provided the rules are pinned in writing *before* anyone looks at results and the snapshot files are kept.
  - Exception: a session that trades a non-nearest expiry is not in the store.
  - **The one item that is truly forward-only is the §3.3 term-structure slope**, because the store holds only one Nifty expiry. Each session not captured is lost. Capturing it means the poller also has to store the next expiry.
- **Power:** at an annualized difference-Sharpe of 1.0, power 0.80 needs roughly 8 years of sessions. This is telemetry, never a gate, and must not be read early.

### 3.5 Evaluating the paper window (MEDIUM, (b))

- **Brooks–Kat 2001; Amin–Kat:**
  - The highest-Sharpe strategies are the short-optionality ones, with extreme negative skew [summary: risk-arb SR 2.26, skew −3.78].
  - Stale marks make returns autocorrelated, which understates σ.
  - **Action:** report skew, excess kurtosis, worst sessions and CVaR next to Sharpe. Check whether thin wing strikes are marked at LTP; if so, re-mark exit-side from the chain.
- **Lo 2001:** estimating a tail frequency to ±1% needs T = p(1−p)/0.01², i.e. 475 sessions for p = 5%. **A crash-free paper window cannot validate tail risk; say so in the E008 report.**
- **Constantinides et al. 2010:** judge a writing strategy by second-order stochastic dominance against index plus cash, not only Sharpe.
  - **Checked against the paper, and this corrects one reader's note:**
    - Writing *all* calls at the bid was insignificant.
    - Only calls whose bid exceeded a stochastic-dominance upper bound were "good sells".
    - Put-bound violations were **too rare for inference: inconclusive, not shown to lose**.
  - So the paper supports *conditioning* the calls NiftyShield writes, and gives no evidence either way on its short puts.
  - A per-leg `bid − bound` shadow fact is possible, but it is the costliest item here (a four-moment tree). (MEDIUM, after §3.1–3.3)
- **LOW additions:**
  - **Anderson–Bianchi–Goldberg 2014:** a covariance term between lots and per-lot P&L shows whether margin-driven sizing helps or hurts versus a fixed lot count.
  - **Foster–Hart 2013:** ruin-based riskiness R(g) of the session-P&L distribution as a capital check. It is undefined while mean P&L ≤ 0.
  - **Molyboga–L'Ahelec 2017:** the block-bootstrapped probability that the drawdown gate fires on a zero-edge book.
  - **Levy 2017 / Thorp 2006:** report geometric mean and implied Kelly fraction.
  - **Brandt–Santa-Clara 2006:** log the GEX state at entry; a Britten-Jones test later shows whether it belongs as a *sizing* input. Any sizing use is (c).
  - **Barron–Cover 1988:** the mutual information I(afternoon outcome; DayType | VIX bucket) on 1m history is a hard ceiling on what the regime fact can add to growth.

## 4. Stock straddle selling — the `ca_in_hold` measurement

**Repo fact checked:**
- `build_stock_straddles.py:61` flags a day when |ln(close/prev_close)| ≥ 0.25 on the front future.
- Line 104 sums those flags over the hold.
- `analyze_stock_straddles.py:15` and `cycle_study.py:18` drop every cycle with a non-zero count.
- The flag is a price-jump **proxy** for corporate actions, so it catches genuine crashes as well.

**Action (HIGH, (b); Mitchell–Pulvino 2000; Jacobs–Levy ch. 7; Daniel–Moskowitz 2016):**
1. Split the dropped cycles into CA-verified (check against the corporate-actions tables from `scripts/csmp/ingest_corporate_actions.py`) and pure large moves. **Only the second group is outcome censoring.**
2. Aggregate to one equal-weight seller P&L per expiry cycle. Fit a **kinked market-beta regression** on the Nifty hold-window return, with the kink threshold fixed in advance, once on kept cycles and once with the pure-move drops restored.
   - In merger arbitrage the unconditional β ≈ 0.12 hid β ≈ 0.49 below a −4% market month [summary].
   - Few cycles fall below any kink, so report confidence intervals and say so.
3. Report P&L net of the entry value of the equivalent short straddle as well as the raw mean. Report the crash frequency p and E[r | crash] explicitly, so the filtered mean cannot be read as the unconditional one.

**Supporting items (LOW):**
- Lillo et al.: cross-sectional "variety" V(t), market-wide vs idiosyncratic large moves.
- Jansen–Nikiforov: an ex-ante event flag vs the ex-post move.
- Bhansali–Holdom: the continuous gamma cost ½ΣΓ(ΔS)² per cycle in place of a binary drop.

**Constraint:** this re-measures cycles already generated in the spent 2023+ window. It is filter accounting and must not be used to choose a new filter. If policy forbids re-reading 2023+ even for accounting, run it on pre-2023 cycles.

## 5. RFA gate and research governance

**Repo facts checked:**
- `scripts/rfa/power.py` computes ncp = δ·√n / sd with raw n.
- Neither `declaration.py` nor the gate has a field for IC horizon, formation step or autocorrelation.
- `cb_n50.py` (lines ~111–119) **discloses in prose** that the gate does not haircut for autocorrelation, and re-checks at AC₁ = 0.3 (effective n ≈ 477, still PROCEED).

| Item | Class | Source | Note |
|---|---|---|---|
| Add `ic_horizon` and `formation_step` to rank_ic declarations. Deflate to n_eff = n·step/horizon, or apply a declared AC₁ haircut. **The "measurement density" escape in CLAUDE.md holds only up to the signal's own refresh rate**: breadth is g·N, not observations. | (b), METHODOLOGY_VERSION bump | Grinold 2007; Grinold–Kahn | Known in prose, not enforced. No existing verdict changes: ABANDONs only harden, and CB-N50 survives its own check. |
| Floor on the rank-IC SD: sd ≥ 1/√N_cross-section, and realized IC SD runs above it (0.079 vs 1/√500 = 0.045 [summary, verified]). CB-N50's optimistic sd_lo 0.15 sits just above its floor of 0.141, implicitly assuming almost no true IC variation. | (b) | Qian–Hua–Sorensen; Clarke–de Silva–Thorley 2005 | Applies to new declarations; frozen bands stay frozen. |
| Lab-wide trial ledger: count every construct run on the same TRAIN/HOLDOUT, and report future confirmatory p-values against it and against t ≥ 3. | (b) | Harvey–Liu–Zhu; Hou–Xue–Zhang (65% of 452 anomalies fail at 1.96 [summary]) | Per-battery m (e.g. PSB-2 m = 3) understates program-level multiplicity. |
| Use Holm step-down instead of Bonferroni: same family-wise error, never less power. Use a White reality-check bootstrap when selection ran over a grid (TS Basis Daily, F1's bracket grid). | (b) | Harvey–Liu–Zhu; Park–Irwin 2004 | Methodology note; closed batteries are not re-run. |
| An empirical in-sample→out-of-sample haircut fitted to the repo's own pairs: CB-N50 0.059→0.029, C2 0.035→0.023, IVOL −0.055→−0.030→+0.018, Carry, TS Basis. | (b) | Barroso 2016; Lewellen 2015 (OOS slopes 0.44–0.80 [summary]) | n < 10, so a floor on skepticism, not a coefficient. Operationalizes "SD must be independently defended". |
| For per_trade_pnl declarations of premium-selling constructs, require the declared skew and kurtosis. Noncentral-t power assumes near-normal P&L. | (b) | Brooks–Kat | — |
| Composite-sleeve power must apply IC²(combined) = 2IC²/(1+γ) with measured sleeve correlations. | (a) | Grinold–Kahn; Green–Hand–Zhang (mean \|ρ\| 0.22–0.29 even when mean signed ρ ≈ 0) | — |
| Pre-register the number of sort portfolios J. | (a) | Cattaneo 2017 | — |
| **Confirmations:** cadence invariance and demonstrability as the binding constraint. | (a) | Belentepe–Wyner 2005; Grinold–Kahn (SE(IR) ≈ 1/√years) | Independent support; cite in the RFA doc. |

## 6. TS Basis Daily combo paper book

The book is judged on forward futures P&L, never re-tuned. Everything below is expectation-setting or attribution.

- **(MEDIUM) Fama–French 1987 b1/b2 split on the already-burned TRAIN/HOLDOUT:**
  - S(T)−S(t) = a1 + b1·basis and F(t,T)−S(T) = a2 + b2·basis, with b1 + b2 = 1.
  - **Futures-net forward P&L can only come from b2.**
  - No TS Basis *Daily* futures translation exists in `docs/reports/ts_basis/`; the monthly one found futures IC ≈ 0.
  - If b2 ≈ 0 here too, write that down *before* the forward months arrive, so a forward null is not read as noise.
  - The sealed window stays unread.
- **(MEDIUM) Signal vs construction — Clarke–de Silva–Thorley 2005; Grinold 2006:**
  - Log daily the realized cross-sectional IC across the full eligible SSF set and the book's transfer coefficient.
  - A month of −43 bp decomposed into +57 bp signal and −109 bp construction noise in their example [summary].
  - Without this, "judge on futures P&L" cannot distinguish a dead signal from concentration luck.
- **(MEDIUM) Timing vs static drift — Lo 2007:**
  - E[R] = ΣCov(w, R) + ΣE[w]E[R], computed at daily frequency; coarsening flipped the sign in the paper's example [summary].
  - A large static share would be hidden beta or convergence drift: the Carry failure mode.
- **(LOW) Also:**
  - Paleologo 2025: selection × breadth + sizing decomposition.
  - Kane–Enos: sector/liquidity-matched control books.
  - Patton 2007: cubic and downside neutrality tests against Nifty.
  - d'Aspremont: basis half-life vs round-trip cost.

## 7. Cost model — flat κ is contradicted (MEDIUM, (b))

Four independent sources reject a constant bp-per-side cost:
- **Almgren et al. 2005:** temporary impact ∝ σ·(participation)^0.6, with γ ≈ 0.314 and η ≈ 0.142 [summary; US-calibrated].
- **Bouchaud; Gatheral 2010:** the square-root law ∝ σ·√(Q/ADV).
- **GS shortfall model:** cost depends on spread, volatility and participation.

**Action:**
- Add a σ- and participation-scaled sensitivity column beside flat κ in `scripts/signal_engine/carry/capacity_analysis.py` and `scripts/signal_engine/ts_basis_daily/run_capacity.py`, using futures bhavcopy volume and daily σ.
- For the combo book, declare the alternative cost model **before** reading forward results.

**Expected size:** probably second-order at retail participation (≪ 1% ADV). The value is flagging thin, volatile names.

(Avellaneda–Lee 2008 notes that 5 bp per side is the literature convention for large liquid names.)

## 8. N200 regime HMM — spec frozen; diagnostics only

**Repo fact checked:** the design spec (line 147) already scores Brier skill against a **persistence baseline** and an unconditional base rate. The readers' main suggestion is already in place.

Remaining (LOW–MEDIUM):
- **Nystrup–Boyd 2018:** verify the implementation takes tercile probabilities from the full mixture predictive distribution, including the between-regime variance term Σπ(μ−μ̄)², and uses ξΓ^h for h-step state probabilities.
- **Rogers–Zhou 2007:** check the GK inputs for Category I names after CAS. The auction-print close paired with the continuous-session high and low, and range-estimator bias under jumps, can distort them.
- **Daniel–Jagannathan–Kim 2012 / 2019:** report selectivity (state-occupancy rate), plus a table of how worst-decile outcomes fall across deciles of the *filtered* high-vol probability.
- **He–Kou–Peng 2022:** report the ranked probability score beside Brier (it respects tercile order) — beside, never instead.
- **Neely et al. 2010:** a Clark–West style test with HAC errors for the overlapping 5-day windows; skill split by VIX regime.
- **Lillo et al.; Avellaneda–Lee:** do the HMM states just track cross-sectional variety or eigenvalue concentration?

## 9. Explanations for closed areas — (a) only, no retries

- **Basis family is a spot effect** — Fama–French 1987; Gorton–Rouwenhorst 2004; Gorton–Hayashi–Rouwenhorst 2007.
  - Basis = expected spot change + premium.
  - Where the basis is financing minus dividends (no convenience yield), a basis sort can predict *spot* without futures earning it.
  - This is the repo's measured convergence cost (−137 bp/month, t −16.7).
  - `BASIS_FAMILY_POST_MORTEM_2026-09-24.md` has no storage or cost-of-carry framing yet.
  - **Proposed RFA rule for the operator:** declare the effect band on the *traded instrument's* return. If it is anchored on spot, show the translation futures ≈ spot − carry.
- **IVOL sealed sign flip** — Haugen–Heins (short-window risk slopes are biased by the window's market surprise); Baker–Wurgler (the sign of the volatility spread flips with sentiment); Ang et al.; Malkiel–Xu (the prior is sign-contested); Drechsler (anomalies vanish where shorting is cheap, as with SSF); Bali et al. (lottery demand). The IVOL post-mortem could cite these.
- **GEX Stage B** — Breeden–Litzenberger. A fly's premium *is* the risk-neutral mass at the pin. Stage A's compression can be real and still priced in, which is consistent with gross +0.22 / net −0.75.
- **Nifty–BankNifty pair** — Balvers–Wu–Gilliland (single-series cointegration tests have 0.1–0.2 power [summary]; reword "not cointegrated" as "not detected"; the closure rests on the out-of-sample failures); Do–Faff–Hamza (ratio spreads assume β = 1); Balvers–Wu (leaving out momentum biases reversion speed down).
- **Reversal (PSB-1, CB-N50)** — Da–Liu–Schaumburg (reversal lives in the within-industry residual, consistent with C2 > C1); Lo–MacKinlay via Lo 2007 (half of contrarian profit is cross-autocorrelation); Llorente et al. (large caps reverse after high volume).
- **TS Basis Daily selection** — Ready 2002 (rules chosen in-sample carry ~0 out-of-sample information [summary]).
- **Trend sleeve** — Kim–Tse–Wald (much of TSMOM's alpha is the volatility scaling). `TREND_PHASE0_PRE_REGISTRATION.md` uses volatility scaling but doesn't cite it.

## 10. Suggested order

1. **§3.2 spot-only study.** No options data, no rule change. It answers the bracket-scaling question and the regime-value question together.
2. **§3.3 term-structure slope** — the only item that is forward-only (it needs the next expiry stored). No hard deadline, but every session it isn't captured is lost.
3. **§3.1 attribution and §3.4 fixed-structure shadow.** Both can be rebuilt from `wall_chain_snapshots` for the nearest expiry. Pin their rules in writing before looking.
4. **§4 `ca_in_hold` split and kinked beta** — the straddle surface's already-stated next step.
5. **§6 b1/b2 expectation** for the combo book, written before forward months accrue.
6. **§5 gate hardening** (overlap fields, IC-SD floor, trial ledger, Holm), bundled into one METHODOLOGY_VERSION bump.

## 11. Do not

1. **Backtest anything over Nifty index options 2016-02-11 → 2022-12-31** (the NiftyShield prohibition). Every NiftyShield item above uses the forward chain or spot bars only.
2. **Use any shadow fact above to gate, size or select NiftyShield trades** inside the current window. That changes the execution identity and restarts the window; it is a promotion-pipeline decision pinned before the data is seen.
3. **Re-mine the spent 2023+ stock-option window for variants.** §4 is accounting for an existing filter, not a new selection read.
4. **Reopen closed constructs** (C2, F1, Carry-as-futures, TS Basis, IVOL, Trend, pair, CB-N50) on the strength of §9. Those entries are explanations only.
5. **Import US effect sizes or cost constants as truth.** Every [summary] number is a secondary-summary figure from US or other markets; use them as sensitivity bands.
6. **Commit the library to git.** Its provenance is unclear.
