# Instrument-Correctness Audit of Rejected Research Candidates

**Date:** 2026-09-24 · **Branch:** `research/funnels-filter` · **Type:** audit only.

**Scope honoured.** No backtest was run, no data was read (sealed or otherwise), and no parameter,
signal, target or threshold was changed. Evidence consists of repo code, reports and git history.
The basis family (Carry, TS Basis, TS Basis Daily) is out of scope: `BASIS_FAMILY_POST_MORTEM_2026-09-24.md`
already closed it and it is excluded from the counts.

**Evidence tags.** **[E]** means read directly from code or from a script-generated report.
**[I]** means inference from existing numbers, not measured.

**The question for each candidate.** Did the gate measure the economic object the candidate
proposed to trade? A "wrong instrument" finding means only that the existing rejection may not
answer the intended question. It says nothing about whether the strategy works.

---

## 0. Conclusion

- **No rejected candidate has its rejection invalidated by an instrument mismatch alone.** Section
  A below is empty.
- **The `fwd_ret_1m` error reaches exactly four non-basis constructs: IVOL, Trend, Skew and LAG.**
  - All four were pre-registered as single-stock-futures (SSF) books and all were gated on spot
    `fwd_ret_1m` [E].
  - No other rejected construct consumes that target (§1.2).
- **For IVOL, Trend and LAG the missing component (basis convergence) is plausibly immaterial**,
  because their signals are uncorrelated with basis (|ρ| ≤ 0.04) [I]. Their rejections stand.
- **Skew is the one sleeve where the mismatch is material, and that traces to a construction
  defect.**
  - Its implied vols are inverted with Black-76 using the **spot** close as the forward.
  - This leaks the futures basis into the signal mechanically: ρ(skew, carry) = −0.63.
  - Skew therefore needs **repair before any translation** (section C).
- **PSB is instrument-correct.** An earlier concern that a quintile short leg can't be held in cash
  does not apply. The PSB net-spread gate is long-only top quintile minus a long baseline
  (`psb1/screening_harness.py:774-780`); the Q1−Q5 figure is reported gross only [E].
- **No translation audit is warranted** (section E).

---

## 1. The `fwd_ret_1m` trace

### 1.1 Definition

All five signal-engine builders compute it identically, as the forward one-month **spot close-to-close,
CA-adjusted, price-only** return [E]:

| Builder | Line | Construction |
|---|---|---|
| `carry/build_carry.py` | 340–353 | `(a2.close − a1.close)/a1.close` on `eq_subset` ← `equity_bhavcopy_adjusted` (series EQ) |
| `ivol/build_ivol.py` | 198–213 | same, joins `eq.equity_bhavcopy_adjusted` directly |
| `trend/build_trend.py` | 239–251 | same |
| `lag/build_lag.py` | 231–243 | same |
| `skew/build_skew.py` | 346–358 | same |

- **What it contains:** the stock's close-to-close price change from one formation date to the next.
- **What it leaves out:** futures basis convergence, the T−3 roll, and dividends (the adjusted view
  does not add them back).
- **Costs the gates charged:** futures fees (`core/execution/futures/futures_fees.py`) applied to
  the spot return. Skew instead used a flat 35.2 bp copied from Carry. **No gate charged roll cost.**

### 1.2 Every consumer in `scripts/`, `core/` and `governance/`

The list comes from a repo-wide grep [E].

| Consumer | Construct | Instrument note |
|---|---|---|
| `ivol/{run_train,run_holdout,run_sealed}.py` | IVOL gates 2, 3, SEALED | SSF book on spot target. The SEALED P&L books `fwd_ret_1m` (`run_sealed.py:272-277`); `futures_bhavcopy` is attached only for the ADV cap (`:90`) |
| `ivol/composite_check.py` | Gate-4 composite power (Carry+Trend+IVOL) | Composite IC on spot target |
| `combination/sleeve_pair_matrix.py` | Pairwise sleeve matrix | ICs on spot target; the source of the ρ figures used in §1.3 |
| `trend/run_train.py`, `lag/run_train.py`, `skew/run_train.py` | TRAIN gates | SSF book on spot target |
| `carry/*`, `ts_basis/*`, `ts_basis_daily/*`, `carry_rebalancer.py:668`, `carry_paper_replay.py`, `carry_forward_parity.py`, `carry_production_report.py`, `ts_basis*_paper_replay.py`, `ts_basis*_concentrated_backtest.py` | Basis family: gates, replay, parity, capacity, production reports | Covered by the post-mortem (P1); excluded here |
| `carry/futures_translation.py`, `ts_basis/futures_translation.py` | 2026-09-24 translations | Read `fwd_ret_1m` as the spot leg and add convergence explicitly; instrument-correct |

**No other rejected construct uses this target.**
- PSB, ISD, RELIANCE, MRLC and F1 use their own return builders (§2).
- CB-N50 uses open-to-open constituent returns.

### 1.3 How much the mismatch can matter

**Intended instrument.** Every sleeve pre-registration specifies an SSF book: futures fees,
futures-ADV caps, and continuous futures prices for signal construction. Each also pins the target
as "forward one-month name return (using spot adjusted returns)". IVOL `:90`, Trend `:89` and LAG
`:121` say so verbatim; Skew `:48-49` says the book trades futures [E]. The mismatch was
therefore **pre-registered**, not accidental.

**Size of the missing term.** futures return = spot return + convergence.
- For Carry the IC moved from +0.042 on spot to −0.011 on futures, because the Carry z has an IC
  of −0.56 against convergence (`CARRY_FUTURES_TRANSLATION_REPORT.md` §2) [E].
- A signal's exposure to that channel runs mainly through its correlation with the basis
  *level*. `SLEEVE_COMBINATION_MATRIX.md` measures ρ(signal, Carry z) as:

  | Sleeve | ρ(signal, Carry z) | Implied IC shift, spot → futures [I] |
  |---|--:|---|
  | IVOL | −0.036 | about 0.002, negligible |
  | Trend | −0.039 | about 0.002, negligible |
  | LAG | +0.019 | about 0.002, negligible |
  | **Skew** | **−0.633** | about +0.03, same order as its spot IC of −0.018 |

  The shift is the Carry shift of about 0.05 scaled by ρ.
- This bounds only the basis-*level* channel, not covariance with basis *changes*. It is **[I]**.

---

## 2. Per-candidate table

**Classification rules:**
- **CLOSED:** the rejection stands, whether or not the instrument matched.
- **ALREADY INSTRUMENT-CORRECT:** not rejected, and measured on the right object.
- **REQUIRES REPAIR:** a non-instrument defect comes first.
- **INSUFFICIENT EVIDENCE:** the evidence cannot support a verdict either way.
- **Question-correct:** the construct asked a statistical question, not a P&L one, so no tradable
  instrument is implied.

**"Translation" column.** It gives two things:
- whether a translation is needed before the rejection can stand;
- whether a valid translation already exists in the repo.

**Reusable machinery.** For every SSF sleeve, `carry/futures_translation.py` is reusable. It
provides a per-name futures return by the split-robust identity, plus convergence. It has only
ever been applied to the Carry and TS Basis books.

| Candidate | Intended instrument | Actual gate target | Correct? | Existing rejection valid? | Translation: needed? / present? | Clean window? | Classification |
|---|---|---|---|---|---|---|---|
| **IVOL** | SSF L/S, monthly (pre-reg §3, §8) | spot `fwd_ret_1m`, all gates incl. gate-4 and SEALED P&L [E] | WRONG INSTRUMENT (no convergence, roll, dividends) | **Stands [I].** SEALED sign flip (IC +0.018 vs registered −); ρ to basis −0.04 | No / none applied; machinery reusable | None. Own SEALED spent; forward time only | **CLOSED** |
| **Trend** | SSF L/S, vol-scaled TSMOM | spot `fwd_ret_1m` [E] | WRONG INSTRUMENT | **Stands [I].** TRAIN IC +0.022, t 1.13; ρ to basis −0.04 | No / none applied; machinery reusable | HOLDOUT (own pin 2022-01 → 2023-12) unread by this signal. The panel is read by other constructs, and 2023 lies in the SSF sealed span | **CLOSED** |
| **Skew** | SSF L/S, option-implied skew signal | spot `fwd_ret_1m`; flat 35.2 bp fee [E] | WRONG INSTRUMENT, **and signal contaminated**: Black-76 with `F=spot` (`build_skew.py:236,244,271,275`) [E] | **INCONCLUSIVE.** The signal carries basis mechanically (ρ −0.63), so the spot rejection tests a basis-loaded proxy of skew | Not before repair / none present | HOLDOUT 2021–22 unread by Skew; panel read by others | **REQUIRES REPAIR** |
| **LAG** | SSF L/S, sector lead-lag | spot `fwd_ret_1m` [E] | WRONG INSTRUMENT | **Stands [I].** Wrong sign (IC −0.031); 58% subsumed by Trend; ρ to basis +0.02 | No / none applied | HOLDOUT unread by signal; panel read by others | **CLOSED** |
| **Flow** | SSF L/S, OI dynamics | none; RFA only, no data read | n/a | **Stands.** Power arithmetic, max power 0.605 at n\*=42, independent of target | No / n/a | n/a | **CLOSED** |
| **RS-MOM** | Nifty/BankNifty futures pair | none; RFA only | n/a | **Stands.** `ncp = S·√T` wall; target-independent | No / n/a | n/a | **CLOSED** |
| **O1** (Nifty VRP, weekly defined-risk, SPAN margin) | Nifty index options, short premium | none; **withdrawn at RFA** (crossed corner), no data gate ran [E]. Adjacent evidence on the right instrument only: the seller-edge study's *monthly naked ATM* NIFTY straddle, n.s. (t −0.4 to +2.2; `OPTIONS_SELLER_EDGE_STUDY_2026-09-11.md` §2.2, on `main`) | n/a (never gated) | **Stands.** Withdrawal was a declaration defect; the adjacent option-premium evidence does not contradict it | No / n/a | No. NIFTY options 2016 → 2026-07 read by seller-edge | **CLOSED** |
| **A-INDEX-INTRADAY** | near-month Nifty futures, intraday, EOD-flat | `NSE_INDEX\|Nifty 50` 1m levels as a proxy (no futures 1m exists) (`A_CONSTRUCT_DEFINITION.md` §5) [E] | PARTIALLY WRONG (basis drift and basis noise, disclosed) | **Stands.** HOLDOUT net −0.22 bp; the ~0.4 bp/trade basis mean could move the point estimate to about zero, but HOLDOUT fails on p (0.133/0.150) regardless | No / **partial present**: basis mean and dispersion bound in `A_COST_SUBSTRATE_MEASUREMENTS.md` §B | SEALED untouched, but the construct is retired and the window is not for reuse | **CLOSED** |
| **ISD open-drive** | cash equity, intraday, EOD-flat | 1m equity bars, entry open → 15:29 close, intraday cash fees [E] | CORRECT | **Stands.** Cost arithmetic: floor 8.6 bp vs best gross +6.0 | No / n/a | HOLDOUT and SEALED never read | **CLOSED** |
| **ISD overnight-gap** | cash equity, intraday | same | CORRECT | **Stands.** IC passes (t −6.09) but the net gate fails; cost-dominated on the right instrument | No / n/a | same | **CLOSED** |
| **Intraday Analog Path** | none. Informational question on `NSE_INDEX\|Nifty 50` | index 1m interval returns vs a return-only baseline [E] | Question-correct | **Stands.** HOLDOUT: no information beyond the open→12:30 return | No / n/a | SEALED untouched | **CLOSED** |
| **N200 Regime (A, B)** | none. Estimation only (`N200_REGIME_CLOSURE.md` §1) | forward-volatility Brier target [E] | Question-correct | **Stands.** Both variants fail; family pre-committed closed | No / n/a | Return window untouched (target was volatility) | **CLOSED** |
| **RELIANCE regime** | delivery equity, long/flat | adjusted close-to-close, era delivery fees [E] | CORRECT (price-only: dividends omitted, minor) | **Stands.** IC real, net ≈ 0 under delivery STT | No / n/a | No. 2023+ read | **CLOSED** |
| **PSB-1 C1–C4** | delivery cash equity, long-only vs universe | net spread = long-only top quintile net − long baseline net (`screening_harness.py:774-780`); adjusted close-to-close; delivery fees [E] | CORRECT (price-only: dividends omitted) | **Stands.** Fee drag 12–17 pp/yr on the right instrument | No / n/a | Cash 2023–26 sealed unread by PSB | **CLOSED** |
| **PSB-2 C2, C3** | delivery cash equity | same harness family [E] | CORRECT (price-only) | **Stands.** C2 retired on extended-TRAIN power; C3 net < 0 | No / n/a | same | **CLOSED** |
| **PSB-2 C4** | long-only cash, staggered 6m | adjusted close-to-close, delivery fees [E] | CORRECT (price-only) | **Stands.** Power 0.411 | No / n/a | same | **CLOSED** |
| **SFB-1 / F1** | SSF, concentrated 12-1 momentum | cash price path as synthetic futures, basis "ignored and disclosed" (`F1_FEASIBILITY_SCREEN_SPEC.md` §3) [E] | WRONG INSTRUMENT (disclosed) | **Stands [I].** Two closing grounds are target-independent: bracket inactivity and the demonstrability arithmetic (~350 months at IC ~0.03). Two were computed on the synthetic series: CI includes zero, and MaxDD. Those carry the unmeasured basis term, argued small by analogy to Trend (the nearest momentum construct), whose signal has ρ to basis of −0.04 | No / none present. Real futures exist from 2016 only; TRAIN 2012–18 cannot be translated | SEALED 2023+ read only for cost parameters | **CLOSED** |
| **Nifty/BankNifty pair** | index futures pair (lots 25/15) | index spot levels; roll and lot rounding not modelled (`NIFTY_BANKNIFTY_PAIR_RESEARCH.md` :234) [E] | PARTIALLY WRONG (roll, small index-basis differential) | **Stands.** Not cointegrated, bootstrap p 0.354, the intraday ratio trends: properties of the ratio, not of the carry | No / none present | No. 2016–2026 read | **CLOSED** |
| **CB-N50 breadth → Nifty futures** | Nifty futures, 1 unit, open-to-open | IC on constituent spot open-to-open (correct for the stock-level question); directional check on Nifty next-day return [E] | PARTIALLY WRONG (index vs futures over one day; immaterial) | **Stands.** 48 long days vs 2 short, wrong ordering; breadth pinned near 0.5 | No for the closed expression / none present. See the reconciliation note below | SEALED preserved | **CLOSED** |
| **GEX-gated iron fly (B1)** | Nifty index options | option bhavcopy premiums [E] | CORRECT | **Stands.** B1 STOP, net −0.75 | No / n/a | 2023+ unread | **CLOSED** |
| **JEV-NMS-1** | none. Forecasting (OOF log-likelihood) | index 1m labels [E] | Question-correct | **Stands.** DEVELOPMENT NULL | No / n/a | per its freeze record | **CLOSED** |
| **PTMS Gann (GF-1, GF-4T/R8, GF-10)** | none. Structural screen | surrogate-null screen on N100 1m [E] | Question-correct | **Stands.** All three retired | No / n/a | per its closure | **CLOSED** |
| **DRA (legacy HMM)** | index timing (vehicle unstated) | "Nifty cash index" P&L (−₹1,647 / 200 trades) (`DRA_TECHNICAL_DOSSIER.md` §1). The source report `docs/HMM_REGIME_STRATEGY_REPORT.md` is **absent from the repo**; code lives in `D:\BOT\root` [E] | UNCLEAR. The cash index is not tradable; costs and vehicle unknown | **INCONCLUSIVE.** Cannot be audited from repo evidence | Cannot say / none present | n/a | **INSUFFICIENT EVIDENCE** |
| **MSI** | derivatives platform engine | no signal evidence (review and scoping documents; a paper runner exists but produced no gated result) | n/a | Not rejected | No / n/a | n/a | **INSUFFICIENT EVIDENCE** |
| **MRLC** | delivery cash equity, swing | 1m adjusted bars, delivery fees (`MRLC_TEST_2026-08-30.md`) [E] | CORRECT | Not rejected (40 trades, t 2.12, selection history disclosed) | No / n/a | none declared | **INSUFFICIENT EVIDENCE** |
| **PSB-1 C5 / low-vol** | cash equity, monthly banded, long-only vs baseline | adjusted close-to-close, delivery fees [E] | CORRECT (price-only; dividend omission biases *against* low-vol [I]) | Not rejected; power 0.54 | No / n/a | Cash 2023–26 unread | **INSUFFICIENT EVIDENCE** |

**CB-N50: reconciliation with the post-mortem.** The post-mortem lists CB-N50 as REQUIRES
TRANSLATION / REPAIR. The two labels refer to different objects:
- The **breadth → Nifty futures expression** was closed on its own evidence. That closure stands,
  and it is what this audit classifies.
- The **stock-level spot IC** is spot-measured input for any successor, and it carries a basis
  feature. That is the part the post-mortem flagged.

A pointer to this note has been added to the post-mortem.

**Not rejected, already instrument-correct (listed for completeness, no action):**
- stock-straddle selling (seller-edge, stock option premiums). The instrument is correct; its construction carries an outcome-conditioned exclusion (`STOCK_STRADDLE_SELLING_EVIDENCE_AUDIT_2026-09-24.md` §7.1);
- GEX vol state (Stage A: target ln(RV/IV), the correct target for a volatility-state claim);
- Options-Wall overnight (live chain bid/ask).

---

## A. Candidates genuinely worth reopening

**None.**
- No existing rejection is invalidated by an instrument mismatch alone.
- IVOL, Trend and LAG are wrong-instrument, but their rejections survive the plausible size of the
  missing term [I].
- Skew's mismatch is material, but its first problem is a construction defect (section C), not
  the target.

## B. Candidates that remain closed (do not reopen)

**Wrong or partly wrong instrument, but the rejection stands:** IVOL, Trend, LAG, A-INDEX-INTRADAY,
SFB-1/F1, Nifty/BankNifty pair, CB-N50 breadth → futures.

**Tested on the right instrument, or asking an instrument-free question, and failed:** ISD
open-drive, ISD overnight-gap, Analog Path, N200 A and B, RELIANCE, PSB-1 C1–C4, PSB-2 C2, C3 and
C4, GEX fly B1, JEV-NMS-1, PTMS GF-1, GF-4T/R8 and GF-10.

**Closed without any return read:** Flow and RS-MOM (RFA arithmetic), and O1 (RFA withdrawal).

## C. Candidates requiring non-instrument repair

| Item | Defect | Consequence |
|---|---|---|
| **Skew: IV inversion** | Black-76 is called with `F=spot` (raw `equity_bhavcopy` close) and a flat r = 7% (`build_skew.py:33,236,244,271,275`) [E]. When futures trade rich, call prices embed F > S, so calls invert to higher IV and puts to lower. Put−call skew therefore falls mechanically as basis rises, which matches the measured ρ(skew, carry) = −0.63 [I: mechanism fits sign and size, not measured] | The spot rejection tested a basis-contaminated skew. A futures translation would mostly re-derive the basis result. Repair (forward = same-expiry future or a put-call-parity forward) must precede any translation. Repairing a closed construct needs a new pre-registration; this audit does not authorise it |
| **Skew: sign and cost** | No ex-ante sign: TRAIN read the sign ("Sign: NEGATIVE (from TRAIN)"), and the matrix records "no registered sign". The flat 35.2 bp fee is copied from Carry, not modelled [E] | Any successor must pin the sign from the pre-reg hypothesis (steep put skew → lower returns) and use its own cost model |
| **IVOL HOLDOUT boundary** | `run_holdout.py:38` pins `HOLDOUT_HI = 2022-12-31`, the same bound that let the 2022-12-30 formation (return lands Jan 2023) into Carry's and TS Basis's HOLDOUT [E]. IVOL shares Carry's month-end grid, so the same leak is probable [I: formation not counted] | Does not change IVOL's status (SEALED already failed) |
| **All four sleeves: roll cost** | Gates charged futures fees but no T−3 roll cost [E] | Immaterial to the verdicts; recorded for any successor's cost model |
| **Trend: window pin** | Trend's HOLDOUT is pinned 2022-01 → 2023-12 (`trend/run_train.py:34-35`), which overlaps the SSF track's sealed span 2023+ [E] | Unread, so nothing is contaminated; any reuse would cross the track's sealed boundary |
| **DayType / NiftyShield** (not a rejected candidate) | The label horizon (full session) differs from the traded horizon (13:00 → 15:15) (`DAYTYPE_HORIZON_DISCLOSURE.md`) [E] | Horizon repair, carried from the post-mortem, not an instrument issue |
| **DRA** | Source report and code are outside the repo | Reproducibility repair; nothing can be concluded until the artifacts are recovered |

## D. Research inventory correction

**Unit:** one row per construct, 30 previously rejected constructs. PSB and PTMS constructs are
counted individually. The basis family (Carry, TS Basis, TS Basis Daily) is excluded because it
was closed by the post-mortem.

| Bucket | Count | Constructs |
|---|--:|---|
| Rejected correctly on the right instrument, or instrument-free question | **18** | ISD ×2, Analog Path, N200 ×2, RELIANCE, PSB-1 C1–C4, PSB-2 C2–C4, GEX fly, JEV-NMS-1, PTMS ×3 |
| Closed without a return read | **3** | Flow, RS-MOM, O1 |
| Wrong or partial instrument, rejection still stands | **7** | IVOL, Trend, LAG, F1 (all [I]), A-INDEX, pair, CB-N50 |
| **Remain genuinely rejected (sum of the above)** | **28** | |
| Need translation | **0** | |
| Need other repair | **1** | Skew |
| Insufficiently evidenced (among rejected) | **1** | DRA |

**Never rejected and insufficiently evidenced (outside the 30):** PSB-1 C5, MRLC, MSI.

**Corrections to earlier records.**
- **The spot-target error is real for all four signal-engine sleeves**, not only for Carry and
  TS Basis.
- **It overturns none of their rejections.** For IVOL, Trend and LAG this rests on [I]. For Skew
  the prior problem is the signal itself.
- **Skew's record should change.** It was recorded as "TRAIN FAIL, insignificant". It should read
  "TRAIN FAIL on a basis-contaminated construction; not a clean test of option-implied skew." The
  post-mortem's REJECTED entry for Skew now carries a supersession pointer to §C.
- **The post-mortem's P1 said SFB F1 "carries unmeasured convergence exposure."** That still
  holds, but it does not reach F1's target-independent closing grounds.

## E. Smallest next action

**No translation audit is warranted.** No candidate's rejection depends on the instrument mismatch.

The [I] proxy for IVOL, Trend and LAG could be converted into a measurement. That would mean
computing each frozen z's IC against the convergence term with the committed
`carry/futures_translation.py` machinery (TRAIN+HOLDOUT, fenced). But no result could change their
status:
- IVOL's SEALED is spent.
- Trend and LAG failed on spot IC magnitude and sign, and a basis-orthogonal signal cannot move
  far.

So it is optional record-keeping, not a gate.

**Skew's path, if it is ever wanted, is a new pre-registration.** It would start with a repaired
IV forward, a pinned sign, and a TRAIN-only futures-target read with a pre-written kill rule:
futures IC ≥ 0 or |t| < 2 → closed. It is not a reopening of the closed Skew construct, and this
audit does not recommend it.
