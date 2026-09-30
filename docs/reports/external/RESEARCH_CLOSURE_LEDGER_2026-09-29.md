# Research Closure Ledger — What Was Actually Established (v1)

**Date:** 2026-09-29. **Governing question:** what do we actually know about each construct, based on
evidence genuinely obtained — not what status labels imply.
**Method:** every row traces to a primary report (SPEC audit §9 map); conflicts recorded, never assumed
away. "Data tested" requires a market-data read against a criterion, never the mere existence of a report.
**Governing rules enforced throughout:** empirical failure requires data tested against a predefined
criterion; RFA-ABANDON = "not demonstrable under declared feasibility assumptions," never mechanism
disproof; TRAIN ≠ HOLDOUT confirmation; signal ≠ edge; one construct's evidence does not close its family.
**No next strategy selected, no mechanism proposed, no RFA redesign, no construct reopened.**

Codes — Spec: FROZEN/DRAFT/UNKNOWN/LEGACY/CATALOGUED. Data/Expl/Prereg/TRAIN/VAL/HOLDOUT/SEALED/Econ/Repl/RFA:
Y/N/–. Evid: S/M/W/N = strong/moderate/weak/none, with +/−/0 direction. Closed?: highest defensible Cn
(§2). "Why" gives the binding reason.

## 1. Master ledger

| Construct / family | Mech | Tested hypothesis (short) | Spec | Data | Expl | Prereg | TRAIN | VAL | HOLD | SEAL | Econ | Repl | RFA | RFA-res | Empirical result | Status | Evid | Closed? | Why / Primary source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PSB-1 C1 weekly reversal | M1a | N200 5-day losers > winners, next week | FROZEN | Y | N | Y | Y(dev) | – | – | – | Y | N | N | – | IC+0.023 t3.76; net −16.8% (gate fail) | C5 cost-killed | M− | C5 | Net gate predefined+failed; mech open (gross sig). PSB1_C1_REPORT |
| PSB-1 C2 residual reversal | M1b | Idiosyncratic weekly leg reverts | FROZEN | Y | N | Y | Y(dev) | – | – | – | Y | N | N | – | IC+0.035 t6.63; net −8.6% | C5 cost-killed | M− | C5 | Same as C1. PSB1_C2_REPORT |
| PSB-1 C3 delivery-z weekly | M5a | Abnormal delivery% → return | FROZEN | Y | N | Y | Y(dev) | – | – | – | Y | N | N | – | IC+0.025 t2.93; net −2.45% | C5 cost-killed | M− | C5 | Same. PSB1_C3_REPORT |
| PSB-1 C4 (C1×C3) | M1a/M5a | Delivery-weighted reversal | FROZEN | Y | N | Y | Y(dev) | – | – | – | Y | N | N | – | IC≈0; net −16.1% | C5 | M− | C5 | Criterion failed. PSB1_C4_REPORT |
| PSB-1 C5 low-vol banded | M-lowvol | −σ(252d) monthly, 0.40 band | FROZEN | Y | N | Y | Y(dev) | – | – | – | Y | N | N | – | IC+0.068 t3.14 net+4.3%; power 0.54<0.80 → dropped | C4 power-drop | M+ | C4 | No empirical fail; demonstrability drop, retired. PSB1_C5_REPORT |
| PSB-2 C2 delivery fortn. | M5a | Delivery-z, banded, fortnightly | FROZEN | Y | N | Y | Y(dev)+TRAIN ext | – | –(unspent) | –(sealed kept) | Y | N | N | – | Dev eligible; Phase0.5 TRAIN power ≤0.66 → retired | C5 power-fail | M− | C5 | Predefined power criterion failed on TRAIN. C2_PHASE0_5 reports |
| PSB-2 C3 deliv-cond reversal | M1a/M5a | Delivery-conditioned reversal | FROZEN | Y | N | Y | Y(dev) | – | – | – | Y | N | N | – | Net<0, power 0.18 → not eligible | C4 | M− | C4 | Dropped, no power-fail test. PSB2_C3_REPORT |
| PSB-2 C4 12-1 momentum | M2a | 12-1 long-only staggered | FROZEN | Y | N | Y | Y(dev) | – | – | – | Y | N | N | – | IC+0.047 net+2.9% but power 0.41 → dropped | C4 | M+ | C4 | Same class as C5. PSB2_C4_REPORT |
| CB-N50 breadth | M1a/M7a | Daily XS reversal+basis → next-day return | FROZEN(−) | Y | N | Y | Y | Y | N(G4 missing) | –(unread) | N | N | Y | PROCEED | TRAIN IC+0.059 t11.4; HOLDOUT +0.029 t4.35; breadth→futures directional FAIL at TRAIN; basis contract UNKNOWN | C6 positive/incomplete | M+ | C6 | IC confirmed, P&L gate never evaluated. CB_N50 reports |
| ISD F1 opening drive | M2e | First-30/45m strength persists to close | FROZEN | Y | N | Y | Y | – | – | – | Y | N | Y | PROCEED | 0/4 cells; sign wrong (IC−0.017) | C5 sign-fail | M− | C5 | Pinned sign failed. ISD_BATTERY_TRAIN_REPORT |
| ISD F4 overnight gap | M1d | Gap fades intraday vs peers | FROZEN | Y | N | Y | Y | – | – | – | Y | N | Y | PROCEED | IC−0.029 t−6.09; gross +3–6bp, net negative | C5 cost-killed | M− | C5 | Net gate failed. ISD reports |
| Trend sleeve TSMOM-rank | M2b | Vol-scaled trend rank → 1m return | FROZEN | Y | N | Y | Y | –(unread) | – | – | Y | N | Y | ABANDON | IC+0.022 t1.13 p0.13 FAIL; 2nd half −0.010 | C5 | M− | C5 | Gate-2 fail; HOLDOUT never read. TREND_TRAIN_REPORT |
| Skew sleeve risk-reversal | M-skew | 25Δ RR rank → return (2-sided) | DRAFT | Y | N | N | Y | – | – | – | Y | N | Y | ABANDON | IC−0.018 t−1.15 p0.26 FAIL | C5 | W− | C5 | Prereg never frozen — weakens form, not fact of fail. SKEW_TRAIN_REPORT |
| LAG sector diffusion | M-lag | Leader-minus-own gap predicts | DRAFT | Y | N | N | Y | –(untouched) | – | – | Y | N | Y | ABANDON | IC−0.031 wrong sign; 58% Trend-subsumed | C5 | W− | C5 | Gate-2 fail; DRAFT caveat as above. LAG_TRAIN_REPORT |
| IVOL idio-vol | M-ivol | High ivol underperforms (−sign) | DRAFT(−) | Y | N | Y* | Y | Y | Y(SEALED) | Y | Y | N | Y | ABANDON | TRAIN −0.055 PASS; HOLDOUT −0.030 PASS; SEALED +0.018 net−13.8% FAIL | C5 sealed-fail | S− | C5 | Strongest failure in repo: genuine OOS sign flip. IVOL_*_REPORT |
| Carry v1 (short basis) | M7a | Short high residual basis | FROZEN | Y | N | Y | Y | – | – | – | Y | N | Y | PROCEED | IC+0.041 wrong sign → FAIL | C5 sign-fail | M− | C5 | v1 spec closed. CARRY reports |
| Carry v2 (long basis) | M7a | Long high residual basis | FROZEN | Y | N | Y | Y | Y | Y(SEALED) | Y | Y | N | Y | PROCEED | HOLDOUT +0.046 t3.31 net+6.96%; SEALED +0.061 net+20.52% BUT div-sign inverted, PIT uncertifiable, EW-gate ≠ prereg z-book, futures t≈−0.8, spot-not-futures | C6 positive/incomplete | M+ | C6 | Pass stands only with listed defects; confirmed ≠ as-specified. CARRY_*_REPORT + reviews |
| TS Basis monthly | M7a-var | Own-history basis-z rank | FROZEN | Y | N | Y* | Y | Y | Y(SEALED) | Y | N | N | N | – | HOLDOUT p0.031>0.025 FAIL (Pearson gate); recomputed Spearman; SEALED IC+0.077 p3e-7 net+22.6% BUT opened via broken gate → de-authorized | C6 de-authorized | M+ | C6 | Strong numbers reached through broken gate = selection, not confirmation. POST_MORTEM + REAUTHORIZATION |
| TS Basis Daily | M7a-var | Daily basis-z + overlays | CATALOGUED | Y | Y | N | Y(sel) | Y(sel) | –(preserved) | Y | N | N | N | – | TRAIN/HOLDOUT both selection surfaces; never frozen/gated | C3 exploratory | W+ | C3 | No confirmatory test exists. REAUTHORIZATION §B |
| F1 12-1 + ATR bracket | M2a/M13 | Bracketed momentum survives futures fees | FROZEN(−) | Y | Y | Y* | Y | Y | – | Y* | N | Y | N/A | – | Printed GO superseded NO-GO: MaxDD clause unevaluated, CI incl. zero, bracket inert (DaysH 18.8) | C4 screen-NO-GO | M0 | C4 | Feasibility screen failed its own decision rule; mechanism untested. VERDICT_REVIEW |
| DRA HMM-gated EMA | M9a/M2c | Regime-gated intraday trend | LEGACY | Y | Y | N | Y(walk-fwd) | – | – | – | N | N | N | – | 200 trades −₹1,647; no significance test; primary report absent | C3 legacy | W0 | C3 | Second-hand only; cannot confirm. DRA_TECHNICAL_DOSSIER |
| Gann GF-1/4T/10 | M10a | Swing-time counts → 5-session break | FROZEN | Y | N | Y | Y(screen) | – | – | – | N | N | N | – | p_sur 0.95/0.98/0.21 → retired; explicitly NOT "rule false" | C5 non-confirm | W− | C5 | Screen criterion failed; mechanism scoped out by design. SCREEN_REPORT |
| Gann GO-1/GT-4/catalogue | M10b/M11a | Levels/seasonals catalogue | CATALOGUED | N | N | N | – | – | – | – | N | N | N | – | No measurement | C0 | N | C0 | Catalogue only. CONSTRUCT_CATALOGUE |
| Straddle seller edge | M8a | Late-cycle ATM short premium | UNKNOWN(−) | Y | Y | N | Y(disc)+confirm | – | – | – | Y | Y* | N | – | Discovery t6.05; confirmation t3.78 (unchanged code, unread window); 6-offset selection; filter ambiguity | C3 replicated-explor | M+ | C3 | Replicated but never preregistered; selection + filter caveats. SELLER_EDGE_STUDY |
| MSRP D1 gated straddle | M8b | Forecast-gated premium timing | UNKNOWN | Y | Y | N | Y(in-sample) | – | – | – | Y | N | N | – | ρ(signal,ret)−0.027; D1 net −₹120k in-sample → STOP, do-not-preregister | C4 in-sample STOP | W− | C4 | In-sample negative; development halt, not preregistered fail. FEE_TRIAGE |
| Nifty/BankNifty pair | M6a | Ratio mean reversion | UNKNOWN | Y | Y | N | Y(full-sample) | – | – | – | Y* | N | Y | ABANDON | No cointegration; p0.354; 27/27 intraday negative; params unstable | C3 exploratory | M− | C3 | No prereg → cannot be C5 despite convergent negative evidence. PAIR_RESEARCH |
| A index opening drive | M2d | First-30/45m sign persists to close | FROZEN(−) | Y | N | Y | Y | Y | –(untouched) | Y | N | Y | PROCEED | TRAIN w45 net gate pass; HOLDOUT net −0.22bp FAIL (gross +3.13bp, no gross test) | C5 net-fail | M− | C5 | Net construct closed; gross mechanism open (untested). A_HOLDOUT reports |
| Analog Path | M-path | 09:15→12:30 path beats endpoint-only | FROZEN | Y | N | Y | Y | Y | –(locked) | N | N | Y | N/A | – | TRAIN weak; HOLDOUT 60/60 cells insignificant → RETIRED, "substantially falsified in this formulation" | C5 | M− | C5 | Preregistered HOLDOUT null. ANALOG reports |
| N200 HMM vol-regime | M-volreg | HMM P(S2) forecasts high-vol state | FROZEN | Y | N | Y | Y(folds) | – | – | N | N | N | N | – | Both variants FAIL vs persistence; 0–3/10 folds positive | C5 | M− | C5 | Terminal: family closed per doc. N200_REGIME_CLOSURE |
| JEV-NMS-1 nowcast | M-nowcast | 15-min nowcast adds ΔLL over B3 | FROZEN | Y | Y | Y* | Y(dev-only) | – | – | N | N | N | N | – | D-eval ΔLL≤0 (development NULL); P/L5/F2 never run | C3 development | W0 | C3 | Protocol frozen but confirmatory test never run. JEV docs |
| DayType diagnostics | M9a-evid | 13:00 archetype separates direction | UNKNOWN | Y | Y | N | Y(descr) | – | – | N | N | N | N | – | 13pm Bull−Bear +0.25pp CI excl. zero; 10/11am null; counts/span contradictions carried | C3 informative | M+ | C3 | Separation without cost-inclusive gated P&L. HORIZON/CEILING/TRANSITION docs |
| W2 afternoon variance | M9c-evid | Label predicts VR; VR=1 test | FROZEN | Y | N | Y | Y(2023–26) | – | – | N | N | N | N | – | Pooled VR 1.046 CI incl. 1; by-label CIs overlap → null | C5 null-result | M0 | C5 | Preregistered null finding (informative). AFTERNOON_VARIANCE docs |
| RELIANCE single-name | M2c/M3a | TSMOM/SMA/Donchian/reversal/gates on RELIANCE | UNKNOWN | Y | Y | N? | Y(3 panels) | – | –(RECENT sealed-era) | Y | N | N | N | – | sma_200 net +6/+8/+1.7% but CI incl. zero, −7.7%/yr vs buy-hold; R1 kills all IC direction claims; thin Donchian | C4 single-name | W0 | C4 | No prereg doc; one name long/flat; sealed-era RECENT. RELIANCE_REPORT + R1 |
| MRLC sweep-reclaim | M3b(+M1c/M5b) | Stretch+sweep+reclaim+exits | UNKNOWN | Y | Y | N | Y(dev)+ext+archive | – | – | Y | N | N | N | – | Dev +0.72R t2.12; ext +0.24R t8.62; archive +0.19R t1.90 — all with selection/survivorship/ideal-fill caveats, no prereg | C3 exploratory | M+ | C3 | Positive-but-selected; consistency checks, not holdouts. MRLC_TEST/ARCHIVE |
| A-INDEX-INTRADAY | M2d-var | Opening-drive continuation, 1 trade/day | FROZEN(RFA) | N | N | N(RFA) | – | – | – | –(cost lane cited) | N | Y | PROCEED | No TRAIN/data read | C2 | N | C2 | EMPIRICALLY UNKNOWN. Declaration + RFA report |
| NiftyShield premium machine | M8c/M9a | DayType+VIX-selected structures | UNKNOWN | Y | Y | N | Y(paper/live) | – | – | Y* | N | N | N | – | No completed experiment; sealed bar INCONCLUSIVE (Sharpe 0.746<0.80); regime audit n=8 descriptive | C3 development | W0 | C3 | Paper in progress ≠ result. ADOPTION/REGIME docs |
| Options-Wall/counterfactual | M10b/M11b | OI/gamma walls + slot effects | DRAFT(−) | Y | Y | N | Y(9 sess) | – | – | Y | N | N | N | – | Descriptive only (fly worst −₹65k; pilot net −₹5.3k); DW-1 DRAFT | C3 descriptive | W0 | C3 | Nothing gated. FEASIBILITY/EVIDENCE/COUNTERFACTUAL |
| GEX Stage A state var | M-gex | Dealer GEX → next-day RV/IV | FROZEN | Y | N | Y | Y | Y | – | N | N | Y | N/A | – | TRAIN t−3.20, HOLDOUT t−2.65 PASS (regression, no P&L) | C4/C6 state-only | M+ | C4 | State variable confirmed; no return mechanism tested. GEX_REGIME reports |
| GEX-gated fly B1 | M-gexP&L | GEX-gated iron fly P&L | FROZEN | Y | N | Y | Y(dev window) | – | – | Y | N | Y | N/A | – | Net Sharpe −0.75 → STOP | C5 | M− | C5 | Preregistered STOP on window. GEX_FLY_B1_DEV |
| F-RANGE failed breakout | M3b-var | Liquidity provision at stop clusters | CATALOGUED | N | N | N | – | – | – | –(priced) | N | Y | N/A | – | Zero measurements; priced PLAUSIBLE | C0 | N | C0 | Catalogue + pricing only. DISCOVERY_LAB/GATE0 |
| Gate-0 rest (F-VOL/TOD/REL) | M4a/M11b | Vol/time/relativeillot families | CATALOGUED | N | N | N | – | – | – | –(priced) | N | Y | N/A | – | Priced infeasible/implausible, zero reads | C0 | N | C0 | Pricing ≠ evidence. GATE0 |
| M1c extreme reversion | M1c | Own-history tail reverts unconditionally | FROZEN | N | N | N(RFA) | – | – | –(forward) | – | N | Y | ABANDON | No read; HOLDOUT needs S≥2.49 | C2 | N | C2 | EMPIRICALLY UNKNOWN. Protocol v1.3 + RFA v1–v4 |
| Flow OI crowding | M-flow | Positioning-pressure reversal | FROZEN(RFA) | N | N | N(RFA) | – | – | – | – | N | Y | ABANDON | No TRAIN read; max power 0.61 | C2 | N | C2 | EMPIRICALLY UNKNOWN. FLOW_RFA |
| RS-MOM index momentum | M2pair | Nifty/BankNifty rel-strength weekly | FROZEN(RFA) | N | N | N(RFA) | – | – | – | – | N | Y | ABANDON | Max power 0.34 | C2 | N | C2 | EMPIRICALLY UNKNOWN. RS_MOM_RFA |
| OSC surface richness | M-osc | IV-residual rank → hedged return | UNKNOWN | Y | Y | N | Y(probe) | – | –(preserved) | N | N | Y | ABANDON | Clean IC+0.017, N_eff 1.9, sd 0.25; window unspent | C3 probe | W+ | C3 | Probe sized, not tested; EMPIRICALLY UNKNOWN as mechanism. OSC_ABANDON |
| N50-LS book | M-book | N50 reversal+basis L/S book P&L | FROZEN | N | N | Y(prereg) | – | – | –(unspent) | N | Y | ABANDON | Book never read; power 0.75<0.80 | C2 | N | C2 | Preregistered but EMPIRICALLY UNKNOWN (book). N50-LS_RFA |
| O1 VRP condor | M8a-var | Weekly short-variance harvest | WITHDRAWN | N | N | N | – | – | – | – | Y | DEFECTIVE | No valid RFA exists | C1 | N | C1 | Withdrawn RFA = no conclusion; unresearched. O1_REVIEW |
| STOCK-STRADDLE-M10 | M8a | Forward short-ATM monthly book | FROZEN | N | N | Y(fwd) | –(fwd only) | – | – | – | Y | PROCEED | 0 cycles run | C1 | N | C1 | Specified, forward-only, no result. PREREG + RFA |
| Straddle P5 VRP-tilt | M8b | VRP-conditioned seller timing | UNKNOWN | Y | Y | N | Y(disc+conf) | – | – | Y | N | N | N | – | IC+0.040→+0.014 t1.24 FAIL | C4 | W− | C4 | In-construct conditional fail. SELLER_EDGE §5 |
| Trade Intelligence | M-? (E) | UNKNOWN (book unnamed) | UNKNOWN | Y | Y | N | Y(descr) | – | – | N | N | N | N | 10–11k trades described, no mechanism conclusion | C3 unattributed | E | C3 | Cannot attribute; mechanism relevance undetermined. TI reports |
| PTMS Family G | M-prem-decay | Distance-travelled vs implied displacement | DRAFT | N | N | N | –(fenced) | –(fenced) | –(unspent) | – | Y | PRED-ABANDON | Windows fenced, unspent | C1 | N | C1 | Candidate only. FAMILY_G_P3 |
| MSI program | — | Architecture grounding, no mechanism | CATALOGUED | N | N | N | – | – | – | – | N | N | N | No empirical content | C0 | N | C0 | Not a mechanism test. GROUNDING_BRIEF |
| Options survey/direction | M-survey | Venue-arb + VRP slate; 1-session read | CATALOGUED | Y | Y | N | Y(1 sess) | – | – | N | N | N | N | Anecdote-grade nulls (p≥0.21) | C3/C0 | W0 | C3 | Survey + single-session description. SURVEY/DIRECTION_READ |

*Y* = prereg document existed but never frozen (Skew/LAG DRAFT; TS Basis HOLDOUT computed pre-prereg per post-mortem).

## 2. Closure taxonomy as applied

C0–C9 used exactly as specified; no new category was needed. Two boundary rulings, applied uniformly:
(i) a gate computed on data against a predefined criterion (even TRAIN-only, even a power gate) can reach
C5; pure mathematical projection with no construct test stays C2/C4; (ii) exploratory work with statistics
but no preregistration caps at C3 regardless of how negative the numbers look (pair, MRLC, straddle
confirmation) — C5 requires the criterion to predate the read. DRAFT-prereg TRAIN runs (Skew, LAG) were
scored C5 on the fact of the gated fail with the form defect noted, not upgraded.

## 3. Propositions A/B/C for every failed, abandoned, or closed construct

A = empirically tested and failed. B = experiment could not establish under declared assumptions.
C = evidence the mechanism lacks a meaningful edge. Exactly one primary proposition per construct:

| Construct | Primary | Reason |
|---|---|---|
| PSB-1 C1/C2/C3/C4 | A (cost-inclusive construct) | Predefined net gates failed on data. Mechanism-level C explicitly NOT supported (gross ICs significant) |
| PSB-1 C5, PSB-2 C4 | B | Dropped on power projection, never empirically failed; retirement is demonstrability, not disproof |
| PSB-2 C2 | A (power-fail on TRAIN) | Predefined power criterion failed on data; sealed/HOLDOUT preserved, mechanism not disproven |
| PSB-2 C3 | B | Dropped without a power-fail test; net<0 on dev is in-sample description |
| CB-N50 | Neither fully: C6 | IC confirmed (against C); breadth→futures failed at TRAIN (against economic A for that vehicle); G4 missing |
| ISD F1 | A | Pinned sign failed on TRAIN |
| ISD F4 | A (cost-inclusive) | Net gate failed; gross edge survives as fact (C false for gross) |
| Trend | A | Gate-2 significance failed on TRAIN |
| Skew, LAG | A (form-weakened) | Gated TRAIN fails; DRAFT prereg weakens formality, not the numbers |
| IVOL | A (strongest in repo) | Genuine OOS sign flip on sealed: TRAIN/HOLDOUT PASS → SEALED FAIL |
| Carry v1 | A | Wrong-sign TRAIN fail of the as-specified sign |
| Carry v2 | Neither: C6 positive | Criteria passed; implementation diverged from spec — pass and spec cannot both be claimed cleanly |
| TS Basis | Neither: C6 de-authorized | Strong SEALED numbers reached through a broken gate = selection artifact, signal not falsified |
| A intraday | A (net construct) | Net HOLDOUT gate failed; gross mechanism explicitly open (no gross test exists) |
| Analog Path | A (formulation-scoped) | 60/60 HOLDOUT cells insignificant; "in this formulation" qualifier load-bearing |
| N200 HMM | A | Both variants failed vs persistence baseline |
| Gann screens | A (screen-scoped) | Surrogate criteria failed; freeze doc forbids mechanism-wide reading |
| MSRP D1 | B (in-sample STOP) | Negative in-sample triage halted development; no preregistered test existed to fail |
| Pair | B (exploratory) | Convergent negative evidence, but no predefined criterion → cannot be A; mechanism reading: fixed-param ratio trading unsupported, not "pairs never work" |
| RELIANCE rules | B | No prereg doc; single name; R1 voids direction claims; nets are descriptive |
| MRLC | B | No prereg; selection/survivorship/ideal-fill caveats stated in own docs; t-stats are selected |
| GEX fly | A | Preregistered STOP fired on window |
| GEX Stage A | Neither: state variable | Regression PASS with no P&L leg — nothing to fail or pass economically |
| F1 screen | B | Feasibility screen NO-GO on its own incomplete rule (MaxDD clause unevaluated); momentum mechanism untested |
| Flow, RS-MOM, M1c, N50-LS, O1 | None (C2/C1) | No empirical test exists; B itself is unlicensed — RFA demonstrates only "not demonstrable under bands," which is narrower than B. Verdict: EMPIRICALLY UNKNOWN |
| OSC | None (C3 probe) | Probe sized the problem; no formal test; EMPIRICALLY UNKNOWN as mechanism |
| Straddle study/P5 | B (exploratory) | Unpreregistered; P5 conditional fail is descriptive |

## 4. Special audit of RFA-ABANDON (Flow, RS-MOM, OSC, M1c + N50-LS, O1)

| Question | Flow | RS-MOM | OSC | M1c | N50-LS | O1 |
|---|---|---|---|---|---|---|
| Market data read before abandonment? | N (TRAIN explicitly untaken) | N | Y (probe, burned window) | N | N (book) | N |
| Formal construct test run? | N | N | N (probe ≠ test) | N | N | N |
| TRAIN / HOLDOUT run? | N/N | N/N | N/N | N/N | N/N | N/N |
| Economic feasibility tested empirically? | N | N | N | N (rule-arithmetic floors only) | N | N |
| What RFA demonstrated | max power 0.61 at n=42: undemonstrable at bands | 0.34 at n=186: undemonstrable | 0.79 at n=1701, needs δ≥0.017 vs clean 0.0167 | HOLDOUT needs S≥2.49; best cell 0.26 | 0.75 at n=887; needs 1,012 at optimistic | Nothing (withdrawn; printed 0.99 was coupled-corner artifact) |
| What RFA did NOT demonstrate | Any property of OI flows | Any property of index momentum | Any property of the surface | Any property of tail reversion | Any property of the book | Anything (void) |
| Final status | **EMPIRICALLY UNKNOWN** | **EMPIRICALLY UNKNOWN** | **EMPIRICALLY UNKNOWN** | **EMPIRICALLY UNKNOWN** | **EMPIRICALLY UNKNOWN** | **EMPIRICALLY UNKNOWN** |

Note on OSC: the probe's clean IC (+0.0167), sd (0.25), N_eff (1.9) are genuine scale measurements on
burned data — informative about difficulty, not evidence about the mechanism. Upgrading them to a test
would spend the preserved 1,701-formation window by redefinition; the ledger refuses that upgrade.

## 5. Audit of TESTED-PASS (CB-N50, Carry v2, F1)

- **CB-N50: PASS on IC, not on economics.** Preregistered TRAIN+HOLDOUT IC gates passed (combined
  +0.029, t 4.35). G4 (futures P&L) never evaluated after the TRAIN directional check failed; basis
  contract/day-count UNKNOWN; HOLDOUT figure is reversal+basis combined. A HOLDOUT IC pass is not an
  economic confirmation. Highest: C6.
- **Carry v2: PASS with implementation divergence.** HOLDOUT (n=23) and SEALED (n=42) gates passed on an
  equal-weight quintile spot book, while the frozen spec describes a z-weighted futures book; dividend
  sign inverted in code; PIT uncertifiable; futures-spread gross t≈−0.8. The result confirms *a*
  basis-sorted spot book, not the specified construct. Highest: C6. Production use would need the
  divergence closed, not cited away.
- **F1: a PASS that was superseded.** Printed GO rested on 2 of 3 spec conditions (MaxDD clause never
  evaluated: TRAIN +10.3%/yr vs −45.7% drawdown), CIs including zero at all slippages, and a bracket
  selected into near-inactivity (DaysH 18.8 vs 5-bar cap). Terminal verdict NO-GO. The ledger records
  both verdicts with the override reason; citing the printed GO without the review is false closure.

## 6. Audit of TESTED-FAIL (what exactly failed)

| Construct | Sign | Significance | Power | Costs | HOLDOUT | Implementation | Spec | Economic viability |
|---|---|---|---|---|---|---|---|---|
| PSB-1 C1/C2/C3 | correct | pass | C1 fail/C2-3 pass | **FAIL (cause)** | n/a (dev-only) | clean | clean | infeasible weekly |
| PSB-2 C2 | correct | pass→weaken | **FAIL on ext TRAIN** | pass (reduced) | preserved | clean | clean | moot after power |
| Trend | — | **FAIL p0.13** | — | fail too | unread | clean | clean | infeasible |
| Skew/LAG | wrong/weak | **FAIL** | — | fail | untouched | clean | DRAFT | infeasible |
| IVOL | **flipped OOS** | pass→pass→fail | context | pass→pass→fail | SEALED fail | clean | clean | failed with flip |
| ISD F1 | **wrong** | (neg sig) | — | — | — | clean | clean | moot |
| A | correct | net fail (gross untested) | — | **FAIL net** | FAIL net | 15:14 vs 15:29 doc defect | defect noted | net-infeasible |
| Analog | — | **FAIL all 60** | — | n/a (no strategy) | FAIL | clean | clean | n/a |
| N200 | — | **FAIL vs persistence** | — | n/a | folds | clean | clean | n/a |
| Gann | — | **FAIL surrogates** | — | n/a | n/a (screen) | clean | clean | n/a |
| GEX fly | — | — | — | **STOP net −0.75** | dev-window | clean | clean | infeasible window |
| MSRP D1 | neg | — | — | pass (not binding) | in-sample | strike UNKNOWN | incomplete | untested properly |

Rule applied: each failure is recorded at its level (sign/significance/power/cost/window/implementation).
No row above closes any mechanism beyond its exact construct (see §7).

## 7. Mechanism-level versus construct-level closure (narrow default applied)

| Mechanism (MAP ID) | Exact construct evidence | Closes construct? | Closes mechanism? |
|---|---|---|---|
| M1a weekly XS reversal | C1/C2 dev IC + costs kill | Yes (fee-infeasible weekly N200) | No (gross ICs significant; CB-N50 confirms daily form) |
| M1b residual reversal | C2 dev | Yes (same) | No (same reason) |
| M1a daily XS reversal | CB-N50 reversal+basis combined HOLDOUT | Partial (breadth→futures vehicle failed) | No (reversal component confirmed; basis confounded) |
| M1d gap reversal | ISD F4 TRAIN net gate | Yes (intraday fade net of costs) | No (single window/cost model) |
| M2a 12-1 momentum | PSB-2 C4 (power-drop); F1 (NO-GO screen) | C4 dropped; screen infeasible as bracketed | No (neither is a mechanism falsification) |
| M2b TSMOM-rank | Trend TRAIN fail | Yes (SSF monthly rank, this spec) | No (one window/spec) |
| M2c single-name trend | RELIANCE long/flat one name, no prereg | No (descriptive) | No |
| M2d opening continuation | A net HOLDOUT fail | Yes (net-of-cost index day-trade) | No (gross +3.13bp untested) |
| M2e opening drive XS | ISD F1 sign fail | Yes (continuation direction) | Narrow (sign only) |
| M3a breakout | RELIANCE Donchian (thin, no prereg) | No | No |
| M3b sweep-reclaim | MRLC exploratory (selected) | No (no prereg) | No |
| M5a delivery | C3/C2 dev + Phase-0.5 power fail | Yes (delivery-z cross-section at these cadences) | Narrow (power, not absence) |
| M7a basis predictor | Carry v2 SEALED (defective impl); CB-N50 basis (UNKNOWN contract) | Qualified (spot book / combined IC) | No (impl divergence + confounding) |
| M8a short premium | Straddle discovery+confirmation (exploratory) | No (unpreregistered) | No (informative-positive only) |
| M8b gated timing | MSRP D1 in-sample STOP; P5 t1.24 fail | D1 halted (in-sample); P5 conditional fail | Narrow (tested conditionals only) |
| M6a pair spread | Exploratory (no prereg) | No | Fixed-param form unsupported; mechanism open |
| M10a swing time | Gann screens (non-confirmatory) | Screen-scoped only | Explicitly not closed (freeze doc) |
| M9a regime gating | RELIANCE gates (descriptive); DayType separation (no P&L) | No | No |
| M9c dependence regime | W2 null (label predicts dependence) | Narrow (label-as-predictor only) | Estimator-as-regime form open |
| M-volreg (N200) | Both variants fail vs persistence | Yes (HMM on these features) | Narrow (feature set only) |
| M-nowcast (JEV) | Development NULL only | No | No |
| M-ivol XS | SEALED sign flip | Yes (60-day real-vol SSF form) | Narrow (this construction) |
| M-skew XS | TRAIN fail | Yes (25Δ RR rank) | Narrow |
| M-lag XS | TRAIN fail + subsumption | Yes (sector gap form) | Narrow |
| M-gex state/fly | Stage A PASS (no P&L); fly STOP | Fly window closed; state var open | Narrow |
| M-path (Analog) | 60-cell HOLDOUT null | Yes (this formulation) | Narrow |
| M1c / M-flow / M2pair / M-book / M-osc | RFA-ABANDON only (+OSC probe) | **No — empirically unknown** | No |
| M-lowvol XS | C5 power-drop | Dropped, not failed | No |

## 8. Coverage-map reconciliation (MAP v1.1 + C-dim)

| Mechanism | MAP status | Actual evidence level | Empirically closed? | RFA-only? | Still empirically open? |
|---|---|---|---|---|---|
| M1a | A | C4–C5 dev + C6 HOLDOUT(IC) | Construct-level (cost) | No | Mechanism yes-open; G4 vehicle open |
| M1b | A | C5 dev | Construct-level (cost) | No | Mechanism open |
| M1c | C | C2 protocol+RFA | No | Yes (+frozen protocol) | Fully open |
| M1d | A | C5 TRAIN net | Construct-level (cost) | No | Other windows/vehicles open |
| M2a | A | C4 + screen NO-GO | Dropped/infeasible, not falsified | Partly (F1 also screened) | Mechanism open |
| M2b | A | C5 TRAIN | Construct-level | No | Other windows open |
| M2c | B | C4 single-name descriptive | No | No | Open beyond one name |
| M2d | A | C5 net-fail | Net construct closed | No | Gross form open |
| M2e | A | C5 sign-fail | Direction closed | No | Narrow |
| M3a | B | C4 thin descriptive | No | Partly (Gate 0 priced) | Open |
| M3b | B | C3 exploratory selected | No | No | Open incl. sub-variants |
| M4a | C | C4 forecast-only (N200/GEX) | No directional test exists | Partly (Gate 0 priced) | Fully open |
| M5a | A | C5 dev + power-fail | Construct-level | No | Narrow (power, not absence) |
| M5b | C | C3 conjunct only | No | No | Open |
| M5c/M5d/M6b | D | None (data-blocked M5d/M6b) | No | No | Open/blocked |
| M6a | B | C3 exploratory | No | Partly (RS-MOM RFA) | Open |
| M7a | B | C6 (defective impl) | Qualified only | No | As-specified open |
| M7b | C | Component measurement only | No | No | Open |
| M8a | B | C3 replicated-exploratory | No | Partly (O1 void; M10 fwd) | Confirmatory open |
| M8b | B | C4 in-sample STOP | Halted, not failed | No | Properly-tested form open |
| M8c | C | C3 paper/descriptive | No | No | Open |
| M9a | B | C4/C3, no gated P&L | No | No | Open |
| M9b | C | None | No | No | Open |
| M9c | C | C5 null (label form) | Narrow (label form) | No | Estimator form open |
| M10a | A | C5 non-confirmatory | Screen-scoped | No | Mechanism explicitly open |
| M10b | C | C3 descriptive (walls) | No | No | Open |
| M11a | D | None | No | No | Open |
| M11b | D | C3 descriptive | No | Partly (Gate 0 priced) | Open |
| M13 | B | Tooling inside F1/MRLC/DRA | N/A (exit tooling) | No | As-entry open |
| XS low-vol/ivol/skew/lag | (omitted §2.3) | C4–C5 | Construct-level | Partly (RFA ran) | Variant forms open |
| GEX state/fly | (omitted §2.3) | C4 / C5-STOP | Fly window closed | No | P&L extensions open |
| Analog path | (omitted §2.3) | C5 formulation | Formulation closed | No | Other formulations open |
| N200 vol-regime | (omitted §2.3) | C5 | Feature-set closed | No | Other estimators open |
| JEV nowcast | (omitted §2.3) | C3 development | No | No | Open |
| DayType direction | (omitted §2.3) | C3 separation | No | No | Gated-P&L form open |

Exposed by this reconciliation (covered-but-actually-incomplete): M2a (A via dropped/screened constructs);
M7a (B via defective implementation); M2d (A on net, gross open); M10a (A on a screen scoped not to
confirm); M1a/M1b (A on cost-killed weeklies while gross/daily forms survive); CB-N50's G4-shaped hole
inside an A.

## 9. FALSE CLOSURE CANDIDATES

1. **RFA-ABANDON filed with empirical failures** (Flow, RS-MOM, N50-LS, M1c in coverage tables; O1's
   printed PROCEED before withdrawal). Zero-data verdicts read as findings about markets. Why false: no
   market-data test exists behind any of them.
2. **Weekly fee wall cited as reversal death.** PSB-1 C1–C4 gross ICs are significant; what died is a
   weekly delivery-fee implementation. CB-N50's daily +0.029 exists in the same record.
3. **RELIANCE single-name B-ratings.** M2c/M3a "covered with defects" rests on one long/flat large-cap
   name with no prereg doc and void ICs. A B built on this is one stock thick.
4. **MRLC t-stats cited as B evidence.** +0.24R t8.62 comes from 24-cell selection with survivorship and
   ideal fills, self-described as consistency checks. Selection output presented as mechanism evidence.
5. **CB-N50 HOLDOUT IC as near-confirmation.** G4 (the only P&L gate) was never evaluated; basis contract
   UNKNOWN; HOLDOUT number is two-mechanism combined. An IC pass is not an economic confirmation.
6. **Carry SEALED as production-ready.** Dividend sign inverted, PIT uncertifiable, EW book ≠ prereg
   z-book, futures leg t≈−0.8. A pass on a diverged implementation.
7. **TS Basis SEALED +22.6% cited without the banner.** Numbers reached through the broken Pearson gate;
   de-authorized for selection reasons. Strength without validity.
8. **Straddle confirmation as validation.** Unchanged-code second window, but 6-offset selection plus
   filter ambiguity; exploratory by its own status line. Replication ≠ confirmation.
9. **A gross HOLDOUT (+3.13bp) cited as promise.** No gross significance test was ever reported; the only
   gate was net and it failed.
10. **Gann time-screen cited for price patterns.** Tested time counts do not cover candles, Fib, or
   harmonics (record says so explicitly).
11. **DayType separation cited as regime evidence.** +0.25pp with no cost-inclusive gated P&L and
   whole-sample-fit labels; count/span contradictions carried.
12. **NiftyShield paper cited as progress.** n=8 descriptive audit, fee restatement ongoing, sealed bar
   INCONCLUSIVE. A live book is not a result.
13. **Positive TRAIN cited as confirmation.** CB-N50 TRAIN +0.059 (halved OOS), straddle discovery
   (selected offset), MRLC dev (selected cells). Selection surfaces are not confirmations.
14. **Feasibility arithmetic cited as evidence.** Gate-0 pricing and RFA power tables describe what could
   be shown, not what was shown. M1c's HOLDOUT-needs-S≥2.49 constrains experiment design, not markets.
15. **DRA legacy cited as tested coverage.** Primary report absent; 200-trade P&L second-hand with no
   significance test. Cannot confirm or deny.

## 10. Final research inventory

**A. Genuinely empirically closed** (exact construct; stop treating as open): PSB-1 C1, C2, C3, C4
(cost-killed weeklies); PSB-2 C2 (power-failed, retired), C3, C4 (dropped); ISD F1 (sign), F4 (net);
Trend (TRAIN insignificance); Skew, LAG (TRAIN fails); IVOL (sealed flip); Carry v1 (wrong sign); A
(net HOLDOUT fail); Analog Path (60-cell HOLDOUT null); N200 HMM (both variants); Gann GF screens
(non-confirmatory fail); MSRP D1 (in-sample STOP); GEX fly B1 (STOP on window). *20 constructs.*

**B. Empirically informative but not closed** (real evidence, chain unresolved): CB-N50 (IC confirmed,
G4 missing); Carry v2 (SEALED pass, implementation diverged); TS Basis (strong SEALED via broken gate);
PSB-1 C5 (IC+spread pass, power fail); Straddle study (replicated exploratory); Pair (convergent
exploratory negative); RELIANCE (single-name descriptive, R1-voided directions); MRLC (selected
multi-read positive); GEX Stage A (state PASS, no P&L); DayType (separation, no gated P&L); W2
(preregistered null on label form); NiftyShield/Options-Wall (live/descriptive in progress);
JEV (development NULL); F1 (screen NO-GO, mechanism untested); TS Daily (selection surfaces, sealed
preserved); C2-minibattery context (already inside PSB-2 C2).

**C. RFA/feasibility closed but empirically unknown** (no legitimate empirical conclusion): Flow,
RS-MOM, M1c, N50-LS (book), OSC (probe sizes difficulty only). O1 sits apart: withdrawn defective RFA,
no conclusion at all.

**D. Still genuinely unresearched** (no empirical evidence; no RFA conclusion to mistake): all
single-instrument indicator rules (MA/MACD/oscillator-threshold/BB/Donchian/Supertrend/SAR/Ichimoku/ADX),
grid/martingale/DCA, combo confluence, candlestick/Fib/harmonic, OBV/MFI/VWAP/CVD/FVE, same-asset
venue/product arb, signed order flow (data-blocked), calendar/seasonal, time-of-day standalone,
regression bands, σ-scaled breakout, VWAP anchoring, F-RANGE, Gate-0 rest, Gann catalogue, MSI,
options survey; specified-but-unrun C1s (STOCK-STRADDLE-M10, PTMS Family G).

## 11. Final question: how much coverage is actually empirical?

Counting exact constructs in this ledger (≈45 rows): **20 genuinely closed (A)**, of which 17 are
failures/stops and 3 are cost-kills of gross-positive signals; **≈16 informative-but-open (B)**;
**5 RFA-only unknowns (C)** (+O1 void); **remainder D** — and D dominates by mechanism count because the
Vault's ~15 single-instrument mechanism families were never tested at all. Mechanism-level (MAP ≈24
mechanisms + 9 omitted-tested families): **zero mechanisms are closed in full** — every A-status
mechanism survives in an untested form (gross/daily/vehicle/variant), exactly as §7's narrow default
requires. Put bluntly: **roughly half the construct rows carry real empirical evidence, nearly all of
it negative or cost-constrained; the affirmative column (CB-N50 IC, Carry v2 with defects, TS Basis
de-authorized, straddle exploratory) is thin, defect-marked, or unconfirmed. Everything else —
including every RFA-ABANDON and the entire single-instrument indicator space — is governance/feasibility
closure or untouched ground, not empirical knowledge.** No precision beyond this is manufactured: row
placement follows the cited primary report in each case.

## 12. Governing principle (enforced, not aspirational)

Every row above was scored against these rules, and any future row must be: **no empirical-failure
claim without data tested against a predefined criterion** (hence pair/MRLC/straddle stay C3, never C5);
**RFA-ABANDON means "not demonstrable under declared feasibility assumptions"** (Flow/RS-MOM/OSC/M1c/N50-LS
are EMPIRICALLY UNKNOWN, stated in §4); **TRAIN is not HOLDOUT confirmation** (CB-N50 G4, Carry SEALED-on-diverged-impl, TS Basis gate defect all stay C6, never C7); **signal is not edge** (IC passes without
P&L gates — CB-N50, ISD F4 gross — are recorded as statistical facts with economic status open);
**one construct never closes its family** (§7 narrow default throughout; the only family-level closures
asserted are N200's feature set and the Analog formulation, each explicitly scoped).


## Addendum 2026-09-30 — M1c × M5c VWAP extreme reversion (first empirical test)

Added after the v1 ledger date. It changes no v1 row: the M1c row (§1, C2) refers to the daily own-history-tail construct
(protocol v1.3 + RFA v1–v4), which remains EMPIRICALLY UNKNOWN. This is a different construct (intraday, session-VWAP anchor).

| Construct | Mech | Tested hypothesis | Spec | Data | Prereg | TRAIN | VAL | HOLD | Econ | Result | Closed? | Primary proposition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VWAP-XREV-1 extreme displacement from session VWAP, contrarian | M1c × M5c | Own-vol-scaled abs(z) ≥ rolling pooled q=0.99 from cumulative typical-price VWAP reverts at 5–60 min (PIT F&O names the 1m store carries) | FROZEN (hash-gated) | Y | Y | Y (descriptive) | Y | Y (one-shot) | Y (descriptive; gate not reached) | 3 VAL-confirmed cells (up/h5, down/h10, down/h30) all failed HOLDOUT; up/h5 reversed; HOLDOUT market-excess ≈ 0; event-weighted net negative in all ten HOLDOUT cells at every κ | **C5, construct-scoped** | A (predefined HOLDOUT confirmation criterion tested and failed) |

**Labelling resolution (operator decision 2026-09-30, delegated).** Three labels exist and are kept apart in the record: the
pre-registered frozen-tree output **C6**; the substantive reading *non-replication*; and the ledger category **C5, construct-scoped**.
**The ledger carries C5, construct-scoped.** Reasons: (i) §2(i) — a C5 needs a predefined criterion tested on data, and the
HOLDOUT confirmation rule predates the read; (ii) precedent — IVOL and Analog Path (a confirmatory pass followed by a failed predefined
HOLDOUT/SEALED criterion) are C5, whereas every C6 in this ledger passed a confirmatory criterion and is incomplete elsewhere;
(iii) the protocol's C6 branch keys only on the sign of non-significant HOLDOUT point estimates (raw +1.7/+4.1 bp; market-relative
+0.4/+0.8 bp), and "incomplete" would imply an unspent window that does not exist. **The C5 assignment is a post-hoc re-mapping
recommended by Opus Review C, not the pre-registered result; the frozen output C6 is preserved verbatim in
`docs/reports/research/results/classification.json`.** Any citation of the category must carry "construct-scoped".

Scope (§7 narrow default): closes this exact construct only. **M1c and M5c remain open as mechanisms**; nothing here extends to other
anchors, universes, horizons, thresholds or event definitions, and C9 is unreachable. Source: `docs/reports/research/
VWAP_EXTREME_REVERSION_RESEARCH_REPORT.md` (PR #32, `18ac346`).

Substrate findings recorded with this entry (independent of the result): the certified ISD `pit_universe` F&O flag under-counts eight
names (DLF, BRITANNIA, KOTAKBANK, BAJAJFINSV, ABB, MOTHERSON, CHOLAFIN, PIIND); the 1m store's name list appears chosen on a later
universe (store covers 75–78% of PIT F&O underlyings through Feb 2025, 100% by 2026-09-29).
