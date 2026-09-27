# Basis-Family Post-Mortem and Candidate Inventory

**Date:** 2026-09-24 · **Branch:** `research/funnels-filter`
**Standing:** audit only. Repo documents, code and git history were read. **No data was read, no
backtest run, nothing optimised.** Numbers are quoted from the cited files.
**Tags:** **[E]** established, **[I]** inconclusive, **[H]** hypothesis.
**Note on sources:** `origin/main` is ahead of this branch by PRs #13–#16. Two cited files exist
only there: `OPTIONS_SELLER_EDGE_STUDY_2026-09-11.md` and `DAYTYPE_HORIZON_CEILING.md`. They are
marked *(main)*.

---

## 0. Executive conclusion

1. **The basis family is one phenomenon measured in the wrong currency.**
   - The futures basis at a formation date predicts **spot** returns over the next month because
     spot drifts toward an already-rich (or cheap) futures price.
   - A futures holder pays that convergence. Carry's futures IC is **−0.011 / −0.007**. TS Basis's
     is **+0.010 / −0.006**.
   - Every basis-family gate was scored on spot returns. **No basis-derived construct has shown a
     return a futures book can earn.** [E]
2. **No genuinely independent 2–3 component funnel is supported by existing evidence.**
   - After removing the basis family and everything that failed its own gates, **two** candidates
     remain with instrument-relevant out-of-sample evidence: **late-cycle stock-straddle selling** (since downgraded to INSUFFICIENT EVIDENCE: an unmeasured outcome filter; see `STOCK_STRADDLE_SELLING_EVIDENCE_AUDIT_2026-09-24.md`)
     and the **GEX volatility state**.
   - Both are short-volatility / variance-premium in character. Their independence is **not
     established** and plausibly fails [H].
   - No third component has evidence.
3. **The honest next step is at most a cheap kill screen, not a funnel build** (§8).
   - It asks whether the GEX state carries any information about straddle P&L, using windows
     already spent.
   - It is expected to kill: GEX forecasts one day ahead, while the straddle holds about 10
     sessions.
   - A non-kill still could not confirm a funnel.

---

## 1. The basis-family failure mechanism

### 1.1 Common mechanism (Q1)

| Construct | What it ranks | Registered sign | Target used in gates |
|---|---|---|---|
| Carry v2 | cross-sectional residual basis (F−S)/S, dividend-"adjusted", beta/sector-neutral, monthly | long high basis | spot `fwd_ret_1m` |
| TS Basis | own-history z of raw basis, monthly | long high basis | spot `fwd_ret_1m` |
| TS Basis Daily | own-history z of raw basis, daily, plus selected overlays | long high basis | spot |
| CB-N50 `basis` feature | daily cross-sectional residual basis on Nifty 50 | long high basis | spot open(t+1)→open(t+2) |
| Basis-momentum | proposed, never built | — | — |

Every construct is long names whose futures trade rich to spot.
- By Koijen–Moskowitz–Pedersen–Vrugt Eq. (5), C = (S−F)/F, that is **short carry**.
- Their predictive content is the spot price moving toward the futures price.
- The futures price already sits at the destination, so the holder earns the drift minus the
  premium paid.
- Sources: `carry/CARRY_FUTURES_TRANSLATION_REVIEW.md` §1, §3;
  `ts_basis/TS_BASIS_FUTURES_TRANSLATION_REVIEW.md` §1.

### 1.2 Genuine information vs mechanical convergence (Q2)

| | Carry TRAIN / HOLDOUT | TS Basis TRAIN / HOLDOUT |
|---|---|---|
| Spot IC | +0.042 / +0.042 | +0.059 / +0.043 |
| **IC vs convergence alone** | **−0.558 / −0.583** | **−0.539 / −0.574** |
| **Futures IC** | **−0.011 / −0.007** | **+0.010 / −0.006** |
| Spot Q5−Q1, bp/month | +115 / +70 | +158 / +130 |
| Convergence, bp/month (t) | −137 (−16.7) / −101 (−10.6) | −123 (−16.2) / −101 (−9.6) |
| Share of spot spread consumed | >100% | 78% |
| Net futures, ann. (t) | −6.2% (−1.8) / −7.8% (−1.3) | +0.5% (+0.2) / +0.03% (+0.1) |
| Spot IC earned on day 1 (skip-day diagnostic) | not measured | ~30–36% |
| Dividend mechanics | −2 to −8 bp/month | ≤ ~1 pp/yr |

**Reading:**
- **Genuine information [E]:** the basis does forecast spot. The spot drift is real, stable across
  windows, and positive on Carry's SEALED read (+20.52% spot).
- **Mechanical [E]:** the signal ranks its own convergence almost perfectly (IC ≈ −0.55), and the
  convergence is about equal to the ex-ante basis gap between the legs.
- **Incremental to the futures price: none measurable [E].** A futures IC indistinguishable from
  zero means the futures price was already about as good a forecast as the signal.
- **Possible timing artefact [I]:** part of the spot IC may come from futures-close vs spot-close
  asynchrony. A third of TS Basis's spot IC is earned on the first day. Not measured for Carry.

### 1.3 Procedural errors that made the family look stronger than its tradable evidence (Q3)

| # | Error | Effect | Evidence |
|---|---|---|---|
| P1 | **Scored on the wrong instrument.** Every gate, the net-spread gate, the drawdown, capacity and production-metrics reports, and the +0.0 bp parity check used spot `fwd_ret_1m` for a futures book. **The error runs across the whole signal-engine track, not just the basis family.** IVOL, Trend, Skew and LAG were scored on the same spot series (IVOL's `fwd_ret_1m` matches Carry's store exactly), and SFB F1 was a cash-synthesised screen. Those are rejected anyway, but their spot numbers also carry unmeasured convergence exposure, in proportion to their correlation with basis [H] | Futures P&L was never measured until 2026-09-24 | `build_carry.py:341-355`; `run_sealed.py`; `carry_rebalancer.py:668`; `ts_basis/run_sealed.py:113`; `MULTI_FACTOR_COMBINATION_ASSESSMENT.md` §4 defect 1 |
| P2 | **Parity certified code, not economics.** "+0.0 bp" proved production reproduces research, including research's spot target | A validation that looked like a tradability check wasn't one | `CARRY_PARITY_REPORT.md`; `CARRY_PRODUCTION_METRICS_REPORT.md` |
| P3 | **Sign decided on spot and defended by a misread paper.** v1 (the KMPV direction) was "falsified" on spot returns; v2 was justified as "the canonical carry direction", which is the inverse of Eq. (5) | The family's economic story was never carry | `CARRY_V2_PRE_REGISTRATION.md` §1; `CARRY_FUTURES_TRANSLATION_REVIEW.md` §1 |
| P4 | **Roll cost absent** from every fee model (≈ 15 bp/month for a monthly T−3 book) | Net spreads overstated for any futures expression | both translation reports |
| P5 | **Dividend adjustment wrong-signed** in the frozen pre-reg (subtracts yield; should add back) | Tail-cell distortion, pushed into the short leg | `build_carry.py:251-252`; `CARRY_FUTURES_TRANSLATION_REVIEW.md` §1 |
| P6 | **TS Basis HOLDOUT computed before its pre-registration was written** (`22bb3dd` 23:20 precedes `fa692c8` 23:30) | HOLDOUT was a discovery surface, not a test | `TS_BASIS_EVIDENCE_STATUS_2026-09-24.md` D1 |
| P7 | **Wrong estimator in the authorising gate** (Pearson vs registered Spearman) | Sealed window opened on a gate that failed | `TS_BASIS_SEALED_REPORT.md` banner |
| P8 | **One sealed window read three times by the same family** (Carry, then TS Basis, then IVOL on the same universe). TS Basis was entered with Carry's PASS known | "Out-of-sample" reads were not independent | `BASIS_MOMENTUM_DECISION_REVIEW.md` §3; TS pre-reg §7 |
| P9 | **HOLDOUT/sealed boundary leak**: HOLDOUT IC loops include the 2022-12-30 formation, whose forward return is January 2023 | One sealed month inside HOLDOUT gate statistics. **Present in both.** TS Basis: 24 formations. Carry: the formations table holds 23 formations 2021-02-26 → **2022-12-30** (formation dates only; no returns read), matching `CARRY_HOLDOUT_IC_REPORT.md`'s "23 formations with IC". Carry's gate p = 0.016 is **not recomputed**; this does not change Carry's rejection | `TS_BASIS_FUTURES_TRANSLATION_REVIEW.md` §3; `carry/CARRY_HOLDOUT_IC_REPORT.md` l.9 |
| P10 | **Survivorship membership filter** `fwd_ret_1m IS NOT NULL`, which also makes live scoring impossible | Small bias; no forward path | `build_ts_signals.py:66-69`; `carry_rebalancer.py:624` |
| P11 | **Absolute composite gate** (composite ≥ 0.80, not composite > best leg) | Carry+IVOL diluted, passed, then IVOL sign-flipped on SEALED | `sleeves/MULTI_FACTOR_COMBINATION_ASSESSMENT.md` §1 |
| P12 | **Summary docs outran evidence**: "production-ready", "strongest PAPER candidate", blend Sharpe 2.09 (unverified provenance) | Decisions were taken off the summary, not the measurement | CLAUDE.md; `FUNNEL_CARRY_CONDITIONING_AUDIT_2026-09-24.md` §2 |

---

## 2. Candidate inventory (Q4, Q5)

**Independence** below means independent of the basis family's information source (F−S basis)
and its mechanism (spot/futures convergence). "Tradable instrument?" asks whether the evidence
was measured on the instrument the construct would trade.

### 2.1 Candidates not rejected

| Candidate | Signal source | Target instrument | Horizon | TRAIN | HOLDOUT | SEALED | Tradable instrument? | Governance |
|---|---|---|---|---|---|---|---|---|
| **Late-cycle stock-straddle selling** (seller-edge study) | option premium vs subsequent decay: variance-risk premium over the expiry cycle; strike from the same-expiry future (selection only, not a basis signal) | single-stock ATM options, near month | ~10 sessions to T−1 close | Discovery 2016–22: net @2% spread +11.5% of premium, t 4.98 | *No separate HOLDOUT.* Its confirmation is the 2023-01→2026-08 window, which is the repo's **sealed-era** data. Predictions were written first: +8.2% (t 2.90); conservative exit +6.5% (t 2.25) | **Spent** by that confirmation. Post-Nov-2024 reform: best t 1.49, not significant. The proposed Sep-29-2026 paper cycle was **not run**: no stock-option quotes were captured at the 09-15 entry (`STOCK_STRADDLE_SELLING_EVIDENCE_AUDIT_2026-09-24.md` §5) | **Yes** (option prices, swept spread, fees). Stale-price exits tested | Exploratory memo: **not pre-registered, no RFA** |
| **GEX volatility state** (Stage A) | EOD Nifty option-chain net gamma, normalised | forecast of next-day RV/IV. A state variable, not a P&L | 1 day | t −3.20 (2016–19) | t −2.65 (2020–22) | **2023+ unread; the runner refuses** | The *forecast* target is correct. Its trade (GEX-gated iron fly, B1) failed: Sharpe −0.75, +0.22 at zero cost | Stage A PASS; Stage B STOP; parked |
| **NiftyShield** (with **DayType** facts) | intraday Nifty regime label at 13:00 (DayType model) plus VIX gates | Nifty index options, intraday premium selling | 13:00→15:15 | external backtest filed, not graded | none for NiftyShield itself. *(Input evidence, a different construct: DayType label ceiling +0.23 pp on the traded window, OOS ≤2022 (main))* | 2026 sealed read **INCONCLUSIVE** (Sharpe 0.746 vs 0.80 bar) | Paper uses real option marks (E7-4) | MM12.5 pipeline: CONFORMANT (E007); E008 forward PAPER open. **Nifty index options 2016-02→2022-12 is OSC-preserved for it** |
| **CB-N50 combined score** | daily constituent reversal + **basis** | Nifty 50 constituents (spot target) | 1 day open→open | IC +0.059 (selection-inflated) | IC +0.029 (NW t 4.4) | unread for CB-N50, but its basis feature's data has been read three times | **No:** spot returns. The breadth→futures vehicle is structurally void | Closed; successor would need a new pre-reg |
| **C5 low-vol** | 252-day total volatility | NIFTY-200 cash, long-only top quintile | month | dev 2012–22: IC +0.068, net +4.3% | (inside dev) | cash 2023–26 unread for C5 | Cash delivery, yes; not an L/S or futures book | Closed in PSB-1: power 0.54 < 0.80 |
| **Options-Wall overnight short premium** | none (structure only) | index options, 15:10→09:35 | overnight | 21 index-nights: +5–8 bp, 72–76% wins | — | — | Yes (live bid/ask) | Descriptive; contradicted by seller-edge's index-overnight null |
| **TS Basis Daily** | basis level, daily, plus fitted overlays | SSF | days | selection surface | selection surface | 876 formations preserved unspent | **No:** spot | Research-only by operator (2026-08-01) |
| **DRA HMM** (legacy) | 3-state index HMM | originally Nifty cash | days | not profitable (−₹1,647 / 200 trades) | — | — | — | Legacy dossier; "repurpose as filter" never validated |
| **DW1 dealer wall** | options positioning | index options | weekly | — | — | — | — | DRAFT, not frozen; expected RFA ABANDON |

Sources, in row order:
- *(main)* `strategies/OPTIONS_SELLER_EDGE_STUDY_2026-09-11.md` §2, §4, §5, §9
- `GEX_REGIME_STAGE_A_TRAIN.md`, `GEX_REGIME_STAGE_A_HOLDOUT.md`, `GEX_FLY_B1_REVIEW.md`,
  `HEDGEWALL_BRIEF_2026-09-23.md`, `docs/superpowers/specs/2026-09-23-gex-regime-stage-a-design.md` l.31
- `index_research/NIFTY_SHIELD_SEALED_ACCEPTANCE_BAR.md` §VERDICT, `docs/STRATEGY_PROMOTION_LEDGER.md` E007,
  *(main)* `index_research/DAYTYPE_HORIZON_CEILING.md`
- `index_research/CB_N50_TRAIN_REPORT.md`, `CB_N50_HOLDOUT_REPORT.md`, `CB_N50_TRAIN_REVIEW.md`
- `psb/PSB1_C5_REPORT.md`
- `OPTIONS_WALL_COUNTERFACTUAL_BATTERY.md` §0
- `ts_basis/TS_BASIS_REAUTHORIZATION_ASSESSMENT.md` §B
- `strategies/DRA_TECHNICAL_DOSSIER.md`
- `strategies/DW1_DEALER_WALL_PRE_REGISTRATION.md` l.3, l.64

### 2.2 Rejected by their own gates, or not candidates

| Candidate | Why | Evidence |
|---|---|---|
| Carry (as futures alpha) | spot-only; gross futures negative, futures IC ≈ 0 | `carry/CARRY_FUTURES_TRANSLATION_REVIEW.md` |
| TS Basis | pre-written kill rule fired (HOLDOUT futures IC ≤ 0) | `ts_basis/TS_BASIS_FUTURES_TRANSLATION_REVIEW.md` |
| IVOL | SEALED sign-flip, net −13.78% | `sleeves/IVOL_SEALED_REPORT.md` |
| Trend · Skew · LAG | TRAIN fail (t 1.13 · −1.15 · −1.43); LAG ≈ −Trend (ρ(IC) −0.95) | `sleeves/*_TRAIN_REPORT.md`; `MULTI_FACTOR_COMBINATION_ASSESSMENT.md` F3 |
| Flow · RS-MOM · O1 | RFA ABANDON · ABANDON · withdrawn | CLAUDE.md RFA section; `index_research/RS_MOM_RFA.md` |
| A-INDEX-INTRADAY | HOLDOUT fail (−0.22 bp) | `index_research/A_HOLDOUT_CLOSURE.md` |
| ISD open-drive / overnight-gap | battery TRAIN fail (F4 −3,196 bp) | `strategies/ISD_BATTERY_TRAIN_REPORT.md` |
| Intraday analog path | HOLDOUT: β_analogue insignificant in all 60 cells | `index_research/INTRADAY_ANALOG_PATH_HOLDOUT_REPORT.md` |
| N200 regime HMM (A, B) | calibration gate fail, both variants | `index_research/N200_REGIME_CLOSURE.md` |
| PTMS Gann (GF-1, GF-4T/R8, GF-10) | Stage-1 screen retired all three | `ptms/PTMS_GANN_STAGE1_SCREEN_REPORT.md`, `…_CLOSURE_DRAFT_2026-09-24.md` |
| JEV-NMS-1 | development NULL | `jev/JEV_NMS_1_DEVELOPMENT_REPORT.md`, `…_FORENSIC_POSTMORTEM.md` |
| RELIANCE regime | predictability real; no tradable edge after delivery STT | `index_research/RELIANCE_REGIME_RESEARCH_REPORT.md` §5 |
| PSB C1–C4, PSB-2 C2/C3/C4, SFB F1, Nifty/BankNifty pair | closed per CLAUDE.md sections | CLAUDE.md; `psb/`, `sfb_f1/` |
| GEX-gated iron fly (Stage B) | STOP; effect size, not cost | `GEX_FLY_B1_REVIEW.md` |
| MRLC, MSI engine | analysis / scoping only, no signal evidence | `strategies/MRLC_CONSTRUCT_ASSESSMENT.md`; `MSI_ENGINE_PRODUCTIONIZATION_SCOPING.md` |

---

## 3. Funnel-role fit (Q6)

This classifies roles only. It ranks nothing and recommends nothing.

| Role | Candidates with any evidence | Caveat |
|---|---|---|
| **A. Market / regime filter** | **GEX volatility state** (OOS in both read windows; predicts RV/IV, not direction). DayType (weak: horizon ceiling +0.23 pp; label definition contaminated by a full-panel KMeans fit, `REGIME_TRANSITION_DIAGNOSTIC.md`) | GEX's only tested use as a gate (the fly) failed. No regime filter in the repo has been shown to *condition* another construct's P&L |
| **B. Cross-sectional stock selection** | **None instrument-correct and alive.** CB-N50's reversal+basis IC is spot-measured, and its basis half belongs to the failed family. C5 is cash long-only and underpowered | The seller-edge study is a *cross-sectional book of options* but not stock *selection*: it sells the whole liquid F&O set |
| **C. Confirmation / timing / risk** | GEX state (as a vol-risk flag); NiftyShield's VIX gates (inside a strategy, not standalone) | — |
| **Standalone premium source** (not a funnel role, but the only instrument-correct return) | late-cycle stock-straddle selling | exploratory, not pre-registered; post-reform insignificant |

---

## 4. Independence and overlap assessment (Q7)

| Looks independent | Actual overlap | Tag |
|---|---|---|
| TS Basis vs Carry ("own history vs peers") | same data, same sign; ρ(signal) +0.62, ρ(IC) +0.53; same convergence mechanism | [E] |
| CB-N50 vs Carry ("breadth / constituent IC") | dominant feature **is** basis (TRAIN basis IC +0.056 vs combined +0.059); breadth is market-neutral by construction | [E] |
| TS Basis Daily vs TS Basis | same construct, daily; same target; overlays fitted on TRAIN/HOLDOUT | [E] |
| Basis-momentum vs basis level | derived from the same basis series; a TS residual on Carry would approximate it | [H] |
| IVOL vs Carry ("ρ(signal) −0.04, decorrelated") | ρ(IC) +0.09 to +0.23; composite lift < 1. Signal decorrelation ≠ IC decorrelation | [E] |
| LAG vs Trend | ρ(IC) −0.95: one factor, sign-flipped | [E] |
| C5 vs IVOL | both volatility-level cross-sections; IVOL is the neutralised SSF cousin, and it sign-flipped | [H] |
| **GEX state vs stock-straddle selling** | both earn or forecast the *realised-below-implied* premium. GEX: high index GEX → next-day RV ≈ 20% below implied. Straddle P&L is realised-vs-implied by construction. A market-wide vol regime could drive both | **[H]. Untested, and the decisive question for any funnel** |
| NiftyShield / DayType vs GEX / Options-Wall | all sell Nifty index premium, gated on intraday or EOD market state | [H] |
| Options-Wall overnight vs seller-edge index-overnight | same trade family; the decade-long study found a null for Nifty overnight | [E] conflict |
| **Data-window overlap:** GEX Stage A vs NiftyShield | Stage A read Nifty index options 2016–2022, which is the window preserved unread for NiftyShield. Construct-specific prohibition, so not a breach, but any GEX-gates-NiftyShield design inherits it | [E] |

---

## 5. Classification (Q8)

No ranking and no winner.

| Class | Candidates | Basis for the class |
|---|---|---|
| **READY FOR CLEAN EXPERIMENT** | **Late-cycle stock-straddle selling** *(superseded 2026-09-24: INSUFFICIENT EVIDENCE — an outcome-conditioned hold-period exclusion is unmeasured, the post-reform row is t 1.37, and the Sep-29 cycle was not run; see `STOCK_STRADDLE_SELLING_EVIDENCE_AUDIT_2026-09-24.md`)*, forward only: measured on the traded instrument, predictions written before its confirmation read; needs a formal pre-reg and RFA, with 2023–26 disclosed as spent. Its freeze must post-date any paper cycle already run (operator to confirm the proposed Sep-29 cycle). **GEX volatility state**: 2023+ unread and guarded; Stage A spec written | Only these two hold instrument-relevant evidence plus a clean, unread path (forward time; GEX 2023+) |
| **REQUIRES TRANSLATION / REPAIR** | **CB-N50**: spot-scored; basis half must be separated or translated before any role (this applies to the stock-level IC as successor input; the breadth → Nifty futures expression itself stays closed, `INSTRUMENT_CORRECTNESS_AUDIT_2026-09-24.md` §2). **TS Basis Daily**: futures translation never done; research-only by operator. **DayType**: label-definition contamination and the three deferred audited defects | Evidence exists but in the wrong currency or with known defects |
| **INSUFFICIENT EVIDENCE** | NiftyShield (awaiting E008 forward paper; sealed INCONCLUSIVE); C5 (power 0.54, cash long-only); Options-Wall overnight (21 nights vs a decade-long null); DRA-as-filter (never validated); DW1 (draft); MRLC / MSI (no signal evidence) | Nothing measured supports a role yet |
| **REJECTED** | Carry and TS Basis as futures alpha; IVOL; Trend; Skew (superseded: REQUIRES REPAIR, see `INSTRUMENT_CORRECTNESS_AUDIT_2026-09-24.md` §C); LAG; Flow; RS-MOM; O1; A-INDEX-INTRADAY; ISD ×2; intraday analog path; N200 regime ×2; PTMS Gann ×3; JEV-NMS-1; RELIANCE regime; PSB C1–C4, C2 (PSB-2); SFB F1; Nifty/BankNifty pair; GEX-gated fly; basis-momentum (declined, no window) | Failed their own gates, or measured untradable (§2.2) |

---

## 6. What a funnel would need, and what exists

A 2–3 component funnel needs:
- at least two components that each carry instrument-correct evidence;
- demonstrated **IC/P&L independence** between them, not merely signal decorrelation (F4 in the
  multi-factor assessment);
- a **clean window** to confirm the *combination*.

What exists:
- **Components:** two (straddle selling, GEX state).
- **Independence:** untested and plausibly failing, since both are variance-premium.
- **Window:** GEX 2023+ is unread; stock-option 2023–26 is spent. Forward time is the only clean
  window for the pair.
- **Power:** by the funnel audit's arithmetic, month-level conditioning effects need **65–740
  months** for 80% power (`FUNNEL_CARRY_CONDITIONING_AUDIT_2026-09-24.md` §7). A GEX-gated straddle
  book, at about 12 cycles a year, sits in that regime.

**So a funnel is not currently supported, and building one would be manufacturing it.**

---

## 7. Supporting-evidence index

| Claim | File(s) |
|---|---|
| Carry spot vs futures, sign, dividend defect | `carry/CARRY_FUTURES_TRANSLATION_REVIEW.md`, `…_REPORT.md`, `…_SNAPSHOT.json`; `scripts/signal_engine/carry/futures_translation.py` (`5ac8160`) |
| TS Basis translation, kill rule, boundary leak | `ts_basis/TS_BASIS_FUTURES_TRANSLATION_REVIEW.md`, `…_REPORT.md`, `…_SNAPSHOT.json`; `scripts/signal_engine/ts_basis/futures_translation.py` (`a2bed7c`) |
| TS Basis procedural history (D1–D5) | `ts_basis/TS_BASIS_EVIDENCE_STATUS_2026-09-24.md`; commits `22bb3dd`, `fa692c8`, `5c1f5d2`, `d177a04`, `b9524cf` |
| Pairwise Carry/TS/IVOL/Trend/Skew/LAG | `sleeves/MULTI_FACTOR_COMBINATION_ASSESSMENT.md`, `SLEEVE_COMBINATION_MATRIX.md`, `IVOL_COMPOSITE_CHECK_REPORT.md` |
| CB-N50 structure and basis dominance | `index_research/CB_N50_TRAIN_REPORT.md`, `CB_N50_TRAIN_REVIEW.md`, `CB_N50_HOLDOUT_REPORT.md` |
| Funnel power arithmetic | `FUNNEL_CARRY_CONDITIONING_AUDIT_2026-09-24.md` §7 |
| Seller-edge | *(main)* `strategies/OPTIONS_SELLER_EDGE_STUDY_2026-09-11.md` |
| GEX | `GEX_REGIME_STAGE_A_TRAIN.md`, `GEX_REGIME_STAGE_A_HOLDOUT.md`, `GEX_FLY_B1_REVIEW.md`, `HEDGEWALL_BRIEF_2026-09-23.md` |
| NiftyShield / DayType | `index_research/NIFTY_SHIELD_SEALED_ACCEPTANCE_BAR.md`, `docs/STRATEGY_PROMOTION_LEDGER.md`, `index_research/REGIME_TRANSITION_DIAGNOSTIC.md`, *(main)* `index_research/DAYTYPE_HORIZON_CEILING.md` |
| Rejections | files listed in §2.2 |

---

## 8. Smallest clean experiment (Q9)

**The plain answer first:** the existing evidence does not justify building a funnel. The only
experiment warranted is a cheap kill screen. **It is expected to kill.**
- **Horizon mismatch.** GEX Stage A forecasts *next-day* RV/IV; the straddle holds about 10
  sessions. That is the same one-day-vs-multi-day mismatch used to reject CB-N50 as a monthly
  filter (`FUNNEL_CARRY_CONDITIONING_AUDIT_2026-09-24.md` §3). The same standard applies here.
- **E0 is not a path to a funnel.** Even a non-kill cannot confirm conditioning at ~80 cycles (§6).

**Question (role-A filter test, not mutual independence):** does the index GEX state at entry
carry any information about late-cycle stock-straddle P&L? Here straddle selling is a standalone
premium source and GEX a candidate filter. GEX explaining straddle P&L would be what a *working*
filter looks like, not a reason to stop. So there is no "one factor" stop rule.

**E0: kill screen. Non-confirmatory, on already-spent data only.**

> *Superseded caveat (2026-09-24):* E0 reads the same straddle rows, which drop every cycle with a ≥22 % single-day move during the hold (`ca_in_hold`, an outcome filter). Measure that exclusion before E0 (`STOCK_STRADDLE_SELLING_EVIDENCE_AUDIT_2026-09-24.md` §7.1, §9).
- **Data.** Monthly expiry cycles 2016-02 → 2022-12 (~80). Both inputs have already been read on
  this span: seller-edge discovery, GEX Stage A TRAIN+HOLDOUT. Hard fence at 2022-12-31: **no GEX
  2023+ read**, and no 2023+ stock-option data.
- **Inputs, frozen from existing specs with no new parameters:**
  - per cycle, the seller-edge construct's cross-name mean net return at 2% spread (as specified in
    the study, §2);
  - GEX N at the entry date (Stage A definition).
- **Measure, two quantities only:**
  1. ρ(N_entry, cycle return);
  2. the cycle-return difference between N terciles (no threshold search: terciles are fixed now).
- **Kill rule, written now:** if the |ρ| upper 95% bound < 0.15 **and** the tercile-difference
  upper 95% bound < 1% of premium per cycle, GEX carries no usable information about this book.
  GEX has no filter role for it. **Stop.**
  Anything else is **inconclusive**. It licenses at most a forward pre-registration and authorises
  nothing else.
- **Why this is the smallest clean step:**
  - It spends no unread data.
  - It uses no free parameters.
  - It can only kill.
  - It is the only overlap between the two survivors worth checking before any design exists.

**E1: only if E0 does not kill.** A forward-only pre-registration, after a new freeze date F:
- the straddle book as a standalone primary, with its own RFA and an independently defended
  Sharpe band (the study's post-reform 0.84 is the honest anchor, not 1.42);
- GEX N recorded at each entry as a **pre-registered descriptive covariate, not a gate**.

The funnel question stays descriptive until forward time accumulates enough cycles for its RFA to
PROCEED.

**Explicitly out of scope:**
- any basis-family component;
- CB-N50;
- C5;
- NiftyShield;
- any third component;
- any use of GEX 2023+ before E1's freeze.

A third funnel component would need its own evidence first. None exists today.
